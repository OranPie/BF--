#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler

code = """
declare byte x
set 53 on x
move to x
output
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

with open('test_direct.bf', 'w') as f:
    f.write(bf_code)

import subprocess
result = subprocess.run(['python3', 'compiler.py', 'test_direct.bf'],
                       capture_output=True, text=True, timeout=5)

print("Output between markers:")
lines = result.stdout.split('\n')
in_output = False
for line in lines:
    if '================' in line:
        if not in_output:
            in_output = True
            print("START")
        else:
            print("END")
            break
    elif in_output:
        print(repr(line))
