#!/usr/bin/env python3
"""Debug for loop issue"""
from core import BrainFuckPlusPlusCompiler

# Simple for loop test
code = """
declare byte i
for (set 0 on i; i != 3; inc on i) {
    print string "B"
}
"""

print("Compiling for loop...")
compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars of BF code\n")
print("BF Code:")
print(bf_code)
print(f"\nVariables: {compiler.variables}")

# Compare with equivalent while loop
while_code = """
declare byte i
set 0 on i
while (i != 3) {
    print string "B"
    inc on i
}
"""

print("\n" + "="*60)
print("Compiling equivalent while loop...")
compiler2 = BrainFuckPlusPlusCompiler()
bf_code2 = compiler2.compile(while_code)

print(f"Generated {len(bf_code2)} chars of BF code\n")
print("BF Code:")
print(bf_code2)
print(f"\nVariables: {compiler2.variables}")

# Test the while loop version
print("\n" + "="*60)
print("Testing while loop version...")
import subprocess
with open('test_while_equiv.bf', 'w') as f:
    f.write(bf_code2)

try:
    result = subprocess.run(['python3', 'compiler.py', 'test_while_equiv.bf'],
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

    print(f"Output: '{output.strip()}'")
except subprocess.TimeoutExpired:
    print("TIMEOUT!")
