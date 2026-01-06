#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

code = """
declare int x
set 5 on x
varout x
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print(f"Generated {len(bf_code)} chars")

with open('test_simple_int.bf', 'w') as f:
    f.write(bf_code)

result = subprocess.run(['python3', 'compiler.py', 'test_simple_int.bf'],
                       capture_output=True, text=True, timeout=30)

print(f"STDOUT:\n{result.stdout}")
print(f"\nSTDERR:\n{result.stderr}")
