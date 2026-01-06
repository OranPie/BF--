#!/usr/bin/env python3
"""Simple bitwise test - just output the raw byte"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare int a
declare int b
declare int result
set 5 on a
set 3 on b
set $a & $b on result
move to result
output
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars")

with open('test_and_raw.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_and_raw.bf'],
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

print(f"Output byte value: {ord(output[0]) if output else 'none'}")
print(f"Expected: 1")
print(f"Result: {'✓ PASS' if output and ord(output[0]) == 1 else '✗ FAIL'}")
