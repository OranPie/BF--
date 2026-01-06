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
python3 examples/05_macros.py
python3 examples/06_fizzbuzz.py
python3 examples/07_caesar_cipher_byte.py
python3 examples/08_frequency_table.py
```

Each example writes `examples/_out.bf` and then executes it.

## What to read first

- **00_hello_world.py**
  - Basics: compilation + execution pipeline.
- **01_vars_and_math.py**
  - Int math + `if` condition.
- **03_control_flow_match.py**
  - `match` + loops.
- **05_macros.py**
  - Preprocessor macros (`#define`, parameterized macros, semicolons).
- **06_fizzbuzz.py**
  - A classic educational program using arithmetic + nested control flow.
- **08_frequency_table.py**
  - A small “real-world-ish” counter using dicts + runtime subscripts.
