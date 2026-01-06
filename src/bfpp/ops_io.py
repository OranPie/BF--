from __future__ import annotations


class IOMixin:
    # ===== Literal / string output helpers =====

    def _decode_string_escapes(self, s: str) -> str:
        out = []
        i = 0
        while i < len(s):
            ch = s[i]
            if ch != '\\':
                out.append(ch)
                i += 1
                continue
            i += 1
            if i >= len(s):
                out.append('\\')
                break
            esc = s[i]
            i += 1
            if esc == 'n':
                out.append('\n')
            elif esc == 'r':
                out.append('\r')
            elif esc == 't':
                out.append('\t')
            elif esc == '0':
                out.append('\x00')
            elif esc == '\\':
                out.append('\\')
            elif esc == '"':
                out.append('"')
            elif esc == 'x' and i + 1 <= len(s):
                hx = s[i:i + 2]
                if len(hx) == 2 and all(c in '0123456789abcdefABCDEF' for c in hx):
                    out.append(chr(int(hx, 16)))
                    i += 2
                else:
                    out.append('x')
            else:
                out.append(esc)
        return ''.join(out)

    def _output_literal(self, token):
        # Output a literal token (string or numeric byte) to stdout.
        temp = self._allocate_temp()
        if token.startswith('"') and token.endswith('"'):
            s = self._decode_string_escapes(token[1:-1])
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

    def _handle_inputint(self, tokens):
        if not tokens:
            raise ValueError("inputint on requires a variable reference")

        var_ref = tokens[0]
        var_info = self._resolve_var(var_ref)
        if var_info['type'] != 'int' or var_info['size'] != 8:
            raise NotImplementedError("inputint currently supports only 8-byte int variables")

        dest = var_info['pos']

        # Temporary cells (bytes)
        c = self._allocate_temp()          # current char
        sign = self._allocate_temp()       # 1 if negative
        value = self._allocate_temp()      # parsed magnitude (0..255)
        stop = self._allocate_temp()       # loop flag
        digit = self._allocate_temp()      # 0..9
        is_digit = self._allocate_temp()   # 1 when digit matched
        tmp = self._allocate_temp()        # general temp
        scratch = self._allocate_temp()    # general temp

        self._generate_clear(sign)
        self._generate_clear(value)
        self._generate_set_value(1, stop)

        # Read first character
        self._move_pointer(c)
        self.bf_code.append(',')

        # Optional leading '-'
        def _consume_minus():
            self._generate_set_value(1, sign)
            self._move_pointer(c)
            self.bf_code.append(',')

        self._generate_if_byte_equals(c, 45, _consume_minus)

        # Parse digits until newline (10) or EOF (0)
        self._move_pointer(stop)
        self.bf_code.append('[')

        def _stop_now():
            self._generate_clear(stop)

        self._generate_if_byte_equals(c, 10, _stop_now)
        self._generate_if_byte_equals(c, 0, _stop_now)

        def _parse_digit_when_running():
            self._generate_clear(digit)
            self._generate_clear(is_digit)

            # Map ASCII '0'..'9' to digit 0..9
            for d in range(10):
                asc = 48 + d

                def _set_d(d=d):
                    self._generate_set_value(d, digit)
                    self._generate_set_value(1, is_digit)

                self._generate_if_byte_equals(c, asc, _set_d)

            def _apply_digit():
                # value = value * 10 + digit
                orig = self._allocate_temp()
                t2 = self._allocate_temp()
                self._generate_clear(t2)
                self._copy_cell(value, orig, t2)

                self._generate_clear(value)
                counter = self._allocate_temp()
                self._generate_set_value(10, counter)
                self._move_pointer(counter)
                self.bf_code.append('[')
                self.bf_code.append('-')
                self._add_cell(orig, value, tmp)
                self._move_pointer(counter)
                self.bf_code.append(']')
                self._free_temp(counter)

                self._add_cell(digit, value, tmp)

                self._free_temp(t2)
                self._free_temp(orig)

            self._generate_if_nonzero(is_digit, _apply_digit)

        self._generate_if_nonzero(stop, _parse_digit_when_running)

        def _read_next():
            self._move_pointer(c)
            self.bf_code.append(',')

        self._generate_if_nonzero(stop, _read_next)

        self._move_pointer(stop)
        self.bf_code.append(']')

        # Store into destination int (little-endian). Clear whole int first.
        for i in range(8):
            self._generate_clear(dest + i)
        self._add_cell(value, dest, tmp)

        # Apply sign (two's complement) if needed.
        def _apply_sign():
            tmp_block = self._allocate_temp(8)
            self._copy_block(dest, tmp_block, 8)
            self._perform_bitwise_not(tmp_block, dest)
            self._free_temp(tmp_block)
            self._increment_multi_byte(dest)

        self._generate_if_nonzero(sign, _apply_sign)

        self._free_temp(scratch)
        self._free_temp(tmp)
        self._free_temp(is_digit)
        self._free_temp(digit)
        self._free_temp(stop)
        self._free_temp(value)
        self._free_temp(sign)
        self._free_temp(c)

    def _handle_inputfloat(self, tokens):
        if not tokens:
            raise ValueError("inputfloat on requires a variable reference")

        var_ref = tokens[0]
        var_info = self._resolve_var(var_ref)
        if var_info['type'] not in ('float', 'float64') or var_info['size'] != 8:
            raise NotImplementedError("inputfloat currently supports only 8-byte float/float64 variables")

        dest = var_info['pos']

        c = self._allocate_temp()
        sign = self._allocate_temp()
        stop = self._allocate_temp()
        int_part = self._allocate_temp()
        frac1 = self._allocate_temp()
        frac2 = self._allocate_temp()
        frac3 = self._allocate_temp()
        digit = self._allocate_temp()
        is_digit = self._allocate_temp()
        tmp = self._allocate_temp()
        scratch = self._allocate_temp()

        low = self._allocate_temp()
        high = self._allocate_temp()

        self._generate_clear(sign)
        self._generate_set_value(1, stop)
        self._generate_clear(int_part)
        self._generate_clear(frac1)
        self._generate_clear(frac2)
        self._generate_clear(frac3)
        self._generate_clear(low)
        self._generate_clear(high)

        self._move_pointer(c)
        self.bf_code.append(',')

        def _consume_minus():
            self._generate_set_value(1, sign)
            self._move_pointer(c)
            self.bf_code.append(',')

        self._generate_if_byte_equals(c, 45, _consume_minus)

        # Parse integer digits until '.' or newline/EOF
        self._move_pointer(stop)
        self.bf_code.append('[')

        def _stop_now():
            self._generate_clear(stop)

        self._generate_if_byte_equals(c, 10, _stop_now)
        self._generate_if_byte_equals(c, 0, _stop_now)

        # If '.' -> stop integer parse but continue to fraction
        def _stop_on_dot():
            self._generate_clear(stop)

        self._generate_if_byte_equals(c, 46, _stop_on_dot)

        def _parse_int_digit():
            self._generate_clear(digit)
            self._generate_clear(is_digit)
            for d in range(10):
                asc = 48 + d

                def _set_d(d=d):
                    self._generate_set_value(d, digit)
                    self._generate_set_value(1, is_digit)

                self._generate_if_byte_equals(c, asc, _set_d)

            def _apply_digit():
                orig = self._allocate_temp()
                t2 = self._allocate_temp()
                self._generate_clear(t2)
                self._copy_cell(int_part, orig, t2)
                self._generate_clear(int_part)
                counter = self._allocate_temp()
                self._generate_set_value(10, counter)
                self._move_pointer(counter)
                self.bf_code.append('[')
                self.bf_code.append('-')
                self._add_cell(orig, int_part, tmp)
                self._move_pointer(counter)
                self.bf_code.append(']')
                self._free_temp(counter)
                self._add_cell(digit, int_part, tmp)
                self._free_temp(t2)
                self._free_temp(orig)

            self._generate_if_nonzero(is_digit, _apply_digit)

        self._generate_if_nonzero(stop, _parse_int_digit)

        def _read_next():
            self._move_pointer(c)
            self.bf_code.append(',')

        self._generate_if_nonzero(stop, _read_next)

        self._move_pointer(stop)
        self.bf_code.append(']')

        # If we stopped on '.', parse up to 3 fractional digits
        def _parse_fraction():
            # c is currently '.'
            self._move_pointer(c)
            self.bf_code.append(',')

            def _read_frac_digit(dst):
                self._generate_clear(digit)
                self._generate_clear(is_digit)
                for d in range(10):
                    asc = 48 + d

                    def _set_d(d=d):
                        self._generate_set_value(d, digit)
                        self._generate_set_value(1, is_digit)

                    self._generate_if_byte_equals(c, asc, _set_d)

                def _store():
                    self._copy_cell(digit, dst, scratch)

                self._generate_if_nonzero(is_digit, _store)

            _read_frac_digit(frac1)
            self._move_pointer(c)
            self.bf_code.append(',')
            _read_frac_digit(frac2)
            self._move_pointer(c)
            self.bf_code.append(',')
            _read_frac_digit(frac3)

        self._generate_if_byte_equals(c, 46, _parse_fraction)

        # Build scaled magnitude into low/high (16-bit) from int_part and frac digits.
        def _inc16():
            self._move_pointer(low)
            self.bf_code.append('+')
            self._generate_if_byte_equals(low, 0, lambda: (self._move_pointer(high), self.bf_code.append('+')))

        def _add_const_n(n):
            cnt = self._allocate_temp()
            self._generate_set_value(n, cnt)
            self._move_pointer(cnt)
            self.bf_code.append('[')
            self.bf_code.append('-')
            _inc16()
            self._move_pointer(cnt)
            self.bf_code.append(']')
            self._free_temp(cnt)

        def _add_1000():
            _add_const_n(232)
            self._move_pointer(high)
            self.bf_code.append('+++')

        # Add int_part * 1000
        counter_int = self._allocate_temp()
        self._generate_clear(scratch)
        self._copy_cell(int_part, counter_int, scratch)
        self._move_pointer(counter_int)
        self.bf_code.append('[')
        self.bf_code.append('-')
        _add_1000()
        self._move_pointer(counter_int)
        self.bf_code.append(']')
        self._free_temp(counter_int)

        # Add frac1*100 + frac2*10 + frac3
        def _add_digit_times(dst_digit, base):
            cnt = self._allocate_temp()
            self._generate_clear(scratch)
            self._copy_cell(dst_digit, cnt, scratch)
            self._move_pointer(cnt)
            self.bf_code.append('[')
            self.bf_code.append('-')
            _add_const_n(base)
            self._move_pointer(cnt)
            self.bf_code.append(']')
            self._free_temp(cnt)

        _add_digit_times(frac1, 100)
        _add_digit_times(frac2, 10)
        _add_digit_times(frac3, 1)

        # Store to destination (8 bytes)
        for i in range(8):
            self._generate_clear(dest + i)

        self._copy_cell(low, dest + 0, scratch)
        self._copy_cell(high, dest + 1, scratch)

        def _apply_sign():
            tmp_block = self._allocate_temp(8)
            self._copy_block(dest, tmp_block, 8)
            self._perform_bitwise_not(tmp_block, dest)
            self._free_temp(tmp_block)
            self._increment_multi_byte(dest)

        self._generate_if_nonzero(sign, _apply_sign)

        self._free_temp(high)
        self._free_temp(low)
        self._free_temp(scratch)
        self._free_temp(tmp)
        self._free_temp(is_digit)
        self._free_temp(digit)
        self._free_temp(frac3)
        self._free_temp(frac2)
        self._free_temp(frac1)
        self._free_temp(int_part)
        self._free_temp(stop)
        self._free_temp(sign)
        self._free_temp(c)

    # ===== I/O Operations =====

    def _handle_move_to(self, tokens):
        """Handle 'move to <var>' command."""
        if tokens:
            self._move_to_var(tokens[0])

    def _handle_print_string(self, tokens):
        if tokens and tokens[0].startswith('"'):
            string_val = self._decode_string_escapes(tokens[0].strip('"'))
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
                elif base_info['type'] in ('float', 'float64'):
                    self._output_float_as_decimal_1000(pos)
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

            if var_info['type'] in ('float', 'float64'):
                if sep_token is None:
                    sep_token = '32'
                for i in range(length):
                    self._output_float_as_decimal_1000(var_info['pos'] + i * elem_size)
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

        elif var_info['type'] in ('float', 'float64'):
            self._output_float_as_decimal_1000(var_info['pos'])
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

    def _output_float_as_decimal_1000(self, pos):
        # R1 printer for scaled values (scale=1000) that fit in low 16 bits.
        msb = pos + 7
        is_neg = self._allocate_temp()
        self._generate_clear(is_neg)
        self._generate_if_byte_equals(msb, 255, lambda: self._generate_set_value(1, is_neg))

        abs_block = self._allocate_temp(8)
        self._copy_block(pos, abs_block, 8)

        def _abs_in_place():
            tmp_block = self._allocate_temp(8)
            self._copy_block(abs_block, tmp_block, 8)
            self._perform_bitwise_not(tmp_block, abs_block)
            self._free_temp(tmp_block)
            self._increment_multi_byte(abs_block)

        self._generate_if_nonzero(is_neg, lambda: (self._output_literal('"-"'), _abs_in_place()))

        low = self._allocate_temp()
        high = self._allocate_temp()
        scratch = self._allocate_temp()
        self._generate_clear(scratch)
        self._generate_clear(low)
        self._generate_clear(high)
        self._copy_cell(abs_block + 0, low, scratch)
        self._copy_cell(abs_block + 1, high, scratch)

        def _low_ge_n_flag(n: int, out_flag):
            self._generate_clear(out_flag)
            for v in range(n, 256):
                self._generate_if_byte_equals(low, v, lambda: self._generate_set_value(1, out_flag))

        def _ge1000_flag(out_flag):
            # value >= 1000 <=> high >= 4 OR (high==3 AND low>=232)
            self._generate_clear(out_flag)
            high_ge4 = self._allocate_temp()
            self._generate_set_value(1, high_ge4)
            for v in (0, 1, 2, 3):
                self._generate_if_byte_equals(high, v, lambda: self._generate_clear(high_ge4))
            self._generate_if_nonzero(high_ge4, lambda: self._generate_set_value(1, out_flag))

            high_eq3 = self._allocate_temp()
            self._generate_clear(high_eq3)
            self._generate_if_byte_equals(high, 3, lambda: self._generate_set_value(1, high_eq3))
            low_ge232 = self._allocate_temp()
            self._generate_clear(low_ge232)
            for v in range(232, 256):
                self._generate_if_byte_equals(low, v, lambda: self._generate_set_value(1, low_ge232))
            self._generate_if_nonzero(high_eq3, lambda: self._generate_if_nonzero(low_ge232, lambda: self._generate_set_value(1, out_flag)))

            self._free_temp(low_ge232)
            self._free_temp(high_eq3)
            self._free_temp(high_ge4)

        def _sub_1000():
            low_ge232 = self._allocate_temp()
            self._generate_clear(low_ge232)
            for v in range(232, 256):
                self._generate_if_byte_equals(low, v, lambda: self._generate_set_value(1, low_ge232))

            def _sub_ge():
                cnt = self._allocate_temp()
                self._generate_set_value(232, cnt)
                self._move_pointer(cnt)
                self.bf_code.append('[')
                self.bf_code.append('-')
                self._move_pointer(low)
                self.bf_code.append('-')
                self._move_pointer(cnt)
                self.bf_code.append(']')
                self._free_temp(cnt)
                self._move_pointer(high)
                self.bf_code.append('---')

            def _sub_lt():
                self._move_pointer(low)
                self.bf_code.append('+' * 24)
                self._move_pointer(high)
                self.bf_code.append('----')

            self._generate_if_nonzero(low_ge232, _sub_ge)
            inv = self._allocate_temp()
            self._generate_set_value(1, inv)
            self._move_pointer(low_ge232)
            self.bf_code.append('[')
            self._move_pointer(inv)
            self.bf_code.append('-')
            self._generate_clear(low_ge232)
            self.bf_code.append(']')
            self._generate_if_nonzero(inv, _sub_lt)
            self._free_temp(inv)
            self._free_temp(low_ge232)

        int_part = self._allocate_temp()
        self._generate_clear(int_part)
        ge1000 = self._allocate_temp()
        _ge1000_flag(ge1000)
        self._move_pointer(ge1000)
        self.bf_code.append('[')
        self._move_pointer(int_part)
        self.bf_code.append('+')
        _sub_1000()
        self._generate_clear(ge1000)
        _ge1000_flag(ge1000)
        self._move_pointer(ge1000)
        self.bf_code.append(']')
        self._free_temp(ge1000)

        tmp_int = self._allocate_temp(8)
        for i in range(8):
            self._generate_clear(tmp_int + i)
        self._copy_cell(int_part, tmp_int, scratch)
        self._output_int_as_decimal(tmp_int)
        self._free_temp(tmp_int)

        self._output_literal('"."')

        # remainder is now in (high, low), < 1000
        hundreds = self._allocate_temp()
        tens = self._allocate_temp()
        ones = self._allocate_temp()
        self._generate_clear(hundreds)
        self._generate_clear(tens)
        self._generate_clear(ones)

        def _emit_digit(dpos):
            out = self._allocate_temp()
            tmpd = self._allocate_temp()
            scr2 = self._allocate_temp()
            self._generate_set_value(48, out)
            self._generate_clear(scr2)
            self._copy_cell(dpos, tmpd, scr2)
            self._move_pointer(tmpd)
            self.bf_code.append('[')
            self._move_pointer(out)
            self.bf_code.append('+')
            self._move_pointer(tmpd)
            self.bf_code.append('-]')
            self._move_pointer(out)
            self.bf_code.append('.')
            self._generate_clear(out)
            self._free_temp(scr2)
            self._free_temp(tmpd)
            self._free_temp(out)

        # hundreds: while rem >= 100
        ge100 = self._allocate_temp()
        self._generate_clear(ge100)
        self._generate_if_nonzero(high, lambda: self._generate_set_value(1, ge100))
        low_ge100 = self._allocate_temp()
        _low_ge_n_flag(100, low_ge100)
        inv_high = self._allocate_temp()
        self._generate_set_value(1, inv_high)
        self._generate_if_nonzero(high, lambda: self._generate_clear(inv_high))
        self._generate_if_nonzero(inv_high, lambda: self._generate_if_nonzero(low_ge100, lambda: self._generate_set_value(1, ge100)))
        self._free_temp(inv_high)
        self._free_temp(low_ge100)

        self._move_pointer(ge100)
        self.bf_code.append('[')
        self._move_pointer(hundreds)
        self.bf_code.append('+')
        # subtract 100 from 16-bit
        low_ge100 = self._allocate_temp()
        _low_ge_n_flag(100, low_ge100)
        def _sub100_ge():
            self._move_pointer(low)
            self.bf_code.append('-' * 100)
        def _sub100_lt():
            self._move_pointer(low)
            self.bf_code.append('+' * 156)
            self._move_pointer(high)
            self.bf_code.append('-')
        self._generate_if_nonzero(low_ge100, _sub100_ge)
        inv = self._allocate_temp()
        self._generate_set_value(1, inv)
        self._move_pointer(low_ge100)
        self.bf_code.append('[')
        self._move_pointer(inv)
        self.bf_code.append('-')
        self._generate_clear(low_ge100)
        self.bf_code.append(']')
        self._generate_if_nonzero(inv, _sub100_lt)
        self._free_temp(inv)
        self._free_temp(low_ge100)

        self._generate_clear(ge100)
        self._generate_if_nonzero(high, lambda: self._generate_set_value(1, ge100))
        low_ge100 = self._allocate_temp()
        _low_ge_n_flag(100, low_ge100)
        inv_high2 = self._allocate_temp()
        self._generate_set_value(1, inv_high2)
        self._generate_if_nonzero(high, lambda: self._generate_clear(inv_high2))
        self._generate_if_nonzero(inv_high2, lambda: self._generate_if_nonzero(low_ge100, lambda: self._generate_set_value(1, ge100)))
        self._free_temp(inv_high2)
        self._free_temp(low_ge100)
        self._move_pointer(ge100)
        self.bf_code.append(']')
        self._free_temp(ge100)

        # tens: while low >= 10 (high should be 0 now)
        ge10 = self._allocate_temp()
        _low_ge_n_flag(10, ge10)
        self._move_pointer(ge10)
        self.bf_code.append('[')
        self._move_pointer(tens)
        self.bf_code.append('+')
        self._move_pointer(low)
        self.bf_code.append('-' * 10)
        self._generate_clear(ge10)
        _low_ge_n_flag(10, ge10)
        self._move_pointer(ge10)
        self.bf_code.append(']')
        self._free_temp(ge10)

        self._generate_clear(scratch)
        self._copy_cell(low, ones, scratch)

        _emit_digit(hundreds)
        _emit_digit(tens)
        _emit_digit(ones)

        self._free_temp(ones)
        self._free_temp(tens)
        self._free_temp(hundreds)
        self._free_temp(int_part)
        self._free_temp(scratch)
        self._free_temp(high)
        self._free_temp(low)
        self._free_temp(abs_block)
        self._free_temp(is_neg)
