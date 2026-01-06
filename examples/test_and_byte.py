#!/usr/bin/env python3
"""Test bitwise AND on bytes instead of ints"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare byte a
declare byte b
declare byte result
set 5 on a
set 3 on b
set $a & $b on result
move to result
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
inc
output
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars")

with open('test_and_byte.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_and_byte.bf'],
                       capture_output=True, text=True, timeout=10)

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

print(f"Output: '{output}'")
print(f"Expected: '1' (ASCII 49)")
if output.strip() == '1':
    print("✓ PASS")
else:
    print(f"✗ FAIL - got {repr(output)}")
