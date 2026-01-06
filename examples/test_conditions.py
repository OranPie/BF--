#!/usr/bin/env python3
"""Test different loop conditions"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

def test_code(name, code, timeout=3):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)

    print(f"Generated {len(bf_code)} chars")

    with open('test_cond.bf', 'w') as f:
        f.write(bf_code)

    try:
        result = subprocess.run(['python3', 'compiler.py', 'test_cond.bf'],
                               capture_output=True, text=True, timeout=timeout)

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
        return output.strip()
    except subprocess.TimeoutExpired:
        print("TIMEOUT!")
        return None

# Test 1: While with truthiness (working)
test_code("While with truthiness",
"""
declare byte c
set 3 on c
while (c) {
    print string "A"
    dec on c
}
""")

# Test 2: While with != (broken?)
test_code("While with != operator",
"""
declare byte c
set 0 on c
while (c != 3) {
    print string "B"
    inc on c
}
""")

# Test 3: If with != (to see if != works at all)
test_code("If with != operator (true)",
"""
declare byte x
set 1 on x
if (x != 3) {
    print string "YES"
} else {
    print string "NO"
}
""")

# Test 4: If with != (false case)
test_code("If with != operator (false)",
"""
declare byte x
set 3 on x
if (x != 3) {
    print string "YES"
} else {
    print string "NO"
}
""")
