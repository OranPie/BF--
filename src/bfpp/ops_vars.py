from __future__ import annotations

import re


class VarsOpsMixin:
    def _split_var_ref(self, ref):
        # Returns (base_name, subscript_or_none)
        # - subscript can be int (array index) or str (dict key)
        m_int = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[(\-?\d+)\]$', ref)
        if m_int:
            base = m_int.group(1)
            idx = int(m_int.group(2))
            if idx < 0:
                raise ValueError(f"Array index must be >= 0: {ref}")
            return base, idx

        m_key = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[("[^"]*"|[A-Za-z_][A-Za-z0-9_]*)\]$', ref)
        if m_key:
            base = m_key.group(1)
            key_tok = m_key.group(2)
            if key_tok.startswith('"') and key_tok.endswith('"'):
                return base, key_tok[1:-1]
            return base, key_tok

        return ref, None

    def _split_runtime_subscript_ref(self, ref):
        # Matches: name[$i]
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[\$([A-Za-z_][A-Za-z0-9_]*)\]$', ref)
        if not m:
            return None
        return m.group(1), m.group(2)

    def _resolve_var(self, ref):
        # Resolve scalar var or array element ref into a concrete (pos,type,size).
        if ref.startswith('$'):
            ref = ref[1:]

        base, sub = self._split_var_ref(ref)
        if base not in self.variables:
            raise ValueError(f"Unknown variable: {base}")

        info = self.variables[base]
        if sub is None:
            return {
                'base': base,
                'pos': info['pos'],
                'type': info['type'],
                'size': info['size'],
                'is_array': info.get('is_array', False),
                'is_dict': info.get('is_dict', False),
                'elem_size': info.get('elem_size', info['size']),
                'length': info.get('length', 1),
            }

        if info.get('is_array', False):
            if not isinstance(sub, int):
                raise ValueError(f"Array index must be integer: {base}[{sub}]")
            length = info['length']
            if sub >= length:
                raise ValueError(f"Array index out of range: {base}[{sub}] (len={length})")
            pos = info['pos'] + sub * info['elem_size']
            return {
                'base': base,
                'pos': pos,
                'type': info['type'],
                'size': info['elem_size'],
                'is_array': False,
                'elem_size': info['elem_size'],
                'length': info['length'],
            }

        if info.get('is_dict', False):
            if isinstance(sub, int):
                key = str(sub)
            else:
                key = str(sub)
            key_map = info.get('key_map', {})
            if key not in key_map:
                raise ValueError(f"Unknown dict key: {base}[{key}]")
            slot = key_map[key]
            pos = info['pos'] + slot * info['elem_size']
            return {
                'base': base,
                'pos': pos,
                'type': info['type'],
                'size': info['elem_size'],
                'is_dict': False,
                'elem_size': info['elem_size'],
                'length': info['length'],
            }

        raise ValueError(f"Variable '{base}' does not support subscript access")

    def _collection_element_ref(self, base_name, index):
        return f"{base_name}[{index}]"

    def _set_collection_numeric_literal(self, value, dest_info):
        # Set all elements in an array/dict to the same numeric value.
        base = dest_info['base']
        length = dest_info.get('length', 1)
        elem_size = dest_info.get('elem_size', dest_info['size'])
        if not dest_info.get('is_array') and not dest_info.get('is_dict'):
            raise ValueError("Not a collection")

        if dest_info['type'] == 'int':
            byte_values = int(value).to_bytes(8, 'little', signed=True)
            for idx in range(length):
                pos = dest_info['pos'] + idx * elem_size
                for i, byte_val in enumerate(byte_values):
                    self._generate_set_value(byte_val, pos=pos + i)
        else:
            for idx in range(length):
                pos = dest_info['pos'] + idx * elem_size
                self._generate_set_value(int(value), pos=pos)

    def _set_string_value_at_pos(self, string_token, pos, max_size):
        string_val = string_token.strip('"')
        if max_size <= len(string_val):
            raise ValueError("String too large for destination")
        for i, ch in enumerate(string_val):
            self._generate_set_value(ord(ch), pos=pos + i)
        self._generate_set_value(0, pos=pos + len(string_val))

    def _set_collection_string_literal(self, string_token, dest_info):
        if dest_info['type'] != 'string':
            raise ValueError("String fill requires string collection")
        length = dest_info.get('length', 1)
        elem_size = dest_info.get('elem_size', dest_info['size'])
        for idx in range(length):
            self._set_string_value_at_pos(string_token, dest_info['pos'] + idx * elem_size, elem_size)

    def _move_to_var(self, var_name):
        """Move pointer to the start of a variable's memory location."""
        var_info = self._resolve_var(var_name)
        self._move_pointer(var_info['pos'])

    def _handle_declare(self, tokens):
        """
        Handle variable declaration.

        Syntax: declare <type> <name>
        Types: byte, char, int (8 bytes), string <size> <name>

        BF Code Generation:
        - Allocate memory space
        - Initialize to zero
        """
        if len(tokens) < 2:
            raise ValueError("`declare` requires <type> <name>")

        raw_type = tokens[0].lower()
        raw_name = tokens[1]

        # Dict form (single-line only):
        #   declare dict <type> <name> { key1, key2, "key 3" }
        if raw_type == 'dict':
            if len(tokens) < 5:
                raise ValueError("Dict declaration requires: dict <type> <name> { <keys...> }")

            value_type = tokens[1].lower()

            string_elem_size = None
            if value_type == 'string':
                if len(tokens) < 6:
                    raise ValueError("Dict string declaration requires: dict string <size> <name> { ... }")
                string_elem_size = int(tokens[2]) + 1
                var_name = tokens[3]
            else:
                var_name = tokens[2]

            if '{' not in tokens or '}' not in tokens:
                raise ValueError("Dict declaration requires '{' and '}' on the same line")
            l = tokens.index('{')
            r = len(tokens) - 1 - list(reversed(tokens)).index('}')
            if r <= l:
                raise ValueError("Invalid dict key list")

            key_tokens = [t for t in tokens[l + 1:r] if t != ',']
            if not key_tokens:
                raise ValueError("Dict must declare at least one key")

            keys = []
            for t in key_tokens:
                if t.startswith('"') and t.endswith('"'):
                    keys.append(t[1:-1])
                else:
                    keys.append(t)

            if len(set(keys)) != len(keys):
                raise ValueError("Dict keys must be unique")

            if value_type in ('byte', 'char'):
                elem_size = 1
            elif value_type == 'int':
                elem_size = 8
            elif value_type == 'string':
                elem_size = string_elem_size
            else:
                raise NotImplementedError("Dict currently supports value types: byte, char, int, string")

            length = len(keys)
            size = elem_size * length
            var_pos = self.max_ptr
            self.variables[var_name] = {
                'pos': var_pos,
                'type': value_type,
                'size': size,
                'is_dict': True,
                'is_array': False,
                'elem_size': elem_size,
                'length': length,
                'key_map': {k: i for i, k in enumerate(keys)},
            }
            self.max_ptr += size
            for i in range(size):
                self._generate_clear(var_pos + i)
            return

        # Array forms:
        # - declare int arr[10]
        # - declare int[10] arr
        elem_type = raw_type
        length = None

        m_type_arr = re.match(r'^(byte|char|int)\[(\d+)\]$', raw_type)
        if m_type_arr:
            elem_type = m_type_arr.group(1)
            length = int(m_type_arr.group(2))
            var_name = raw_name
        else:
            var_name = raw_name
            m_name_arr = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]$', raw_name)
            if m_name_arr:
                var_name = m_name_arr.group(1)
                length = int(m_name_arr.group(2))

        # String (existing syntax): declare string <size> <name>
        if elem_type == 'string':
            if len(tokens) < 3:
                raise ValueError("String declaration requires: string <size> <name>")
            elem_size = int(tokens[1]) + 1  # +1 for null terminator
            var_name_token = tokens[2]

            m_name_arr = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]$', var_name_token)
            if m_name_arr:
                var_name = m_name_arr.group(1)
                length = int(m_name_arr.group(2))
                is_array = True
                size = elem_size * length
            else:
                var_name = var_name_token
                is_array = False
                length = 1
                size = elem_size

            var_pos = self.max_ptr
            self.variables[var_name] = {
                'pos': var_pos,
                'type': 'string',
                'size': size,
                'is_array': is_array,
                'is_dict': False,
                'elem_size': elem_size,
                'length': length,
            }
            self.max_ptr += size
            for i in range(size):
                self._generate_clear(var_pos + i)
            return

        if elem_type in ('byte', 'char'):
            elem_size = 1
        elif elem_type == 'int':
            elem_size = 8
        else:
            raise ValueError(f"Unknown type: {elem_type}")

        is_array = length is not None
        size = elem_size * (length if is_array else 1)

        # Allocate variable
        var_pos = self.max_ptr
        self.variables[var_name] = {
            'pos': var_pos,
            'type': elem_type,
            'size': size,
            'is_array': is_array,
            'elem_size': elem_size,
            'length': (length if is_array else 1),
        }
        self.max_ptr += size

        # Initialize to zero
        for i in range(size):
            self._generate_clear(var_pos + i)

    def _handle_set(self, tokens):
        """
        Handle variable assignment.

        Syntax: set <value> on <var>
        Supports: literals, strings, variables ($var), expressions
        """
        if 'on' not in tokens:
            raise ValueError("`set` requires `on <var>` clause")

        on_idx = tokens.index('on')
        expr_tokens = tokens[:on_idx]
        dest_ref = tokens[on_idx + 1]
        runtime = self._split_runtime_subscript_ref(dest_ref)
        if runtime is not None:
            base_name, idx_var = runtime
            base_info = self._resolve_var(base_name)
            if not (base_info.get('is_array') or base_info.get('is_dict')):
                raise ValueError("Runtime subscript target must be array or dict")

            if expr_tokens[0].startswith('"'):
                if base_info['type'] != 'string':
                    raise ValueError("String literal assignment requires a string destination")

                def _slot_set_string(pos, slot):
                    self._set_string_value_at_pos(expr_tokens[0], pos, base_info['elem_size'])

                self._apply_runtime_subscript_op(base_info, idx_var, _slot_set_string)
                return

            if len(expr_tokens) == 2 and expr_tokens[0] == '-' and expr_tokens[1].lstrip('-').isdigit():
                value = -int(expr_tokens[1])
            else:
                value = int(expr_tokens[0])

            def _slot_set_num(pos, slot):
                if base_info['type'] == 'int':
                    byte_values = int(value).to_bytes(8, 'little', signed=True)
                    for i, byte_val in enumerate(byte_values):
                        self._generate_set_value(byte_val, pos=pos + i)
                else:
                    self._generate_set_value(int(value), pos=pos)

            self._apply_runtime_subscript_op(base_info, idx_var, _slot_set_num)
            return

        dest_info = self._resolve_var(dest_ref)

        # String literal
        if expr_tokens[0].startswith('"'):
            if dest_info['type'] not in ('string', 'varstring'):
                raise ValueError("String literal assignment requires a string variable")
            if dest_info.get('is_array') or dest_info.get('is_dict'):
                self._set_collection_string_literal(expr_tokens[0], dest_info)
            else:
                self._set_string_literal(expr_tokens[0], dest_ref)

        # Negative numeric literal (e.g., "-5" tokenized as ['-', '5'])
        elif (len(expr_tokens) == 2 and expr_tokens[0] == '-' and expr_tokens[1].lstrip('-').isdigit()):
            self._set_numeric_literal(-int(expr_tokens[1]), dest_ref)

        # Expression or variable copy
        elif expr_tokens[0].startswith('$') or any(op in expr_tokens for op in ['+', '-', '*', '/', '%', '&', '|', '^', '~']):
            if dest_info.get('is_array') or dest_info.get('is_dict'):
                raise NotImplementedError("Cannot assign expression to whole array/dict; use an element like a[0] or m[key]")
            self._handle_expression_assignment(expr_tokens, dest_ref)

        # Numeric literal
        else:
            lit = int(expr_tokens[0])
            if dest_info.get('is_array') or dest_info.get('is_dict'):
                self._set_collection_numeric_literal(lit, dest_info)
            else:
                self._set_numeric_literal(lit, dest_ref)

    def _set_string_literal(self, string_token, dest_var):
        """Set a string literal value to a string variable."""
        string_val = string_token.strip('"')
        var_info = self._resolve_var(dest_var)

        if var_info['size'] <= len(string_val):
            raise ValueError(f"String too large for variable '{dest_var}'")

        self._move_to_var(dest_var)
        for char in string_val:
            self._generate_set_value(ord(char))
            self.bf_code.append('>')
            self.current_ptr += 1
        self._generate_set_value(0)  # Null terminator
        # Move pointer back to start of string
        self._move_to_var(dest_var)

    def _set_numeric_literal(self, value, dest_var):
        """Set a numeric literal to a variable."""
        var_info = self._resolve_var(dest_var)

        if var_info['type'] == 'int':
            # Convert to 8-byte little-endian
            byte_values = value.to_bytes(8, 'little', signed=True)
            for i, byte_val in enumerate(byte_values):
                self._generate_set_value(byte_val, pos=var_info['pos'] + i)
        else:
            # byte/char
            self._generate_set_value(value, pos=var_info['pos'])

    def _handle_inc_dec(self, operation, tokens):
        """
        Handle increment/decrement operations.

        BF Code Generation:
        - For bytes: single + or -
        - For ints: increment LSB only (simplified)
        """
        var_name = None
        if len(tokens) > 1 and tokens[0] == 'on':
            var_name = tokens[1]
            runtime = self._split_runtime_subscript_ref(var_name)
            if runtime is not None:
                base_name, idx_var = runtime
                base_info = self._resolve_var(base_name)
                if not (base_info.get('is_array') or base_info.get('is_dict')):
                    raise ValueError("Runtime subscript target must be array or dict")

                def _slot_incdec(pos, slot):
                    if base_info['type'] == 'int':
                        if operation == 'inc':
                            self._increment_multi_byte(pos)
                        else:
                            self._decrement_multi_byte(pos)
                    else:
                        self._move_pointer(pos)
                        if operation == 'inc':
                            self.bf_code.append('+')
                        else:
                            self.bf_code.append('-')

                self._apply_runtime_subscript_op(base_info, idx_var, _slot_incdec)
                return

            self._move_to_var(var_name)

        if var_name is not None:
            var_info = self._resolve_var(var_name)
            if var_info['type'] == 'int':
                if operation == 'inc':
                    self._increment_multi_byte(var_info['pos'])
                else:
                    self._decrement_multi_byte(var_info['pos'])
                return

        if operation == 'inc':
            self.bf_code.append('+')
        else:
            self.bf_code.append('-')
