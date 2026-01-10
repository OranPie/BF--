from __future__ import annotations


class MemoryOpsMixin:
    def _allocate_temp(self, size=1):
        pos = self.max_ptr
        self.max_ptr += size
        self.temp_cells.append((pos, size))
        return pos

    def _free_temp(self, pos):
        if not self.temp_cells:
            raise ValueError("Compiler Error: No temporary cells to free.")
        last_pos, size = self.temp_cells.pop()
        if pos != last_pos:
            raise ValueError(
                f"Compiler Error: Invalid temp cell free order. Expected {last_pos}, got {pos}."
            )
        self.max_ptr -= size

    def _move_pointer(self, target_pos):
        diff = target_pos - self.current_ptr
        if diff > 0:
            self.bf_code.append('>' * diff)
        elif diff < 0:
            self.bf_code.append('<' * (-diff))
        self.current_ptr = target_pos

    def _generate_clear(self, pos=None):
        if pos is not None:
            self._move_pointer(pos)
        self.bf_code.append('[-]')

    def _generate_set_value(self, value, pos=None):
        if pos is not None:
            self._move_pointer(pos)
        self._generate_clear()
        value = int(value)
        if value > 0:
            self.bf_code.append('+' * value)

    def _copy_cell(self, src_pos, dest_pos, temp_pos):
        if src_pos == dest_pos:
            return
        self._move_pointer(dest_pos)
        self._generate_clear()

        self._move_pointer(temp_pos)
        self._generate_clear()

        self._move_pointer(src_pos)
        self.bf_code.append('[')
        self._move_pointer(dest_pos)
        self.bf_code.append('+')
        self._move_pointer(temp_pos)
        self.bf_code.append('+')
        self._move_pointer(src_pos)
        self.bf_code.append('-]')

        self._move_pointer(temp_pos)
        self.bf_code.append('[')
        self._move_pointer(src_pos)
        self.bf_code.append('+')
        self._move_pointer(temp_pos)
        self.bf_code.append('-]')

    def _add_cell(self, src_pos, dest_pos, temp_pos):
        """dest += src (byte), preserving src. temp_pos is clobbered."""
        if src_pos == dest_pos:
            # dest *= 2
            self._generate_clear(temp_pos)
            self._move_pointer(src_pos)
            self.bf_code.append('[')
            self._move_pointer(temp_pos)
            self.bf_code.append('+')
            self._move_pointer(src_pos)
            self.bf_code.append('-]')
            self._move_pointer(temp_pos)
            self.bf_code.append('[')
            self._move_pointer(dest_pos)
            self.bf_code.append('++')
            self._move_pointer(temp_pos)
            self.bf_code.append('-]')
            return

        self._generate_clear(temp_pos)
        self._move_pointer(src_pos)
        self.bf_code.append('[')
        self._move_pointer(dest_pos)
        self.bf_code.append('+')
        self._move_pointer(temp_pos)
        self.bf_code.append('+')
        self._move_pointer(src_pos)
        self.bf_code.append('-]')

        # restore src from temp_pos
        self._move_pointer(temp_pos)
        self.bf_code.append('[')
        self._move_pointer(src_pos)
        self.bf_code.append('+')
        self._move_pointer(temp_pos)
        self.bf_code.append('-]')

    def _sub_cell(self, src_pos, dest_pos, temp_pos):
        """dest -= src (byte), preserving src. temp_pos is clobbered."""
        if src_pos == dest_pos:
            # dest = 0
            self._generate_clear(dest_pos)
            return

        self._generate_clear(temp_pos)
        self._move_pointer(src_pos)
        self.bf_code.append('[')
        self._move_pointer(dest_pos)
        self.bf_code.append('-')
        self._move_pointer(temp_pos)
        self.bf_code.append('+')
        self._move_pointer(src_pos)
        self.bf_code.append('-]')

        # restore src from temp_pos
        self._move_pointer(temp_pos)
        self.bf_code.append('[')
        self._move_pointer(src_pos)
        self.bf_code.append('+')
        self._move_pointer(temp_pos)
        self.bf_code.append('-]')

    def _copy_block(self, src_pos, dest_pos, size):
        # Use a single temporary for all byte copies to save memory and ensure LIFO
        scratch = self._allocate_temp(1)
        for i in range(size):
            self._copy_cell(src_pos + i, dest_pos + i, scratch)
        self._free_temp(scratch)
