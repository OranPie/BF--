#!/usr/bin/env python3
"""Test if bit detection is working at all"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

# Simple test: just copy the value (no operation)
# This tests if the bit detection and reconstruction works
code = """
declare int a
declare int result
set 5 on a
set $a on result
move to result
output
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars")

with open('test_copy.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_copy.bf'],
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
    print(f"Expected: 5")
    if ord(output[0]) == 5:
        print("✓ Copy works")
    else:
        print("✗ Copy failed")
else:
    print("No output")
