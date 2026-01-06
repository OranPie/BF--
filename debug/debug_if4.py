#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler

# Add some debug logging to understand the flow
import bfpp.compiler

original_process_block = bfpp.compiler.BrainFuckPlusPlusCompiler._process_block

def debug_process_block(self, lines, start_idx):
    print(f"_process_block called with start_idx={start_idx}")
    if start_idx < len(lines):
        print(f"  Starting line: '{lines[start_idx]}'")
    result = original_process_block(self, lines, start_idx)
    print(f"  Returned: {result}")
    if result < len(lines):
        print(f"  End line: '{lines[result]}'")
    return result

bfpp.compiler.BrainFuckPlusPlusCompiler._process_block = debug_process_block

code = """if (x == 5) {
    move to y
    output
} else {
    move to n
    output
}"""

# Split into lines like the compiler does
lines = code.split('\n')
print("Lines:")
for i, line in enumerate(lines):
    print(f"  {i}: '{line}'")

print("\n" + "="*60)
compiler = BrainFuckPlusPlusCompiler()
compiler.variables['x'] = {'pos': 0, 'type': 'byte', 'size': 1}
compiler.variables['y'] = {'pos': 1, 'type': 'byte', 'size': 1}
compiler.variables['n'] = {'pos': 2, 'type': 'byte', 'size': 1}
compiler.max_ptr = 3

tokens = compiler._tokenize(lines[0])
print(f"\nProcessing line 0: {tokens}")
result = compiler._handle_if_statement(tokens[1:], lines, 0)
print(f"Returned: {result}")
