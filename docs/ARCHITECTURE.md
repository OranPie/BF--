# Compiler architecture

## Overview

The compiler lives in `src/bfpp/` and is centered around:

- `bfpp.compiler.BrainFuckPlusPlusCompiler`: main class
- `bfpp.state.CompilerState`: mutable state container
- A set of mixins that implement subsystems

The goal of the current architecture is to keep the public surface compatible while breaking up the implementation into smaller modules.

## Key modules

- `bfpp/compiler.py`
  - Orchestrates compilation (`compile`), statement dispatch, and wires mixins.
  - Keeps backward-compatible method names that delegate to mixins.

- `bfpp/state.py`
  - `CompilerState` dataclass holding mutable state:
    - `variables`, `bf_code`, `current_ptr`, `max_ptr`, temp stack, etc.

## Mixins

- `bfpp/ops_memory.py` (`MemoryOpsMixin`)
  - Low-level tape operations, temp allocation, copy/clear primitives.

- `bfpp/ops_runtime.py` (`RuntimeOpsMixin`)
  - Runtime helpers such as runtime subscripts and small conditional helpers.

- `bfpp/ops_vars.py` (`VarsOpsMixin`)
  - Variable addressing and declarations/assignments:
    - `_resolve_var`, `declare`, `set`, `inc/dec`, collection helpers.

- `bfpp/ops_arith.py` (`ArithOpsMixin`)
  - Integer arithmetic/bitwise expression compilation:
    - `_handle_expression_assignment`, add/sub/mul/div/mod, bitwise ops.

- `bfpp/ops_io.py` (`IOMixin`)
  - I/O statements:
    - `print string`, `varout`, `input on`.

- `bfpp/ops_control.py` (`ControlFlowMixin`)
  - Control flow:
    - `if/else`, `while`, `for`, `break`, `match`.

## Backward compatibility

- `src/core.py` re-exports `BrainFuckPlusPlusCompiler` for older imports.
- `bfpp.__init__` re-exports `BrainFuckPlusPlusCompiler`, `preprocess`, `tokenize`, and the `bfpp.api` helpers.
