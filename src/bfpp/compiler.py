import re

from bfpp.lexer import preprocess, tokenize
from bfpp.errors import BFPPCompileError, BFPPPreprocessError, make_compile_error
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
        try:
            code = self._preprocess(code)
        except BFPPPreprocessError:
            raise
        lines = code.split('\n')

        i = 0
        while i < len(lines):
            self._last_line = i + 1
            try:
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                tokens = self._tokenize(line)
                if tokens:
                    i = self._process_statement(tokens, lines, i)
                i += 1
            except BFPPCompileError:
                raise
            except BFPPPreprocessError:
                raise
            except Exception as e:
                self._raise_compile_error(e, lines)

        bf = ''.join(self.bf_code)
        level = self.optimize_level if optimize_level is None else optimize_level
        if level is not None:
            from optimizer import optimize_bf

            bf = optimize_bf(bf, level=int(level), cell_size=256, wrap=True)
        return bf

    def _preprocess(self, code):
        """Remove single-line and multi-line comments from source code."""
        return preprocess(code)

    def _raise_compile_error(self, e: Exception, lines):
        line_no = getattr(self, '_last_line', 1)
        raise make_compile_error(message=f"{type(e).__name__}: {e}", source='\n'.join(lines), line=line_no) from e

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

    def _split_runtime_subscript_ref(self, ref):
        return super()._split_runtime_subscript_ref(ref)

    def _resolve_var(self, ref):
        return super()._resolve_var(ref)

    def _collection_element_ref(self, base_name, index):
        return super()._collection_element_ref(base_name, index)

    def _set_collection_numeric_literal(self, value, dest_info):
        return super()._set_collection_numeric_literal(value, dest_info)

    def _set_string_value_at_pos(self, string_token, pos, max_size):
        return super()._set_string_value_at_pos(string_token, pos, max_size)

    def _set_collection_string_literal(self, string_token, dest_info):
        return super()._set_collection_string_literal(string_token, dest_info)

    def _output_literal(self, token):
        return super()._output_literal(token)

    def _output_string_until_null_deterministic(self, pos, size):
        return super()._output_string_until_null_deterministic(pos, size)

    def _process_lines_range(self, lines, start_idx, end_idx):
        i = start_idx
        while i <= end_idx and i < len(lines):
            self._last_line = i + 1
            try:
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                tokens = self._tokenize(line)
                if tokens:
                    i = self._process_statement(tokens, lines, i)
                i += 1
            except BFPPCompileError:
                raise
            except BFPPPreprocessError:
                raise
            except Exception as e:
                self._raise_compile_error(e, lines)

    def _split_semicolon_statements(self, tokens):
        parts = []
        cur = []
        depth = 0
        for t in tokens:
            if t == '(':
                depth += 1
            elif t == ')':
                depth = max(0, depth - 1)
            if t == ';' and depth == 0:
                if cur:
                    parts.append(cur)
                cur = []
                continue
            cur.append(t)
        if cur:
            parts.append(cur)
        return parts

    def _process_statement(self, tokens, lines, line_idx):
        """
        Process a single statement and generate corresponding BF code.

        Returns the new line index after processing.
        """
        if not tokens:
            return line_idx

        if ';' in tokens:
            for part in self._split_semicolon_statements(tokens):
                if not part:
                    continue
                new_idx = self._process_single_statement(part, lines, line_idx)
                if new_idx != line_idx:
                    return new_idx
            return line_idx

        return self._process_single_statement(tokens, lines, line_idx)

    def _process_single_statement(self, tokens, lines, line_idx):
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
        elif cmd == 'inputint':
            if len(tokens) > 2 and tokens[1] == 'on':
                self._handle_inputint(tokens[2:])
            else:
                raise ValueError("inputint requires: inputint on <intvar>")
        elif cmd == 'inputfloat':
            if len(tokens) > 2 and tokens[1] == 'on':
                self._handle_inputfloat(tokens[2:])
            else:
                raise ValueError("inputfloat requires: inputfloat on <floatvar>")
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

    def _handle_set(self, tokens):
        """
        Handle variable assignment.

        Syntax: set <value> on <var>
        Supports: literals, strings, variables ($var), expressions
        """
        return super()._handle_set(tokens)

    def _set_string_literal(self, string_token, dest_var):
        """Set a string literal value to a string variable."""
        return super()._set_string_literal(string_token, dest_var)

    def _set_numeric_literal(self, value, dest_var):
        """Set a numeric literal to a variable."""
        return super()._set_numeric_literal(value, dest_var)

    def _handle_inc_dec(self, operation, tokens):
        """
        Handle increment/decrement operations.

        BF Code Generation:
        - For bytes: single + or -
        - For ints: increment LSB only (simplified)
        """
        return super()._handle_inc_dec(operation, tokens)

    # ===== Bitwise Operations =====

    def _handle_expression_assignment(self, expr_tokens, dest_var):
        """Handle arithmetic and bitwise expression assignment."""
        return super()._handle_expression_assignment(expr_tokens, dest_var)

    def _parse_expression(self, tokens):
        """Parse expression tokens into operands and operator."""
        return super()._parse_expression(tokens)

    def _load_operand(self, operand, target_pos, size=8):
        """Load a variable or literal into memory position."""
        return super()._load_operand(operand, target_pos, size=size)

    def _perform_bitwise_and(self, pos_a, pos_b, pos_result, size=8):
        """Perform bytewise AND on two multi-byte integers."""
        return super()._perform_bitwise_and(pos_a, pos_b, pos_result, size=size)

    def _perform_bitwise_or(self, pos_a, pos_b, pos_result, size=8):
        """Perform bytewise OR on two multi-byte integers."""
        return super()._perform_bitwise_or(pos_a, pos_b, pos_result, size=size)

    def _perform_bitwise_xor(self, pos_a, pos_b, pos_result, size=8):
        """Perform bytewise XOR on two multi-byte integers."""
        return super()._perform_bitwise_xor(pos_a, pos_b, pos_result, size=size)

    def _perform_bitwise_not(self, pos_in, pos_result, size=8):
        """
        Perform bytewise NOT (255 - value) on multi-byte integer.
        """
        return super()._perform_bitwise_not(pos_in, pos_result, size=size)

    def _perform_add(self, pos_a, pos_b, pos_result, size=8):
        """Perform addition on multi-byte integers."""
        return super()._perform_add(pos_a, pos_b, pos_result, size=size)

    def _perform_sub(self, pos_a, pos_b, pos_result, size=8):
        """Perform subtraction (a - b) on multi-byte integers."""
        return super()._perform_sub(pos_a, pos_b, pos_result, size=size)

    def _perform_mul(self, pos_a, pos_b, pos_result):
        """Perform multiplication using repeated addition (simplified)."""
        return super()._perform_mul(pos_a, pos_b, pos_result)

    def _perform_div(self, pos_a, pos_b, pos_result):
        """Perform integer division using repeated subtraction."""
        return super()._perform_div(pos_a, pos_b, pos_result)

    def _perform_mod(self, pos_a, pos_b, pos_result):
        """Perform modulo operation using repeated subtraction."""
        return super()._perform_mod(pos_a, pos_b, pos_result)

    def _bitwise_byte_operation(self, op, pos_a, pos_b, pos_result):
        """
        Generate BF code for bitwise operation on single byte using decomposition.

        Algorithm: Decompose both numbers by repeatedly extracting highest bit.
        """
        return super()._bitwise_byte_operation(op, pos_a, pos_b, pos_result)

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

    def _handle_while_loop(self, tokens, lines, line_idx):
        """
        Handle while loops.

        BF Code Pattern:
        1. Evaluate condition
        2. Loop: [execute body, if flag still set re-evaluate condition]
        """
        return super()._handle_while_loop(tokens, lines, line_idx)

    def _handle_for_loop(self, tokens, lines, line_idx):
        """
        Handle for loops.

        Desugars: for (init; cond; step) {...}
        Into: init; while (cond) {...; step}
        """
        return super()._handle_for_loop(tokens, lines, line_idx)

    def _handle_break(self):
        """
        Handle break statement.

        Clears the current loop's condition flag to exit.
        """
        return super()._handle_break()

    def _evaluate_condition(self, tokens, flag_pos):
        """
        Evaluate a condition and set flag (1=true, 0=false).

        Supports:
        - Variable truthiness
        - Comparisons (==, !=)
        - Negation (!)
        """
        return super()._evaluate_condition(tokens, flag_pos)

    def _generate_if_nonzero(self, pos, body_fn):
        return super()._generate_if_nonzero(pos, body_fn)

    def _load_runtime_subscript_into_buffer(self, base_info, idx_var, target_pos, size):
        return super()._load_runtime_subscript_into_buffer(base_info, idx_var, target_pos, size)

    def _input_string_at_pos(self, pos, size):
        return super()._input_string_at_pos(pos, size)

    def _handle_input(self, tokens):
        return super()._handle_input(tokens)

    def _handle_inputint(self, tokens):
        return super()._handle_inputint(tokens)

    def _handle_inputfloat(self, tokens):
        return super()._handle_inputfloat(tokens)

    def _process_block(self, lines, start_idx):
        """Process a code block enclosed in braces."""
        return super()._process_block(lines, start_idx)

    # ===== I/O Operations =====

    def _handle_move_to(self, tokens):
        """Handle 'move to <var>' command."""
        return super()._handle_move_to(tokens)

    def _handle_print_string(self, tokens):
        """
        Handle 'print string <literal>'.

        BF Code Generation:
        - For each character: set value, output, clear
        """
        return super()._handle_print_string(tokens)

    def _handle_varout(self, tokens):
        """
        Handle variable output (varout <var>).

        BF Code Generation:
        - For integers: convert to decimal and output digits
        - For strings: output until null terminator
        - For bytes: output as character
        """
        return super()._handle_varout(tokens)

    def _output_int_as_decimal(self, pos, size=8):
        return super()._output_int_as_decimal(pos, size=size)

    # ===== Helper Methods =====

    def _extract_parentheses_content(self, tokens):
        """Extract tokens between matching parentheses."""
        return super()._extract_parentheses_content(tokens)

    def _increment_multi_byte(self, pos, size=8):
        """Increment multi-byte integer with carry propagation."""
        return super()._increment_multi_byte(pos, size=size)

    def _decrement_multi_byte(self, pos, size=8):
        """Decrement multi-byte integer with borrow propagation."""
        return super()._decrement_multi_byte(pos, size=size)

    def _sum_bytes_to_check_zero(self, pos, sum_pos, size):
        """Sum bytes to check if all are zero (non-destructive)."""
        return super()._sum_bytes_to_check_zero(pos, sum_pos, size)