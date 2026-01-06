#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare byte i
set 10 on i
while (i) {
    print string "X"
    break
}
"""

print("Testing break statement...")
compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code")

with open('test_break.bf', 'w') as f:
    f.write(bf_code)

try:
    result = subprocess.run(['python3', 'compiler.py', 'test_break.bf'],
                           capture_output=True, text=True, timeout=3)

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

    output = output.strip()
    print(f"Output: '{output}'")
    print(f"Expected: 'X'")

    if output == 'X':
        print("✓ Break works!")
    else:
        print("✗ Break failed")
except subprocess.TimeoutExpired:
    print("✗ Timeout")
