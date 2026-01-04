#!/usr/bin/env python3
from core import BrainFuckPlusPlusCompiler

code = """
declare int x
set 0 on x
varout x
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} BF chars")

# Count number of dots (output commands)
dot_count = bf_code.count('.')
print(f"Number of output commands: {dot_count}")

with open('test_int_zero.bf', 'w') as f:
    f.write(bf_code)

import subprocess
result = subprocess.run(['python3', 'compiler.py', 'test_int_zero.bf'],
                       capture_output=True, text=True, timeout=30)

print("\nSTDOUT:")
print(result.stdout)
