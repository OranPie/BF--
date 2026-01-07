# Project Status (NOW) and TODO

This document is a pragmatic snapshot of the BF++ project:

- **NOW**: what the repository currently supports (language + compiler + runtime helpers).
- **TODO**: what remains unfinished or needs improvement across the project.

It intentionally covers the whole project (not only floats).

---

## NOW: What works today

- **Robust int64 backend**
  - Full 8-byte `int` arithmetic primitives:
    - Addition/Subtraction
    - Signed Multiplication (`*`)
    - Signed Division (`/`) and Modulo (`%`)
    - Bitwise operations (`&`, `|`, `^`, `~`)
  - Full 64-bit decimal printing for `int`.

### Repository structure

- `src/bfpp/`
  - BF++ compiler implementation (Python).
- `src/compiler.py`
  - Brainfuck interpreter / execution helper used by tests and scripts.
- `src/optimizer.py`
  - Optional Brainfuck optimizer.
- `src/visualizer.py`
  - GUI visualizer (useful for debugging Brainfuck execution).
- `tests/test_execution.py`
  - End-to-end execution tests (compile BF++ -> run generated BF -> compare output).

### Compiler architecture

- Main entry point:
  - `bfpp.compiler.BrainFuckPlusPlusCompiler`
- Core architecture is mixin-based (see `docs/ARCHITECTURE.md`):
  - `MemoryOpsMixin` (low-level tape operations)
  - `RuntimeOpsMixin` (runtime subscripts helpers)
  - `VarsOpsMixin` (declare/set/inc/dec, variable resolution)
  - `ArithOpsMixin` (expression assignment)
  - `IOMixin` (I/O statements)
  - `ControlFlowMixin` (if/while/for/match)

### Error Reporting

- **Classification**: Compile-time errors are categorized into `ParseError`, `TypeError`, `NotImplementedError`, `RuntimeError`, and `InternalError`.
- **Context & Hints**: Every error includes a source code snippet with line numbers and a pragmatic `Hint:` for resolution.

### Output & Runtime Efficiency Status

- **Numeric Types (int/float/expfloat)**: 
  - **Arithmetic Complexity**:
    - **Addition/Subtraction**: O(N) where N is bytes. Low BF overhead.
    - **Multiplication**: O(bits^2) via Russian Peasant algorithm. Significant BF code size (~50k-200k chars for 64-bit).
    - **Division/Modulo**: O(bits^2) via bit-by-bit long division. Extremely heavy BF code overhead (~500k+ chars for 64-bit).
  - **Lightweight Printing (varout)**: Both `float` and `expfloat` currently use a 16-bit-based decimal printer.
    - **Efficiency**: High (~1.4M chars for basic output).
    - **Trade-off**: **Lossy**. Only correctly prints values in range `[-32.768, 32.767]`. Larger values wrap.
  - **Robust Printing**: `int` uses full 64-bit long-division-by-10. Accurate but very large BF code size.
- **String Operations**:
  - **Assignment/Output**: O(L) where L is string length. Linear BF code generation.
  - **Memory**: Each string has a fixed buffer size allocated at declaration time.
- **Runtime Subscripts**:
  - Uses deterministic pointer-shifting loops.
  - **Efficiency**: O(Index) runtime complexity. Generates a fixed-size BF loop block regardless of array size.
- **Control Flow**:
  - **if/while**: Constant BF overhead for jumping.
  - **for**: Fixed-step loops are efficient.
  - **match**: O(Cases) complexity using sequential if-checks.
- **Memory Management**:
  - Uses a stack-based temporary allocator for constants and intermediate results.
  - Automatic cleanup of temporary cells prevents memory leaks on the BF tape.
- **Preprocessor**:
  - **Macro Expansion**: O(Depth * Tokens). Expansion limit enforced at 50 to prevent infinite recursion.
  - **Code Stripping**: Comments and whitespaces are stripped before tokenization.
- **Optimization**:
  - **Level 1+**: Folds repeated `+` / `-` / `>` / `<` and simplifies loops.
  - **Trade-off**: Increases compilation time but reduces generated BF size significantly.

Authoritative language reference: `docs/LANGUAGE.md`.

Supported major features:

- **Preprocessor macros**
  - `#define` (with and without args), `#undef`
  - Token-based expansion (not inside string literals)

- **Declarations**
  - Scalars: `byte`, `char`, `int`, `string <N>`
  - Arrays: `T name[Len]` and `T[Len] name` forms (numeric); `string <N> name[Len]`
  - Dicts: `declare dict <type> name { keys... }` with compile-time key set

- **Assignment**
  - Numeric literal: `set <number> on <varRef>` (including `set - <number> on ...`)
  - String literal: `set "..." on <varRef>`
  - Collection fill: `set <literal> on <arrayOrDict>`
  - Runtime subscripts supported for certain operations (see below)

- **Expression assignment**
  - `set <expr> on <dest>` where `<expr>` is `$a <op> $b` or unary `~ $a`
  - See `docs/LANGUAGE.md` for the catalog of operators.

- **Increment/decrement**
  - `inc on <varRef>`
  - `dec on <varRef>`

- **Control flow**
  - `if (...) { ... }` + optional `else`
  - `while (...) { ... }`
  - `for (init; cond; step) { ... }`
  - `break`
  - `match` statement

