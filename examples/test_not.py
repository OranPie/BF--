#!/usr/bin/env python3
"""Test ~5 (bitwise NOT) should give -6 in two's complement"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare int a
declare int result
set 5 on a
set ~$a on result
move to result
output
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars")

with open('test_not.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_not.bf'],
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

if output:
    byte_val = ord(output[0])
    print(f"Output byte value: {byte_val}")
    print(f"Expected: 250 (LSB of ~5)")
    if byte_val == 250:
        print("✓ ~5 LSB = 250")
    else:
        print(f"✗ FAIL - got {byte_val}")
else:
    print("No output")
