#!/usr/bin/env python3
from core import BrainFuckPlusPlusCompiler

# Simpler test - no variable declarations inside blocks
code = """
declare byte x
declare byte y
declare byte n
set 5 on x
set 89 on y
set 78 on n
if (x == 5) {
    move to y
    output
} else {
    move to n
    output
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)

print("BF Code with annotations:")
print(bf_code)
print(f"\n\nVariables: {compiler.variables}")

# Try to annotate the structure
print("\n\nLet me break down the structure:")
# Count the brackets to understand structure
opens = []
for i, c in enumerate(bf_code):
    if c == '[':
        opens.append(i)
        print(f"Position {i}: '[' opened")
    elif c == ']':
        if opens:
            start = opens.pop()
            print(f"Position {i}: ']' closes '[' at position {start}")
