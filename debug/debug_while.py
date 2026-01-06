#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler

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

print("Generated BF code:")
print(bf_code)
print(f"\nLength: {len(bf_code)}")
print(f"Variables: {compiler.variables}")

# Let's also test a simpler while loop
simple_code = """
declare byte x
set 1 on x
while (x) {
    move to x
    output
    clear
}
"""

compiler2 = BrainFuckPlusPlusCompiler()
bf_code2 = compiler2.compile(simple_code)

print("\n\n=== Simpler test ===")
print("Code:")
print(simple_code)
print("\nGenerated BF:")
print(bf_code2)
print(f"\nVariables: {compiler2.variables}")

# Test it
import subprocess
with open('test_simple_while.bf', 'w') as f:
    f.write(bf_code2)

result = subprocess.run(['python3', 'compiler.py', 'test_simple_while.bf'],
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

output = output.strip()
print(f"\nOutput: '{output}' (ASCII: {[ord(c) for c in output]})")
print(f"Expected: ASCII 1 (which is unprintable)")
