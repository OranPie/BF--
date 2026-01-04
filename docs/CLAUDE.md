# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BF++ is a BrainFuck compiler and visualization toolkit consisting of:
- **BF++ Compiler** (`core.py`): A high-level language that compiles to BrainFuck
- **BrainFuck Interpreter** (`compiler.py`): Basic BrainFuck interpreter with JIT-like execution
- **BrainFuck Visualizer** (`visualizer.py`): Advanced PyQt5-based GUI with JIT-compiled execution (Numba)
- **Code Optimizer** (`simplify.py`): BrainFuck code simplification and optimization

## Running the Project

### BF++ Compiler (High-level to BrainFuck)
```bash
# Compile BF++ code to BrainFuck
python core.py
# Output is written to output.bf by default
```

### BrainFuck Interpreter
```bash
# Run a BrainFuck program
python compiler.py <filename.bf>
```

### Interactive Visualizer (Recommended)
```bash
# Launch GUI visualizer with JIT execution
python visualizer.py
```

### Code Optimization
```bash
# Simplify and optimize BrainFuck code
python simplify.py
# Reads from bf.bf, outputs to neat.bf
```

## Architecture

### BF++ Language (`core.py`)

**Memory Model:**
- Variables allocated sequentially from position 0
- Temporary cells allocated from end of used memory
- Stack-based temporary cell management (must free in LIFO order)

**Type System:**
- `byte`/`char`: 1 byte
- `int`: 8 bytes (64-bit little-endian)
- `string <size>`: Variable-length with null terminator

**Code Generation Strategy:**
- Direct translation for simple ops (+, -, <, >)
- Loop-based algorithms for complex ops (copy, compare, bitwise)
- All bitwise operations work on byte level for 8-byte integers
- Bit extraction uses divmod-by-2 pattern in BF loops

**Key Classes & Methods:**
- `BrainFuckPlusPlusCompiler`: Main compiler class
  - `compile(code)`: Entry point for compilation
  - `_allocate_temp(size)` / `_free_temp(pos)`: Temporary memory management
  - `_move_pointer(target_pos)`: Generate pointer movement code
  - `_copy_cell(src, dest, temp)`: Non-destructive cell copy
  - `_bitwise_byte_operation(op, pos_a, pos_b, pos_result)`: Bitwise AND/OR/XOR on bytes
  - `_evaluate_condition(tokens, flag_pos)`: Condition evaluation for control flow

### BrainFuck Interpreter (`compiler.py`)

Simple interpreter with:
- Memory: 30,000 cells (standard BrainFuck tape)
- Jump table preprocessing for bracket matching
- `generate_code(source)`: Returns executable Python function
- `execute(mem)`: Runs the generated code

### Visualizer (`visualizer.py`)

**Performance Architecture:**
- Uses **Numba JIT** for high-speed execution (>10,000x faster than pure Python)
- Dual execution modes:
  - **Step mode**: <500 steps/s, updates UI every step
  - **JIT mode**: >500 steps/s, uses `jit_loop_optimized()` with batched updates
- Memory optimizations:
  - Power-of-2 memory size (32768) for fast bitwise modulo
  - Uint8 arithmetic to prevent overflow
  - Selective UI updates (only changed cells within view range)

**Key Components:**
- `BrainFuckRunner`: Core execution engine
  - `load_program(text)`: Preprocess and prepare program
  - `step()`: Single-step execution (step mode)
  - `run_jit_step()`: Batch execution (JIT mode)
  - `_preprocess_brackets()`: Build jump table as NumPy array for Numba
- `BrainFuckVisualizer`: PyQt5 GUI
  - Memory table with color-coded cells (orange=pointer, green=non-zero)
  - Real-time execution graph with matplotlib
  - Keyboard shortcuts: F5=step, F6=run/pause, F7=stop, F8=reset
- `VideoExportThread`: HD video export (requires opencv-python)
  - Uses `jit_execute_bulk()` for fast rendering without I/O
  - Parallel frame generation with ThreadPoolExecutor

**JIT Functions (Numba):**
- `jit_loop_optimized()`: Main execution loop, returns after max_steps or I/O
- `jit_execute_bulk()`: Skips I/O for video generation

### Code Optimizer (`simplify.py`)

**Optimization Techniques:**
- Collapse runs of +/- and >/< commands
- Canonicalize clear loops: `[---]` → `[-]`
- Modulo-256 arithmetic for cell deltas
- Recursive simplification of nested loops

## BF++ Language Syntax

### Variable Declaration
```
declare byte x
declare int y
declare string 20 message
```

### Assignment
```
set 42 on x
set "Hello!" on message
set $x & $y on result    // Bitwise AND
set ~ $x on result       // Bitwise NOT
```

### Control Flow
```
if (x == 5) { ... } else { ... }
while (counter) { ... }
for (set 0 on i; i != 10; inc on i) { ... }
break
```

### I/O
```
output              // Output current cell (BF '.')
input               // Input to current cell (BF ',')
print string "Hi"   // Print string literal
varout message      // Print variable value
```

### Operations
- `inc` / `dec`: Increment/decrement
- `left` / `right`: Move pointer
- `move to <var>`: Move pointer to variable
- `clear`: Set current cell to zero

## Recent Bug Fixes

### Session 1 (Initial fixes):
1. String varout - Pointer position after string assignment
2. If/else blocks - Both branches executing
3. While loops - Condition evaluation
4. Negative numbers support
5. Comparison operators basic functionality
6. Block parsing for `} else {`

### Session 2 (Complex problems):
1. **For loops** - Fixed token joining bug (was creating `"set0oni"` instead of `['set', '0', 'on', 'i']`)
2. **!= operator** - Rewrote comparison algorithm (8-bit wrap issue with absolute value simulation)
3. **Break statement** - Added conditional re-evaluation (was unconditionally overwriting break)

### Known Issues (Still Broken):
- **Integer varout** - Complex decimal conversion algorithm (25K+ char BF, no output)
- **Bitwise operations** - AND, OR, XOR, NOT all timeout (bit extraction loop bugs)

### Working Features (92.9% test pass rate):
- ✓ Byte variables and I/O
- ✓ String variables and output
- ✓ If/else statements with == and !=
- ✓ While loops (including complex conditions)
- ✓ For loops
- ✓ Break statement
- ✓ Inc/dec operations
- ✓ Print string literals
- ✓ Negative number literals

## Development Notes

**When modifying the BF++ compiler:**
- Always maintain stack discipline for temp cells (free in reverse order)
- When clearing cells in loops, specify position: use `_generate_clear(pos)` not `_generate_clear()`
- Don't join tokens into strings - preserve token list structure
- Comparison operators use simple subtraction, not absolute value simulation
- While loops copy cond_flag before re-evaluating to support break
- Block processing checks `}` before `{` to handle `} else {` correctly

**When modifying the visualizer:**
- Be careful with NumPy uint8 overflow - use explicit modulo arithmetic
- JIT threshold (`JIT_THRESHOLD = 500`) controls mode switching
- Update `bracket_map_arr` as NumPy array for Numba compatibility

**When running:**
- Basic operations (bytes, strings, if/else, while, for, break) are reliable
- Avoid integer varout and bitwise operations until fixed
- For production BF code, run through simplify.py to optimize
