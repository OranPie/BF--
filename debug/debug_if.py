#!/usr/bin/env python3
from core import BrainFuckPlusPlusCompiler

code = """
declare byte x
set 5 on x
if (x == 5) {
    print string "Y"
} else {
    print string "N"
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print("Generated BF code:")
print(bf_code)
print(f"\nLength: {len(bf_code)}")
print(f"\nVariables: {compiler.variables}")
