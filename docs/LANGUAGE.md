# BF++ Language Reference

BF++ is a small, line-oriented, imperative language that compiles to Brainfuck.

This document describes **the language as implemented in this repository** (see `src/bfpp/compiler.py`).

---

## 0. Quick start (this repository)

### 0.1 Compile BF++ to Brainfuck

In Python:

```python
from bfpp import BrainFuckPlusPlusCompiler

code = 'print string "Hello!\\n"'
bf = BrainFuckPlusPlusCompiler().compile(code)
open('out.bf', 'w').write(bf)
```

Notes:

- The compiler implementation is `src/bfpp/compiler.py`.
- BF++ compiles to Brainfuck source (a string of `+-<>[],.`).

### 0.2 Run Brainfuck

This repo includes a simple Brainfuck interpreter/JIT helper (`src/compiler.py`). Typical usage:

```bash
python src/compiler.py out.bf
```

### 0.3 Optional optimization

The compiler can optionally run the generated Brainfuck through `src/optimizer.py`.

Depending on how you invoke the compiler, you can pass an optimization level:

- `BrainFuckPlusPlusCompiler(optimize_level=5)`
- or per-compile: `compile(code, optimize_level=5)`

---

## 1. Lexical rules

### 1.1 Comments

- `// ...` line comment
- `/* ... */` block comment

Comments are removed before parsing.

### 1.2 Tokens

- Keywords and identifiers are separated by whitespace.
- String literals are double-quoted: `"Hello"`
- Operators include: `+ - * / % & | ^ ~ == != < > <= >= !`
- Delimiters include: `{ } ( ) [ ] , ;`

### 1.4 Preprocessor macros

Preprocessing runs before parsing.

Supported directives (must start at the beginning of a line):

- `#define NAME <replacement...>`
- `#define NAME(arg1, arg2, ...) <replacement...>`
- `#undef NAME`

Notes:

- Macro expansion is token-based.
- Expansion does **not** happen inside string literals.
- Parameterized macros require parentheses at the call site (use `MACRO()` for zero-arg macros).
- Recursive macro expansion is limited (to prevent infinite recursion).

### 1.3 Case

Keywords are case-insensitive (internally lowered). Identifiers are treated as written.

---

## 2. Program structure

BF++ is processed **line-by-line**. Each line is either:

- a statement (e.g. `set 5 on x`)
- a block header (`if (...) {`, `while (...) do`, etc.)
- a block terminator (`}`, `endif`, `endwhile`)

In general:

- Most statements are a single line.
- Block bodies are a sequence of statements.
- Braces (`{ ... }`) and keyword terminators (`then/endif`, `do/endwhile`) are both accepted for `if` and `while`.

### 2.1 Semicolon-separated statements

Multiple statements may appear on a single line separated by `;`:

```bfpp
declare byte x ; set 65 on x ; move to x ; output
```

Rules:

- Splitting only happens at top-level (not inside parentheses), so `for (init; cond; step)` keeps working.

---

## 3. Types and memory model

### 3.1 Memory model

- Variables are allocated sequentially on the Brainfuck tape.
- Temporary cells are allocated after variables and are freed in LIFO order.

### 3.2 Scalar types

- `byte` / `char`
  - Size: 1 cell
  - Used for small integers (0..255) and character output.
- `int`
  - Size: 8 cells
  - 64-bit **little-endian**, signed.
- `string <N>`
  - Stored as `N + 1` cells (null-terminated)
  - Example: `declare string 20 msg` allocates 21 cells.

---

## 4. Declarations

### 4.1 Scalar variables

```bfpp
declare byte x
declare char c
declare int n
declare string 20 msg
```

### 4.2 Arrays

Arrays are contiguous blocks of fixed length.

#### Numeric arrays

Either form is accepted:

```bfpp
declare byte arr[10]
declare int[4] nums
```

#### String arrays

```bfpp
declare string 10 names[3]
```

Meaning: 3 strings, each with capacity 10 chars (+ null terminator).

### 4.3 Dicts (compile-time key sets)

Dicts are fixed-size maps where keys are declared up front.

#### Numeric dicts

```bfpp
declare dict byte m { a, b, "c" }
declare dict int scores { alice, bob }
```

#### String dicts

```bfpp
declare dict string 10 sm { left, right }
```

Keys may be identifiers (`left`) or string literals (`"key"`). Keys must be unique.

Implementation detail: dict entries are stored as a contiguous array in key-declaration order.

This order matters for runtime dict subscripting `m[$k]` (see §5.4).

---

## 5. Addressing / variable references

### 5.1 Scalars

Use the variable name directly:

- `x`
- `msg`

### 5.2 Array element (compile-time index)

```bfpp
arr[0]
nums[3]
```

Index must be a non-negative integer literal.

### 5.3 Dict entry (compile-time key)

```bfpp
m[a]
m["c"]
```

### 5.4 Runtime subscripts (deterministic scan)

Some operations support runtime selection via a **1-byte index variable**:

```bfpp
arr[$i]
m[$k]
```

- `$i` / `$k` must be a declared **byte/char-sized** variable (1 cell).
- Runtime subscripts are implemented by scanning slot indices and applying the operation on the matching slot.
- This is intentionally pointer-safe for the current compiler design.

