# Examples

These examples compile BF++ source code to Brainfuck using `bfpp`, then execute the generated Brainfuck with the interpreter in `src/compiler.py`.

## How to run

From the repo root:

```bash
python3 examples/00_hello_world.py
python3 examples/01_vars_and_math.py
python3 examples/02_arrays_dicts_runtime_index.py
python3 examples/03_control_flow_match.py
python3 examples/04_input_echo.py
```

Each example writes `examples/_out.bf` and then executes it.
