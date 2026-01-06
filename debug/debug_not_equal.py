#!/usr/bin/env python3
"""Debug != operator"""
from bfpp import BrainFuckPlusPlusCompiler

# Add detailed logging
import bfpp.compiler

original_move_pointer = bfpp.compiler.BrainFuckPlusPlusCompiler._move_pointer

def debug_move_pointer(self, target_pos):
    if hasattr(self, '_debug_mode') and self._debug_mode:
        print(f"  _move_pointer: {self.current_ptr} -> {target_pos}")
    return original_move_pointer(self, target_pos)

bfpp.compiler.BrainFuckPlusPlusCompiler._move_pointer = debug_move_pointer

# Test != evaluation
code = """
declare byte x
set 1 on x
"""

compiler = BrainFuckPlusPlusCompiler()
compiler._debug_mode = True

# Manually call compile to setup variables
compiler.compile(code)

# Now manually test the condition evaluation
print("Testing condition: x != 3")
print("Variables:", compiler.variables)
print(f"Initial current_ptr: {compiler.current_ptr}")

# Allocate a flag
flag_pos = compiler._allocate_temp()
print(f"Allocated flag at position: {flag_pos}")
print(f"current_ptr after allocate: {compiler.current_ptr}")

# Evaluate the condition
compiler._debug_mode = True
compiler._evaluate_condition(['x', '!=', '3'], flag_pos)

print(f"\nFinal current_ptr: {compiler.current_ptr}")
print(f"Flag is at: {flag_pos}")

# Generate full BF code
compiler2 = BrainFuckPlusPlusCompiler()
compiler2._debug_mode = False
bf = compiler2.compile("""
declare byte x
set 1 on x
if (x != 3) {
    print string "T"
} else {
    print string "F"
}
""")

print("\n" + "="*60)
print("Full BF code:")
print(bf)
print(f"\nLength: {len(bf)}")