Dicts with runtime subscripts use **slot-id indexing**, not key lookup:

- `declare dict byte m { a, b, c }`
- `m[$k]` selects:
  - slot `0` = key `a`
  - slot `1` = key `b`
  - slot `2` = key `c`

Current runtime-subscripting is **not** a general “pointer-to-element” operation; it is only supported in certain statements (documented below).

---

## 6. Statement reference (complete)

This section is the authoritative catalog of statements supported by the current compiler.

### 6.1 Declarations

- `declare byte <name>`
- `declare char <name>`
- `declare int <name>`
- `declare string <N> <name>`
- Arrays:
  - `declare byte <name>[<Len>]`
  - `declare int <name>[<Len>]`
  - `declare string <N> <name>[<Len>]`
  - Alternate numeric form: `declare int[<Len>] <name>`
- Dicts:
  - `declare dict byte <name> { <keys...> }`
  - `declare dict int <name> { <keys...> }`
  - `declare dict string <N> <name> { <keys...> }`

Keys can be identifiers or string literals. Commas are optional separators.

### 6.2 Assignment

- `set <number> on <varRef>`
- `set - <number> on <varRef>` (negative literal tokenized as `-` + number)
- `set "<string>" on <varRef>`

Where `<varRef>` can be:

- scalar: `x`, `msg`
- element: `arr[0]`, `m[a]`, `names[1]`
- whole collection: `arr`, `m`, `names`, `sm`
- runtime subscript (limited): `arr[$i]`, `m[$k]`, `names[$i]`

Expression assignment (ints only):

- `set $a + $b on c`
- `set $a - $b on c`
- `set $a * $b on c`
- `set $a / $b on c`
- `set $a % $b on c`
- `set $a & $b on c`
- `set $a | $b on c`
- `set $a ^ $b on c`
- `set ~ $a on c`

### 6.3 Increment/decrement

- `inc on <varRef>`
- `dec on <varRef>`

Supports scalar refs, element refs, and runtime subscripts (`arr[$i]`, `m[$k]`).

### 6.4 Tape movement

- `left`
- `right`

### 6.5 Move to variable

- `move to <varRef>`

Supports scalar refs and compile-time element refs (`arr[0]`, `m[a]`).
Runtime `move to arr[$i]` is not supported.

### 6.6 Memory

- `clear`

Clears the **current tape cell** (equivalent to Brainfuck `[-]`).

### 6.7 Raw Brainfuck I/O

- `output` (Brainfuck `.`)
- `input` (Brainfuck `,`)

### 6.8 Print string literal

- `print string "..."`

### 6.9 Variable output

- `varout <varRef> [sep <token>] [end <token>]`

Behavior by type:

- `byte`/`char`:
  - scalar: prints one character
  - collection: prints each element as a character
- `int`:
  - scalar: prints decimal (see implementation notes/limitations)
  - collection: prints each element; default `sep` is a space (`32`) if none is provided
- `string`:
  - scalar: prints bytes until `\0` (null terminator), bounded by declared size
  - collection: prints each string element similarly

`sep` / `end` tokens can be:

- string literal: `"\n"`, `","`, `"-"`
- numeric byte: `32` for space, `10` for newline

### 6.10 Control flow

`if`:

- `if (<cond>) { ... }`
- `if (<cond>) { ... } else { ... }`
- `if (<cond>) then ... endif`
- `if (<cond>) then ... else ... endif`

`while`:

- `while (<cond>) { ... }`
- `while (<cond>) do ... endwhile`

`for`:

- `for (<init>; <cond>; <step>) { ... }`

`break`:

- `break`

---

## 7. Optimizer

The compiler supports optional Brainfuck optimization via `optimizer.py`.

If enabled, generated BF code is passed through `optimize_bf` with a configurable level.

(Exact entry points depend on how you call `BrainFuckPlusPlusCompiler` in your scripts.)

---

## 8. Known limitations

These are limitations of the current implementation (not theoretical BF++ constraints):

- Runtime subscripts are supported only for specific statements (`set` literal, `inc/dec`, `varout`).
- Runtime subscripts require a 1-byte index variable.
- Runtime dict access uses **slot-id** indexing (`m[$k]`), not string hashing.
- Some advanced operations (notably complex integer I/O / heavy bitwise workloads) can produce very large BF or be slow.

---

## 9. Examples

### 9.1 Hello world

```bfpp
print string "Hello, World!\n"
```

### 9.2 Arrays + runtime index

```bfpp
declare byte i
declare byte arr[3]

set 1 on i
set 66 on arr[$i]

varout arr end "\n"
```

### 9.3 Collection fill + formatting

```bfpp
declare byte arr[5]
set 65 on arr
varout arr sep "," end "\n"
```

### 9.4 Dict slot-id runtime indexing

```bfpp
declare dict byte m { a, b, c }
declare byte k

set 2 on k
set 90 on m[$k]

varout m sep "-" end "\n"
```

### 9.5 String collections

```bfpp
declare string 6 sarr[2]
set "hi" on sarr[0]
set "yo" on sarr[1]
varout sarr sep "," end "\n"

declare dict string 6 sm { left, right }
set "L" on sm[left]
set "R" on sm[right]
varout sm sep ":" end "\n"
```
