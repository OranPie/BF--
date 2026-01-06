from __future__ import annotations

from decimal import Decimal, InvalidOperation


class ControlFlowMixin:
    def _extract_parentheses_content(self, tokens):
        if '(' not in tokens:
            return tokens

        start = tokens.index('(')
        balance = 1
        end = -1

        for i in range(start + 1, len(tokens)):
            if tokens[i] == '(':
                balance += 1
            elif tokens[i] == ')':
                balance -= 1
                if balance == 0:
                    end = i
                    break

        if end == -1:
            raise ValueError('Mismatched parentheses')

        return tokens[start + 1:end]

    def _process_block(self, lines, start_idx):
        i = start_idx

        if i < len(lines) and lines[i].strip() == '{':
            i += 1

        depth = 0
        while i < len(lines):
            line = lines[i].strip()
            if '}' in line:
                if depth == 0:
                    return i
                depth -= 1
            if '{' in line:
                depth += 1

            tokens = self._tokenize(line)
            if tokens:
                i = self._process_statement(tokens, lines, i)
            i += 1

        return i - 1

    def _handle_if_statement(self, tokens, lines, line_idx):
        if 'then' in tokens:
            then_idx = tokens.index('then')
            cond_tokens = self._extract_parentheses_content(tokens[:then_idx])

            depth = 0
            else_line = None
            end_line = len(lines) - 1
            i = line_idx + 1
            while i < len(lines):
                t = self._tokenize(lines[i].strip())
                if not t:
                    i += 1
                    continue
                cmd = t[0].lower()
                if cmd == 'if' and 'then' in t:
                    depth += 1
                elif cmd == 'endif':
                    if depth == 0:
                        end_line = i
                        break
                    depth -= 1
                elif cmd == 'else' and depth == 0:
                    else_line = i
                i += 1

            cond_flag = self._allocate_temp()
            else_flag = self._allocate_temp()

            self._evaluate_condition(cond_tokens, cond_flag)
            self._generate_set_value(1, pos=else_flag)

            self._move_pointer(cond_flag)
            self.bf_code.append('[')
            self._generate_clear(else_flag)

            if else_line is None:
                self._process_lines_range(lines, line_idx + 1, end_line - 1)
            else:
                self._process_lines_range(lines, line_idx + 1, else_line - 1)

            self._generate_clear(cond_flag)
            self.bf_code.append(']')

            self._move_pointer(else_flag)
            self.bf_code.append('[')
            if else_line is not None:
                self._process_lines_range(lines, else_line + 1, end_line - 1)
            self._generate_clear(else_flag)
            self.bf_code.append(']')

            self._free_temp(else_flag)
            self._free_temp(cond_flag)
            return end_line

        cond_tokens = self._extract_parentheses_content(tokens)

        cond_flag = self._allocate_temp()
        else_flag = self._allocate_temp()

        self._evaluate_condition(cond_tokens, cond_flag)
        self._generate_set_value(1, pos=else_flag)

        self._move_pointer(cond_flag)
        self.bf_code.append('[')
        self._generate_clear(else_flag)
        if_end = self._process_block(lines, line_idx + 1)
        self._generate_clear(cond_flag)
        self.bf_code.append(']')

        has_else = False
        next_idx = if_end + 1
        if if_end < len(lines):
            end_line_tokens = self._tokenize(lines[if_end].strip())
            has_else = 'else' in end_line_tokens

        self._move_pointer(else_flag)
        self.bf_code.append('[')
        if has_else:
            else_end = self._process_block(lines, if_end + 1)
            next_idx = else_end + 1
        self._generate_clear(else_flag)
        self.bf_code.append(']')

        self._free_temp(else_flag)
        self._free_temp(cond_flag)

        return next_idx - 1

    def _handle_while_loop(self, tokens, lines, line_idx):
        if 'do' in tokens:
            do_idx = tokens.index('do')
            cond_tokens = self._extract_parentheses_content(tokens[:do_idx])

            depth = 0
            end_line = len(lines) - 1
            i = line_idx + 1
            while i < len(lines):
                t = self._tokenize(lines[i].strip())
                if not t:
                    i += 1
                    continue
                cmd = t[0].lower()
                if cmd in ('while', 'loop') and 'do' in t:
                    depth += 1
                elif cmd == 'endwhile':
                    if depth == 0:
                        end_line = i
                        break
                    depth -= 1
                i += 1

            cond_flag = self._allocate_temp()
            self.loop_condition_stack.append(cond_flag)

            self._evaluate_condition(cond_tokens, cond_flag)

            self._move_pointer(cond_flag)
            self.bf_code.append('[')

            self._process_lines_range(lines, line_idx + 1, end_line - 1)

            check_temp = self._allocate_temp()
            copy_temp = self._allocate_temp()
            self._copy_cell(cond_flag, check_temp, copy_temp)
            self._free_temp(copy_temp)

            self._move_pointer(check_temp)
            self.bf_code.append('[')
            self._generate_clear(cond_flag)
            self._evaluate_condition(cond_tokens, cond_flag)
            self._generate_clear(check_temp)
            self.bf_code.append(']')

            self._free_temp(check_temp)

            self._move_pointer(cond_flag)
            self.bf_code.append(']')

            self.loop_condition_stack.pop()
            self._free_temp(cond_flag)

            return end_line

        cond_tokens = self._extract_parentheses_content(tokens)

        cond_flag = self._allocate_temp()
        self.loop_condition_stack.append(cond_flag)

        self._evaluate_condition(cond_tokens, cond_flag)

        self._move_pointer(cond_flag)
        self.bf_code.append('[')

        end_line = self._process_block(lines, line_idx + 1)

        check_temp = self._allocate_temp()
        copy_temp = self._allocate_temp()
        self._copy_cell(cond_flag, check_temp, copy_temp)
        self._free_temp(copy_temp)

        self._move_pointer(check_temp)
        self.bf_code.append('[')
        self._generate_clear(cond_flag)
        self._evaluate_condition(cond_tokens, cond_flag)
        self._generate_clear(check_temp)
        self.bf_code.append(']')

        self._free_temp(check_temp)

        self._move_pointer(cond_flag)
        self.bf_code.append(']')

        self.loop_condition_stack.pop()
        self._free_temp(cond_flag)

        return end_line

    def _handle_for_loop(self, tokens, lines, line_idx):
        paren_tokens = self._extract_parentheses_content(tokens)

        semi_indices = [i for i, t in enumerate(paren_tokens) if t == ';']
        if len(semi_indices) != 2:
            raise ValueError('For loop requires (init; condition; step)')

        init_tokens = paren_tokens[:semi_indices[0]]
        cond_tokens = paren_tokens[semi_indices[0] + 1:semi_indices[1]]
        step_tokens = paren_tokens[semi_indices[1] + 1:]

        if init_tokens:
            self._process_statement(init_tokens, [], 0)

        cond_flag = self._allocate_temp()
        self.loop_condition_stack.append(cond_flag)

        self._evaluate_condition(cond_tokens, cond_flag)
        self._move_pointer(cond_flag)
        self.bf_code.append('[')

        end_line = self._process_block(lines, line_idx + 1)

        if step_tokens:
            self._process_statement(step_tokens, [], 0)

        self._evaluate_condition(cond_tokens, cond_flag)
        self._move_pointer(cond_flag)
        self.bf_code.append(']')

        self.loop_condition_stack.pop()
        self._free_temp(cond_flag)

        return end_line

    def _handle_break(self):
        if not self.loop_condition_stack:
            raise RuntimeError('Break used outside of loop')
        cond_flag = self.loop_condition_stack[-1]
        self._generate_clear(cond_flag)

    def _handle_match_statement(self, tokens, lines, line_idx):
        # Syntax supported:
        #   match (<expr>) { case <val>: ... ; default: ... }
        # or
        #   match (<expr>)
        #     case <val>: ...
        #     default: ...
        #   endmatch
        #
        # No fallthrough; first match wins.

        subject_tokens = self._extract_parentheses_content(tokens)
        if not subject_tokens:
            raise ValueError('match requires a subject expression in parentheses')
        if len(subject_tokens) != 1:
            raise NotImplementedError('match subject currently supports a single token (var or literal)')
        subject = subject_tokens[0]

        # For now, require the subject to be a scalar variable (or $var).
        subj_ref = subject[1:] if subject.startswith('$') else subject
        if subj_ref.lstrip('-').isdigit():
            raise NotImplementedError('match subject does not support numeric literals yet; use a variable')
        subj_info = self._resolve_var(subject)
        if subj_info['type'] not in ('int', 'int16', 'int64', 'byte', 'char'):
            raise NotImplementedError('match subject currently supports only integer and byte/char variables')
        subj_size = subj_info['size']

        def _find_brace_block_end(start_idx: int) -> int:
            # start_idx points at a line containing an opening '{'.
            depth = 0
            i = start_idx
            while i < len(lines):
                s = lines[i]
                if '{' in s:
                    depth += s.count('{')
                if '}' in s:
                    depth -= s.count('}')
                    if depth <= 0:
                        return i
                i += 1
            return len(lines) - 1

        end_line = None
        match_body_start = None
        match_body_end = None  # inclusive

        if '{' in tokens:
            # Brace form: '{' is on the match line.
            end_line = _find_brace_block_end(line_idx)
            match_body_start = line_idx + 1
            match_body_end = end_line - 1
        else:
            # endmatch form
            depth = 0
            i = line_idx + 1
            end_line = len(lines) - 1
            while i < len(lines):
                t = self._tokenize(lines[i].strip())
                if not t:
                    i += 1
                    continue
                cmd = t[0].lower().rstrip(':')
                if cmd == 'match':
                    depth += 1
                elif cmd == 'endmatch':
                    if depth == 0:
                        end_line = i
                        break
                    depth -= 1
                i += 1
            match_body_start = line_idx + 1
            match_body_end = end_line - 1

        # Parse cases within the match block.
        cases = []
        default_range = None

        def _strip_trailing_colon(tok: str) -> str:
            return tok[:-1] if tok.endswith(':') else tok

        def _parse_case_value_tokens(line_tokens):
            # Return tokens suitable for _evaluate_condition's RHS
            # Supports:
            #   case 10:
            #   case -10:
            #   case - 10:
            # and accepts optional trailing ':' attached to last token.
            if len(line_tokens) < 2:
                raise ValueError('case requires a value')
            raw = [_strip_trailing_colon(t) for t in line_tokens[1:]]
            # Drop a standalone ':' if it ever appears
            raw = [t for t in raw if t != ':']
            if not raw:
                raise ValueError('case requires a value')
            if len(raw) == 1:
                return [raw[0]]
            if len(raw) >= 2 and raw[0] == '-' and raw[1].lstrip('-').isdigit():
                return ['-', raw[1]]
            # Fallback: treat first token as the value (e.g., '10')
            return [raw[0]]

        # Scan only inside match body, and only recognize case/default at brace depth 0.
        i = match_body_start
        brace_depth = 0
        while i < len(lines) and i <= match_body_end:
            raw = lines[i].strip()
            if not raw:
                i += 1
                continue

            # Update brace depth for nested blocks within the match.
            if '{' in raw:
                brace_depth += raw.count('{')
            if '}' in raw:
                brace_depth -= raw.count('}')

            t = self._tokenize(raw)
            if not t:
                i += 1
                continue

            cmd = t[0].lower().rstrip(':')
            if brace_depth == 0 and cmd in ('case', 'default'):
                # Expect forms:
                #   case 123:
                #   case "x":
                #   default:
                if cmd == 'case':
                    case_value_tokens = _parse_case_value_tokens(t)
                else:
                    case_value_tokens = None

                # Determine body start/end.
                body_start = i + 1
                # Body can be a brace block starting on next line or inline on same line after ':'
                inline_tokens = None
                if ':' in t:
                    colon_idx = t.index(':')
                    if colon_idx + 1 < len(t):
                        inline_tokens = t[colon_idx + 1:]

                if inline_tokens:
                    # Inline statement body is treated as a single statement on this line.
                    body_end = i
                    body_inline = inline_tokens
                else:
                    # Block body: either a { ... } block or a sequence until next case/default/end.
                    body_inline = None
                    if body_start < len(lines) and lines[body_start].strip() == '{':
                        body_end = _find_brace_block_end(body_start)
                    else:
                        j = body_start
                        local_depth = 0
                        while j < len(lines) and j <= match_body_end:
                            s2 = lines[j].strip()
                            if '{' in s2:
                                local_depth += s2.count('{')
                            if '}' in s2:
                                local_depth -= s2.count('}')
                            tt = self._tokenize(s2)
                            if local_depth == 0 and tt and tt[0].lower().rstrip(':') in ('case', 'default'):
                                break
                            j += 1
                        body_end = j - 1

                if cmd == 'case':
                    cases.append((case_value_tokens, body_start, body_end, body_inline))
                else:
                    default_range = (body_start, body_end, body_inline)

                # Advance i
                if body_end < i:
                    i += 1
                else:
                    i = body_end + 1
                continue

            # Ignore other lines (e.g., '{')
            i += 1

        if not cases and default_range is None:
            return end_line

        def _match_case_equals_int_literal(case_tokens, flag_pos):
            # Strict equality check between match subject (multi-byte int variable) and a numeric literal.
            # Writes 1 to flag_pos if equal, else 0.
            if not case_tokens:
                raise ValueError('case requires a value')
            if len(case_tokens) == 2 and case_tokens[0] == '-' and case_tokens[1].lstrip('-').isdigit():
                value = -int(case_tokens[1])
            else:
                value = int(case_tokens[0])

            self._generate_clear(flag_pos)

            temp_a = self._allocate_temp(subj_size)
            temp_b = self._allocate_temp(subj_size)

            self._copy_block(subj_info['pos'], temp_a, subj_size)
            byte_values = int(value).to_bytes(subj_size, 'little', signed=True)
            for i, byte_val in enumerate(byte_values):
                self._generate_set_value(byte_val, pos=temp_b + i)

            is_lt = self._allocate_temp(1)
            is_gt = self._allocate_temp(1)
            is_eq = self._allocate_temp(1)
            
            self._compare_multi_byte_signed(temp_a, temp_b, subj_size, is_lt, is_gt, is_eq)
            
            self._copy_cell(is_eq, flag_pos, self._allocate_temp(1))
            self._free_temp(self.current_ptr)

            self._free_temp(is_eq)
            self._free_temp(is_gt)
            self._free_temp(is_lt)
            self._free_temp(temp_b)
            self._free_temp(temp_a)

        def _match_case_equals_byte_literal(case_tokens, flag_pos):
            # Strict equality check between match subject (byte/char) and a numeric literal (0..255).
            if not case_tokens:
                raise ValueError('case requires a value')
            if len(case_tokens) == 2 and case_tokens[0] == '-' and case_tokens[1].lstrip('-').isdigit():
                raise ValueError('byte/char match cases do not support negative literals')
            value = int(case_tokens[0])
            if value < 0 or value > 255:
                raise ValueError('byte/char match case value must be in 0..255')

            self._generate_clear(flag_pos)
            self._generate_if_byte_equals(subj_info['pos'], value, lambda: self._generate_set_value(1, flag_pos))

        # Compile: gate on matched flag to ensure first-match-wins.
        matched = self._allocate_temp()
        self._generate_clear(matched)

        def _emit_body(body_start, body_end, body_inline):
            if body_inline is not None:
                self._process_statement(body_inline, lines, body_start)
                return
            if body_end >= body_start:
                self._process_lines_range(lines, body_start, body_end)

        for (case_value_tokens, body_start, body_end, body_inline) in cases:
            inv_matched = self._allocate_temp()
            self._generate_set_value(1, inv_matched)
            self._generate_if_nonzero(matched, lambda: self._generate_clear(inv_matched))

            def _run_case_when_unmatched():
                cond_flag = self._allocate_temp()
                if subj_info['type'] in ('int', 'int16', 'int64'):
                    _match_case_equals_int_literal(case_value_tokens, cond_flag)
                else:
                    _match_case_equals_byte_literal(case_value_tokens, cond_flag)

                self._move_pointer(cond_flag)
                self.bf_code.append('[')
                _emit_body(body_start, body_end, body_inline)
                self._generate_set_value(1, inv_matched)  # reuse as scratch "one"
                self._move_pointer(inv_matched)
                self.bf_code.append('[')
                self._move_pointer(matched)
                self.bf_code.append('+')
                self._move_pointer(inv_matched)
                self.bf_code.append('-]')
                self._move_pointer(matched)
                self._generate_clear(cond_flag)
                self.bf_code.append(']')

                self._free_temp(cond_flag)

            self._generate_if_nonzero(inv_matched, _run_case_when_unmatched)
            self._generate_clear(inv_matched)
            self._free_temp(inv_matched)

        if default_range is not None:
            body_start, body_end, body_inline = default_range
            inv_matched = self._allocate_temp()
            self._generate_set_value(1, inv_matched)
            self._generate_if_nonzero(matched, lambda: self._generate_clear(inv_matched))
            self._generate_if_nonzero(inv_matched, lambda: _emit_body(body_start, body_end, body_inline))
            self._generate_clear(inv_matched)
            self._free_temp(inv_matched)

        self._free_temp(matched)
        return end_line

    def _compare_multi_byte_signed(self, pos_a, pos_b, size, result_lt, result_gt, result_eq):
        """
        Performs a signed comparison of two multi-byte integers.
        Sets result_lt, result_gt, or result_eq to 1 based on the comparison (a < b, a > b, a == b).
        Algorithm:
        1. Check signs (MSB bit 7).
        2. If signs differ, negative is smaller.
        3. If signs are same, compare bytes from MSB down to LSB as unsigned.
        """
        self._generate_clear(result_lt)
        self._generate_clear(result_gt)
        self._generate_set_value(1, result_eq)

        msb_a = pos_a + size - 1
        msb_b = pos_b + size - 1

        sign_a = self._allocate_temp(1)
        sign_b = self._allocate_temp(1)
        self._generate_clear(sign_a)
        self._generate_clear(sign_b)

        # Check MSB >= 128
        flag_ge128_a = self._allocate_temp(1)
        flag_ge128_b = self._allocate_temp(1)
        self._generate_clear(flag_ge128_a)
        self._generate_clear(flag_ge128_b)
        for v in range(128, 256):
            self._generate_if_byte_equals(msb_a, v, lambda: self._generate_set_value(1, flag_ge128_a))
            self._generate_if_byte_equals(msb_b, v, lambda: self._generate_set_value(1, flag_ge128_b))
        
        self._copy_cell(flag_ge128_a, sign_a, self._allocate_temp(1))
        self._free_temp(self.current_ptr)
        self._copy_cell(flag_ge128_b, sign_b, self._allocate_temp(1))
        self._free_temp(self.current_ptr)
        self._free_temp(flag_ge128_b)
        self._free_temp(flag_ge128_a)

        # Compare signs
        # case a < 0, b >= 0 => a < b
        self._generate_if_nonzero(sign_a, lambda: self._generate_if_nonzero(sign_b, lambda: None, body_fn_else=lambda: (
            self._generate_set_value(1, result_lt),
            self._generate_clear(result_eq)
        )))

        # case a >= 0, b < 0 => a > b
        inv_sign_a = self._allocate_temp(1)
        self._generate_set_value(1, inv_sign_a)
        self._generate_if_nonzero(sign_a, lambda: self._generate_clear(inv_sign_a))
        
        self._generate_if_nonzero(inv_sign_a, lambda: self._generate_if_nonzero(sign_b, lambda: (
            self._generate_set_value(1, result_gt),
            self._generate_clear(result_eq)
        )))
        self._free_temp(inv_sign_a)

        # If signs are same, compare magnitude
        # We'll use a stop flag to exit early once a difference is found.
        stop = self._allocate_temp(1)
        self._generate_clear(stop)
        
        # We only proceed if result_eq is still 1 (meaning signs were same)
        self._move_pointer(result_eq)
        self.bf_code.append('[')
        
        for i in reversed(range(size)):
            # if not stop:
            inv_stop = self._allocate_temp(1)
            self._generate_set_value(1, inv_stop)
            self._generate_if_nonzero(stop, lambda: self._generate_clear(inv_stop))
            
            def _compare_byte(idx=i):
                byte_a = self._allocate_temp(1)
                byte_b = self._allocate_temp(1)
                scr = self._allocate_temp(1)
                self._copy_cell(pos_a + idx, byte_a, scr)
                self._copy_cell(pos_b + idx, byte_b, scr)
                self._free_temp(scr)
                
                # Unsigned byte comparison: while a > 0 and b > 0: a--, b--
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
                
                # If a > 0 => a > b
                self._generate_if_nonzero(byte_a, lambda: (
                    self._generate_set_value(1, result_gt),
                    self._generate_clear(result_eq),
                    self._generate_set_value(1, stop)
                ))
                # If b > 0 => a < b
                self._generate_if_nonzero(byte_b, lambda: (
                    self._generate_set_value(1, result_lt),
                    self._generate_clear(result_eq),
                    self._generate_set_value(1, stop)
                ))
                
                self._free_temp(byte_b)
                self._free_temp(byte_a)

            self._generate_if_nonzero(inv_stop, _compare_byte)
            self._free_temp(inv_stop)
            
        self._move_pointer(result_eq)
        self.bf_code.append(']') # Close result_eq check (if signs were different, eq is 0)

        self._free_temp(stop)
        self._free_temp(sign_b)
        self._free_temp(sign_a)

    def _evaluate_condition(self, tokens, flag_pos):
        self._generate_clear(flag_pos)

        if not tokens:
            self._generate_set_value(1, flag_pos)
            return

        negate = tokens[0] == '!'
        if negate:
            tokens = tokens[1:]

        var_info = None
        temp_buf = None
        if len(tokens) == 1:
            tok = tokens[0]
            rt = self._split_runtime_subscript_ref(tok[1:] if tok.startswith('$') else tok)
            if rt is not None:
                base_name, idx_var = rt
                base_info = self._resolve_var(base_name)
                if not (base_info.get('is_array') or base_info.get('is_dict')):
                    raise ValueError('Runtime subscript target must be array or dict')
                elem_size = base_info.get('elem_size', 1)
                temp_buf = self._allocate_temp(elem_size)
                self._load_runtime_subscript_into_buffer(base_info, idx_var, temp_buf, elem_size)
                var_info = {'pos': temp_buf, 'size': elem_size}
            else:
                try:
                    var_info = self._resolve_var(tok)
                except Exception:
                    var_info = None

        if len(tokens) == 1 and var_info is not None:
            temp_scratch = self._allocate_temp()
            temp_copy = self._allocate_temp()
            any_nonzero = self._allocate_temp()

            for i in range(var_info['size']):
                self._copy_cell(var_info['pos'] + i, temp_copy, temp_scratch)
                self._move_pointer(temp_copy)
                self.bf_code.append('[')
                self._generate_set_value(1, any_nonzero)
                self._generate_clear(temp_copy)
                self.bf_code.append(']')

            self._move_pointer(any_nonzero)
            self.bf_code.append('[')
            self._move_pointer(flag_pos)
            self.bf_code.append('+')
            self._move_pointer(any_nonzero)
            self.bf_code.append('-]')
            self._move_pointer(flag_pos)

            self._free_temp(any_nonzero)
            self._free_temp(temp_copy)
            self._free_temp(temp_scratch)

            if temp_buf is not None:
                self._free_temp(temp_buf)

        elif len(tokens) in (3, 4):
            left_ref = tokens[0]
            op = tokens[1]

            rhs_is_var = False
            rhs_ref = None
            value = None

            if len(tokens) == 3:
                try:
                    if '.' in tokens[2]:
                        try:
                            value = int(Decimal(tokens[2]) * 1000)
                        except InvalidOperation:
                            raise ValueError(f"Invalid float literal: {tokens[2]}")
                    else:
                        value = int(tokens[2])
                except Exception:
                    rhs_is_var = True
                    rhs_ref = tokens[2]
            else:
                if tokens[2] != '-' or not tokens[3].lstrip('-').isdigit():
                    raise ValueError(f"Invalid condition: {' '.join(tokens)}")
                value = -int(tokens[3])

            temps_to_free = []

            def _resolve_int_operand(ref):
                r = ref[1:] if ref.startswith('$') else ref
                rt = self._split_runtime_subscript_ref(r)
                if rt is not None:
                    base_name, idx_var = rt
                    base_info = self._resolve_var(base_name)
                    if base_info['type'] not in ('int', 'int16', 'int64', 'float', 'float64'):
                        raise NotImplementedError('Runtime-subscript comparisons support only integer and float elements')
                    size = base_info.get('elem_size', 8)
                    tmp = self._allocate_temp(size)
                    temps_to_free.append(tmp)
                    self._load_runtime_subscript_into_buffer(base_info, idx_var, tmp, size)
                    return tmp, size
                info = self._resolve_var(ref)
                if info['type'] not in ('int', 'int16', 'int64', 'float', 'float64'):
                    raise NotImplementedError("Comparisons currently supported only for integer and float values")
                return info['pos'], info['size']

            var_pos, var_size = _resolve_int_operand(left_ref)

            if rhs_is_var:
                rhs_pos, rhs_size = _resolve_int_operand(rhs_ref)
                if var_size != rhs_size:
                    raise NotImplementedError("Mixed-size integer comparisons not yet supported")
                comp_size = var_size
            else:
                comp_size = var_size

            if op in ('==', '!=', '<', '>', '<=', '>='):
                temp_a = self._allocate_temp(comp_size)
                temp_b = self._allocate_temp(comp_size)

                self._copy_block(var_pos, temp_a, comp_size)

                if rhs_is_var:
                    self._copy_block(rhs_pos, temp_b, comp_size)
                else:
                    byte_values = int(value).to_bytes(comp_size, 'little', signed=True)
                    for i, byte_val in enumerate(byte_values):
                        self._generate_set_value(byte_val, pos=temp_b + i)

                is_lt = self._allocate_temp(1)
                is_gt = self._allocate_temp(1)
                is_eq = self._allocate_temp(1)
                
                self._compare_multi_byte_signed(temp_a, temp_b, comp_size, is_lt, is_gt, is_eq)

                if op == '==':
                    self._copy_cell(is_eq, flag_pos, self._allocate_temp(1))
                    self._free_temp(self.current_ptr)
                elif op == '!=':
                    inv_eq = self._allocate_temp(1)
                    self._generate_set_value(1, inv_eq)
                    self._generate_if_nonzero(is_eq, lambda: self._generate_clear(inv_eq))
                    self._copy_cell(inv_eq, flag_pos, self._allocate_temp(1))
                    self._free_temp(self.current_ptr)
                    self._free_temp(inv_eq)
                elif op == '<':
                    self._copy_cell(is_lt, flag_pos, self._allocate_temp(1))
                    self._free_temp(self.current_ptr)
                elif op == '>':
                    self._copy_cell(is_gt, flag_pos, self._allocate_temp(1))
                    self._free_temp(self.current_ptr)
                elif op == '<=':
                    self._copy_cell(is_lt, flag_pos, self._allocate_temp(1))
                    self._free_temp(self.current_ptr)
                    self._generate_if_nonzero(is_eq, lambda: self._generate_set_value(1, flag_pos))
                elif op == '>=':
                    self._copy_cell(is_gt, flag_pos, self._allocate_temp(1))
                    self._free_temp(self.current_ptr)
                    self._generate_if_nonzero(is_eq, lambda: self._generate_set_value(1, flag_pos))

                self._free_temp(is_eq)
                self._free_temp(is_gt)
                self._free_temp(is_lt)
                self._free_temp(temp_b)
                self._free_temp(temp_a)
            else:
                raise NotImplementedError(f"Operator '{op}' not implemented")

            for p in reversed(temps_to_free):
                self._free_temp(p)

        if negate:
            temp = self._allocate_temp()
            self._generate_set_value(1, temp)
            self._move_pointer(flag_pos)
            self.bf_code.append('[')
            self._move_pointer(temp)
            self.bf_code.append('-')
            self._move_pointer(flag_pos)
            self.bf_code.append('-]')
            self._move_pointer(temp)
            self.bf_code.append('[-<+>]')
            self._move_pointer(flag_pos)
            self._free_temp(temp)
