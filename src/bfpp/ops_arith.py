from __future__ import annotations


class ArithOpsMixin:
    def _handle_expression_assignment(self, expr_tokens, dest_var):
        """Handle arithmetic and bitwise expression assignment."""
        dest_info = self._resolve_var(dest_var)

        if dest_info['type'] not in ('int', 'int16', 'int64', 'float', 'float64'):
            raise NotImplementedError("Expressions only supported for integer and float types")

        left, op, right = self._parse_expression(expr_tokens)
        dest_size = dest_info['size']

        def _sign_extend_16(tmp16_pos):
            flag = self._allocate_temp()
            self._generate_clear(flag)
            for v in range(128, 256):
                self._generate_if_byte_equals(tmp16_pos + 1, v, lambda: self._generate_set_value(1, flag))
            for i in range(2, 8):
                self._generate_clear(tmp16_pos + i)
            def _fill_ff():
                for i in range(2, 8):
                    self._generate_set_value(255, tmp16_pos + i)
            self._generate_if_nonzero(flag, _fill_ff)
            self._free_temp(flag)

        def _add_1000_to_16(lo, hi):
            # +1000 == +232 to low, +3 to high (with carry in low naturally wrapping)
            cnt = self._allocate_temp()
            self._generate_set_value(232, cnt)
            self._move_pointer(cnt)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(lo)
            self.bf_code.append('+')
            self._generate_if_byte_equals(lo, 0, lambda: (self._move_pointer(hi), self.bf_code.append('+')))
            self._move_pointer(cnt)
            self.bf_code.append(']')
            self._free_temp(cnt)
            self._move_pointer(hi)
            self.bf_code.append('+++')

        def _scale_int_byte_to_float16(src_pos, dst_pos):
            # dst_pos is 8 bytes; uses only low two bytes for scaled
            scratch = self._allocate_temp()
            counter = self._allocate_temp()
            self._generate_clear(scratch)
            self._generate_clear(counter)
            self._copy_cell(src_pos, counter, scratch)
            for i in range(8):
                self._generate_clear(dst_pos + i)

            self._move_pointer(counter)
            self.bf_code.append('[')
            self.bf_code.append('-')
            _add_1000_to_16(dst_pos + 0, dst_pos + 1)
            self._move_pointer(counter)
            self.bf_code.append(']')
            _sign_extend_16(dst_pos)
            self._free_temp(counter)
            self._free_temp(scratch)

        def _load_operand_float_scaled(operand, target_pos):
            # Load into target_pos (8 bytes). Produces signed 16-bit scaled in bytes 0..1 with sign-extension.
            opnd = operand[1:] if operand.startswith('$') else operand
            runtime = self._split_runtime_subscript_ref(opnd)
            if runtime is not None:
                base_name, idx_var = runtime
                base_info = self._resolve_var(base_name)
                if base_info['type'] not in ('float', 'float64') or base_info.get('elem_size', 8) != 8:
                    raise NotImplementedError("Runtime-subscript float operands support only float/float64")
                self._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, 8)
                return

            if operand.startswith('$'):
                info = self._resolve_var(operand)
                if info['type'] in ('float', 'float64'):
                    self._copy_block(info['pos'], target_pos, 8)
                    return
                if info['type'] == 'int':
                    # Scale from int LSB only (current int runtime is effectively 1-byte for I/O)
                    _scale_int_byte_to_float16(info['pos'], target_pos)
                    return
                if info['type'] in ('byte', 'char'):
                    _scale_int_byte_to_float16(info['pos'], target_pos)
                    return
                raise NotImplementedError("Unsupported source type for float conversion")

            # literal
            if '.' in operand:
                value = int(self._parse_float_literal_scaled(operand))
            else:
                value = int(operand) * 1000
            b = int(value).to_bytes(2, 'little', signed=True)
            for i in range(8):
                self._generate_clear(target_pos + i)
            self._generate_set_value(b[0], target_pos + 0)
            self._generate_set_value(b[1], target_pos + 1)
            _sign_extend_16(target_pos)

        def _add_u16(a_pos, b_pos, res_pos):
            # res = a + b over 16-bit (two's complement); operands are 8-byte, low/high used.
            tmp_a0 = self._allocate_temp()
            tmp_a1 = self._allocate_temp()
            tmp_b0 = self._allocate_temp()
            tmp_b1 = self._allocate_temp()
            scratch = self._allocate_temp()
            self._generate_clear(scratch)

            self._copy_cell(a_pos + 0, res_pos + 0, scratch)
            self._copy_cell(a_pos + 1, res_pos + 1, scratch)

            self._generate_clear(tmp_a0)
            self._generate_clear(tmp_a1)
            self._generate_clear(tmp_b0)
            self._generate_clear(tmp_b1)
            self._copy_cell(b_pos + 0, tmp_b0, scratch)
            self._copy_cell(b_pos + 1, tmp_b1, scratch)

            # add low byte with carry into high
            self._move_pointer(tmp_b0)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(res_pos + 0)
            self.bf_code.append('+')
            self._generate_if_byte_equals(res_pos + 0, 0, lambda: (self._move_pointer(res_pos + 1), self.bf_code.append('+')))
            self._move_pointer(tmp_b0)
            self.bf_code.append(']')

            # add high byte
            self._move_pointer(tmp_b1)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(res_pos + 1)
            self.bf_code.append('+')
            self._move_pointer(tmp_b1)
            self.bf_code.append(']')

            _sign_extend_16(res_pos)
            self._free_temp(scratch)
            self._free_temp(tmp_b1)
            self._free_temp(tmp_b0)
            self._free_temp(tmp_a1)
            self._free_temp(tmp_a0)

        def _sub_u16(a_pos, b_pos, res_pos):
            # res = a - b over 16-bit; operands 8-byte, low/high used.
            tmp_b0 = self._allocate_temp()
            tmp_b1 = self._allocate_temp()
            scratch = self._allocate_temp()
            self._generate_clear(scratch)

            self._copy_cell(a_pos + 0, res_pos + 0, scratch)
            self._copy_cell(a_pos + 1, res_pos + 1, scratch)

            self._generate_clear(tmp_b0)
            self._generate_clear(tmp_b1)
            self._copy_cell(b_pos + 0, tmp_b0, scratch)
            self._copy_cell(b_pos + 1, tmp_b1, scratch)

            # subtract low with borrow
            self._move_pointer(tmp_b0)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(res_pos + 0)
            self.bf_code.append('-')
            self._generate_if_byte_equals(res_pos + 0, 255, lambda: (self._move_pointer(res_pos + 1), self.bf_code.append('-')))
            self._move_pointer(tmp_b0)
            self.bf_code.append(']')

            # subtract high
            self._move_pointer(tmp_b1)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(res_pos + 1)
            self.bf_code.append('-')
            self._move_pointer(tmp_b1)
            self.bf_code.append(']')

            _sign_extend_16(res_pos)
            self._free_temp(scratch)
            self._free_temp(tmp_b1)
            self._free_temp(tmp_b0)

        if dest_info['type'] in ('float', 'float64'):
            # ... (float logic kept as is for now, it already assumes 8-byte scaled)
            if op in ('*', '/', '%', '&', '|', '^', '~'):
                raise NotImplementedError("Float expressions currently support only + and -")

            temp_left = self._allocate_temp(8)
            temp_right = self._allocate_temp(8)
            for i in range(8):
                self._generate_clear(temp_left + i)
                self._generate_clear(temp_right + i)
            _load_operand_float_scaled(left, temp_left)

            if op is None and right is None:
                self._copy_block(temp_left, dest_info['pos'], 8)
                self._free_temp(temp_right)
                self._free_temp(temp_left)
                return

            _load_operand_float_scaled(right, temp_right)
            if op == '+':
                _add_u16(temp_left, temp_right, dest_info['pos'])
            elif op == '-':
                _sub_u16(temp_left, temp_right, dest_info['pos'])
            else:
                raise NotImplementedError("Float expressions currently support only + and -")

            self._free_temp(temp_right)
            self._free_temp(temp_left)
            return

        # Handle conversions for integer destinations
        if dest_info['type'] in ('int', 'int16', 'int64') and op is None and right is None:
            if not left.startswith('$'):
                # literal assignment - handled by VarsOpsMixin usually, but here if called
                val = int(left)
                byte_values = val.to_bytes(dest_size, 'little', signed=True)
                for i, b in enumerate(byte_values):
                    self._generate_set_value(b, dest_info['pos'] + i)
                return

            src_info = self._resolve_var(left)
            if src_info['type'] in ('float', 'float64'):
                # Float -> Int conversion (scale down by 1000)
                low = self._allocate_temp()
                high = self._allocate_temp()
                scratch = self._allocate_temp()
                self._generate_clear(scratch)
                self._generate_clear(low)
                self._generate_clear(high)
                self._copy_cell(src_info['pos'] + 0, low, scratch)
                self._copy_cell(src_info['pos'] + 1, high, scratch)

                int_part = self._allocate_temp()
                self._generate_clear(int_part)

                def _ge1000_flag(out_flag):
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
                    for vv in range(232, 256):
                        self._generate_if_byte_equals(low, vv, lambda: self._generate_set_value(1, low_ge232))
                    self._generate_if_nonzero(high_eq3, lambda: self._generate_if_nonzero(low_ge232, lambda: self._generate_set_value(1, out_flag)))
                    self._free_temp(low_ge232)
                    self._free_temp(high_eq3)
                    self._free_temp(high_ge4)

                def _sub_1000():
                    low_ge232 = self._allocate_temp()
                    self._generate_clear(low_ge232)
                    for vv in range(232, 256):
                        self._generate_if_byte_equals(low, vv, lambda: self._generate_set_value(1, low_ge232))
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

                for i in range(dest_size):
                    self._generate_clear(dest_info['pos'] + i)
                self._copy_cell(int_part, dest_info['pos'], scratch)

                self._free_temp(int_part)
                self._free_temp(scratch)
                self._free_temp(high)
                self._free_temp(low)
                return

            # Integer -> Integer copy/conversion
            src_size = src_info['size']
            if src_size == dest_size:
                self._copy_block(src_info['pos'], dest_info['pos'], dest_size)
            elif src_size < dest_size:
                # Widen (zero-extend for now as sign-extension is complex for arbitrary sizes)
                self._copy_block(src_info['pos'], dest_info['pos'], src_size)
                for i in range(src_size, dest_size):
                    self._generate_clear(dest_info['pos'] + i)
            else:
                # Narrow (truncate)
                self._copy_block(src_info['pos'], dest_info['pos'], dest_size)
            return

        if op == '~':
            temp_operand = self._allocate_temp(dest_size)
            self._load_operand(left, temp_operand, size=dest_size)
            self._perform_bitwise_not(temp_operand, dest_info['pos'], size=dest_size)
            self._free_temp(temp_operand)
            return

        # Binary operations for integers
        temp_left = self._allocate_temp(dest_size)
        temp_right = self._allocate_temp(dest_size)

        self._load_operand(left, temp_left, size=dest_size)
        self._load_operand(right, temp_right, size=dest_size)

        if op == '&':
            self._perform_bitwise_and(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '|':
            self._perform_bitwise_or(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '^':
            self._perform_bitwise_xor(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '+':
            self._perform_add(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '-':
            self._perform_sub(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '*':
            if dest_size != 8:
                raise NotImplementedError("Multiplication only supported for 8-byte integers currently")
            self._perform_mul(temp_left, temp_right, dest_info['pos'])
        elif op == '/':
            if dest_size != 8:
                raise NotImplementedError("Division only supported for 8-byte integers currently")
            self._perform_div(temp_left, temp_right, dest_info['pos'])
        elif op == '%':
            if dest_size != 8:
                raise NotImplementedError("Modulo only supported for 8-byte integers currently")
            self._perform_mod(temp_left, temp_right, dest_info['pos'])
        else:
            raise NotImplementedError(f"Operator '{op}' not implemented")

        self._free_temp(temp_right)
        self._free_temp(temp_left)

    def _parse_expression(self, tokens):
        """Parse expression tokens into operands and operator."""
        if len(tokens) >= 2 and tokens[0] == '~':
            return tokens[1], '~', None
        elif len(tokens) == 3:
            return tokens[0], tokens[1], tokens[2]
        elif len(tokens) == 1:
            return tokens[0], None, None
        else:
            raise ValueError(f"Cannot parse expression: {' '.join(tokens)}")

    def _load_operand(self, operand, target_pos, size=8):
        """Load a variable or literal into memory position."""
        op = operand[1:] if operand.startswith('$') else operand
        runtime = self._split_runtime_subscript_ref(op)
        if runtime is not None:
            base_name, idx_var = runtime
            base_info = self._resolve_var(base_name)
            if base_info['type'] not in ('int', 'int16', 'int64') or base_info.get('elem_size', 8) != size:
                raise NotImplementedError(f"Runtime-subscripted expression operands currently support only {size}-byte int elements")
            self._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, size)
            return

        if operand.startswith('$'):
            var_info = self._resolve_var(operand)
            if var_info['type'] not in ('int', 'int16', 'int64') or var_info['size'] != size:
                raise NotImplementedError(f"Expression operands currently support only {size}-byte int variables")
            self._copy_block(var_info['pos'], target_pos, size)
            return

        value = int(operand)
        byte_values = value.to_bytes(size, 'little', signed=True)
        for i, byte_val in enumerate(byte_values):
            self._generate_set_value(byte_val, pos=target_pos + i)

    def _perform_bitwise_and(self, pos_a, pos_b, pos_result, size=8):
        """Perform bytewise AND on two multi-byte integers."""
        for i in range(size):
            self._bitwise_byte_operation('and', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_or(self, pos_a, pos_b, pos_result, size=8):
        """Perform bytewise OR on two multi-byte integers."""
        for i in range(size):
            self._bitwise_byte_operation('or', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_xor(self, pos_a, pos_b, pos_result, size=8):
        """Perform bytewise XOR on two multi-byte integers."""
        for i in range(size):
            self._bitwise_byte_operation('xor', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_not(self, pos_in, pos_result, size=8):
        """
        Perform bytewise NOT (255 - value) on multi-byte integer.
        """
        temp_in = self._allocate_temp(size)
        self._copy_block(pos_in, temp_in, size)

        for i in range(size):
            self._generate_set_value(255, pos=pos_result + i)
            # Subtract temp_in[i] from result[i]
            self._move_pointer(temp_in + i)
            self.bf_code.append('[')
            self._move_pointer(pos_result + i)
            self.bf_code.append('-')
            self._move_pointer(temp_in + i)
            self.bf_code.append('-]')
            self._move_pointer(pos_result + i)

        self._free_temp(temp_in)

    def _perform_add(self, pos_a, pos_b, pos_result, size=8):
        """Robust and correct multi-byte addition."""
        # 1. Initialize result with A
        self._copy_block(pos_a, pos_result, size)
        
        # 2. Add B byte-by-byte with carry propagation
        # We use a temporary copy of B to avoid destroying it
        temp_b = self._allocate_temp(size)
        self._copy_block(pos_b, temp_b, size)
        
        for i in range(size):
            # For each byte of B, repeatedly increment result with carry
            self._move_pointer(temp_b + i)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._increment_multi_byte(pos_result + i, size=size - i)
            self._move_pointer(temp_b + i)
            self.bf_code.append(']')
            
        self._free_temp(temp_b)

    def _perform_sub(self, pos_a, pos_b, pos_result, size=8):
        """Robust and correct multi-byte subtraction."""
        # 1. Initialize result with A
        self._copy_block(pos_a, pos_result, size)
        
        # 2. Subtract B byte-by-byte with borrow propagation
        temp_b = self._allocate_temp(size)
        self._copy_block(pos_b, temp_b, size)
        
        for i in range(size):
            # For each byte of B, repeatedly decrement result with borrow
            self._move_pointer(temp_b + i)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._decrement_multi_byte(pos_result + i, size=size - i)
            self._move_pointer(temp_b + i)
            self.bf_code.append(']')
            
        self._free_temp(temp_b)

    def _perform_mul(self, pos_a, pos_b, pos_result):
        """Perform multiplication using repeated addition (simplified)."""
        temp_result = self._allocate_temp(8)
        temp_counter = self._allocate_temp(8)

        # Clear result
        for i in range(8):
            self._generate_clear(pos_result + i)
            self._generate_clear(temp_result + i)
            self._generate_clear(temp_counter + i)

        # Copy B to counter
        self._copy_block(pos_b, temp_counter, 8)

        # Add A to result B times (simplified - only works for small positive numbers)
        self._move_pointer(temp_counter)
        self.bf_code.append('[')

        # Add A to result
        for i in range(8):
            self._copy_cell(pos_a + i, temp_result + i, self._allocate_temp())
            self._free_temp(self.current_ptr)

        # Decrement counter
        for i in range(8):
            self._move_pointer(temp_counter + i)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(temp_counter + i)
            self.bf_code.append('-]')

        self.bf_code.append(']')

        # Copy temp_result to result
        self._copy_block(temp_result, pos_result, 8)

        self._free_temp(temp_counter)
        self._free_temp(temp_result)

    def _perform_div(self, pos_a, pos_b, pos_result):
        """Perform integer division using repeated subtraction."""
        quotient = self._allocate_temp(8)
        remainder = self._allocate_temp(8)
        temp_b = self._allocate_temp(8)

        # Clear all
        for i in range(8):
            self._generate_clear(pos_result + i)
            self._generate_clear(quotient + i)
            self._generate_clear(remainder + i)

        # Copy A to remainder, B to temp_b
        self._copy_block(pos_a, remainder, 8)
        self._copy_block(pos_b, temp_b, 8)

        # Repeated subtraction: count how many times B fits into A
        self._move_pointer(remainder)
        self.bf_code.append('[')  # While remainder > 0

        # Subtract B from remainder
        for i in range(8):
            self._move_pointer(temp_b + i)
            self.bf_code.append('[')
            self._move_pointer(remainder + i)
            self.bf_code.append('-')
            self._move_pointer(temp_b + i)
            self.bf_code.append('-]')

        # If subtraction succeeded, increment quotient
        self._move_pointer(remainder)
        self.bf_code.append('[')
        for i in range(8):
            self._move_pointer(quotient + i)
            self.bf_code.append('+')
        self.bf_code.append(']')

        self.bf_code.append(']')

        # Copy quotient to result
        self._copy_block(quotient, pos_result, 8)

        self._free_temp(temp_b)
        self._free_temp(remainder)
        self._free_temp(quotient)

    def _perform_mod(self, pos_a, pos_b, pos_result):
        """Perform modulo operation using repeated subtraction."""
        remainder = self._allocate_temp(8)
        temp_b = self._allocate_temp(8)

        # Clear all
        for i in range(8):
            self._generate_clear(pos_result + i)
            self._generate_clear(remainder + i)

        # Copy A to remainder, B to temp_b
        self._copy_block(pos_a, remainder, 8)
        self._copy_block(pos_b, temp_b, 8)

        # Repeated subtraction until remainder < B
        self._move_pointer(remainder)
        self.bf_code.append('[')

        # Try to subtract B from remainder
        for i in range(8):
            self._move_pointer(temp_b + i)
            self.bf_code.append('[')
            self._move_pointer(remainder + i)
            self.bf_code.append('-')
            self._move_pointer(temp_b + i)
            self.bf_code.append('-]')

        # Restore B if subtraction failed (remainder < B)
        for i in range(8):
            self._move_pointer(temp_b + i)
            self.bf_code.append('[')
            self._move_pointer(remainder + i)
            self.bf_code.append('+')
            self._move_pointer(temp_b + i)
            self.bf_code.append('-]')

        self.bf_code.append(']')

        # Copy remainder to result
        self._copy_block(remainder, pos_result, 8)

        self._free_temp(temp_b)
        self._free_temp(remainder)

    def _bitwise_byte_operation(self, op, pos_a, pos_b, pos_result):
        """
        Generate BF code for bitwise operation on single byte using decomposition.

        Algorithm: Decompose both numbers by repeatedly extracting highest bit.
        """
        # Clear result
        self._generate_clear(pos_result)

        # Copy operands to working cells (will be destroyed)
        a_remain = self._allocate_temp()
        b_remain = self._allocate_temp()
        temp = self._allocate_temp()

        self._copy_cell(pos_a, a_remain, temp)
        self._copy_cell(pos_b, b_remain, temp)

        # Process each bit from MSB to LSB
        for power in [128, 64, 32, 16, 8, 4, 2, 1]:
            # Check and extract bit from A
            bit_a = self._allocate_temp()

            # Safe subtraction using adjacent cells
            test = self._allocate_temp()
            temp_val = self._allocate_temp()  # Adjacent to test
            scr = self._allocate_temp()

            self._copy_cell(a_remain, test, scr)
            self._generate_set_value(power, temp_val)

            # Safe subtraction: simultaneously decrement test and temp_val
            self._move_pointer(test)
            self.bf_code.append('['     # while test > 0
                                '>'     # move to temp_val
                                '['     # if temp_val > 0
                                '-<->'  # decrement temp_val, move to test, decrement test, move back to temp_val
                                ']'     # loop if temp_val > 0
                                '<[-]>' # if temp_val reached 0: clear test to exit, move back to temp_val
                                '<'     # move to test
                                ']')    # loop if test > 0

            # If temp_val is now 0, bit was set (a_remain >= power)
            self._generate_set_value(1, bit_a)
            self._move_pointer(temp_val)
            self.bf_code.append('[')  # if temp_val > 0, bit was NOT set
            self._generate_clear(bit_a)
            self._generate_clear(temp_val)
            self.bf_code.append(']')

            self._free_temp(scr)
            self._free_temp(temp_val)
            self._free_temp(test)

            # If bit_a is set, actually subtract power from a_remain
            self._move_pointer(bit_a)
            self.bf_code.append('[')
            self._move_pointer(a_remain)
            for _ in range(power):
                self.bf_code.append('-')
            # Keep bit_a set for operation
            self._move_pointer(bit_a)
            self.bf_code.append(']')

            # Check and extract bit from B
            bit_b = self._allocate_temp()

            # Safe subtraction using adjacent cells
            test = self._allocate_temp()
            temp_val = self._allocate_temp()  # Adjacent to test
            scr = self._allocate_temp()

            self._copy_cell(b_remain, test, scr)
            self._generate_set_value(power, temp_val)

            # Safe subtraction: simultaneously decrement test and temp_val
            self._move_pointer(test)
            self.bf_code.append('['     # while test > 0
                                '>'     # move to temp_val
                                '['     # if temp_val > 0
                                '-<->'  # decrement temp_val, move to test, decrement test, move back to temp_val
                                ']'     # loop if temp_val > 0
                                '<[-]>' # if temp_val reached 0: clear test to exit
                                '<'     # move to test
                                ']')    # loop if test > 0

            # If temp_val is now 0, bit was set
            self._generate_set_value(1, bit_b)
            self._move_pointer(temp_val)
            self.bf_code.append('[')
            self._generate_clear(bit_b)
            self._generate_clear(temp_val)
            self.bf_code.append(']')

            self._free_temp(scr)
            self._free_temp(temp_val)
            self._free_temp(test)

            self._move_pointer(bit_b)
            self.bf_code.append('[')
            self._move_pointer(b_remain)
            for _ in range(power):
                self.bf_code.append('-')
            self._move_pointer(bit_b)
            self.bf_code.append(']')

            # Now apply the operation
            if op == 'and':
                # Both must be set
                self._move_pointer(bit_a)
                self.bf_code.append('[')
                self._move_pointer(bit_b)
                self.bf_code.append('[')
                self._move_pointer(pos_result)
                for _ in range(power):
                    self.bf_code.append('+')
                self._generate_clear(bit_b)
                self.bf_code.append(']')
                self._generate_clear(bit_a)
                self.bf_code.append(']')

            elif op == 'or':
                # At least one must be set: add bit_a and bit_b
                self._move_pointer(bit_b)
                self.bf_code.append('[')
                self._move_pointer(bit_a)
                self.bf_code.append('+')
                self._generate_clear(bit_b)
                self.bf_code.append(']')
                self._move_pointer(bit_a)
                self.bf_code.append('[')
                self._move_pointer(pos_result)
                for _ in range(power):
                    self.bf_code.append('+')
                self._generate_clear(bit_a)
                self.bf_code.append(']')

            elif op == 'xor':
                # Exactly one must be set
                self._move_pointer(bit_b)
                self.bf_code.append('[')
                self._move_pointer(bit_a)
                self.bf_code.append('+')
                self._generate_clear(bit_b)
                self.bf_code.append(']')
                # bit_a is now 0, 1, or 2
                # Decrement and check if it becomes 0 (was 1)
                flag = self._allocate_temp()
                self._generate_set_value(1, flag)
                self._move_pointer(bit_a)
                self.bf_code.append('-')  # Now 255, 0, or 1
                self.bf_code.append('[')  # if non-zero (was 0 or 2)
                self._generate_clear(flag)
                self._generate_clear(bit_a)
                self.bf_code.append(']')
                # Add power if flag still set
                self._move_pointer(flag)
                self.bf_code.append('[')
                self._move_pointer(pos_result)
                for _ in range(power):
                    self.bf_code.append('+')
                self._generate_clear(flag)
                self.bf_code.append(']')
                self._free_temp(flag)

            # Clean up bit flags (might already be cleared by operation)
            self._generate_clear(bit_b)
            self._generate_clear(bit_a)
            self._free_temp(bit_b)
            self._free_temp(bit_a)

        # Free working cells
        self._free_temp(temp)
        self._free_temp(b_remain)
        self._free_temp(a_remain)

    def _increment_multi_byte(self, pos, size=8):
        """Increment multi-byte integer with carry propagation."""
        carry_flag = self._allocate_temp(1)
        self._generate_set_value(1, carry_flag)

        for i in range(size):
            self._move_pointer(carry_flag)
            self.bf_code.append('[')
            self.bf_code.append('-')

            self._move_pointer(pos + i)
            self.bf_code.append('+')

            overflow = self._allocate_temp(1)
            self._generate_set_value(1, overflow)
            temp = self._allocate_temp(1)
            scratch = self._allocate_temp(1)
            self._copy_cell(pos + i, temp, scratch)
            self._move_pointer(temp)
            self.bf_code.append('[')
            self._generate_clear(overflow)
            self._generate_clear(temp)
            self.bf_code.append(']')
            self._free_temp(scratch)
            self._free_temp(temp)

            self._move_pointer(overflow)
            self.bf_code.append('[')
            self._move_pointer(carry_flag)
            self.bf_code.append('+')
            self._move_pointer(overflow)
            self.bf_code.append('-]')
            self._free_temp(overflow)

            self._move_pointer(carry_flag)
            self.bf_code.append(']')

        self._free_temp(carry_flag)

    def _decrement_multi_byte(self, pos, size=8):
        """Decrement multi-byte integer with borrow propagation."""
        borrow_flag = self._allocate_temp(1)
        self._generate_set_value(1, borrow_flag)

        for i in range(size):
            self._move_pointer(borrow_flag)
            self.bf_code.append('[')
            self.bf_code.append('-')

            is_zero = self._allocate_temp(1)
            self._generate_set_value(1, is_zero)
            temp = self._allocate_temp(1)
            scratch = self._allocate_temp(1)
            self._copy_cell(pos + i, temp, scratch)
            self._move_pointer(temp)
            self.bf_code.append('[')
            self._generate_clear(is_zero)
            self._generate_clear(temp)
            self.bf_code.append(']')
            self._free_temp(scratch)
            self._free_temp(temp)

            self._move_pointer(pos + i)
            self.bf_code.append('-')

            self._move_pointer(is_zero)
            self.bf_code.append('[')
            self._move_pointer(borrow_flag)
            self.bf_code.append('+')
            self._move_pointer(is_zero)
            self.bf_code.append('-]')
            self._free_temp(is_zero)

            self._move_pointer(borrow_flag)
            self.bf_code.append(']')

        self._free_temp(borrow_flag)

    def _divmod10_multi_byte(self, pos_in, pos_quotient, rem_pos, size=8):
        """
        Perform (quotient, remainder) = value // 10, value % 10 for multi-byte.
        Algorithm: standard long division by 10.
        """
        # Clear quotient and remainder
        for i in range(size):
            self._generate_clear(pos_quotient + i)
        self._generate_clear(rem_pos)
        
        # We need a temporary copy of the input because we process it byte-by-byte
        temp_val = self._allocate_temp(size)
        self._copy_block(pos_in, temp_val, size)
        
        # Process from MSB to LSB
        for i in reversed(range(size)):
            # rem = (rem * 256) + current_byte
            # In BF, we can think of this as adding current_byte to rem,
            # then for each unit in rem, we'd add 256 to next... wait.
            # Simpler: 
            # while temp_val[i] > 0:
            #   temp_val[i]--, rem++
            #   if rem == 10: rem=0, quotient[i]++
            # This is not quite right for long division.
            
            # Correct long division step:
            # For each byte i:
            #   remainder = (remainder << 8) | current_byte
            #   quotient[i] = remainder / 10
            #   remainder = remainder % 10
            
            # Implementation:
            # 1. Transfer current byte to a 16-bit intermediate (high=rem, low=temp_val[i])
            # 2. Repeatedly subtract 10 from this 16-bit value, incrementing pos_quotient[i]
            
            # Since rem < 10, (rem * 256 + byte) < 2560 + 256 = 2816.
            # This fits in 16 bits.
            
            # We already have rem in rem_pos (0..9).
            # We have temp_val[i] (0..255).
            
            # While temp_val[i] > 0 or rem > 0:
            #   if we can subtract 10 from (rem, temp_val[i]):
            #     do it, quotient[i]++
            
            loop_flag = self._allocate_temp(1)
            self._generate_set_value(1, loop_flag)
            
            self._move_pointer(loop_flag)
            self.bf_code.append('[')
            
            # Can we subtract 10?
            # ge10 if rem > 0 or temp_val[i] >= 10
            ge10 = self._allocate_temp(1)
            self._generate_clear(ge10)
            self._generate_if_nonzero(rem_pos, lambda: self._generate_set_value(1, ge10))
            
            low_ge10 = self._allocate_temp(1)
            self._generate_clear(low_ge10)
            for v in range(10, 256):
                self._generate_if_byte_equals(temp_val + i, v, lambda: self._generate_set_value(1, low_ge10))
            
            self._generate_if_nonzero(low_ge10, lambda: self._generate_set_value(1, ge10))
            self._free_temp(low_ge10)
            
            def _sub10():
                self._move_pointer(pos_quotient + i)
                self.bf_code.append('+')
                # subtract 10 from 16-bit (rem, temp_val[i])
                low_ge10_inner = self._allocate_temp(1)
                self._generate_clear(low_ge10_inner)
                for v in range(10, 256):
                    self._generate_if_byte_equals(temp_val + i, v, lambda: self._generate_set_value(1, low_ge10_inner))
                
                def _low_ge():
                    self._move_pointer(temp_val + i)
                    self.bf_code.append('----------')
                def _low_lt():
                    # borrow from rem
                    self._move_pointer(rem_pos)
                    self.bf_code.append('-')
                    self._move_pointer(temp_val + i)
                    self.bf_code.append('+' * 246) # +256 - 10
                
                self._generate_if_nonzero(low_ge10_inner, _low_ge)
                
                inv = self._allocate_temp(1)
                self._generate_set_value(1, inv)
                self._move_pointer(low_ge10_inner)
                self.bf_code.append('[')
                self._move_pointer(inv)
                self.bf_code.append('-')
                self._generate_clear(low_ge10_inner)
                self.bf_code.append(']')
                self._generate_if_nonzero(inv, _low_lt)
                self._free_temp(inv)
                self._free_temp(low_ge10_inner)

            self._generate_if_nonzero(ge10, _sub10)
            
            # if not ge10: clear loop_flag
            inv_ge10 = self._allocate_temp(1)
            self._generate_set_value(1, inv_ge10)
            self._move_pointer(ge10)
            self.bf_code.append('[')
            self._move_pointer(inv_ge10)
            self.bf_code.append('-')
            self._generate_clear(ge10)
            self.bf_code.append(']')
            self._move_pointer(inv_ge10)
            self.bf_code.append('[')
            self._generate_clear(loop_flag)
            self._generate_clear(inv_ge10)
            self.bf_code.append(']')
            self._free_temp(inv_ge10)
            self._free_temp(ge10)
            
            self._move_pointer(loop_flag)
            self.bf_code.append(']')
            self._free_temp(loop_flag)
            
            # The remaining value in temp_val[i] IS the new rem for next iteration if we were doing bits,
            # but here it's just the remainder of this byte division.
            # Wait, the long division step is:
            # new_rem = (old_rem * 256 + current_byte) % 10
            # We already have this! It's whatever is left in temp_val[i] after the loop.
            self._move_pointer(temp_val + i)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(rem_pos)
            self.bf_code.append('+')
            self._move_pointer(temp_val + i)
            self.bf_code.append(']')
            
        self._free_temp(temp_val)
