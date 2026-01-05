# Public Python API

## Recommended entry points

Use `bfpp.api` for a stable, minimal API surface:

```python
from bfpp.api import CompileOptions, compile_string

result = compile_string(
    'print string "Hello"',
    options=CompileOptions(optimize_level=5),
)

print(result.bf_code)
print(result.variables)
print(result.max_ptr)
```

## `CompileOptions`

- `optimize_level: int | None`
  - If set, the generated Brainfuck is passed through `optimizer.optimize_bf`.

## `CompileResult`

- `bf_code: str`
  - Generated Brainfuck source.
- `variables: dict[str, dict[str, Any]]`
  - Variable allocation metadata from the compiler.
- `max_ptr: int`
  - Maximum tape position used.

## Lower-level compiler API

You can still use `BrainFuckPlusPlusCompiler` directly:

```python
from bfpp import BrainFuckPlusPlusCompiler

compiler = BrainFuckPlusPlusCompiler(optimize_level=2)
code = 'print string "Hello"'
brainfuck = compiler.compile(code)
```

This is considered a lower-level API than `bfpp.api`.
