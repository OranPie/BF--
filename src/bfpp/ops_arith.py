from __future__ import annotations


class ArithOpsMixin:
    def _sign_extend_8_to_64(self, pos):
        """Sign-extend an 8-bit value at pos[0] to 64-bit in-place (pos[0..7])."""
        flag = self._allocate_temp()
        self._generate_clear(flag)
        # If byte 0 >= 128, then it's negative.
        for v in range(128, 256):
            self._generate_if_byte_equals(pos, v, lambda: self._generate_set_value(1, flag))
        
        def _fill_ff():
            for i in range(1, 8):
                self._generate_set_value(255, pos + i)
        
        for i in range(1, 8):
            self._generate_clear(pos + i)
        self._generate_if_nonzero(flag, _fill_ff)
        self._free_temp(flag)

    def _sign_extend_16_to_64(self, pos):
        """Sign-extend a 16-bit value at pos[0..1] to 64-bit in-place (pos[0..7])."""
        flag = self._allocate_temp()
        self._generate_clear(flag)
        # If byte 1 >= 128, then it's negative.
        for v in range(128, 256):
            self._generate_if_byte_equals(pos + 1, v, lambda: self._generate_set_value(1, flag))
        
        def _fill_ff():
            for i in range(2, 8):
                self._generate_set_value(255, pos + i)
        
        for i in range(2, 8):
            self._generate_clear(pos + i)
        self._generate_if_nonzero(flag, _fill_ff)
        self._free_temp(flag)

    def _handle_expression_assignment(self, expr_tokens, dest_var):
        """Handle arithmetic and bitwise expression assignment."""
        dest_info = self._resolve_var(dest_var)

        if dest_info['type'] not in ('int', 'int16', 'int64', 'float', 'float64', 'expfloat'):
            raise NotImplementedError("Expressions only supported for integer and float types")

        left, op, right = self._parse_expression(expr_tokens)
        dest_size = dest_info['size']

        def _set_int64_const(value, pos):
            byte_values = int(value).to_bytes(8, 'little', signed=True)
            for i, byte_val in enumerate(byte_values):
                self._generate_set_value(byte_val, pos=pos + i)

        def _is_plain_literal(tok):
            if tok.startswith('$'):
                return False
            if self._split_runtime_subscript_ref(tok) is not None:
                return False
            if tok in getattr(self, 'variables', {}):
                return False
            return True

        def _is_literal_zero(tok):
            if not _is_plain_literal(tok):
                return False
            try:
                if any(c in tok for c in ('.', 'e', 'E')):
                    return float(tok) == 0.0
                return int(tok) == 0
            except ValueError:
                return False

        def _sign_extend_8_to_16(pos):
            flag = self._allocate_temp()
            self._generate_clear(flag)
            for v in range(128, 256):
                self._generate_if_byte_equals(pos, v, lambda: self._generate_set_value(1, flag))

            self._generate_clear(pos + 1)
            self._generate_if_nonzero(flag, lambda: self._generate_set_value(255, pos + 1))
            self._free_temp(flag)

        def _load_operand_float_scaled(operand, target_pos):
            opnd = operand[1:] if operand.startswith('$') else operand
            runtime = self._split_runtime_subscript_ref(opnd)
            if runtime is not None:
                base_name, idx_var = runtime
                base_info = self._resolve_var(base_name)
                if base_info['type'] not in ('float', 'float64', 'expfloat') or base_info.get('elem_size', 8) != 8:
                    raise NotImplementedError("Runtime-subscript float operands support only float/float64/expfloat")
                self._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, 8)
                return

            if operand.startswith('$'):
                info = self._resolve_var(operand)
                if info['type'] in ('float', 'float64', 'expfloat'):
                    self._copy_block(info['pos'], target_pos, 8)
                    return

                if info['type'] in ('int', 'int16', 'int64', 'byte', 'char'):
                    temp_src_64 = self._allocate_temp(8)
                    self._generate_clear_block(temp_src_64, 8)
                    self._copy_block(info['pos'], temp_src_64, info['size'])

                    if info['type'] == 'int16':
                        self._sign_extend_16_to_64(temp_src_64)
                    elif info['type'] in ('byte', 'char'):
                        self._sign_extend_8_to_64(temp_src_64)

                    const_1000 = self._allocate_temp(8)
                    _set_int64_const(1000, const_1000)
                    self._perform_mul_signed(temp_src_64, const_1000, target_pos, size=8)
                    self._free_temp(const_1000)
                    self._free_temp(temp_src_64)
                    return

                raise NotImplementedError(f"Unsupported source type for float conversion: {info['type']}")

            if any(c in operand for c in ('.', 'e', 'E')):
                if dest_info['type'] == 'expfloat':
                    value = int(self._parse_expfloat_literal_scaled(operand))
                else:
                    value = int(self._parse_float_literal_scaled(operand))
            else:
                value = int(operand) * 1000

            _set_int64_const(value, target_pos)

        if dest_info['type'] in ('float', 'float64', 'expfloat'):
            if op in ('&', '|', '^', '~', '%'):
                raise NotImplementedError(f"{dest_info['type']} expressions do not support bitwise or modulo operators")

            temp_left = self._allocate_temp(8)
            temp_right = self._allocate_temp(8)
            self._generate_clear_block(temp_left, 8)
            self._generate_clear_block(temp_right, 8)

            _load_operand_float_scaled(left, temp_left)

            if op is None and right is None:
                self._copy_block(temp_left, dest_info['pos'], 8)
                self._free_temp(temp_right)
                self._free_temp(temp_left)
                return

            _load_operand_float_scaled(right, temp_right)

            if op == '+':
                self._perform_add(temp_left, temp_right, dest_info['pos'], size=8)
            elif op == '-':
                self._perform_sub(temp_left, temp_right, dest_info['pos'], size=8)
            elif op == '*':
                raw_prod = self._allocate_temp(8)
                self._perform_mul_signed(temp_left, temp_right, raw_prod, size=8)
                const_1000 = self._allocate_temp(8)
                _set_int64_const(1000, const_1000)
                self._perform_div_signed(raw_prod, const_1000, dest_info['pos'], size=8)
                self._free_temp(const_1000)
                self._free_temp(raw_prod)
            elif op == '/':
                # check for literal division by zero
                if _is_literal_zero(right):
                    raise ValueError(f"Division by zero in {dest_info['type']} expression")
                const_1000 = self._allocate_temp(8)
                _set_int64_const(1000, const_1000)
                scaled_left = self._allocate_temp(8)
                self._perform_mul_signed(temp_left, const_1000, scaled_left, size=8)
                self._perform_div_signed(scaled_left, temp_right, dest_info['pos'], size=8)
                self._free_temp(scaled_left)
                self._free_temp(const_1000)
            else:
                raise NotImplementedError(f"{dest_info['type']} expressions currently support +, -, *, / (got {op})")

            if dest_info['type'] == 'float':
                self._generate_runtime_range_check_r1(dest_info['pos'])

            self._free_temp(temp_right)
            self._free_temp(temp_left)
            return

        if dest_info['type'] in ('int', 'int16', 'int64') and op is None and right is None:
            if not left.startswith('$'):
                # literal assignment
                val = int(left)
                byte_values = val.to_bytes(dest_size, 'little', signed=True)
                for i, b in enumerate(byte_values):
                    self._generate_set_value(b, dest_info['pos'] + i)
                return

            src_info = self._resolve_var(left)
            if src_info['type'] in ('float', 'float64', 'expfloat'):
                # Float/Expfloat -> Int conversion (scale down by 1000)
                const_1000 = self._allocate_temp(8)
                _set_int64_const(1000, const_1000)

                tmp_q = self._allocate_temp(8)
                self._generate_clear_block(tmp_q, 8)
                self._perform_div_signed(src_info['pos'], const_1000, tmp_q, size=8)
                self._copy_block(tmp_q, dest_info['pos'], dest_size)

                self._free_temp(tmp_q)
                self._free_temp(const_1000)
                return

            # Integer -> Integer copy/conversion
            src_size = src_info['size']
            if src_size == dest_size:
                self._copy_block(src_info['pos'], dest_info['pos'], dest_size)
            elif src_size < dest_size:
                # Widen
                self._copy_block(src_info['pos'], dest_info['pos'], src_size)
                if src_info['type'] == 'int16' and dest_size == 8:
                    self._sign_extend_16_to_64(dest_info['pos'])
                elif src_info['type'] in ('byte', 'char') and dest_size == 8:
                    self._sign_extend_8_to_64(dest_info['pos'])
                elif src_info['type'] in ('byte', 'char') and dest_size == 2:
                    _sign_extend_8_to_16(dest_info['pos'])
                else:
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

        temp_left = self._allocate_temp(dest_size)
        temp_right = self._allocate_temp(dest_size)

        self._load_operand(left, temp_left, size=dest_size)
        self._load_operand(right, temp_right, size=dest_size)

        if op == '+':
            self._perform_add(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '-':
            self._perform_sub(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '*':
            self._perform_mul_signed(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '/':
            self._perform_div_signed(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '%':
            self._perform_mod_signed(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '&':
            self._perform_bitwise_and(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '|':
            self._perform_bitwise_or(temp_left, temp_right, dest_info['pos'], size=dest_size)
        elif op == '^':
            self._perform_bitwise_xor(temp_left, temp_right, dest_info['pos'], size=dest_size)
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
        is_var = operand.startswith('$') or operand in self.variables
        op = operand[1:] if operand.startswith('$') else operand
        
        runtime = self._split_runtime_subscript_ref(op)
        if runtime is not None:
            base_name, idx_var = runtime
            base_info = self._resolve_var(base_name)
            if base_info['type'] not in ('int', 'int16', 'int64') or base_info.get('elem_size', 8) != size:
                raise NotImplementedError(f"Runtime-subscripted expression operands currently support only {size}-byte int elements")
            self._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, size)
            return

        if is_var:
            var_info = self._resolve_var(operand)
            if var_info['type'] not in ('int', 'int16', 'int64') or var_info['size'] != size:
                raise NotImplementedError(f"Expression operands currently support only {size}-byte int variables (got {var_info['type']} size {var_info['size']}, expected {size})")
            self._copy_block(var_info['pos'], target_pos, size)
            return

        try:
            value = int(operand)
        except ValueError:
            raise ValueError(f"Invalid operand: {operand} (not a variable or integer literal)")
            
        byte_values = value.to_bytes(size, 'little', signed=True)
        for i, byte_val in enumerate(byte_values):
            self._generate_set_value(byte_val, pos=target_pos + i)

    def _generate_runtime_range_check_r1(self, pos):
        """
        Generate BF code to check if an 8-byte scaled value at pos is within R1 range [-32.768, 32.767].
        R1 range scaled is [-32768, 32767].
        In two's complement 64-bit, this means the value must be the sign-extension of its low 16 bits.
        """
        # If byte 1 bit 7 is 0 (pos): bytes 2-7 must be 0
        # If byte 1 bit 7 is 1 (neg): bytes 2-7 must be 255
        
        is_neg = self._allocate_temp(1)
        self._generate_clear(is_neg)
        
        # Check sign bit (bit 7 of byte 1)
        byte1 = pos + 1
        flag_ge128 = self._allocate_temp(1)
        self._generate_clear(flag_ge128)
        for v in range(128, 256):
            self._generate_if_byte_equals(byte1, v, lambda: self._generate_set_value(1, flag_ge128))
        self._generate_if_nonzero(flag_ge128, lambda: self._generate_set_value(1, is_neg))
        self._free_temp(flag_ge128)
        
        # We'll use a 'valid' flag. If it becomes 0, we've detected an out-of-range value.
        valid = self._allocate_temp(1)
        self._generate_set_value(1, valid)
        
        def _check_pos():
            # All bytes from 2 to 7 must be 0
            for i in range(2, 8):
                self._generate_if_nonzero(pos + i, lambda: self._generate_clear(valid))
                
        def _check_neg():
            # All bytes from 2 to 7 must be 255
            for i in range(2, 8):
                # if byte != 255: valid = 0
                is_255 = self._allocate_temp(1)
                self._generate_clear(is_255)
                self._generate_if_byte_equals(pos + i, 255, lambda: self._generate_set_value(1, is_255))
                not_255 = self._allocate_temp(1)
                self._generate_set_value(1, not_255)
                self._generate_if_nonzero(is_255, lambda: self._generate_clear(not_255))
                self._generate_if_nonzero(not_255, lambda: self._generate_clear(valid))
                self._free_temp(not_255)
                self._free_temp(is_255)

        self._generate_if_nonzero(is_neg, _check_neg, body_fn_else=_check_pos)
        
        # If not valid, we trigger a 'halt' by entering an infinite loop.
        # This is a crude but effective way to signal a runtime error in BF.
        # We can also output an error message if we want to be fancy.
        def _on_error():
            self._output_literal('"RUNTIME ERROR: float R1 overflow\n"')
            loop = self._allocate_temp(1)
            self._generate_set_value(1, loop)
            self.bf_code.append('[#]') # Infinite loop marker
            self._free_temp(loop)
            
        inv_valid = self._allocate_temp(1)
        self._generate_set_value(1, inv_valid)
        self._generate_if_nonzero(valid, lambda: self._generate_clear(inv_valid))
        self._generate_if_nonzero(inv_valid, _on_error)
        
        self._free_temp(inv_valid)
        self._free_temp(valid)
        self._free_temp(is_neg)

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

    def _perform_mul(self, pos_a, pos_b, pos_result, size=8):
        """Perform multiplication on multi-byte integers using bit-shifting (Russian Peasant)."""
        # result = 0
        # while b > 0:
        #   if b is odd: result += a
        #   a <<= 1
        #   b >>= 1
        
        self._generate_clear_block(pos_result, size)
        
        temp_a = self._allocate_temp(size)
        temp_b = self._allocate_temp(size)
        self._copy_block(pos_a, temp_a, size)
        self._copy_block(pos_b, temp_b, size)
        
        loop_flag = self._allocate_temp(1)
        self._generate_set_value(1, loop_flag)
        
        self._move_pointer(loop_flag)
        self.bf_code.append('[')
        
        # Check if b is odd (LSB & 1)
        is_odd = self._allocate_temp(1)
        self._generate_clear(is_odd)
        # We only need bit 0 of temp_b[0]
        bit0 = self._allocate_temp(1)
        self._bitwise_byte_operation('and', temp_b, self._allocate_temp_const(1), bit0)
        self._free_temp_const()
        
        self._generate_if_nonzero(bit0, lambda: self._perform_add(pos_result, temp_a, pos_result, size=size))
        self._free_temp(bit0)
        self._free_temp(is_odd)
        
        # a <<= 1 (a = a + a)
        # We can't just add to itself easily if it's destructive, but our _perform_add is robust.
        scr_a = self._allocate_temp(size)
        self._copy_block(temp_a, scr_a, size)
        self._perform_add(temp_a, scr_a, temp_a, size=size)
        self._free_temp(scr_a)
        
        # b >>= 1
        self._shift_right_multi_byte(temp_b, size=size)
        
        # Check if b is zero
        b_nonzero = self._allocate_temp(1)
        self._generate_clear(b_nonzero)
        for i in range(size):
            self._generate_if_nonzero(temp_b + i, lambda: self._generate_set_value(1, b_nonzero))
            
        self._generate_if_nonzero(b_nonzero, lambda: None, body_fn_else=lambda: self._generate_clear(loop_flag))
        self._free_temp(b_nonzero)
        
        self._move_pointer(loop_flag)
        self.bf_code.append(']')
        
        self._free_temp(loop_flag)
        self._free_temp(temp_b)
        self._free_temp(temp_a)

    def _shift_left_multi_byte(self, pos, size=8):
        """Shift multi-byte integer left by 1 bit."""
        # For each byte from MSB to LSB:
        #   byte = (byte << 1) | (prev_byte_msb)
        
        # We process from MSB down to LSB to easily propagate carries from lower bytes
        for i in reversed(range(size)):
            # byte[i] = (byte[i] << 1)
            # Carry from byte[i-1] bit 7
            carry_in = self._allocate_temp(1)
            self._generate_clear(carry_in)
            if i > 0:
                # bit 7 of pos[i-1]
                bit7 = self._allocate_temp(1)
                self._generate_clear(bit7)
                # Check if byte >= 128
                for v in range(128, 256):
                    self._generate_if_byte_equals(pos + i - 1, v, lambda: self._generate_set_value(1, bit7))
                self._generate_if_nonzero(bit7, lambda: self._generate_set_value(1, carry_in))
                self._free_temp(bit7)
            
            # byte = (byte << 1) | carry_in
            # In BF: byte = byte + byte + carry_in
            old_byte = self._allocate_temp(1)
            scr = self._allocate_temp(1)
            self._copy_cell(pos + i, old_byte, scr)
            self._free_temp(scr)
            
            # pos[i] = old_byte + old_byte + carry_in
            self._generate_clear(pos + i)
            self._add_cell(old_byte, pos + i, self._allocate_temp(1))
            self._free_temp(self.current_ptr)
            self._add_cell(old_byte, pos + i, self._allocate_temp(1))
            self._free_temp(self.current_ptr)
            self._add_cell(carry_in, pos + i, self._allocate_temp(1))
            self._free_temp(self.current_ptr)
            
            self._free_temp(old_byte)
            self._free_temp(carry_in)

    def _shift_right_multi_byte(self, pos, size=8):
        """Shift multi-byte integer right by 1 bit."""
        # For each byte from LSB to MSB:
        #   byte = (byte >> 1) | (next_byte_lsb << 7)
        for i in range(size):
            carry_in = self._allocate_temp(1)
            self._generate_clear(carry_in)
            if i < size - 1:
                # bit 0 of pos[i+1]
                bit0 = self._allocate_temp(1)
                self._get_bit_multi_byte(pos, (i + 1) * 8, bit0, size=size)
                self._generate_if_nonzero(bit0, lambda: self._generate_set_value(128, carry_in))
                self._free_temp(bit0)
            
            # byte = (byte >> 1)
            temp_byte = self._allocate_temp(1)
            scr = self._allocate_temp(1)
            self._copy_cell(pos + i, temp_byte, scr)
            self._free_temp(scr)
            
            self._generate_clear(pos + i)
            # Unsigned byte shift right: new = old // 2
            # while temp_byte >= 2: temp_byte -= 2, pos[i] += 1
            self._move_pointer(temp_byte)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(temp_byte)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(pos + i)
            self.bf_code.append('+')
            self._move_pointer(temp_byte)
            self.bf_code.append(']')
            self.bf_code.append(']')
            
            # pos[i] |= carry_in
            self._add_cell(carry_in, pos + i, self._allocate_temp(1))
            self._free_temp(self.current_ptr)
            
            self._free_temp(temp_byte)
            self._free_temp(carry_in)

    def _get_bit_multi_byte(self, pos, bit_idx, result_pos, size=8):
        """Extract a single bit from a multi-byte integer."""
        byte_idx = bit_idx // 8
        bit_in_byte = bit_idx % 8
        
        if byte_idx >= size:
            self._generate_clear(result_pos)
            return
            
        # Extract bit_in_byte from pos[byte_idx]
        temp_byte = self._allocate_temp(1)
        scr = self._allocate_temp(1)
        self._copy_cell(pos + byte_idx, temp_byte, scr)
        self._free_temp(scr)
        
        # bit = (temp_byte >> bit_in_byte) & 1
        # Shift right bit_in_byte times
        for _ in range(bit_in_byte):
            new_byte = self._allocate_temp(1)
            self._generate_clear(new_byte)
            self._move_pointer(temp_byte)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(temp_byte)
            self.bf_code.append('[')
            self.bf_code.append('-')
            self._move_pointer(new_byte)
            self.bf_code.append('+')
            self._move_pointer(temp_byte)
            self.bf_code.append(']')
            self.bf_code.append(']')
            self._copy_cell(new_byte, temp_byte, self._allocate_temp(1))
            self._free_temp(self.current_ptr)
            self._free_temp(new_byte)
            
        # result = temp_byte & 1
        self._generate_clear(result_pos)
        self._bitwise_byte_operation('and', temp_byte, self._allocate_temp_const(1), result_pos)
        self._free_temp_const()
        
        self._free_temp(temp_byte)

    def _set_bit_multi_byte(self, pos, bit_idx, value_pos, size=8):
        """Set a single bit in a multi-byte integer to the value in value_pos (0 or 1)."""
        byte_idx = bit_idx // 8
        bit_in_byte = bit_idx % 8
        
        if byte_idx >= size:
            return
            
        # mask = 1 << bit_in_byte
        mask_val = 1 << bit_in_byte
        
        # if value_pos: byte |= mask
        # else: byte &= ~mask
        
        def _set_bit():
            mask_temp = self._allocate_temp(1)
            self._generate_set_value(mask_val, mask_temp)
            self._bitwise_byte_operation('or', pos + byte_idx, mask_temp, pos + byte_idx)
            self._free_temp(mask_temp)
            
        def _clear_bit():
            mask_temp = self._allocate_temp(1)
            self._generate_set_value(255 ^ mask_val, mask_temp)
            self._bitwise_byte_operation('and', pos + byte_idx, mask_temp, pos + byte_idx)
            self._free_temp(mask_temp)
            
        self._generate_if_nonzero(value_pos, _set_bit, body_fn_else=_clear_bit)

    def _generate_clear_block(self, pos, size):
        for i in range(size):
            self._generate_clear(pos + i)

    def _allocate_temp_const(self, val):
        if not hasattr(self, '_temp_const_stack'):
            self._temp_const_stack = []
        t = self._allocate_temp(1)
        self._generate_set_value(val, t)
        self._temp_const_stack.append(t)
        return t
        
    def _free_temp_const(self):
        if not hasattr(self, '_temp_const_stack'):
            return
        if not self._temp_const_stack:
            return
        t = self._temp_const_stack.pop()
        self._free_temp(t)

    def _perform_div(self, pos_a, pos_b, pos_result, size=8):
        """Perform integer division on multi-byte integers."""
        quotient = self._allocate_temp(size)
        remainder = self._allocate_temp(size)
        self._perform_divmod_multi_byte(pos_a, pos_b, quotient, remainder, size=size)
        self._copy_block(quotient, pos_result, size)
        self._free_temp(remainder)
        self._free_temp(quotient)

    def _perform_mod(self, pos_a, pos_b, pos_result, size=8):
        """Perform modulo operation on multi-byte integers."""
        quotient = self._allocate_temp(size)
        remainder = self._allocate_temp(size)
        self._perform_divmod_multi_byte(pos_a, pos_b, quotient, remainder, size=size)
        self._copy_block(remainder, pos_result, size)
        self._free_temp(remainder)
        self._free_temp(quotient)

    def _perform_mul_signed(self, pos_a, pos_b, pos_result, size=8):
        """Perform signed multiplication on multi-byte integers."""
        sign_a = self._allocate_temp(1)
        sign_b = self._allocate_temp(1)
        mag_a = self._allocate_temp(size)
        mag_b = self._allocate_temp(size)
        
        self._get_sign_and_abs(pos_a, sign_a, mag_a, size=size)
        self._get_sign_and_abs(pos_b, sign_b, mag_b, size=size)
        
        res_mag = self._allocate_temp(size)
        self._perform_mul(mag_a, mag_b, res_mag, size=size)
        
        # res_sign = sign_a ^ sign_b
        res_sign = self._allocate_temp(1)
        self._bitwise_byte_operation('xor', sign_a, sign_b, res_sign)
        
        self._apply_sign(res_mag, res_sign, pos_result, size=size)
        
        self._free_temp(res_sign)
        self._free_temp(res_mag)
        self._free_temp(mag_b)
        self._free_temp(mag_a)
        self._free_temp(sign_b)
        self._free_temp(sign_a)

    def _perform_div_signed(self, pos_a, pos_b, pos_result, size=8):
        """Perform signed division on multi-byte integers."""
        quot = self._allocate_temp(size)
        rem = self._allocate_temp(size)
        self._perform_divmod_signed(pos_a, pos_b, quot, rem, size=size)
        self._copy_block(quot, pos_result, size)
        self._free_temp(rem)
        self._free_temp(quot)

    def _perform_mod_signed(self, pos_a, pos_b, pos_result, size=8):
        """Perform signed modulo on multi-byte integers."""
        quot = self._allocate_temp(size)
        rem = self._allocate_temp(size)
        self._perform_divmod_signed(pos_a, pos_b, quot, rem, size=size)
        self._copy_block(rem, pos_result, size)
        self._free_temp(rem)
        self._free_temp(quot)

    def _perform_divmod_signed(self, pos_a, pos_b, pos_q, pos_r, size=8):
        """Perform signed divmod on multi-byte integers."""
        sign_a = self._allocate_temp(1)
        sign_b = self._allocate_temp(1)
        mag_a = self._allocate_temp(size)
        mag_b = self._allocate_temp(size)
        
        self._get_sign_and_abs(pos_a, sign_a, mag_a, size=size)
        self._get_sign_and_abs(pos_b, sign_b, mag_b, size=size)
        
        q_mag = self._allocate_temp(size)
        r_mag = self._allocate_temp(size)
        self._perform_divmod_multi_byte(mag_a, mag_b, q_mag, r_mag, size=size)
        
        # Quotient sign = sign_a ^ sign_b
        q_sign = self._allocate_temp(1)
        self._bitwise_byte_operation('xor', sign_a, sign_b, q_sign)
        self._apply_sign(q_mag, q_sign, pos_q, size=size)
        
        # Remainder sign = sign_a (standard C-like behavior: rem matches dividend sign)
        self._apply_sign(r_mag, sign_a, pos_r, size=size)
        
        self._free_temp(q_sign)
        self._free_temp(r_mag)
        self._free_temp(q_mag)
        self._free_temp(mag_b)
        self._free_temp(mag_a)
        self._free_temp(sign_b)
        self._free_temp(sign_a)

    def _get_sign_and_abs(self, pos, sign_pos, abs_pos, size=8):
        """Extract sign bit and absolute value of a multi-byte integer."""
        msb = pos + size - 1
        self._generate_clear(sign_pos)
        self._copy_block(pos, abs_pos, size)
        
        flag_ge128 = self._allocate_temp(1)
        self._generate_clear(flag_ge128)
        for v in range(128, 256):
            self._generate_if_byte_equals(msb, v, lambda: self._generate_set_value(1, flag_ge128))
        
        def _to_abs():
            self._generate_set_value(1, sign_pos)
            # mag = -val = NOT(val) + 1
            tmp_not = self._allocate_temp(size)
            self._perform_bitwise_not(abs_pos, tmp_not, size=size)
            self._copy_block(tmp_not, abs_pos, size)
            self._free_temp(tmp_not)
            self._increment_multi_byte(abs_pos, size=size)
            
        self._generate_if_nonzero(flag_ge128, _to_abs)
        self._free_temp(flag_ge128)

    def _apply_sign(self, mag_pos, sign_pos, res_pos, size=8):
        """Apply sign to magnitude to get signed result."""
        self._copy_block(mag_pos, res_pos, size)
        
        def _negate():
            # res = -mag = NOT(mag) + 1
            tmp_not = self._allocate_temp(size)
            self._perform_bitwise_not(res_pos, tmp_not, size=size)
            self._copy_block(tmp_not, res_pos, size)
            self._free_temp(tmp_not)
            self._increment_multi_byte(res_pos, size=size)
            
        self._generate_if_nonzero(sign_pos, _negate)

    def _perform_divmod_multi_byte(self, pos_a, pos_b, pos_q, pos_r, size=8):
        """
        Unsigned bit-by-bit long division for multi-byte integers.
        Algorithm:
        R = 0
        Q = 0
        for i from size*8 - 1 down to 0:
            R = R << 1
            R(0) = A(i)
            if R >= B:
                R = R - B
                Q(i) = 1
        """
        self._generate_clear_block(pos_q, size)
        self._generate_clear_block(pos_r, size)

        temp_a = self._allocate_temp(size)
        temp_b = self._allocate_temp(size)
        self._copy_block(pos_a, temp_a, size)
        self._copy_block(pos_b, temp_b, size)

        # Check for division by zero
        is_zero_b = self._allocate_temp(1)
        self._generate_clear(is_zero_b)
        self._generate_set_value(1, is_zero_b)
        for i in range(size):
            self._generate_if_nonzero(temp_b + i, lambda: self._generate_clear(is_zero_b))
        
        # if is_zero_b: raise error or skip
        # For now, we skip if b is zero (standard BF behavior or implementation defined)
        non_zero_b = self._allocate_temp(1)
        self._generate_set_value(1, non_zero_b)
        self._generate_if_nonzero(is_zero_b, lambda: self._generate_clear(non_zero_b))

        def _div_body():
            for bit_i in reversed(range(size * 8)):
                # R = R << 1
                self._shift_left_multi_byte(pos_r, size=size)
                
                # R(0) = A(i)
                bit_a = self._allocate_temp(1)
                self._get_bit_multi_byte(temp_a, bit_i, bit_a, size=size)
                self._set_bit_multi_byte(pos_r, 0, bit_a, size=size)
                self._free_temp(bit_a)
                
                # if R >= B:
                # Use _compare_multi_byte_signed from ControlFlowMixin? 
                # No, we need a simple magnitude comparison here.
                # Actually, let's just use a helper for unsigned comparison.
                is_lt = self._allocate_temp(1)
                is_gt = self._allocate_temp(1)
                is_eq = self._allocate_temp(1)
                
                # Use a temp method for unsigned comparison
                self._compare_multi_byte_unsigned(pos_r, temp_b, size, is_lt, is_gt, is_eq)
                
                # if R >= B (i.e. not R < B)
                def _do_sub():
                    self._perform_sub(pos_r, temp_b, pos_r, size=size)
                    one = self._allocate_temp(1)
                    self._generate_set_value(1, one)
                    self._set_bit_multi_byte(pos_q, bit_i, one, size=size)
                    self._free_temp(one)
                
                self._generate_if_nonzero(is_lt, lambda: None, body_fn_else=_do_sub)
                
                self._free_temp(is_eq)
                self._free_temp(is_gt)
                self._free_temp(is_lt)

        self._generate_if_nonzero(non_zero_b, _div_body)
        
        self._free_temp(non_zero_b)
        self._free_temp(is_zero_b)
        self._free_temp(temp_b)
        self._free_temp(temp_a)

    def _compare_multi_byte_unsigned(self, pos_a, pos_b, size, result_lt, result_gt, result_eq):
        """Unsigned comparison of two multi-byte integers."""
        self._generate_clear(result_lt)
        self._generate_clear(result_gt)
        self._generate_set_value(1, result_eq)

        stop = self._allocate_temp(1)
        self._generate_clear(stop)

        for i in reversed(range(size)):
            inv_stop = self._allocate_temp(1)
            self._generate_set_value(1, inv_stop)
            self._generate_if_nonzero(stop, lambda: self._generate_clear(inv_stop))

            def _comp(idx=i):
                byte_a = self._allocate_temp(1)
                byte_b = self._allocate_temp(1)
                scr = self._allocate_temp(1)
                self._copy_cell(pos_a + idx, byte_a, scr)
                self._copy_cell(pos_b + idx, byte_b, scr)
                self._free_temp(scr)

                # while a > 0 and b > 0: a--, b--
                self._move_pointer(byte_a)
                self.bf_code.append('[')
                self._move_pointer(byte_b)
                self.bf_code.append('[')
                self._move_pointer(byte_a)
                self.bf_code.append('-')
                self._move_pointer(byte_b)
                self.bf_code.append('-')
                self.bf_code.append(']')
                self.bf_code.append('[') # if b still > 0, clear both
                self._generate_clear(byte_a)
                self._generate_clear(byte_b)
                self.bf_code.append(']')
                self._move_pointer(byte_a)
                self.bf_code.append(']')

                self._generate_if_nonzero(byte_a, lambda: (
                    self._generate_set_value(1, result_gt),
                    self._generate_clear(result_eq),
                    self._generate_set_value(1, stop)
                ))
                self._generate_if_nonzero(byte_b, lambda: (
                    self._generate_set_value(1, result_lt),
                    self._generate_clear(result_eq),
                    self._generate_set_value(1, stop)
                ))
                self._free_temp(byte_b)
                self._free_temp(byte_a)

            self._generate_if_nonzero(inv_stop, _comp)
            self._free_temp(inv_stop)
        
        self._free_temp(stop)

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
        # More efficient implementation using a destructive check on a temporary copy
        carry = self._allocate_temp(1)
        self._generate_set_value(1, carry)
        
        for i in range(size):
            def _step(idx=i):
                # byte++
                self._move_pointer(pos + idx)
                self.bf_code.append('+')
                
                # if byte != 0: carry = 0
                # else: carry = 1 (remains 1)
                is_nonzero = self._allocate_temp(1)
                self._generate_clear(is_nonzero)
                
                temp = self._allocate_temp(1)
                scr = self._allocate_temp(1)
                self._copy_cell(pos + idx, temp, scr)
                self._free_temp(scr)
                
                self._move_pointer(temp)
                self.bf_code.append('[')
                self._generate_set_value(1, is_nonzero)
                self._generate_clear(temp)
                self.bf_code.append(']')
                self._free_temp(temp)
                
                # if is_nonzero: carry = 0
                self._move_pointer(is_nonzero)
                self.bf_code.append('[')
                self._generate_clear(carry)
                self._generate_clear(is_nonzero)
                self.bf_code.append(']')
                self._free_temp(is_nonzero)
                
            self._generate_if_nonzero(carry, _step)
            
        self._generate_clear(carry)
        self._free_temp(carry)

    def _decrement_multi_byte(self, pos, size=8):
        """Decrement multi-byte integer with borrow propagation."""
        borrow = self._allocate_temp(1)
        self._generate_set_value(1, borrow)
        
        for i in range(size):
            def _step(idx=i):
                # if byte == 0: byte = 255, borrow = 1
                # else: byte--, borrow = 0
                
                is_zero = self._allocate_temp(1)
                self._generate_set_value(1, is_zero)
                
                temp = self._allocate_temp(1)
                scr = self._allocate_temp(1)
                self._copy_cell(pos + idx, temp, scr)
                self._free_temp(scr)
                
                self._move_pointer(temp)
                self.bf_code.append('[')
                self._generate_clear(is_zero)
                self._generate_clear(temp)
                self.bf_code.append(']')
                self._free_temp(temp)
                
                def _on_zero():
                    self._generate_set_value(255, pos + idx)
                    # borrow remains 1
                    
                def _on_nonzero():
                    self._move_pointer(pos + idx)
                    self.bf_code.append('-')
                    self._generate_clear(borrow)
                    
                self._generate_if_nonzero(is_zero, _on_zero, body_fn_else=_on_nonzero)
                self._free_temp(is_zero)
                
            self._generate_if_nonzero(borrow, _step)
            
        self._generate_clear(borrow)
        self._free_temp(borrow)

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
