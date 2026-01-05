# BF++

BF++ is a small, line-oriented language that compiles to Brainfuck.

The repository contains:

- `src/bfpp/`: The BF++ compiler implementation (Python)
- `src/compiler.py`: A Brainfuck interpreter / execution helper
- `src/optimizer.py`: Optional Brainfuck optimizer
- `src/visualizer.py`: GUI visualizer

## Quick start

### Compile BF++ to Brainfuck (Python)

```python
from bfpp.api import compile_string

result = compile_string('print string "Hello"')
open('out.bf', 'w', encoding='utf-8').write(result.bf_code)
```

### Run Brainfuck

```bash
python3 src/compiler.py out.bf
```

## Documentation

- `docs/README.md`: Documentation index
- `docs/LANGUAGE.md`: BF++ language reference
- `docs/API.md`: Public Python API (`bfpp.api`)
- `docs/ARCHITECTURE.md`: Compiler architecture and module layout
