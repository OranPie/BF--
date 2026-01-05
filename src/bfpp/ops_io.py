from __future__ import annotations


class IOMixin:
    # ===== Literal / string output helpers =====

    def _output_literal(self, token):
        # Output a literal token (string or numeric byte) to stdout.
        temp = self._allocate_temp()
        if token.startswith('"') and token.endswith('"'):
            s = token[1:-1]
            for ch in s:
                self._generate_set_value(ord(ch), temp)
                self.bf_code.append('.')
                self._generate_clear(temp)
        else:
            self._generate_set_value(int(token), temp)
            self.bf_code.append('.')
            self._generate_clear(temp)
        self._free_temp(temp)

    def _output_string_until_null_deterministic(self, pos, size):
        # Deterministic pointer-safe string output (max length = size-1)
        stop = self._allocate_temp()
        gate = self._allocate_temp()
        char_tmp = self._allocate_temp()
        scratch = self._allocate_temp()
        is_zero = self._allocate_temp()

        self._generate_set_value(1, stop)

        for i in range(size):
            # gate = stop
            gate_scratch = self._allocate_temp()
            self._copy_cell(stop, gate, gate_scratch)
            self._free_temp(gate_scratch)

            self._move_pointer(gate)
            self.bf_code.append('[')
            # char_tmp = s[i]
            self._copy_cell(pos + i, char_tmp, scratch)

            self._generate_set_value(1, is_zero)
            self._move_pointer(char_tmp)
            self.bf_code.append('[')
            # non-zero: clear is_zero, output char, clear char_tmp
            self._generate_clear(is_zero)
            self._move_pointer(pos + i)
            self.bf_code.append('.')
            self._generate_clear(char_tmp)
            self.bf_code.append(']')

            # if is_zero still 1 => stop = 0
            self._move_pointer(is_zero)
            self.bf_code.append('[')
            self._generate_clear(stop)
            self._generate_clear(is_zero)
            self.bf_code.append(']')

            # clear gate to exit
            self._generate_clear(gate)
            self.bf_code.append(']')

        self._free_temp(is_zero)
        self._free_temp(scratch)
        self._free_temp(char_tmp)
        self._free_temp(gate)
        self._free_temp(stop)

    # ===== Input =====

    def _input_string_at_pos(self, pos, size):
        # Read up to size-1 chars, stop at newline (10) or EOF (0). Ensure null terminator.
        stop = self._allocate_temp()
        self._generate_set_value(1, stop)

        for i in range(size - 1):
            def _read_char(i=i):
                self._move_pointer(pos + i)
                self.bf_code.append(',')

                def _nl_body():
                    self._generate_clear(pos + i)
                    self._generate_clear(stop)

                self._generate_if_byte_equals(pos + i, 10, _nl_body)

                def _eof_body():
                    self._generate_clear(pos + i)
                    self._generate_clear(stop)

                self._generate_if_byte_equals(pos + i, 0, _eof_body)

            self._generate_if_nonzero(stop, _read_char)

        self._generate_clear(pos + size - 1)
        self._free_temp(stop)

    def _handle_input(self, tokens):
        if not tokens:
            raise ValueError("input on requires a variable reference")

        var_ref = tokens[0]
        runtime = self._split_runtime_subscript_ref(var_ref)
        if runtime is not None:
            base_name, idx_var = runtime
            base_info = self._resolve_var(base_name)
            if not (base_info.get('is_array') or base_info.get('is_dict')):
                raise ValueError("Runtime subscript target must be array or dict")

            def _slot_in(pos, slot):
                if base_info['type'] in ('byte', 'char'):
                    self._move_pointer(pos)
                    self.bf_code.append(',')
                elif base_info['type'] == 'int':
                    for j in range(8):
                        self._generate_clear(pos + j)
                    self._move_pointer(pos)
                    self.bf_code.append(',')
                elif base_info['type'] == 'string':
                    self._input_string_at_pos(pos, base_info['elem_size'])
                else:
                    raise NotImplementedError(
                        f"input on not implemented for runtime collection type {base_info['type']}"
                    )

            self._apply_runtime_subscript_op(base_info, idx_var, _slot_in)
            return

        var_info = self._resolve_var(var_ref)
        if var_info['type'] in ('byte', 'char'):
            self._move_pointer(var_info['pos'])
            self.bf_code.append(',')
            return

        if var_info['type'] == 'int':
            for i in range(8):
                self._generate_clear(var_info['pos'] + i)
            self._move_pointer(var_info['pos'])
            self.bf_code.append(',')
            return

        if var_info['type'] == 'string':
            self._input_string_at_pos(var_info['pos'], var_info['size'])
            return

        raise NotImplementedError(f"input on not implemented for type {var_info['type']}")

    # ===== I/O Operations =====

    def _handle_move_to(self, tokens):
        """Handle 'move to <var>' command."""
        if tokens:
            self._move_to_var(tokens[0])

    def _handle_print_string(self, tokens):
        if tokens and tokens[0].startswith('"'):
            string_val = tokens[0].strip('"')
            temp = self._allocate_temp()

            for char in string_val:
                self._generate_set_value(ord(char), temp)
                self.bf_code.append('.')
                self._generate_clear(temp)

            self._free_temp(temp)

    def _handle_varout(self, tokens):
        if not tokens:
            raise ValueError("varout requires variable name")

        var_name = tokens[0]

        sep_token = None
        end_token = None
        j = 1
        while j < len(tokens):
            if tokens[j] == 'sep' and j + 1 < len(tokens):
                sep_token = tokens[j + 1]
                j += 2
                continue
            if tokens[j] == 'end' and j + 1 < len(tokens):
                end_token = tokens[j + 1]
                j += 2
                continue
            raise ValueError(f"Invalid varout arguments: {' '.join(tokens[1:])}")

        runtime = self._split_runtime_subscript_ref(var_name)
        if runtime is not None:
            base_name, idx_var = runtime
            base_info = self._resolve_var(base_name)
            if not (base_info.get('is_array') or base_info.get('is_dict')):
                raise ValueError("Runtime subscript target must be array or dict")

            def _slot_out(pos, slot):
                if base_info['type'] in ('byte', 'char'):
                    self._move_pointer(pos)
                    self.bf_code.append('.')
                elif base_info['type'] == 'int':
                    self._output_int_as_decimal(pos)
                elif base_info['type'] == 'string':
                    self._output_string_until_null_deterministic(pos, base_info['elem_size'])
                else:
                    raise NotImplementedError(
                        f"varout not implemented for runtime collection type {base_info['type']}"
                    )

            self._apply_runtime_subscript_op(base_info, idx_var, _slot_out)
            if end_token is not None:
                self._output_literal(end_token)
            return

        var_info = self._resolve_var(var_name)

        if var_info.get('is_array') or var_info.get('is_dict'):
            length = var_info.get('length', 1)
            elem_size = var_info.get('elem_size', 1)

            if var_info['type'] in ['byte', 'char']:
                for i in range(length):
                    self._move_pointer(var_info['pos'] + i * elem_size)
                    self.bf_code.append('.')
                    if sep_token is not None and i != length - 1:
                        self._output_literal(sep_token)
                if end_token is not None:
                    self._output_literal(end_token)
                return

            if var_info['type'] == 'int':
                if sep_token is None:
                    sep_token = '32'
                for i in range(length):
                    self._output_int_as_decimal(var_info['pos'] + i * elem_size)
                    if i != length - 1 and sep_token is not None:
                        self._output_literal(sep_token)
                if end_token is not None:
                    self._output_literal(end_token)
                return

            if var_info['type'] == 'string':
                if sep_token is None:
                    sep_token = None
                for i in range(length):
                    self._output_string_until_null_deterministic(var_info['pos'] + i * elem_size, elem_size)
                    if sep_token is not None and i != length - 1:
                        self._output_literal(sep_token)
                if end_token is not None:
                    self._output_literal(end_token)
                return

            raise NotImplementedError(f"varout not implemented for collection of type {var_info['type']}")

        if var_info['type'] in ['string', 'varstring']:
            self._output_string_until_null_deterministic(var_info['pos'], var_info['size'])
            if end_token is not None:
                self._output_literal(end_token)

        elif var_info['type'] == 'int':
            self._output_int_as_decimal(var_info['pos'])
            if end_token is not None:
                self._output_literal(end_token)

        elif var_info['type'] in ['byte', 'char']:
            self._move_to_var(var_name)
            self.bf_code.append('.')
            if end_token is not None:
                self._output_literal(end_token)

        else:
            raise NotImplementedError(f"varout not implemented for type {var_info['type']}")

    def _output_int_as_decimal(self, pos):
        # Deterministic small-int output for debugging.
        msb = pos + 7
        is_neg = self._allocate_temp()
        self._generate_clear(is_neg)
        self._generate_if_byte_equals(msb, 255, lambda: self._generate_set_value(1, is_neg))

        mag = self._allocate_temp()
        scratch = self._allocate_temp()
        self._generate_clear(scratch)
        self._generate_clear(mag)

        def _set_mag_positive():
            self._copy_cell(pos, mag, scratch)

        def _set_mag_negative_and_print_sign():
            self._output_literal('"-"')
            tmp = self._allocate_temp()
            self._copy_cell(pos, tmp, scratch)
            self._move_pointer(tmp)
            self.bf_code.append('[')
            self._move_pointer(mag)
            self.bf_code.append('-')
            self._move_pointer(tmp)
            self.bf_code.append('-]')
            self._free_temp(tmp)

        self._generate_if_nonzero(is_neg, _set_mag_negative_and_print_sign)

        inv_neg = self._allocate_temp()
        self._generate_set_value(1, inv_neg)
        self._move_pointer(is_neg)
        self.bf_code.append('[')
        self._move_pointer(inv_neg)
        self.bf_code.append('-')
        self._move_pointer(is_neg)
        self.bf_code.append('-]')
        self._move_pointer(inv_neg)
        self.bf_code.append('[')
        _set_mag_positive()
        self._generate_clear(inv_neg)
        self.bf_code.append(']')
        self._free_temp(inv_neg)

        counter = self._allocate_temp()
        self._generate_clear(scratch)
        self._copy_cell(mag, counter, scratch)

        ones = self._allocate_temp()
        tens = self._allocate_temp()
        hundreds = self._allocate_temp()
        self._generate_clear(ones)
        self._generate_clear(tens)
        self._generate_clear(hundreds)

        self._move_pointer(counter)
        self.bf_code.append('[')
        self.bf_code.append('-')

        self._move_pointer(ones)
        self.bf_code.append('+')

        def _roll_tens():
            self._generate_clear(tens)
            self._move_pointer(hundreds)
            self.bf_code.append('+')

        def _roll_ones():
            self._generate_clear(ones)
            self._move_pointer(tens)
            self.bf_code.append('+')
            self._generate_if_byte_equals(tens, 10, _roll_tens)

        self._generate_if_byte_equals(ones, 10, _roll_ones)

        self._move_pointer(counter)
        self.bf_code.append(']')

        out = self._allocate_temp()
        tmp = self._allocate_temp()

        def _emit_digit(dpos):
            self._generate_set_value(48, out)
            scr2 = self._allocate_temp()
            self._generate_clear(scr2)
            self._copy_cell(dpos, tmp, scr2)
            self._move_pointer(tmp)
            self.bf_code.append('[')
            self._move_pointer(out)
            self.bf_code.append('+')
            self._move_pointer(tmp)
            self.bf_code.append('-]')
            self._move_pointer(out)
            self.bf_code.append('.')
            self._generate_clear(out)
            self._free_temp(scr2)

        started = self._allocate_temp()
        self._generate_clear(started)

        def _start_and_emit_hundreds():
            _emit_digit(hundreds)
            self._generate_set_value(1, started)

        def _start_and_emit_tens():
            _emit_digit(tens)
            self._generate_set_value(1, started)

        self._generate_if_nonzero(hundreds, _start_and_emit_hundreds)

        def _emit_tens_when_started():
            _emit_digit(tens)

        self._generate_if_nonzero(started, _emit_tens_when_started)

        inv_started = self._allocate_temp()
        self._generate_set_value(1, inv_started)
        self._move_pointer(started)
        self.bf_code.append('[')
        self._move_pointer(inv_started)
        self.bf_code.append('-')
        self._move_pointer(started)
        self.bf_code.append('-]')
        self._move_pointer(inv_started)
        self.bf_code.append('[')
        self._generate_if_nonzero(tens, _start_and_emit_tens)
        self._generate_clear(inv_started)
        self.bf_code.append(']')
        self._free_temp(inv_started)

        _emit_digit(ones)

        self._free_temp(started)
        self._free_temp(tmp)
        self._free_temp(out)
        self._free_temp(hundreds)
        self._free_temp(tens)
        self._free_temp(ones)
        self._free_temp(counter)
        self._free_temp(scratch)
        self._free_temp(mag)
        self._free_temp(is_neg)
