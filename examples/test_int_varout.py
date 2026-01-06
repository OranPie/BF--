#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare int x
set 5 on x
varout x
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code")
print(f"Variables: {compiler.variables}")

# Write and execute
with open('test_int_varout.bf', 'w') as f:
    f.write(bf_code)

print("\nExecuting...")
try:
    result = subprocess.run(['python3', 'compiler.py', 'test_int_varout.bf'],
                           capture_output=True, text=True, timeout=10)

    # Extract output
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
    print(f"Actual output: '{output}'")
    print(f"Expected: '5'")

    if output == '5':
        print("✓ Integer varout works!")
    else:
        print(f"✗ Integer varout failed")
except subprocess.TimeoutExpired:
    print("✗ Timeout - probably infinite loop in the BF code")
