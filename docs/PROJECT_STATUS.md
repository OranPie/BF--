# Project Status (NOW) and TODO

This document is a pragmatic snapshot of the BF++ project:

- **NOW**: what the repository currently supports (language + compiler + runtime helpers).
- **TODO**: what remains unfinished or needs improvement across the project.

It intentionally covers the whole project (not only floats).

---

## NOW: What works today

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

### Language surface (statements)

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
    - Expression assignment supports `+` / `-`
    - Conversions via `set $int on float` and `set $float on int` (truncation)

- `float64` (deferred for full correctness)
  - Declared and stored as 8 cells like `float`.
  - Input/output plumbing exists, but full arithmetic correctness depends on upgrading the 8-byte backend.

---

## TODO: What should be done next

### Highest priority

- **Float R1: complete arithmetic set**
  - Implement `*` and `/` for `float` expressions (scale-aware):
    - `a*b` should compute `(a_scaled * b_scaled) / 1000`
    - `a/b` should compute `(a_scaled * 1000) / b_scaled`
  - Define and enforce behavior for division-by-zero and overflow.

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

- **Performance / BF size improvements**
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
  - varout decimal: YES (deterministic; backend still needs upgrades)
  - inputint: YES
  - expression assignment: YES

- **string**
  - declare/set/varout/input: YES

- **float (scale=1000)**
  - declare/set literal: YES
  - inputfloat: YES
  - varout `INT.FFF`: YES
  - comparisons: YES
  - expression assignment: `+/-` YES, `*//` TODO

- **float64**
  - declare/set literal/input/varout: PARTIAL
  - arithmetic: TODO (requires int64 backend upgrades)
