#!/usr/bin/env python3
from core import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare byte i
for (set 0 on i; i != 3; inc on i) {
    print string "B"
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code")
print(f"Variables: {compiler.variables}")

# Write and execute
with open('test_for.bf', 'w') as f:
    f.write(bf_code)

print("\nExecuting...")
try:
    result = subprocess.run(['python3', 'compiler.py', 'test_for.bf'],
                           capture_output=True, text=True, timeout=5)

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
    print(f"Expected: 'BBB'")

    if output == 'BBB':
        print("✓ For loop works!")
    else:
        print(f"✗ For loop failed")
except subprocess.TimeoutExpired:
    print("✗ Timeout - infinite loop in the BF code")
