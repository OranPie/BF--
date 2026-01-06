# Error reporting

BF++ aims to provide **strict, readable errors** with:

- The error type (`PreprocessError` or `CompileError`)
- The exact 1-based line number
- A small code excerpt with the failing line marked
- A short **Hint** when possible
- The original exception is chained (`raise ... from e`) so Python tracebacks still show the root cause.

## Preprocess errors

Preprocessing runs before parsing and currently supports:

- `//` and `/* */` comment stripping
- Macros:
  - `#define NAME replacement...`
  - `#define NAME(arg1, arg2, ...) replacement...`
  - `#undef NAME`

Example error:

```text
PreprocessError: ValueError: Unknown preprocessor directive: #include (line 3)
   1 | #define X 1
   2 | declare byte a
>  3 | #include "x"
   4 | set X on a
Hint: Only #define and #undef are supported. Directives must start at the beginning of the line.
```

## Compile errors

Compilation errors can happen while parsing a statement or while compiling nested blocks.

Example error:

```text
CompileError: ValueError: Unknown variable: a (line 2)
   1 | print string "hi"
>  2 | set 1 on a
   3 | print string "bye"
Hint: Declare the variable first (declare byte/char/int/string...) and check spelling.
```

## Semicolon-separated statements

A single line may contain multiple statements separated by `;`.

- Splitting happens only at top-level (not inside parentheses).
- This is designed so `for (init; cond; step)` keeps working.
