from __future__ import annotations

class ArithOpsMixin:
    def _sign_extend_8_to_64(self, pos):
        """Compact sign-extend 8-bit to 64-bit."""
        is_neg = self._allocate_temp(1)
        scr = self._allocate_temp(1)
        self._generate_clear(is_neg)
        t = self._allocate_temp(1)
        self._copy_cell(pos, t, scr)
        c = self._allocate_temp(1)
        self._generate_set_value(128, c)
        self._move_pointer(t)
        self.bf_code.append('[')
        self._move_pointer(c)
        self.bf_code.append('-')
        self._move_pointer(t)
        self.bf_code.append('-]')
        self._generate_if_nonzero(c, lambda: None, body_fn_else=lambda: self._generate_set_value(1, is_neg))
        for x in [c, t]:
            self._free_temp(x)
        
        def _fill():
            for i in range(1, 8):
                self._generate_set_value(255, pos + i)
        
        for i in range(1, 8):
            self._generate_clear(pos + i)
        self._generate_if_nonzero(is_neg, _fill)
        self._free_temp(scr)
        self._free_temp(is_neg)

    def _sign_extend_16_to_64(self, pos):
        """Compact sign-extend 16-bit to 64-bit."""
        is_neg = self._allocate_temp(1)
        scr = self._allocate_temp(1)
        self._generate_clear(is_neg)
        t = self._allocate_temp(1)
        self._copy_cell(pos + 1, t, scr)
        c = self._allocate_temp(1)
        self._generate_set_value(128, c)
        self._move_pointer(t)
        self.bf_code.append('[')
        self._move_pointer(c)
        self.bf_code.append('-')
        self._move_pointer(t)
        self.bf_code.append('-]')
        self._generate_if_nonzero(c, lambda: None, body_fn_else=lambda: self._generate_set_value(1, is_neg))
        for x in [c, t]:
            self._free_temp(x)
        
        def _fill():
            for i in range(2, 8):
                self._generate_set_value(255, pos + i)
        
        for i in range(2, 8):
            self._generate_clear(pos + i)
        self._generate_if_nonzero(is_neg, _fill)
        self._free_temp(scr)
        self._free_temp(is_neg)

    def _sign_extend_8_to_16(self, pos):
        """Compact sign-extend 8-bit to 16-bit."""
        is_neg = self._allocate_temp(1)
        scr = self._allocate_temp(1)
        self._generate_clear(is_neg)
        t = self._allocate_temp(1)
        self._copy_cell(pos, t, scr)
        c = self._allocate_temp(1)
        self._generate_set_value(128, c)
        self._move_pointer(t)
        self.bf_code.append('[')
        self._move_pointer(c)
        self.bf_code.append('-')
        self._move_pointer(t)
        self.bf_code.append('-]')
        self._generate_if_nonzero(c, lambda: None, body_fn_else=lambda: self._generate_set_value(1, is_neg))
        for x in [c, t]:
            self._free_temp(x)
        self._generate_clear(pos + 1)
        self._generate_if_nonzero(is_neg, lambda: self._generate_set_value(255, pos + 1))
        self._free_temp(scr)
        self._free_temp(is_neg)

    def _handle_expression_assignment(self, expr_tokens, dest_var):
        """Handle arithmetic and bitwise expression assignment."""
        dest_info = self._resolve_var(dest_var)
        if dest_info['type'] not in ('int', 'int16', 'int64', 'float', 'float64', 'expfloat'):
            raise NotImplementedError("Expressions only supported for integer and float types")

        def _set_int64_const(value, pos):
            byte_values = int(value).to_bytes(8, 'little', signed=True)
            for i, b in enumerate(byte_values):
                self._generate_set_value(b, pos + i)

        def _is_plain_literal(tok):
            if tok.startswith('$'): return False
            if self._split_runtime_subscript_ref(tok): return False
            if tok in getattr(self, 'variables', {}): return False
            return True

        def _is_literal_zero(tok):
            if not _is_plain_literal(tok): return False
            try:
                if any(c in tok for c in ('.', 'e', 'E')):
                    return float(tok) == 0.0
                return int(tok) == 0
            except ValueError:
                return False

        def _load_operand_float_scaled(operand, target_pos):
            opnd = operand[1:] if operand.startswith('$') else operand
            runtime = self._split_runtime_subscript_ref(opnd)
            if runtime:
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
                    ts = self._allocate_temp(8)
                    self._generate_clear_block(ts, 8)
                    self._copy_block(info['pos'], ts, info['size'])
                    if info['type'] == 'int16':
                        self._sign_extend_16_to_64(ts)
                    elif info['type'] in ('byte', 'char'):
                        self._sign_extend_8_to_64(ts)

                    # Multiply by 1000 using shifts/adds (avoids relying on general mul).
                    # target = ts * 1000 = (((ts*10)*10)*10)
                    def _mul10(src_pos, dst_pos):
                        t8 = self._allocate_temp(8)
                        t2 = self._allocate_temp(8)
                        self._copy_block(src_pos, t8, 8)
                        self._copy_block(src_pos, t2, 8)
                        # t8 = src * 8
                        for _ in range(3):
                            self._shift_left_multi_byte(t8, size=8)
                        # t2 = src * 2
                        self._shift_left_multi_byte(t2, size=8)
                        # dst = t8 + t2
                        self._perform_add(t8, t2, dst_pos, size=8)
                        self._free_temp(t2)
                        self._free_temp(t8)

                    t10 = self._allocate_temp(8)
                    t100 = self._allocate_temp(8)
                    _mul10(ts, t10)
                    _mul10(t10, t100)
                    _mul10(t100, target_pos)
                    self._free_temp(t100)
                    self._free_temp(t10)
                    self._free_temp(ts)
                    return
                raise NotImplementedError(f"Unsupported source type for float conversion: {info['type']}")
            
            # For literals, scale by 1000
            if any(c in operand for c in ('.', 'e', 'E')):
                if dest_info['type'] == 'expfloat':
                    val = int(float(self._parse_expfloat_literal_scaled(operand)))
                else:
                    val = int(float(self._parse_float_literal_scaled(operand)))
            else:
                val = int(operand) * 1000
            _set_int64_const(val, target_pos)

        left, op, right = self._parse_expression(expr_tokens)
        dest_size = dest_info['size']

        if dest_info['type'] in ('float', 'float64', 'expfloat'):
            if op in ('&', '|', '^', '~', '%'):
                raise NotImplementedError(f"{dest_info['type']} expressions do not support bitwise or modulo")
            tl = self._allocate_temp(8)
            tr = self._allocate_temp(8)
            self._generate_clear_block(tl, 8)
            self._generate_clear_block(tr, 8)
            _load_operand_float_scaled(left, tl)
            
            if op is None:
                self._copy_block(tl, dest_info['pos'], 8)
            else:
                _load_operand_float_scaled(right, tr)
                if op == '+':
                    self._perform_add(tl, tr, dest_info['pos'], size=8)
                elif op == '-':
                    self._perform_sub(tl, tr, dest_info['pos'], size=8)
                elif op == '*':
                    raw = self._allocate_temp(16)
                    self._generate_clear_block(raw, 16)
                    self._perform_mul_signed(tl, tr, raw, size=8, result_size=16)
                    c1000 = self._allocate_temp(8)
                    _set_int64_const(1000, c1000)
                    self._perform_div_signed(raw, c1000, dest_info['pos'], size=8, a_size=16)
                    self._free_temp(c1000)
                    self._free_temp(raw)
                elif op == '/':
                    if _is_literal_zero(right):
                        raise ValueError("Division by zero")
                    c1000 = self._allocate_temp(8)
                    _set_int64_const(1000, c1000)
                    sl = self._allocate_temp(16)
                    self._generate_clear_block(sl, 16)
                    self._perform_mul_signed(tl, c1000, sl, size=8, result_size=16)
                    self._perform_div_signed(sl, tr, dest_info['pos'], size=8, a_size=16)
                    self._free_temp(sl)
                    self._free_temp(c1000)
            
            if dest_info['type'] == 'float':
                self._generate_runtime_range_check_r1(dest_info['pos'])
            
            self._free_temp(tr)
            self._free_temp(tl)
            return

        if op is None:
            if not left.startswith('$'):
                val = int(left)
                bytes_v = val.to_bytes(dest_size, 'little', signed=True)
                for idx, b in enumerate(bytes_v):
                    self._generate_set_value(b, dest_info['pos'] + idx)
                return
            
            si = self._resolve_var(left)
            if si['type'] in ('float', 'float64', 'expfloat'):
                c1000 = self._allocate_temp(8)
                _set_int64_const(1000, c1000)
                tq = self._allocate_temp(8)
                self._generate_clear_block(tq, 8)
                self._perform_div_signed(si['pos'], c1000, tq, size=8)
                self._copy_block(tq, dest_info['pos'], dest_size)
                self._free_temp(tq)
                self._free_temp(c1000)
                return
            
            ss = si['size']
            if ss == dest_size:
                self._copy_block(si['pos'], dest_info['pos'], dest_size)
            elif ss < dest_size:
                self._copy_block(si['pos'], dest_info['pos'], ss)
                if si['type'] == 'int16' and dest_size == 8:
                    self._sign_extend_16_to_64(dest_info['pos'])
                elif si['type'] in ('byte', 'char') and dest_size == 8:
                    self._sign_extend_8_to_64(dest_info['pos'])
                elif si['type'] in ('byte', 'char') and dest_size == 2:
                    self._sign_extend_8_to_16(dest_info['pos'])
                else:
                    for i in range(ss, dest_size):
                        self._generate_clear(dest_info['pos'] + i)
            else:
                self._copy_block(si['pos'], dest_info['pos'], dest_size)
            return

        tl = self._allocate_temp(dest_size)
        tr = self._allocate_temp(dest_size)
        self._load_operand(left, tl, size=dest_size)
        
        if op == '~':
            self._perform_bitwise_not(tl, dest_info['pos'], size=dest_size)
        else:
            self._load_operand(right, tr, size=dest_size)
            if op == '+':
                self._perform_add(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '-':
                self._perform_sub(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '*':
                self._perform_mul_signed(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '/':
                self._perform_div_signed(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '%':
                self._perform_mod_signed(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '&':
                self._perform_bitwise_and(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '|':
                self._perform_bitwise_or(tl, tr, dest_info['pos'], size=dest_size)
            elif op == '^':
                self._perform_bitwise_xor(tl, tr, dest_info['pos'], size=dest_size)
        
        self._free_temp(tr)
        self._free_temp(tl)

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
            if base_info.get('elem_size', 1) != size:
                raise NotImplementedError(f"Runtime-subscripted expression operands currently support only {size}-byte elements (got {base_info.get('elem_size')})")
            self._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, size)
            return

        if is_var:
            var_info = self._resolve_var(operand)
            if var_info['size'] != size:
                # Handle widening/narrowing load
                if var_info['size'] < size:
                    self._copy_block(var_info['pos'], target_pos, var_info['size'])
                    if var_info['type'] == 'int16' and size == 8:
                        self._sign_extend_16_to_64(target_pos)
                    elif var_info['type'] in ('byte', 'char') and size == 8:
                        self._sign_extend_8_to_64(target_pos)
                    elif var_info['type'] in ('byte', 'char') and size == 2:
                        self._sign_extend_8_to_16(target_pos)
                    else:
                        for i in range(var_info['size'], size):
                            self._generate_clear(target_pos + i)
                else:
                    # Truncate
                    self._copy_block(var_info['pos'], target_pos, size)
                return
            self._copy_block(var_info['pos'], target_pos, size)
            return

        try:
            value = int(operand)
        except ValueError:
            raise ValueError(f"Invalid operand: {operand} (not a variable or integer literal)")
            
        byte_values = value.to_bytes(size, 'little', signed=True)
        for i, b in enumerate(byte_values):
            self._generate_set_value(b, target_pos + i)

    def _generate_runtime_range_check_r1(self, pos):
        """Compact runtime range check for float R1."""
        is_neg = self._allocate_temp(1)
        self._generate_clear(is_neg)
        
        lt, gt, eq = self._allocate_temp(1), self._allocate_temp(1), self._allocate_temp(1)
        val_127 = self._allocate_temp(1)
        self._generate_set_value(127, val_127)
        self._compare_bytes_unsigned(pos + 7, val_127, lt, gt, eq)
        self._generate_if_nonzero(gt, lambda: self._generate_set_value(1, is_neg))
        for x in [val_127, eq, gt, lt]:
            self._free_temp(x)
        
        error = self._allocate_temp(1)
        self._generate_clear(error)
        
        def _check_pos():
            # positive: bytes 3-7 must be 0
            for i in range(3, 8):
                self._generate_if_nonzero(pos + i, lambda: self._generate_set_value(1, error))
        
        def _check_neg():
            # negative: bytes 3-7 must be 255
            for i in range(3, 8):
                self._generate_if_byte_equals(pos + i, 255, lambda: None, body_fn_else=lambda: self._generate_set_value(1, error))
        
        self._generate_if_nonzero(is_neg, _check_neg, body_fn_else=_check_pos)
        
        def _on_error():
            self._output_literal('"RUNTIME ERROR: float R1 overflow\\n"')
            self.bf_code.append('[#]')
            
        self._generate_if_nonzero(error, _on_error)
        self._free_temp(error)
        self._free_temp(is_neg)

    def _perform_bitwise_and(self, pos_a, pos_b, pos_res, size=8):
        """Perform bytewise AND on two multi-byte integers."""
        for i in range(size):
            self._bitwise_byte_operation('and', pos_a + i, pos_b + i, pos_res + i)

    def _perform_bitwise_or(self, pos_a, pos_b, pos_res, size=8):
        """Perform bytewise OR on two multi-byte integers."""
        for i in range(size):
            self._bitwise_byte_operation('or', pos_a + i, pos_b + i, pos_res + i)

    def _perform_bitwise_xor(self, pos_a, pos_b, pos_res, size=8):
        """Perform bytewise XOR on two multi-byte integers."""
        for i in range(size):
            self._bitwise_byte_operation('xor', pos_a + i, pos_b + i, pos_res + i)

    def _perform_bitwise_not(self, pos_in, pos_res, size=8):
        """Perform bytewise NOT (255 - value) on multi-byte integer."""
        ti = self._allocate_temp(size)
        self._copy_block(pos_in, ti, size)
        for i in range(size):
            self._generate_set_value(255, pos_res + i)
            self._move_pointer(ti + i)
            self.bf_code.append('[')
            self._move_pointer(pos_res + i)
            self.bf_code.append('-')
            self._move_pointer(ti + i)
            self.bf_code.append('-]')
        self._free_temp(ti)

    def _compare_bytes_unsigned(self, pos_a, pos_b, result_lt, result_gt, result_eq):
        """Safe and robust O(256) unsigned byte comparison."""
        self._generate_clear(result_lt)
        self._generate_clear(result_gt)
        self._generate_set_value(1, result_eq)
        ta = self._allocate_temp(1)
        tb = self._allocate_temp(1)
        s = self._allocate_temp(1)
        self._copy_cell(pos_a, ta, s)
        self._copy_cell(pos_b, tb, s)
        self._move_pointer(ta)
        self.bf_code.append('[ - ')
        
        def _on_tb():
            self._move_pointer(tb)
            self.bf_code.append('- ')
            self._move_pointer(ta)
            
        def _on_no_tb():
            self._generate_set_value(1, result_gt)
            self._generate_clear(result_eq)
            self._generate_clear(ta)
            self._move_pointer(ta)
            
        self._generate_if_nonzero(tb, _on_tb, body_fn_else=_on_no_tb)
        self._move_pointer(ta)
        self.bf_code.append(']')
        
        self._generate_if_nonzero(tb, lambda: (
            self._generate_set_value(1, result_lt),
            self._generate_clear(result_eq)
        ))
        
        for x in [s, tb, ta]:
            self._free_temp(x)

    def _bitwise_byte_operation(self, op, pos_a, pos_b, pos_result):
        """Compact bitwise operation using BF-side loop."""
        self._generate_clear(pos_result)
        ta = self._allocate_temp(1)
        tb = self._allocate_temp(1)
        s = self._allocate_temp(1)
        self._copy_cell(pos_a, ta, s)
        self._copy_cell(pos_b, tb, s)
        
        p = self._allocate_temp(1)
        cnt = self._allocate_temp(1)
        self._generate_set_value(1, p)
        self._generate_set_value(8, cnt)
        
        self._move_pointer(cnt)
        self.bf_code.append('[ - ')
        
        ba = self._allocate_temp(1)
        ra = self._allocate_temp(1)
        bb = self._allocate_temp(1)
        rb = self._allocate_temp(1)
        
        self._divmod2_cell(ta, ba, ra)
        self._divmod2_cell(tb, bb, rb)
        
        # Restore ta, tb for next bit
        self._move_pointer(ba)
        self.bf_code.append('[ - ')
        self._move_pointer(ta)
        self.bf_code.append('+ ]')
        
        self._move_pointer(bb)
        self.bf_code.append('[ - ')
        self._move_pointer(tb)
        self.bf_code.append('+ ]')
        
        rbit = self._allocate_temp(1)
        self._generate_clear(rbit)
        
        if op == 'and':
            self._generate_if_nonzero(ra, lambda: self._generate_if_nonzero(rb, lambda: self._generate_set_value(1, rbit)))
        elif op == 'or':
            self._generate_if_nonzero(ra, lambda: self._generate_set_value(1, rbit), 
                                     body_fn_else=lambda: self._generate_if_nonzero(rb, lambda: self._generate_set_value(1, rbit)))
        elif op == 'xor':
            self._generate_if_nonzero(ra, 
                                     lambda: self._generate_if_nonzero(rb, lambda: None, body_fn_else=lambda: self._generate_set_value(1, rbit)), 
                                     body_fn_else=lambda: self._generate_if_nonzero(rb, lambda: self._generate_set_value(1, rbit)))
            
        def _on_rbit():
            sc = self._allocate_temp(1)
            self._add_cell(p, pos_result, sc)
            self._free_temp(sc)
            
        self._generate_if_nonzero(rbit, _on_rbit)
        
        # Shift p left (p *= 2)
        sc2 = self._allocate_temp(1)
        self._add_cell(p, p, sc2)
        self._free_temp(sc2)
        
        for x in [rbit, rb, bb, ra, ba]:
            self._free_temp(x)
            
        self._move_pointer(cnt)
        self.bf_code.append(']')
        
        for x in [cnt, p, s, tb, ta]:
            self._free_temp(x)

    def _perform_add(self, pos_a, pos_b, pos_res, size=8):
        """Robust multi-byte addition using O(256) wrap detection."""
        ta = self._allocate_temp(size)
        tb = self._allocate_temp(size)
        tr = self._allocate_temp(size)
        carry = self._allocate_temp(1)
        
        self._copy_block(pos_a, ta, size)
        self._copy_block(pos_b, tb, size)
        self._generate_clear_block(tr, size)
        self._generate_clear(carry)
        
        for i in range(size):
            target = tr + i
            scr = self._allocate_temp(1)
            self._copy_cell(ta + i, target, scr)
            self._free_temp(scr)
            
            # Current carry bit for this byte
            nc = self._allocate_temp(1)
            self._generate_clear(nc)
            
            def _on_carry():
                self._generate_if_byte_equals(target, 255, lambda: self._generate_set_value(1, nc))
                self._move_pointer(target)
                self.bf_code.append('+')
                
            self._generate_if_nonzero(carry, _on_carry)
            
            tv = self._allocate_temp(1)
            s2 = self._allocate_temp(1)
            self._copy_cell(tb + i, tv, s2)
            self._free_temp(s2)
            
            self._move_pointer(tv)
            self.bf_code.append('[ - ')
            self._generate_if_byte_equals(target, 255, lambda: self._generate_set_value(1, nc))
            self._move_pointer(target)
            self.bf_code.append('+')
            self._move_pointer(tv)
            self.bf_code.append(']')
            self._free_temp(tv)
            
            # Carry bit for next byte is in nc
            self._generate_clear(carry)
            self._move_pointer(nc)
            self.bf_code.append('[ - ')
            self._move_pointer(carry)
            self.bf_code.append('+ ')
            self._move_pointer(nc)
            self.bf_code.append(']')
            self._free_temp(nc)
            
        self._copy_block(tr, pos_res, size)
        for x in [carry, tr, tb, ta]:
            self._free_temp(x)

    def _perform_sub(self, pos_a, pos_b, pos_res, size=8):
        """Robust multi-byte subtraction using O(256) borrow detection."""
        ta = self._allocate_temp(size)
        tb = self._allocate_temp(size)
        tr = self._allocate_temp(size)
        borrow = self._allocate_temp(1)
        
        self._copy_block(pos_a, ta, size)
        self._copy_block(pos_b, tb, size)
        self._generate_clear_block(tr, size)
        self._generate_clear(borrow)
        
        for i in range(size):
            target = tr + i
            scr = self._allocate_temp(1)
            self._copy_cell(ta + i, target, scr)
            self._free_temp(scr)
            
            # Current borrow bit for this byte
            nb = self._allocate_temp(1)
            self._generate_clear(nb)
            
            def _on_borrow():
                self._generate_if_byte_equals(target, 0, lambda: self._generate_set_value(1, nb))
                self._move_pointer(target)
                self.bf_code.append('-')
                
            self._generate_if_nonzero(borrow, _on_borrow)
            
            tv = self._allocate_temp(1)
            s2 = self._allocate_temp(1)
            self._copy_cell(tb + i, tv, s2)
            self._free_temp(s2)
            
            self._move_pointer(tv)
            self.bf_code.append('[ - ')
            self._generate_if_byte_equals(target, 0, lambda: self._generate_set_value(1, nb))
            self._move_pointer(target)
            self.bf_code.append('-')
            self._move_pointer(tv)
            self.bf_code.append(']')
            self._free_temp(tv)
            
            # Borrow bit for next byte is in nb
            self._generate_clear(borrow)
            self._move_pointer(nb)
            self.bf_code.append('[ - ')
            self._move_pointer(borrow)
            self.bf_code.append('+ ')
            self._move_pointer(nb)
            self.bf_code.append(']')
            self._free_temp(nb)
            
        self._copy_block(tr, pos_res, size)
        for x in [borrow, tr, tb, ta]:
            self._free_temp(x)

    def _compare_multi_byte_unsigned(self, pos_a, pos_b, result_lt, result_gt, result_eq, size=8):
        """Compare two multi-byte unsigned integers."""
        self._generate_clear(result_lt)
        self._generate_clear(result_gt)
        self._generate_set_value(1, result_eq)
        for i in reversed(range(size)):
            self._generate_if_nonzero(result_eq, lambda idx=i: self._compare_bytes_and_update(pos_a + idx, pos_b + idx, result_lt, result_gt, result_eq))

    def _compare_bytes_and_update(self, p1, p2, r_lt, r_gt, r_eq):
        """Helper for multi-byte comparison."""
        lt = self._allocate_temp(1)
        gt = self._allocate_temp(1)
        eq = self._allocate_temp(1)
        self._compare_bytes_unsigned(p1, p2, lt, gt, eq)
        self._generate_if_nonzero(lt, lambda: (self._generate_set_value(1, r_lt), self._generate_clear(r_eq)))
        self._generate_if_nonzero(gt, lambda: (self._generate_set_value(1, r_gt), self._generate_clear(r_eq)))
        for x in [eq, gt, lt]:
            self._free_temp(x)

    def _shift_left_multi_byte(self, pos, size=8):
        """Compact multi-byte left shift."""
        carry = self._allocate_temp(1)
        self._generate_clear(carry)
        for i in range(size):
            target = pos + i

            # nc = 1 if target >= 128 else 0
            nc = self._allocate_temp(1)
            self._generate_clear(nc)
            const128 = self._allocate_temp(1)
            self._generate_set_value(128, const128)
            lt = self._allocate_temp(1)
            gt = self._allocate_temp(1)
            eq = self._allocate_temp(1)
            self._compare_bytes_unsigned(target, const128, lt, gt, eq)
            self._generate_if_nonzero(gt, lambda: self._generate_set_value(1, nc))
            self._generate_if_nonzero(eq, lambda: self._generate_set_value(1, nc))
            for x in [eq, gt, lt, const128]:
                self._free_temp(x)

            # target = (target * 2) + carry
            scr = self._allocate_temp(1)
            self._add_cell(target, target, scr)
            self._add_cell(carry, target, scr)
            self._free_temp(scr)

            # carry = nc
            self._generate_clear(carry)
            self._move_pointer(nc)
            self.bf_code.append('[ - ')
            self._move_pointer(carry)
            self.bf_code.append('+ ')
            self._move_pointer(nc)
            self.bf_code.append(']')
            self._free_temp(nc)

        self._free_temp(carry)

    def _shift_right_multi_byte(self, pos, size=8):
        """Compact multi-byte right shift."""
        carry = self._allocate_temp(1)
        self._generate_clear(carry)
        for i in reversed(range(size)):
            target = pos + i
            q = self._allocate_temp(1)
            r = self._allocate_temp(1)
            self._divmod2_cell(target, q, r)
            self._generate_clear(target)
            scr = self._allocate_temp(1)
            self._add_cell(q, target, scr)
            self._generate_if_nonzero(carry, lambda: (self._move_pointer(target), self.bf_code.append('+' * 128)))
            self._free_temp(scr)
            self._generate_clear(carry)
            self._move_pointer(r)
            self.bf_code.append('[ - ')
            self._move_pointer(carry)
            self.bf_code.append('+ ')
            self._move_pointer(r)
            self.bf_code.append(']')
            for x in [r, q]:
                self._free_temp(x)
        self._free_temp(carry)

    def _get_bit_multi_byte(self, pos, bit_idx, result_pos, size=8):
        """Compact bit extraction using BF-side shift loop."""
        byte_idx, bit_in_byte = bit_idx // 8, bit_idx % 8
        if byte_idx >= size:
            self._generate_clear(result_pos)
            return
        tb = self._allocate_temp(1)
        s = self._allocate_temp(1)
        self._copy_cell(pos + byte_idx, tb, s)
        if bit_in_byte > 0:
            cnt = self._allocate_temp(1)
            self._generate_set_value(bit_in_byte, cnt)
            self._move_pointer(cnt)
            self.bf_code.append('[ - ')
            q = self._allocate_temp(1)
            r = self._allocate_temp(1)
            self._divmod2_cell(tb, q, r)
            self._move_pointer(q)
            self.bf_code.append('[ - ')
            self._move_pointer(tb)
            self.bf_code.append('+ ]')
            for x in [r, q]:
                self._free_temp(x)
            self._move_pointer(cnt)
            self.bf_code.append(']')
            self._free_temp(cnt)
        q = self._allocate_temp(1)
        r = self._allocate_temp(1)
        self._divmod2_cell(tb, q, r)
        self._copy_cell(r, result_pos, s)
        for x in [r, q, s, tb]:
            self._free_temp(x)

    def _set_bit_multi_byte(self, pos, bit_idx, value_pos, size=8):
        """Compact bit setting."""
        byte_idx, bit_in_byte = bit_idx // 8, bit_idx % 8
        if byte_idx >= size: return
        mask_val = 1 << bit_in_byte
        m = self._allocate_temp(1)
        self._generate_set_value(mask_val, m)
        def _set():
            self._bitwise_byte_operation('or', pos + byte_idx, m, pos + byte_idx)
        def _clr():
            nm = self._allocate_temp(1)
            self._generate_set_value(255 ^ mask_val, nm)
            self._bitwise_byte_operation('and', pos + byte_idx, nm, pos + byte_idx)
            self._free_temp(nm)
        self._generate_if_nonzero(value_pos, _set, body_fn_else=_clr)
        self._free_temp(m)

    def _generate_clear_block(self, pos, size):
        """Clear a block of memory."""
        for i in range(size):
            self._generate_clear(pos + i)

    def _allocate_temp_const(self, val):
        """Allocate a temporary cell and set it to a constant value."""
        if not hasattr(self, '_temp_const_stack'):
            self._temp_const_stack = []
        t = self._allocate_temp(1)
        self._generate_set_value(val, t)
        self._temp_const_stack.append(t)
        return t

    def _free_temp_const(self):
        """Free the last allocated constant temporary cell."""
        if not hasattr(self, '_temp_const_stack') or not self._temp_const_stack:
            return
        t = self._temp_const_stack.pop()
        self._free_temp(t)

    def _perform_div(self, pos_a, pos_b, pos_result, size=8):
        """Perform integer division on multi-byte integers."""
        q = self._allocate_temp(size)
        r = self._allocate_temp(size)
        self._perform_divmod_multi_byte(pos_a, pos_b, q, r, size=size)
        self._copy_block(q, pos_result, size)
        for x in [r, q]:
            self._free_temp(x)

    def _perform_mod(self, pos_a, pos_b, pos_result, size=8):
        """Perform modulo operation on multi-byte integers."""
        q = self._allocate_temp(size)
        r = self._allocate_temp(size)
        self._perform_divmod_multi_byte(pos_a, pos_b, q, r, size=size)
        self._copy_block(r, pos_result, size)
        for x in [r, q]:
            self._free_temp(x)

    def _perform_mul_signed(self, pos_a, pos_b, pos_result, size=8, result_size=None):
        """Perform signed multiplication on multi-byte integers."""
        if result_size is None:
            result_size = size
        sa = self._allocate_temp(1)
        sb = self._allocate_temp(1)
        ma = self._allocate_temp(size)
        mb = self._allocate_temp(size)
        self._get_sign_and_abs(pos_a, sa, ma, size=size)
        self._get_sign_and_abs(pos_b, sb, mb, size=size)
        rm = self._allocate_temp(result_size)
        self._perform_mul(ma, mb, rm, size=size, result_size=result_size)
        rs = self._allocate_temp(1)
        self._bitwise_byte_operation('xor', sa, sb, rs)
        self._apply_sign(rm, rs, pos_result, size=result_size)
        for x in [rs, rm, mb, ma, sb, sa]:
            self._free_temp(x)

    def _perform_mul(self, pos_a, pos_b, pos_result, size=8, result_size=None):
        """Russian Peasant multiplication with optimized multi-byte loop."""
        if result_size is None:
            result_size = size
        ta = self._allocate_temp(result_size)
        tb = self._allocate_temp(size)
        tr = self._allocate_temp(result_size)
        self._generate_clear_block(ta, result_size)
        self._copy_block(pos_a, ta, size)
        self._copy_block(pos_b, tb, size)
        self._generate_clear_block(tr, result_size)
        for bit in range(size * 8):
            lsb = self._allocate_temp(1)
            q = self._allocate_temp(1)
            r = self._allocate_temp(1)
            self._copy_cell(tb, lsb, r)
            self._generate_clear(q)
            self._generate_clear(r)
            self._divmod2_cell(lsb, q, r)
            self._generate_if_nonzero(r, lambda: self._perform_add(tr, ta, tr, size=result_size))
            self._shift_left_multi_byte(ta, size=result_size)
            self._shift_right_multi_byte(tb, size=size)
            for x in [r, q, lsb]:
                self._free_temp(x)
        self._copy_block(tr, pos_result, result_size)
        for x in [tr, tb, ta]:
            self._free_temp(x)

    def _perform_div_signed(self, pos_a, pos_b, pos_res, size=8, a_size=None):
        """Perform signed division on multi-byte integers."""
        if a_size is None:
            a_size = size
        q = self._allocate_temp(a_size)
        r = self._allocate_temp(size)
        self._perform_divmod_signed(pos_a, pos_b, q, r, size=size, a_size=a_size)
        self._copy_block(q, pos_res, a_size)
        for x in [r, q]:
            self._free_temp(x)

    def _perform_mod_signed(self, pos_a, pos_b, pos_res, size=8):
        """Perform signed modulo on multi-byte integers."""
        q = self._allocate_temp(size)
        r = self._allocate_temp(size)
        self._perform_divmod_signed(pos_a, pos_b, q, r, size=size)
        self._copy_block(r, pos_res, size)
        for x in [r, q]:
            self._free_temp(x)

    def _perform_divmod_signed(self, pos_a, pos_b, pos_q, pos_r, size=8, a_size=None):
        """Perform signed divmod on multi-byte integers."""
        if a_size is None:
            a_size = size
        sa = self._allocate_temp(1)
        sb = self._allocate_temp(1)
        ma = self._allocate_temp(a_size)
        mb = self._allocate_temp(size)
        self._get_sign_and_abs(pos_a, sa, ma, size=a_size)
        self._get_sign_and_abs(pos_b, sb, mb, size=size)
        qm = self._allocate_temp(a_size)
        rm = self._allocate_temp(size)
        self._perform_divmod_multi_byte(ma, mb, qm, rm, size=size, a_size=a_size)
        qs = self._allocate_temp(1)
        self._bitwise_byte_operation('xor', sa, sb, qs)
        self._apply_sign(qm, qs, pos_q, size=a_size)
        self._apply_sign(rm, sa, pos_r, size=size)
        for x in [qs, rm, qm, mb, ma, sb, sa]:
            self._free_temp(x)

    def _perform_divmod_multi_byte(self, pos_a, pos_b, pos_q, pos_r, size=8, a_size=None):
        """Standard bit-by-bit long division using BF-side shift loop."""
        if a_size is None:
            a_size = size
        self._generate_clear_block(pos_q, a_size)
        self._generate_clear_block(pos_r, size)
        
        izb = self._allocate_temp(1)
        self._generate_set_value(1, izb)
        for i in range(size):
            self._generate_if_nonzero(pos_b + i, lambda: self._generate_clear(izb))
            
        nzb = self._allocate_temp(1)
        self._generate_set_value(1, nzb)
        self._generate_if_nonzero(izb, lambda: self._generate_clear(nzb))
        
        def _div_logic():
            ta = self._allocate_temp(a_size)
            self._copy_block(pos_a, ta, a_size)
            for bit in reversed(range(a_size * 8)):
                self._shift_left_multi_byte(pos_r, size)
                bv = self._allocate_temp(1)
                self._get_bit_multi_byte(ta, bit, bv, size=a_size)
                self._generate_if_nonzero(bv, lambda: (self._move_pointer(pos_r), self.bf_code.append('+')))
                self._free_temp(bv)
                
                lt = self._allocate_temp(1)
                gt = self._allocate_temp(1)
                eq = self._allocate_temp(1)
                self._compare_multi_byte_unsigned(pos_r, pos_b, lt, gt, eq, size=size)
                
                not_lt = self._allocate_temp(1)
                self._generate_set_value(1, not_lt)
                self._generate_if_nonzero(lt, lambda: self._generate_clear(not_lt))
                
                def _on_ge():
                    self._perform_sub(pos_r, pos_b, pos_r, size)
                    one = self._allocate_temp(1)
                    self._generate_set_value(1, one)
                    self._set_bit_multi_byte(pos_q, bit, one, size=a_size)
                    self._free_temp(one)
                    
                self._generate_if_nonzero(not_lt, _on_ge)
                for x in [not_lt, eq, gt, lt]:
                    self._free_temp(x)
            self._free_temp(ta)
            
        self._generate_if_nonzero(nzb, _div_logic)
        for x in [nzb, izb]:
            self._free_temp(x)

    def _get_sign_and_abs(self, pos, sign_pos, abs_pos, size=8):
        """Extract sign bit and absolute value of a multi-byte integer."""
        self._generate_clear(sign_pos)
        self._copy_block(pos, abs_pos, size)
        
        t128 = self._allocate_temp(1)
        lt = self._allocate_temp(1)
        gt = self._allocate_temp(1)
        eq = self._allocate_temp(1)
        
        self._generate_set_value(128, t128)
        self._compare_bytes_unsigned(pos + size - 1, t128, lt, gt, eq)
        
        ge128 = self._allocate_temp(1)
        self._generate_set_value(1, ge128)
        self._generate_if_nonzero(lt, lambda: self._generate_clear(ge128))
        
        def _to_abs():
            self._generate_set_value(1, sign_pos)
            tn = self._allocate_temp(size)
            self._perform_bitwise_not(abs_pos, tn, size=size)
            self._copy_block(tn, abs_pos, size)
            self._free_temp(tn)
            self._increment_multi_byte(abs_pos, size=size)
            
        self._generate_if_nonzero(ge128, _to_abs)
        for x in [ge128, eq, gt, lt, t128]:
            self._free_temp(x)

    def _apply_sign(self, mag_pos, sign_pos, res_pos, size=8):
        """Apply sign to magnitude to get signed result."""
        self._copy_block(mag_pos, res_pos, size)
        
        def _negate():
            tn = self._allocate_temp(size)
            self._perform_bitwise_not(res_pos, tn, size=size)
            self._copy_block(tn, res_pos, size)
            self._free_temp(tn)
            self._increment_multi_byte(res_pos, size=size)
            
        self._generate_if_nonzero(sign_pos, _negate)

    def _divmod2_cell(self, pos_in, pos_q, pos_r):
        """BF divmod 2: q = in // 2, r = in % 2. Destroys in.

        Implemented as a toggle:
        - Each decrement of input toggles r between 0 and 1
        - Every time r toggles from 1->0 we increment q
        """
        self._generate_clear(pos_q)
        self._generate_clear(pos_r)

        # flag is set to 1 each iteration; cleared if we took the 'r was 1' branch.
        flag = self._allocate_temp(1)
        self._generate_clear(flag)

        self._move_pointer(pos_in)
        self.bf_code.append('[')
        self.bf_code.append('-')

        # flag = 1
        self._move_pointer(flag)
        self.bf_code.append('+')

        # if r != 0: r-- ; q++ ; flag--
        self._move_pointer(pos_r)
        self.bf_code.append('[')
        self.bf_code.append('-')
        self._move_pointer(pos_q)
        self.bf_code.append('+')
        self._move_pointer(flag)
        self.bf_code.append('-')
        self._move_pointer(pos_r)
        self.bf_code.append(']')

        # if flag != 0: flag-- ; r++
        self._move_pointer(flag)
        self.bf_code.append('[')
        self.bf_code.append('-')
        self._move_pointer(pos_r)
        self.bf_code.append('+')
        self._move_pointer(flag)
        self.bf_code.append(']')

        self._move_pointer(pos_in)
        self.bf_code.append(']')

        self._free_temp(flag)

    def _increment_multi_byte(self, pos, size=8):
        """Increment multi-byte integer with carry propagation."""
        carry = self._allocate_temp(1)
        self._generate_set_value(1, carry)
        for i in range(size):
            def _step(idx=i):
                # Increment current byte
                self._move_pointer(pos + idx)
                self.bf_code.append('+')
                
                # Check if it's non-zero (didn't wrap 255 -> 0)
                nz = self._allocate_temp(1)
                t = self._allocate_temp(1)
                scr = self._allocate_temp(1)
                self._generate_clear(nz)
                self._copy_cell(pos + idx, t, scr)
                self._free_temp(scr)
                
                self._move_pointer(t)
                self.bf_code.append('[')
                self._generate_set_value(1, nz)
                self._generate_clear(t)
                self.bf_code.append(']')
                self._free_temp(t)
                
                # If non-zero, clear carry
                self._generate_if_nonzero(nz, lambda: self._generate_clear(carry))
                self._free_temp(nz)
                
            self._generate_if_nonzero(carry, _step)
        self._free_temp(carry)

    def _decrement_multi_byte(self, pos, size=8):
        """Decrement multi-byte integer with borrow propagation."""
        borrow = self._allocate_temp(1)
        self._generate_set_value(1, borrow)
        for i in range(size):
            def _step(idx=i):
                # Check if current byte is zero
                iz = self._allocate_temp(1)
                t = self._allocate_temp(1)
                scr = self._allocate_temp(1)
                self._generate_set_value(1, iz)
                self._copy_cell(pos + idx, t, scr)
                self._free_temp(scr)
                self._move_pointer(t)
                self.bf_code.append('[')
                self._generate_clear(iz)
                self._generate_clear(t)
                self.bf_code.append(']')
                self._free_temp(t)
                
                # Use a flag to track if we should clear borrow
                should_clear_borrow = self._allocate_temp(1)
                self._generate_clear(should_clear_borrow)
                
                def _on_zero():
                    # 0 -> 255, borrow remains 1
                    self._generate_set_value(255, pos + idx)
                    
                def _on_nonzero():
                    # Non-zero: decrement and mark borrow for clearing
                    self._move_pointer(pos + idx)
                    self.bf_code.append('-')
                    self._generate_set_value(1, should_clear_borrow)
                    
                self._generate_if_nonzero(iz, _on_zero, body_fn_else=_on_nonzero)
                
                # If we decremented a non-zero byte, clear the borrow for the next byte
                self._generate_if_nonzero(should_clear_borrow, lambda: self._generate_clear(borrow))
                
                self._free_temp(should_clear_borrow)
                self._free_temp(iz)
                
            self._generate_if_nonzero(borrow, _step)
        self._free_temp(borrow)

    def _divmod10_multi_byte(self, pos_in, pos_quotient, rem_pos, size=8):
        """Standard long division by 10 for multi-byte output."""
        self._generate_clear_block(pos_quotient, size)
        self._generate_clear(rem_pos)
        
        # Working buffer
        temp_val = self._allocate_temp(size)
        self._copy_block(pos_in, temp_val, size)
        
        for i in reversed(range(size)):
            # 1. Carry from previous byte
            if i < size - 1:
                # new_val = rem * 256 + current_byte
                # new_val // 10 = (rem * 25) + (current_byte + rem * 6) // 10
                # new_val % 10 = (current_byte + rem * 6) % 10
                r_val = self._allocate_temp(1)
                s = self._allocate_temp(1)
                self._copy_cell(rem_pos, r_val, s)
                self._free_temp(s)
                
                self._move_pointer(r_val)
                self.bf_code.append('[ - ')
                for _ in range(25):
                    self._move_pointer(pos_quotient + i)
                    self.bf_code.append('+')
                for _ in range(6):
                    self._move_pointer(temp_val + i)
                    self.bf_code.append('+')
                self._move_pointer(r_val)
                self.bf_code.append(']')
                self._free_temp(r_val)
                self._generate_clear(rem_pos)

            # 2. Single-byte divmod 10 on the accumulated value
            # while temp_val[i] >= 10: temp_val[i] -= 10, pos_quotient[i]++
            # then rem_pos = temp_val[i]
            t1 = self._allocate_temp(1)
            t2 = self._allocate_temp(1)
            
            self._move_pointer(temp_val + i)
            self.bf_code.append('[')
            
            # Check if value >= 10
            self._generate_clear(t1)
            self._generate_clear(t2)
            
            # Use a more direct check for >= 10 to be efficient
            # if val >= 10: val -= 10, quot++
            # else: rem = val, val = 0 (break)
            is_ge_10 = self._allocate_temp(1)
            lt, gt, eq = self._allocate_temp(1), self._allocate_temp(1), self._allocate_temp(1)
            c9 = self._allocate_temp(1)
            self._generate_set_value(9, c9)
            self._compare_bytes_unsigned(temp_val + i, c9, lt, gt, eq)
            
            self._generate_clear(is_ge_10)
            self._generate_if_nonzero(gt, lambda: self._generate_set_value(1, is_ge_10))
            self._generate_if_nonzero(eq, lambda: None)
            
            def _on_ge():
                self._move_pointer(temp_val + i)
                self.bf_code.append('----------')
                self._move_pointer(pos_quotient + i)
                self.bf_code.append('+')
                
            def _on_lt():
                sc = self._allocate_temp(1)
                self._copy_cell(temp_val + i, rem_pos, sc)
                self._free_temp(sc)
                self._generate_clear(temp_val + i)
                
            self._generate_if_nonzero(is_ge_10, _on_ge, body_fn_else=_on_lt)
            
            for x in [c9, eq, gt, lt, is_ge_10]:
                self._free_temp(x)
                
            self._move_pointer(temp_val + i)
            self.bf_code.append(']')
            
            self._free_temp(t2)
            self._free_temp(t1)
            
        self._free_temp(temp_val)
