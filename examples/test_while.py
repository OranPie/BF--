#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare byte counter
set 3 on counter
while (counter) {
    print string "A"
    dec on counter
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code")
print(f"Variables: {compiler.variables}")

# Write and execute
with open('test_while.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_while.bf'],
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
print(f"\nActual output: '{output}'")
print(f"Expected: 'AAA'")

if output == 'AAA':
    print("✓ While loop works!")
else:
    print(f"✗ While loop failed")
