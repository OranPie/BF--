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

## Deep Trace and Debugging

The compiler supports an opt-in **Trace Mode** for deep debugging.

- Enable by passing `is_tracing=True` to `BrainFuckPlusPlusCompiler.compile()`.
- When tracing is active, `BFPPCompileError` will include a **Compilation Trace** of the last 10 processed statements.
- Trace output includes the line number and original source tokens for each step.

Example with trace:
```python
compiler = BrainFuckPlusPlusCompiler()
try:
    bf = compiler.compile(code, is_tracing=True)
except BFPPCompileError as e:
    print(e)
```

## Structured Metadata

Errors now include a `metadata` dictionary with the compiler's internal state at the time of failure:
- `ptr`: Current Brainfuck tape pointer position.
- `max_ptr`: Highest memory address allocated.
- `temp_cells_count`: Number of active temporary cells.
- `vars_count`: Total number of declared variables.
