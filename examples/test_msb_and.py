#!/usr/bin/env python3
"""Test 128 & 128 (MSB) should give 128"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare int a
declare int b
declare int result
set 128 on a
set 128 on b
set $a & $b on result
move to result
output
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars")

with open('test_msb_and.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_msb_and.bf'],
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
    print(f"Output byte value: {ord(output[0])}")
    print(f"Expected: 128")
    if ord(output[0]) == 128:
        print("✓ 128 & 128 = 128")
    else:
        print(f"✗ FAIL - got {ord(output[0])}")
else:
    print("No output")
