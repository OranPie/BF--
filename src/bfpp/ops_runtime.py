from __future__ import annotations


class RuntimeOpsMixin:
    def _generate_if_byte_equals(self, byte_pos, const_value, body_fn):
        # Executes body_fn() if *byte_pos == const_value (0..255). Does not consume byte.
        temp_a = self._allocate_temp()
        temp_b = self._allocate_temp()
        temp_scratch = self._allocate_temp()
        is_equal = self._allocate_temp()

        self._generate_clear(temp_scratch)
        self._copy_cell(byte_pos, temp_a, temp_scratch)
        self._generate_set_value(const_value, temp_b)

        self._move_pointer(temp_b)
        self.bf_code.append('[')
        self._move_pointer(temp_a)
        self.bf_code.append('-')
        self._move_pointer(temp_b)
        self.bf_code.append('-]')

        self._generate_set_value(1, is_equal)
        self._move_pointer(temp_a)
        self.bf_code.append('[')
        self._generate_clear(is_equal)
        self._generate_clear(temp_a)
        self.bf_code.append(']')

        self._move_pointer(is_equal)
        self.bf_code.append('[')
        body_fn()
        self._move_pointer(is_equal)
        self.bf_code.append('-]')

        self._free_temp(is_equal)
        self._free_temp(temp_scratch)
        self._free_temp(temp_b)
        self._free_temp(temp_a)

    def _generate_if_nonzero(self, pos, body_fn, body_fn_else=None):
        # Executes body_fn() if *pos != 0 (non-destructive).
        # Optional body_fn_else() if *pos == 0.
        tmp = self._allocate_temp()
        scratch = self._allocate_temp()
        self._generate_clear(scratch)
        self._copy_cell(pos, tmp, scratch)

        if body_fn_else:
            else_flag = self._allocate_temp()
            self._generate_set_value(1, else_flag)
            
            self._move_pointer(tmp)
            self.bf_code.append('[')
            body_fn()
            self._generate_clear(else_flag)
            self._generate_clear(tmp)
            self.bf_code.append(']')
            
            self._move_pointer(else_flag)
            self.bf_code.append('[')
            body_fn_else()
            self._generate_clear(else_flag)
            self.bf_code.append(']')
            self._free_temp(else_flag)
        else:
            self._move_pointer(tmp)
            self.bf_code.append('[')
            body_fn()
            self._generate_clear(tmp)
            self.bf_code.append(']')

        self._free_temp(scratch)
        self._free_temp(tmp)

    def _apply_runtime_subscript_op(self, base_info, index_var_name, per_slot_fn):
        if index_var_name not in self.variables:
            raise ValueError(f"Unknown index variable: {index_var_name}")
        idx_info = self.variables[index_var_name]
        if idx_info['size'] != 1:
            raise NotImplementedError("Runtime subscripts require a 1-byte index variable")

        self._apply_runtime_subscript_op_pos(base_info, idx_info['pos'], per_slot_fn)

    def _apply_runtime_subscript_op_pos(self, base_info, idx_pos, per_slot_fn):
        length = base_info.get('length', 1)
        elem_size = base_info.get('elem_size', 1)
        base_pos = base_info['pos']

        for slot in range(length):
            def _body(slot=slot):
                per_slot_fn(base_pos + slot * elem_size, slot)

            self._generate_if_byte_equals(idx_pos, slot, _body)

        self._move_pointer(idx_pos)

    def _load_runtime_subscript_into_buffer(self, base_info, idx_var, target_pos, size):
        # Clears target buffer then copies the selected element into it.
        for i in range(size):
            self._generate_clear(target_pos + i)

        def _slot_copy(pos, slot):
            self._copy_block(pos, target_pos, size)

        if isinstance(idx_var, str):
            self._apply_runtime_subscript_op(base_info, idx_var, _slot_copy)
        else:
            self._apply_runtime_subscript_op_pos(base_info, idx_var, _slot_copy)
