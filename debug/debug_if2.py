#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

# Test with very simple output to see what executes
code = """
declare byte x
set 5 on x
if (x == 5) {
    declare byte temp
    set 89 on temp
    move to temp
    output
} else {
    declare byte temp2
    set 78 on temp2
    move to temp2
    output
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code")
print(f"Variables: {compiler.variables}")

# Write and execute
with open('test_if_debug.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_if_debug.bf'],
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
print(f"Expected: 'Y' (ASCII 89) if condition true, 'N' (ASCII 78) if condition false")

if output == 'Y':
    print("✓ Only if-block executed!")
elif output == 'N':
    print("✓ Only else-block executed!")
elif output == 'YN' or output == 'NY':
    print("✗ Both blocks executed!")
else:
    print(f"? Unexpected output: {repr(output)}")
