import re

from bfpp.lexer import preprocess, tokenize
from bfpp.state import CompilerState
from bfpp.ops_memory import MemoryOpsMixin
from bfpp.ops_runtime import RuntimeOpsMixin
from bfpp.ops_vars import VarsOpsMixin
from bfpp.ops_arith import ArithOpsMixin
from bfpp.ops_io import IOMixin
from bfpp.ops_control import ControlFlowMixin


class BrainFuckPlusPlusCompiler(
    VarsOpsMixin,
    ArithOpsMixin,
    MemoryOpsMixin,
    RuntimeOpsMixin,
    IOMixin,
    ControlFlowMixin,
):
    """
    BrainFuck++ Compiler

    Compiles a high-level language (BF++) to BrainFuck code.

    Memory Layout:
    - Variables are allocated sequentially from position 0
    - Temporary cells are allocated from the end of used memory
    - Each variable has a fixed position and size

    Code Generation Strategy:
    - Direct translation for simple operations (+, -, <, >)
    - Loop-based algorithms for complex operations (copy, compare, arithmetic)
    - Stack-based temporary cell management for intermediate values
    """

    def __init__(self, optimize_level=None):
        self.state = CompilerState(optimize_level=optimize_level)

    @property
    def variables(self):
        return self.state.variables

    @variables.setter
    def variables(self, value):
        self.state.variables = value

    @property
    def current_ptr(self):
        return self.state.current_ptr

    @current_ptr.setter
    def current_ptr(self, value):
        self.state.current_ptr = value

    @property
    def max_ptr(self):
        return self.state.max_ptr

    @max_ptr.setter
    def max_ptr(self, value):
        self.state.max_ptr = value

    @property
    def temp_cells(self):
        return self.state.temp_cells

    @temp_cells.setter
    def temp_cells(self, value):
        self.state.temp_cells = value

    @property
    def bf_code(self):
        return self.state.bf_code

    @bf_code.setter
    def bf_code(self, value):
        self.state.bf_code = value

    @property
    def loop_condition_stack(self):
        return self.state.loop_condition_stack

    @loop_condition_stack.setter
    def loop_condition_stack(self, value):
        self.state.loop_condition_stack = value

    @property
    def optimize_level(self):
        return self.state.optimize_level

    @optimize_level.setter
    def optimize_level(self, value):
        self.state.optimize_level = value

    # ===== Main Compilation Pipeline =====

    def compile(self, code, optimize_level=None):
        """
        Main compilation method.

        Steps:
        1. Preprocess: Remove comments
        2. Tokenize: Split into tokens line by line
        3. Process: Generate BF code for each statement

        Args:
            code: BF++ source code string

        Returns:
            Generated BrainFuck code string
        """
        code = self._preprocess(code)
        lines = code.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            tokens = self._tokenize(line)
            if tokens:
                i = self._process_statement(tokens, lines, i)
            i += 1

        bf = ''.join(self.bf_code)
        level = self.optimize_level if optimize_level is None else optimize_level
        if level is not None:
            from optimizer import optimize_bf

            bf = optimize_bf(bf, level=int(level), cell_size=256, wrap=True)
        return bf

    def _preprocess(self, code):
        """Remove single-line and multi-line comments from source code."""
        return preprocess(code)

    def _tokenize(self, line):
        """
        Tokenize a line into meaningful units.

        Handles:
        - String literals (quoted)
        - Multi-character operators (==, <=, >=, !=)
        - Single character operators and delimiters
        - Identifiers and numbers
        """
        tokens = tokenize(line)
        # Normalize bracketed references:
        #   name [ 3 ] -> name[3]
        #   name [ key ] -> name[key]
        #   name [ "key" ] -> name["key"]
        # Also works for $name[...] used in expressions.
        out = []
        i = 0
        while i < len(tokens):
            if (
                i + 3 < len(tokens)
                and tokens[i + 1] == '['
                and (
                    tokens[i + 2].lstrip('-').isdigit()
                    or re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', tokens[i + 2])
                    or re.match(r'^\$[A-Za-z_][A-Za-z0-9_]*$', tokens[i + 2])
                    or (tokens[i + 2].startswith('"') and tokens[i + 2].endswith('"'))
                )
                and tokens[i + 3] == ']'
            ):
                out.append(f"{tokens[i]}[{tokens[i + 2]}]")
                i += 4
                continue
            out.append(tokens[i])
            i += 1
        return out

    def _split_var_ref(self, ref):
        return super()._split_var_ref(ref)
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
        return super()._split_runtime_subscript_ref(ref)
        # Matches: name[$i]
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[\$([A-Za-z_][A-Za-z0-9_]*)\]$', ref)
        if not m:
            return None
        return m.group(1), m.group(2)

    def _resolve_var(self, ref):
        return super()._resolve_var(ref)
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
        return super()._collection_element_ref(base_name, index)
        return f"{base_name}[{index}]"

    def _set_collection_numeric_literal(self, value, dest_info):
        return super()._set_collection_numeric_literal(value, dest_info)
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
        return super()._set_string_value_at_pos(string_token, pos, max_size)
        string_val = string_token.strip('"')
        if max_size <= len(string_val):
            raise ValueError("String too large for destination")
        for i, ch in enumerate(string_val):
            self._generate_set_value(ord(ch), pos=pos + i)
        self._generate_set_value(0, pos=pos + len(string_val))

    def _set_collection_string_literal(self, string_token, dest_info):
        return super()._set_collection_string_literal(string_token, dest_info)
        if dest_info['type'] != 'string':
            raise ValueError("String fill requires string collection")
        length = dest_info.get('length', 1)
        elem_size = dest_info.get('elem_size', dest_info['size'])
        for idx in range(length):
            self._set_string_value_at_pos(string_token, dest_info['pos'] + idx * elem_size, elem_size)

    def _output_literal(self, token):
        return super()._output_literal(token)

    def _output_string_until_null_deterministic(self, pos, size):
        return super()._output_string_until_null_deterministic(pos, size)

    def _process_lines_range(self, lines, start_idx, end_idx):
        i = start_idx
        while i <= end_idx and i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            tokens = self._tokenize(line)
            if tokens:
                i = self._process_statement(tokens, lines, i)
            i += 1

    def _process_statement(self, tokens, lines, line_idx):
        """
        Process a single statement and generate corresponding BF code.

        Returns the new line index after processing.
        """
        if not tokens:
            return line_idx

        cmd = tokens[0].lower()

        # Variable declaration
        if cmd == 'declare':
            self._handle_declare(tokens[1:])

        # Variable assignment
        elif cmd == 'set':
            self._handle_set(tokens[1:])

        # Increment/Decrement
        elif cmd in ('inc', 'increment'):
            self._handle_inc_dec('inc', tokens[1:])
        elif cmd in ('dec', 'decrement'):
            self._handle_inc_dec('dec', tokens[1:])

        # Pointer movement
        elif cmd == 'left':
            self._move_pointer(self.current_ptr - 1)
        elif cmd == 'right':
            self._move_pointer(self.current_ptr + 1)
        elif cmd == 'move' and len(tokens) > 2 and tokens[1] == 'to':
            self._handle_move_to(tokens[2:])

        # I/O operations
        elif cmd == 'output':
            self.bf_code.append('.')
        elif cmd == 'input':
            if len(tokens) > 2 and tokens[1] == 'on':
                self._handle_input(tokens[2:])
            else:
                self.bf_code.append(',')
        elif cmd == 'print' and len(tokens) > 1 and tokens[1] == 'string':
            self._handle_print_string(tokens[2:])
        elif cmd == 'varout':
            self._handle_varout(tokens[1:])

        # Memory operations
        elif cmd == 'clear':
            self._generate_clear()

        # Control flow
        elif cmd in ('loop', 'while'):
            return self._handle_while_loop(tokens[1:], lines, line_idx)
        elif cmd == 'if':
            return self._handle_if_statement(tokens[1:], lines, line_idx)
        elif cmd == 'match':
            return self._handle_match_statement(tokens[1:], lines, line_idx)
        elif cmd == 'for':
            return self._handle_for_loop(tokens[1:], lines, line_idx)
        elif cmd == 'break':
            self._handle_break()

        return line_idx

    def _move_to_var(self, var_name):
        """Move pointer to the start of a variable's memory location."""
        return super()._move_to_var(var_name)
        var_info = self._resolve_var(var_name)
        self._move_pointer(var_info['pos'])

    # ===== Variable Operations =====

    def _handle_declare(self, tokens):
        """
        Handle variable declaration.

        Syntax: declare <type> <name>
        Types: byte, char, int (8 bytes), string <size> <name>

        BF Code Generation:
        - Allocate memory space
        - Initialize to zero
        """
        return super()._handle_declare(tokens)
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
        return super()._handle_set(tokens)
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
        elif (len(expr_tokens) == 2 and expr_tokens[0] == '-' and
              expr_tokens[1].lstrip('-').isdigit()):
            self._set_numeric_literal(-int(expr_tokens[1]), dest_ref)

        # Expression or variable copy
        elif expr_tokens[0].startswith('$') or any(
                op in expr_tokens for op in ['+', '-', '*', '/', '%', '&', '|', '^', '~']):
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
        return super()._set_string_literal(string_token, dest_var)
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
        return super()._set_numeric_literal(value, dest_var)
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
        return super()._handle_inc_dec(operation, tokens)
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

    # ===== Bitwise Operations =====

    def _handle_expression_assignment(self, expr_tokens, dest_var):
        """Handle arithmetic and bitwise expression assignment."""
        return super()._handle_expression_assignment(expr_tokens, dest_var)
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
        return super()._parse_expression(tokens)
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
        return super()._load_operand(operand, target_pos)
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
        return super()._perform_bitwise_and(pos_a, pos_b, pos_result)
        for i in range(8):
            self._bitwise_byte_operation('and', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_or(self, pos_a, pos_b, pos_result):
        """Perform bytewise OR on two 8-byte integers."""
        return super()._perform_bitwise_or(pos_a, pos_b, pos_result)
        for i in range(8):
            self._bitwise_byte_operation('or', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_xor(self, pos_a, pos_b, pos_result):
        """Perform bytewise XOR on two 8-byte integers."""
        return super()._perform_bitwise_xor(pos_a, pos_b, pos_result)
        for i in range(8):
            self._bitwise_byte_operation('xor', pos_a + i, pos_b + i, pos_result + i)

    def _perform_bitwise_not(self, pos_in, pos_result):
        """
        Perform bytewise NOT (255 - value) on 8-byte integer.

        BF Code Pattern:
        - Set result to 255
        - Subtract input value
        """
        return super()._perform_bitwise_not(pos_in, pos_result)
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
        return super()._perform_add(pos_a, pos_b, pos_result)
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
        return super()._perform_sub(pos_a, pos_b, pos_result)
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
        return super()._perform_mul(pos_a, pos_b, pos_result)
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
        return super()._perform_div(pos_a, pos_b, pos_result)
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
        return super()._perform_mod(pos_a, pos_b, pos_result)
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
        return super()._bitwise_byte_operation(op, pos_a, pos_b, pos_result)
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

    # ===== Control Flow =====

    def _handle_match_statement(self, tokens, lines, line_idx):
        return super()._handle_match_statement(tokens, lines, line_idx)

    def _handle_if_statement(self, tokens, lines, line_idx):
        """
        Handle if/else statements.

        BF Code Pattern:
        1. Evaluate condition to flag
        2. If flag set: execute if-block, clear else-flag
        3. If else-flag set: execute else-block
        """
        return super()._handle_if_statement(tokens, lines, line_idx)
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

        # Parse condition
        cond_tokens = self._extract_parentheses_content(tokens)

        # Allocate flags
        cond_flag = self._allocate_temp()
        else_flag = self._allocate_temp()

        # Evaluate condition
        self._evaluate_condition(cond_tokens, cond_flag)
        self._generate_set_value(1, pos=else_flag)

        # If block
        self._move_pointer(cond_flag)
        self.bf_code.append('[')
        self._generate_clear(else_flag)  # Don't run else
        if_end = self._process_block(lines, line_idx + 1)
        self._generate_clear(cond_flag)
        self.bf_code.append(']')

        # Check for else - look at the line where the if-block ended
        # It might be "}" or "} else {"
        has_else = False
        next_idx = if_end + 1
        if if_end < len(lines):
            end_line_tokens = self._tokenize(lines[if_end].strip())
            has_else = 'else' in end_line_tokens

        # Else block
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
        """
        Handle while loops.

        BF Code Pattern:
        1. Evaluate condition
        2. Loop: [execute body, if flag still set re-evaluate condition]
        """
        return super()._handle_while_loop(tokens, lines, line_idx)
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

            # Initial condition
            self._evaluate_condition(cond_tokens, cond_flag)

            self._move_pointer(cond_flag)
            self.bf_code.append('[')

            # Body
            self._process_lines_range(lines, line_idx + 1, end_line - 1)

            # Check if we should re-evaluate (flag still set, not broken)
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

        # Initial condition
        self._evaluate_condition(cond_tokens, cond_flag)

        self._move_pointer(cond_flag)
        self.bf_code.append('[')

        # Process body
        end_line = self._process_block(lines, line_idx + 1)

        # Check if we should re-evaluate (flag still set, not broken)
        # Copy flag to a temp to check without consuming it
        check_temp = self._allocate_temp()
        copy_temp = self._allocate_temp()
        self._copy_cell(cond_flag, check_temp, copy_temp)
        self._free_temp(copy_temp)

        self._move_pointer(check_temp)
        self.bf_code.append('[')  # If flag was set (not broken)
        # Clear the original flag and re-evaluate
        self._generate_clear(cond_flag)
        self._evaluate_condition(cond_tokens, cond_flag)
        # Clear check_temp to exit
        self._generate_clear(check_temp)
        self.bf_code.append(']')

        self._free_temp(check_temp)

        # End loop
        self._move_pointer(cond_flag)
        self.bf_code.append(']')

        self.loop_condition_stack.pop()
        self._free_temp(cond_flag)

        return end_line

    def _handle_for_loop(self, tokens, lines, line_idx):
        """
        Handle for loops.

        Desugars: for (init; cond; step) {...}
        Into: init; while (cond) {...; step}
        """
        return super()._handle_for_loop(tokens, lines, line_idx)
        paren_tokens = self._extract_parentheses_content(tokens)

        # Find semicolons to split the three parts
        semi_indices = [i for i, t in enumerate(paren_tokens) if t == ';']
        if len(semi_indices) != 2:
            raise ValueError("For loop requires (init; condition; step)")

        init_tokens = paren_tokens[:semi_indices[0]]
        cond_tokens = paren_tokens[semi_indices[0]+1:semi_indices[1]]
        step_tokens = paren_tokens[semi_indices[1]+1:]

        # Execute initialization
        if init_tokens:
            self._process_statement(init_tokens, [], 0)

        # Set up while loop
        cond_flag = self._allocate_temp()
        self.loop_condition_stack.append(cond_flag)

        self._evaluate_condition(cond_tokens, cond_flag)
        self._move_pointer(cond_flag)
        self.bf_code.append('[')

        # Process body
        end_line = self._process_block(lines, line_idx + 1)

        # Execute step
        if step_tokens:
            self._process_statement(step_tokens, [], 0)

        # Re-evaluate condition
        self._evaluate_condition(cond_tokens, cond_flag)
        self._move_pointer(cond_flag)
        self.bf_code.append(']')

        self.loop_condition_stack.pop()
        self._free_temp(cond_flag)

        return end_line

    def _handle_break(self):
        """
        Handle break statement.

        Clears the current loop's condition flag to exit.
        """
        return super()._handle_break()
        if not self.loop_condition_stack:
            raise RuntimeError("Break used outside of loop")

        cond_flag = self.loop_condition_stack[-1]
        self._generate_clear(cond_flag)

    def _evaluate_condition(self, tokens, flag_pos):
        """
        Evaluate a condition and set flag (1=true, 0=false).

        Supports:
        - Variable truthiness
        - Comparisons (==, !=)
        - Negation (!)
        """
        return super()._evaluate_condition(tokens, flag_pos)
        self._generate_clear(flag_pos)

        if not tokens:
            self._generate_set_value(1, flag_pos)
            return

        # Handle negation
        negate = tokens[0] == '!'
        if negate:
            tokens = tokens[1:]

        # Variable truthiness
        var_info = None
        temp_buf = None
        if len(tokens) == 1:
            tok = tokens[0]
            rt = self._split_runtime_subscript_ref(tok[1:] if tok.startswith('$') else tok)
            if rt is not None:
                base_name, idx_var = rt
                base_info = self._resolve_var(base_name)
                if not (base_info.get('is_array') or base_info.get('is_dict')):
                    raise ValueError("Runtime subscript target must be array or dict")
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

            # Check if any byte is non-zero (non-destructive)
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

        # Comparison
        elif len(tokens) in (3, 4):
            left_ref = tokens[0]
            op = tokens[1]

            rhs_is_var = False
            rhs_ref = None
            value = None

            if len(tokens) == 3:
                try:
                    value = int(tokens[2])
                except Exception:
                    rhs_is_var = True
                    rhs_ref = tokens[2]
            else:  # len(tokens) == 4, allow negative literal tokenized as ['a','==','-','5']
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
                    if base_info['type'] != 'int' or base_info.get('elem_size', 8) != 8:
                        raise NotImplementedError("Runtime-subscript comparisons support only int elements")
                    tmp = self._allocate_temp(8)
                    temps_to_free.append(tmp)
                    self._load_runtime_subscript_into_buffer(base_info, idx_var, tmp, 8)
                    return tmp
                info = self._resolve_var(ref)
                if info['type'] != 'int' or info['size'] != 8:
                    raise NotImplementedError("Comparisons currently supported only for 8-byte 'int' values")
                return info['pos']

            var_pos = _resolve_int_operand(left_ref)

            if rhs_is_var:
                rhs_pos = _resolve_int_operand(rhs_ref)

            if op in ('==', '!=', '<', '>', '<=', '>='):
                temp_a = self._allocate_temp(8)
                temp_b = self._allocate_temp(8)
                temp_diff = self._allocate_temp(8)

                # Copy LHS
                self._copy_block(var_pos, temp_a, 8)

                # Fill RHS
                if rhs_is_var:
                    self._copy_block(rhs_pos, temp_b, 8)
                else:
                    byte_values = int(value).to_bytes(8, 'little', signed=True)
                    for i, byte_val in enumerate(byte_values):
                        self._generate_set_value(byte_val, pos=temp_b + i)

                # diff = a - b
                self._perform_sub(temp_a, temp_b, temp_diff)

                # Compute is_negative from MSB (>= 128)
                is_negative = self._allocate_temp()
                self._generate_set_value(1, is_negative)

                test = self._allocate_temp()
                temp_val = self._allocate_temp()
                scr = self._allocate_temp()
                self._copy_cell(temp_diff + 7, test, scr)
                self._generate_set_value(128, temp_val)
                self._move_pointer(test)
                self.bf_code.append('['
                                    '>'
                                    '['
                                    '-<->'
                                    ']'
                                    '<[-]>'
                                    '<'
                                    ']')
                self._move_pointer(temp_val)
                self.bf_code.append('[')
                self._generate_clear(is_negative)
                self._generate_clear(temp_val)
                self.bf_code.append(']')
                self._free_temp(scr)
                self._free_temp(temp_val)
                self._free_temp(test)

                # Compute is_zero by destroying temp_diff
                is_zero = self._allocate_temp()
                self._generate_set_value(1, is_zero)
                for i in range(8):
                    self._move_pointer(temp_diff + i)
                    self.bf_code.append('[')
                    self._generate_clear(is_zero)
                    self._generate_clear(temp_diff + i)
                    self.bf_code.append(']')

                if op in ('==', '!='):
                    is_equal = self._allocate_temp()
                    self._generate_set_value(1, is_equal)
                    self._move_pointer(is_zero)
                    self.bf_code.append('[')
                    self._move_pointer(is_equal)
                    self.bf_code.append('+')
                    self._move_pointer(is_zero)
                    self.bf_code.append('-]')

                    if op == '==':
                        self._move_pointer(is_equal)
                        self.bf_code.append('[')
                        self._move_pointer(flag_pos)
                        self.bf_code.append('+')
                        self._move_pointer(is_equal)
                        self.bf_code.append('-]')
                        self._move_pointer(flag_pos)
                    else:
                        self._generate_set_value(1, flag_pos)
                        self._move_pointer(is_equal)
                        self.bf_code.append('[')
                        self._move_pointer(flag_pos)
                        self.bf_code.append('-')
                        self._move_pointer(is_equal)
                        self.bf_code.append('-]')
                        self._move_pointer(flag_pos)

                    self._free_temp(is_equal)

                elif op == '<':
                    self._move_pointer(is_negative)
                    self.bf_code.append('[')
                    self._move_pointer(flag_pos)
                    self.bf_code.append('+')
                    self._move_pointer(is_negative)
                    self.bf_code.append('-]')
                    self._move_pointer(flag_pos)

                elif op == '>':
                    self._generate_set_value(1, flag_pos)
                    self._move_pointer(is_negative)
                    self.bf_code.append('[')
                    self._move_pointer(flag_pos)
                    self.bf_code.append('-')
                    self._move_pointer(is_negative)
                    self.bf_code.append('-]')
                    self._move_pointer(is_zero)
                    self.bf_code.append('[')
                    self._move_pointer(flag_pos)
                    self.bf_code.append('-')
                    self._move_pointer(is_zero)
                    self.bf_code.append('-]')
                    self._move_pointer(flag_pos)

                elif op == '<=':
                    self._move_pointer(is_negative)
                    self.bf_code.append('[')
                    self._move_pointer(flag_pos)
                    self.bf_code.append('+')
                    self._move_pointer(is_negative)
                    self.bf_code.append('-]')
                    self._move_pointer(is_zero)
                    self.bf_code.append('[')
                    self._move_pointer(flag_pos)
                    self.bf_code.append('+')
                    self._move_pointer(is_zero)
                    self.bf_code.append('-]')
                    self._move_pointer(flag_pos)

                else:  # >=
                    self._generate_set_value(1, flag_pos)
                    self._move_pointer(is_negative)
                    self.bf_code.append('[')
                    self._move_pointer(flag_pos)
                    self.bf_code.append('-')
                    self._move_pointer(is_negative)
                    self.bf_code.append('-]')
                    self._move_pointer(flag_pos)

                self._free_temp(is_zero)
                self._free_temp(is_negative)
                self._free_temp(temp_diff)
                self._free_temp(temp_b)
                self._free_temp(temp_a)
            else:
                raise NotImplementedError(f"Operator '{op}' not implemented")

            for p in reversed(temps_to_free):
                self._free_temp(p)

        # Apply negation if needed
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

    def _generate_if_nonzero(self, pos, body_fn):
        # Executes body_fn() if *pos != 0 (non-destructive).
        tmp = self._allocate_temp()
        scratch = self._allocate_temp()
        self._generate_clear(scratch)
        self._copy_cell(pos, tmp, scratch)
        self._move_pointer(tmp)
        self.bf_code.append('[')
        body_fn()
        self._generate_clear(tmp)
        self.bf_code.append(']')
        self._free_temp(scratch)
        self._free_temp(tmp)

    def _load_runtime_subscript_into_buffer(self, base_info, idx_var, target_pos, size):
        # Clears target buffer then copies the selected element into it.
        for i in range(size):
            self._generate_clear(target_pos + i)

        def _slot_copy(pos, slot):
            self._copy_block(pos, target_pos, size)

        self._apply_runtime_subscript_op(base_info, idx_var, _slot_copy)

    def _input_string_at_pos(self, pos, size):
        return super()._input_string_at_pos(pos, size)
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
        return super()._handle_input(tokens)
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
                    raise NotImplementedError(f"input on not implemented for runtime collection type {base_info['type']}")

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

    def _process_block(self, lines, start_idx):
        """Process a code block enclosed in braces."""
        return super()._process_block(lines, start_idx)
        i = start_idx

        # Skip opening brace if on separate line
        if i < len(lines) and lines[i].strip() == '{':
            i += 1

        depth = 0
        while i < len(lines):
            line = lines[i].strip()
            # Check for closing brace BEFORE opening brace
            # This handles "} else {" correctly
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

    # ===== I/O Operations =====

    def _handle_move_to(self, tokens):
        """Handle 'move to <var>' command."""
        return super()._handle_move_to(tokens)
        if tokens:
            self._move_to_var(tokens[0])

    def _handle_print_string(self, tokens):
        """
        Handle 'print string <literal>'.

        BF Code Generation:
        - For each character: set value, output, clear
        """
        return super()._handle_print_string(tokens)
        if tokens and tokens[0].startswith('"'):
            string_val = tokens[0].strip('"')
            temp = self._allocate_temp()

            for char in string_val:
                self._generate_set_value(ord(char), temp)
                self.bf_code.append('.')
                self._generate_clear(temp)

            self._free_temp(temp)

    def _handle_varout(self, tokens):
        """
        Handle variable output (varout <var>).

        BF Code Generation:
        - For integers: convert to decimal and output digits
        - For strings: output until null terminator
        - For bytes: output as character
        """
        return super()._handle_varout(tokens)
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
                    raise NotImplementedError(f"varout not implemented for runtime collection type {base_info['type']}")

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
            # Output string until null terminator (deterministic)
            self._output_string_until_null_deterministic(var_info['pos'], var_info['size'])
            if end_token is not None:
                self._output_literal(end_token)

        elif var_info['type'] == 'int':
            # Output integer as decimal (simplified version)
            self._output_int_as_decimal(var_info['pos'])
            if end_token is not None:
                self._output_literal(end_token)

        elif var_info['type'] in ['byte', 'char']:
            # Output single byte as character
            self._move_to_var(var_name)
            self.bf_code.append('.')
            if end_token is not None:
                self._output_literal(end_token)
        
        else:
            raise NotImplementedError(f"varout not implemented for type {var_info['type']}")

    def _output_int_as_decimal(self, pos):
        return super()._output_int_as_decimal(pos)
        # Deterministic small-int output for debugging:
        # - Sign is determined by MSB (byte 7) only.
        # - Magnitude is derived from the low byte only.
        # This intentionally ignores high bytes, because many arithmetic routines
        # in this compiler are simplified and may not maintain a strict 8-byte
        # canonical representation.

        msb = pos + 7
        is_neg = self._allocate_temp()
        self._generate_clear(is_neg)
        self._generate_if_byte_equals(msb, 255, lambda: self._generate_set_value(1, is_neg))

        # Work byte (magnitude)
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
            # mag = 0 - tmp  (mod 256) => 256 - tmp
            self._move_pointer(tmp)
            self.bf_code.append('[')
            self._move_pointer(mag)
            self.bf_code.append('-')
            self._move_pointer(tmp)
            self.bf_code.append('-]')
            self._free_temp(tmp)

        self._set_mag_positive = _set_mag_positive
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

        # Convert magnitude (0..255) to decimal digits using rollover counting.
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

        # If started already, always emit tens (including 0)
        self._generate_if_nonzero(started, _emit_tens_when_started)
        # If not started, only emit tens if non-zero
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

        # Ones: emit if started, else emit (0..9) normally (prints 0 when value is 0)
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

    # ===== Helper Methods =====

    def _extract_parentheses_content(self, tokens):
        """Extract tokens between matching parentheses."""
        return super()._extract_parentheses_content(tokens)
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
            raise ValueError("Mismatched parentheses")

        return tokens[start + 1:end]

    def _increment_multi_byte(self, pos):
        """Increment 8-byte integer with carry propagation."""
        return super()._increment_multi_byte(pos)
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
        return super()._decrement_multi_byte(pos)
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
        return super()._sum_bytes_to_check_zero(pos, sum_pos, size)
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


# Example usage
if __name__ == "__main__":
    code = """
    // Example: Bitwise operations on integers
    declare int a
    declare int b
    declare int result

    // Set values
    set 65535 on a  // 0xFFFF
    set 32512 on b  // 0x7F00

    // Perform bitwise AND
    set $a & $b on result

    // Control flow example
    declare byte counter
    set 5 on counter

    while (counter) {
        dec on counter
    }

    // String example
    declare string 20 message
    set "Hello, World!" on message
    print string "Output: "
    varout message
    """
    code = """
    print string "Hello!"
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)

    print(f"Generated BrainFuck code length: {len(bf_code)}")
    print("\nVariable allocation map:")
    for name, info in compiler.variables.items():
        print(f"  {name}: pos={info['pos']}, type={info['type']}, size={info['size']}")

    # Save to file
    with open("output.bf", "w") as f:
        f.write(bf_code)