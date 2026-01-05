from __future__ import annotations


class ArithOpsMixin:
    def _handle_expression_assignment(self, expr_tokens, dest_var):
        """Handle arithmetic and bitwise expression assignment."""
        dest_info = self._resolve_var(dest_var)

        if dest_info['type'] != 'int':
            raise NotImplementedError("Expressions only supported for 'int' type")

        left, op, right = self._parse_expression(expr_tokens)

        # Unary NOT
        if op == '~':
            temp_operand = self._allocate_temp(8)
            self._load_operand(left, temp_operand)
            self._perform_bitwise_not(temp_operand, dest_info['pos'])
            self._free_temp(temp_operand)

        # Variable copy
        elif op is None and right is None:
            if not left.startswith('$'):
                raise ValueError("Direct copy requires source variable")
            src_info = self._resolve_var(left)
            self._copy_block(src_info['pos'], dest_info['pos'], 8)

        # Binary operations
        else:
            temp_left = self._allocate_temp(8)
            temp_right = self._allocate_temp(8)

            self._load_operand(left, temp_left)
            self._load_operand(right, temp_right)

            if op == '&':
                self._perform_bitwise_and(temp_left, temp_right, dest_info['pos'])
            elif op == '|':
                self._perform_bitwise_or(temp_left, temp_right, dest_info['pos'])
            elif op == '^':
                self._perform_bitwise_xor(temp_left, temp_right, dest_info['pos'])
            elif op == '+':
                self._perform_add(temp_left, temp_right, dest_info['pos'])
            elif op == '-':
                self._perform_sub(temp_left, temp_right, dest_info['pos'])
            elif op == '*':
                self._perform_mul(temp_left, temp_right, dest_info['pos'])
            elif op == '/':
                self._perform_div(temp_left, temp_right, dest_info['pos'])
            elif op == '%':
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

    def _load_operand(self, operand, target_pos):
        """Load a variable or literal into memory position."""
        op = operand[1:] if operand.startswith('$') else operand
        runtime = self._split_runtime_subscript_ref(op)
        if runtime is not None:
            base_name, idx_var = runtime
            base_info = self._resolve_var(base_name)
            if base_info['type'] != 'int' or base_info.get('elem_size', 8) != 8:
                raise NotImplementedError("Runtime-subscripted expression operands currently support only int elements")
            self._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, 8)
            return

        if operand.startswith('$'):
            var_info = self._resolve_var(operand)
            if var_info['type'] != 'int' or var_info['size'] != 8:
                raise NotImplementedError("Expression operands currently support only 8-byte int variables")
            self._copy_block(var_info['pos'], target_pos, 8)
            return

        value = int(operand)
        byte_values = value.to_bytes(8, 'little', signed=True)
        for i, byte_val in enumerate(byte_values):
            self._generate_set_value(byte_val, pos=target_pos + i)

    def _perform_bitwise_and(self, pos_a, pos_b, pos_result):
        """Perform bytewise AND on two 8-byte integers."""
        for i in range(8):
            self._bitwise_byte_operation('and', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_or(self, pos_a, pos_b, pos_result):
        """Perform bytewise OR on two 8-byte integers."""
        for i in range(8):
            self._bitwise_byte_operation('or', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_xor(self, pos_a, pos_b, pos_result):
        """Perform bytewise XOR on two 8-byte integers."""
        for i in range(8):
            self._bitwise_byte_operation('xor', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_not(self, pos_in, pos_result):
        """
        Perform bytewise NOT (255 - value) on 8-byte integer.

        BF Code Pattern:
        - Set result to 255
        - Subtract input value
        """
        temp_in = self._allocate_temp(8)
        self._copy_block(pos_in, temp_in, 8)

        for i in range(8):
            self._generate_set_value(255, pos=pos_result + i)
            # Subtract temp_in[i] from result[i]
            self._move_pointer(temp_in + i)
            self.bf_code.append('[')
            self._move_pointer(pos_result + i)
            self.bf_code.append('-')
            self._move_pointer(temp_in + i)
            self.bf_code.append('-]')

        self._free_temp(temp_in)

    def _perform_add(self, pos_a, pos_b, pos_result):
        """Perform addition on two 8-byte integers."""
        carry_flag = self._allocate_temp()

        # Clear result
        for i in range(8):
            self._generate_clear(pos_result + i)

        # Add each byte with carry propagation
        for i in range(8):
            # Copy byte A to result
            self._copy_cell(pos_a + i, pos_result + i, self._allocate_temp())
            self._free_temp(self.current_ptr)

            # Add byte B to result
            self._move_pointer(pos_b + i)
            self.bf_code.append('[')
            self._move_pointer(pos_result + i)
            self.bf_code.append('+')
            self._move_pointer(pos_b + i)
            self.bf_code.append('-]')

            # Check for overflow (if result byte wrapped around)
            # This is simplified - proper carry propagation is complex in BF
            if i < 7:  # Don't check carry on most significant byte
                self._generate_set_value(1, carry_flag)
                self._move_pointer(pos_result + i)
                self.bf_code.append('[')  # If result is non-zero, might have overflow
                self._generate_clear(carry_flag)
                self.bf_code.append(']')

                # Add carry to next byte (simplified approach)
                self._move_pointer(carry_flag)
                self.bf_code.append('[')
                self._move_pointer(pos_result + i + 1)
                self.bf_code.append('+')
                self._generate_clear(carry_flag)
                self.bf_code.append(']')

        self._free_temp(carry_flag)

    def _perform_sub(self, pos_a, pos_b, pos_result):
        """Perform subtraction (a - b) on two 8-byte integers."""
        borrow_flag = self._allocate_temp()

        # Copy A to result
        self._copy_block(pos_a, pos_result, 8)

        # Subtract B from result
        for i in range(8):
            # Subtract byte B from result byte
            self._move_pointer(pos_b + i)
            self.bf_code.append('[')
            self._move_pointer(pos_result + i)
            self.bf_code.append('-')
            self._move_pointer(pos_b + i)
            self.bf_code.append('-]')

            # Handle borrow (simplified)
            if i < 7:  # Don't borrow from most significant byte
                # Check if we need to borrow (if result underflowed)
                self._generate_set_value(1, borrow_flag)
                self._move_pointer(pos_result + i)
                self.bf_code.append('[')  # If result wrapped around
                # Add 256 and set borrow for next byte
                for _ in range(255):
                    self.bf_code.append('+')
                self._generate_clear(borrow_flag)
                self._move_pointer(pos_result + i + 1)
                self.bf_code.append('-')
                self._move_pointer(pos_result + i)
                self.bf_code.append(']')

        self._free_temp(borrow_flag)

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

    def _increment_multi_byte(self, pos):
        """Increment 8-byte integer with carry propagation."""
        carry_flag = self._allocate_temp(1)
        self._generate_set_value(1, carry_flag)

        for i in range(8):
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

    def _decrement_multi_byte(self, pos):
        """Decrement 8-byte integer with borrow propagation."""
        borrow_flag = self._allocate_temp(1)
        self._generate_set_value(1, borrow_flag)

        for i in range(8):
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

    def _sum_bytes_to_check_zero(self, pos, sum_pos, size):
        """Sum bytes to check if all are zero (non-destructive)."""
        self._generate_clear(sum_pos)
        temp_block = self._allocate_temp(size)
        self._copy_block(pos, temp_block, size)

        for i in range(size):
            self._move_pointer(temp_block + i)
            self.bf_code.append('[')
            self._move_pointer(sum_pos)
            self.bf_code.append('+')
            self._move_pointer(temp_block + i)
            self.bf_code.append('-]')

        self._free_temp(temp_block)
