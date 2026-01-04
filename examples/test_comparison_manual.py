#!/usr/bin/env python3
"""Manually test the comparison logic"""

# Create a simple test: check if 1 == 3
from core import BrainFuckPlusPlusCompiler

code = """
declare byte x
set 1 on x
"""

compiler = BrainFuckPlusPlusCompiler()
compiler.compile(code)

print("Testing x==3 where x=1")
print(f"Variables: {compiler.variables}")

# Manually build the comparison
flag_pos = compiler._allocate_temp()
print(f"Flag at position: {flag_pos}")

# Evaluate x == 3
compiler._evaluate_condition(['x', '==', '3'], flag_pos)

# Now output what's in the flag
compiler._move_to_var('x')
# Add code to move to flag and output it as number
compiler._move_pointer(flag_pos)
# Convert to ASCII digit: add 48 to flag value
for _ in range(48):
    compiler.bf_code.append('+')
compiler.bf_code.append('.')

bf_code = ''.join(compiler.bf_code)

print(f"\nGenerated BF code ({len(bf_code)} chars)")

import subprocess
with open('test_eq_manual.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_eq_manual.bf'],
                       capture_output=True, text=True, timeout=5)

output_lines = result.stdout.split('\n')
output = ""
in_output = False
for line in output_lines:
    if '================' in line:
        if not in_output:
            in_output = True
        else:
            break
    elif in_output:
        output += line

print(f"Output: '{output.strip()}'")
print(f"Expected: '0' (since 1 != 3, flag should be 0)")

# Now test x != 3
compiler2 = BrainFuckPlusPlusCompiler()
compiler2.compile("""declare byte x
set 1 on x""")

flag_pos2 = compiler2._allocate_temp()
compiler2._evaluate_condition(['x', '!=', '3'], flag_pos2)
compiler2._move_to_var('x')
compiler2._move_pointer(flag_pos2)
for _ in range(48):
    compiler2.bf_code.append('+')
compiler2.bf_code.append('.')

bf_code2 = ''.join(compiler2.bf_code)

with open('test_ne_manual.bf', 'w') as f:
    f.write(bf_code2)

result2 = subprocess.run(['python3', 'compiler.py', 'test_ne_manual.bf'],
                        capture_output=True, text=True, timeout=5)

output_lines2 = result2.stdout.split('\n')
output2 = ""
in_output = False
for line in output_lines2:
    if '================' in line:
        if not in_output:
            in_output = True
        else:
            break
    elif in_output:
        output2 += line

print(f"\nTesting x!=3 where x=1")
print(f"Output: '{output2.strip()}'")
print(f"Expected: '1' (since 1 != 3, flag should be 1)")
