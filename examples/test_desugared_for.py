#!/usr/bin/env python3
from core import BrainFuckPlusPlusCompiler
import subprocess

# Test the exact desugared version
code = """
declare byte i
set 0 on i
while (i != 3) {
    print string "B"
    inc on i
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code")
print(f"Variables: {compiler.variables}")

with open('test_desugared_for.bf', 'w') as f:
    f.write(bf_code)

print("\nExecuting...")
try:
    result = subprocess.run(['python3', 'compiler.py', 'test_desugared_for.bf'],
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
    print(f"Expected: 'BBB'")

    if output.strip() == 'BBB':
        print("✓ Works!")
    else:
        print("✗ Failed")
except subprocess.TimeoutExpired:
    print("✗ Timeout")
