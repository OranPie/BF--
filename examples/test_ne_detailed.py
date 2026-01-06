#!/usr/bin/env python3
"""Manually trace BF execution for != condition"""

# Simplified test: just check if x != 3 works
# x = 1, so x != 3 should be true (flag = 1)

code_template = """
declare byte x
set 1 on x
if (x != 3) {{
    declare byte temp
    set 84 on temp
    move to temp
    output
}} else {{
    declare byte temp2
    set 70 on temp2
    move to temp2
    output
}}
"""

from bfpp import BrainFuckPlusPlusCompiler
import subprocess

compiler = BrainFuckPlusPlusCompiler()
bf = compiler.compile(code_template)

print(f"Variables: {compiler.variables}")
print(f"BF code length: {len(bf)}")

with open('test_ne.bf', 'w') as f:
    f.write(bf)

result = subprocess.run(['python3', 'compiler.py', 'test_ne.bf'],
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
print(f"Expected: 'T' (ASCII 84) for true, 'F' (ASCII 70) for false")
print(f"Since x=1 and we're checking x != 3, should be TRUE")

if output.strip() == 'T':
    print("✓ != operator works!")
else:
    print("✗ != operator broken!")

# Also try the opposite
code_template2 = """
declare byte x
set 3 on x
if (x != 3) {{
    declare byte temp
    set 84 on temp
    move to temp
    output
}} else {{
    declare byte temp2
    set 70 on temp2
    move to temp2
    output
}}
"""

print("\n" + "="*60)
print("Testing x=3, x!=3 (should be FALSE)")

compiler2 = BrainFuckPlusPlusCompiler()
bf2 = compiler2.compile(code_template2)

with open('test_ne2.bf', 'w') as f:
    f.write(bf2)

result2 = subprocess.run(['python3', 'compiler.py', 'test_ne2.bf'],
                        capture_output=True, text=True, timeout=5)

output_lines2 = result2.stdout.split('\n')
output2 = ""
in_output = False
for line in output_lines2:
    if '================' in line:
        if not in_output:
            in_output = True
        else:
            break
    elif in_output:
        output2 += line

print(f"Output: '{output2.strip()}'")
print(f"Expected: 'F' (ASCII 70) for false")

if output2.strip() == 'F':
    print("✓ != operator works!")
else:
    print("✗ != operator broken!")