- **I/O**
  - Raw Brainfuck: `input`, `output`
  - `print string "..."`
  - `varout <varRef> [sep <token>] [end <token>]`
  - `input on <varRef>` for byte/char/string
  - Convenience numeric input:
    - `inputint on <intVar>` parses ASCII decimal into 8-byte `int`
    - `inputfloat on <floatVar>` parses ASCII decimal into scaled float storage

### Runtime subscripts (current scope)

Runtime subscripts are supported in a limited, deterministic way:

- Syntax:
  - Arrays: `arr[$i]`
  - Dicts: `m[$k]` (slot-id indexing)
- Requirements:
  - `$i` / `$k` must be a 1-byte variable (byte/char)
- Supported operations (current implementation):
  - `set <literal> on arr[$i]` / `m[$k]`
  - `inc/dec on arr[$i]` / `m[$k]`
  - `varout arr[$i]` / `m[$k]`
  - Some condition / expression operand support exists (tests cover key paths)

### Types (NOW)

- `byte` / `char`
  - 1 cell

- `int`
  - 8 cells
  - Little-endian, signed
  - Deterministic decimal printing exists (primarily for debugging / tests)

- `string <N>`
  - Stored as `N + 1` cells, null-terminated

- `float` (R1, scale=1000)
  - Stored in 8 cells as a signed scaled integer representation.
  - Current arithmetic focus is R1-safe behavior.
  - Supported now:
    - `declare float`
    - `set` with float literals like `1.234` (Decimal-based parsing)
    - `inputfloat on <floatvar>`
    - `varout <floatvar>` prints `[-]INT.FFF`
    - Comparisons in conditions (`== != < > <= >=`)
    - Expression assignment supports `+` / `-` / `*` / `/`
    - Conversions via `set $int on float` and `set $float on int` (truncation)

- `expfloat` (8-byte, scale=1000)
  - Stored as a full 8-byte signed scaled integer.
  - **Scientific Notation**: Supports literals like `1e-3` or `2.5E+6` in `set` and conditions.
  - Supported now:
    - `declare expfloat`
    - `set` with exponential literals (Decimal-based parsing)
    - `varout <expfloatvar>` (uses lightweight 16-bit printer for size efficiency)
    - Comparisons in conditions
    - Expression assignment supports `+` / `-` / `*` / `/` using full 64-bit arithmetic

- `float64` (deferred for full correctness)
  - Declared and stored as 8 cells like `float`.
  - Input/output plumbing exists, but full arithmetic correctness depends on upgrading the 8-byte backend.

---

## TODO: What should be done next

### Highest priority

- **Float (R1) & Expfloat: complete arithmetic set**
  - Implement `*` and `/` expressions (scale-aware): DONE.
  - Current support: `+`, `-`, `*`, `/`.
  - Define and enforce behavior for division-by-zero: Initial compile-time check added.

- **Robust int64 backend**
  - Strengthen 8-byte `int` arithmetic primitives used by expression compilation:
    - multiplication/division/modulo for full 64-bit
    - more robust decimal printing (not “debug-small-int only”)
  - This is prerequisite for making `float64` (R2) fully correct and performant.

### Medium priority

- **Formalize numeric conversion rules**
  - Explicit, documented rules for:
    - int <-> float (scale=1000)
    - float <-> float64 (widen/narrow)
    - mixed-type expression operands
  - Enforce compile-time errors for unsupported implicit conversions.

- **Unify float range enforcement**
  - R1 `float` literals have a range check.
  - Extend range checks to:
    - results of float arithmetic
    - `inputfloat` parsed values
    - assignment conversions (int->float)

- **Runtime subscripts: expand coverage carefully**
  - Consider supporting runtime subscript in more statements (only if pointer-safe):
    - more expression contexts
    - possibly `move to arr[$i]` (if it can be done without unsafe pointer behavior)

### Quality / reliability

- **More execution tests**
  - Float arithmetic (`+ - * /`) including negatives and boundary values
  - Conversion roundtrips: int->float->int, float->int->float
  - Runtime subscripts on float arrays/dicts

- **Optimized 8-byte Decimal Printing**
  - The current `int` printer is robust but the `expfloat` printer is lossy (16-bit only).
  - Goal: Implement an optimized full 64-bit decimal printer for `expfloat` that doesn't explode BF size as much as the current `int` one.
  - Identify hot codegen patterns that explode BF size.
  - Add optimizer passes or smarter code generation where safe.

### Documentation

- **Update language reference (`docs/LANGUAGE.md`)**
  - Add `float` / `float64` section:
    - scale=1000
    - literal format, `varout` format, `inputfloat`
    - conversions
    - expression support matrix

---

## Quick “capability matrix” (high level)

- **byte/char**
  - declare/set/inc/dec: YES
  - varout: YES
  - input: YES

- **int (8-byte)**
  - declare/set/inc/dec: YES
  - varout decimal: YES (robust 64-bit)
  - inputint: YES
  - expression assignment: YES (signed 64-bit)

- **string**
  - declare/set/varout/input: YES

- **float (scale=1000)**
  - declare/set literal: YES
  - inputfloat: YES
  - varout `INT.FFF`: YES
  - comparisons: YES
  - expression assignment: `+/-/*//` YES

- **expfloat (8-byte, scale=1000)**
  - declare/set (literal/scientific): YES
  - inputfloat: YES
  - varout `INT.FFF`: YES (lightweight printer)
  - comparisons: YES
  - expression assignment: `+/-/*//` YES (64-bit)

- **float64**
  - declare/set literal/input/varout: PARTIAL
  - arithmetic: TODO (requires int64 backend upgrades)
