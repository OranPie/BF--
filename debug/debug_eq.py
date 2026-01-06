#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare byte x
set 5 on x
if (x == 5) {
    print string "T"
} else {
    print string "F"
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"BF code:\n{bf_code}\n")

with open('debug_eq.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'debug_eq.bf'],
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
print(f"Expected: 'T'")
