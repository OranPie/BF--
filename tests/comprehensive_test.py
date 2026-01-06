#!/usr/bin/env python3
"""Comprehensive test suite after fixes"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

def test(name, code, expected):
    """Run a test"""
    try:
        compiler = BrainFuckPlusPlusCompiler()
        bf_code = compiler.compile(code)

        with open('comp_test.bf', 'w') as f:
            f.write(bf_code)

        result = subprocess.run(
            ['python3', 'compiler.py', 'comp_test.bf'],
            capture_output=True,
            text=True,
            timeout=3
        )

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

        if output == expected:
            print(f"✓ {name}")
            return True
        else:
            print(f"✗ {name} - Expected: '{expected}', Got: '{output}'")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ {name} - TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ {name} - ERROR: {e}")
        return False

# Run tests
tests_passed = 0
tests_failed = 0

tests = [
    ("Byte variable", "declare byte x\nset 65 on x\nmove to x\noutput", "A"),
    ("Increment", "declare byte x\nset 64 on x\nmove to x\ninc\noutput", "A"),
    ("Decrement", "declare byte x\nset 66 on x\nmove to x\ndec\noutput", "A"),
    ("String literal", "print string \"Hello\"", "Hello"),
    ("String varout", "declare string 10 s\nset \"Hi\" on s\nvarout s", "Hi"),
    ("If true (==)", "declare byte x\nset 5 on x\nif (x == 5) {\nprint string \"Y\"\n} else {\nprint string \"N\"\n}", "Y"),
    ("If false (==)", "declare byte x\nset 3 on x\nif (x == 5) {\nprint string \"Y\"\n} else {\nprint string \"N\"\n}", "N"),
    ("If true (!=)", "declare byte x\nset 3 on x\nif (x != 5) {\nprint string \"Y\"\n} else {\nprint string \"N\"\n}", "Y"),
    ("If false (!=)", "declare byte x\nset 5 on x\nif (x != 5) {\nprint string \"Y\"\n} else {\nprint string \"N\"\n}", "N"),
    ("While loop", "declare byte c\nset 3 on c\nwhile (c) {\nprint string \"A\"\ndec on c\n}", "AAA"),
    ("While with !=", "declare byte i\nset 0 on i\nwhile (i != 3) {\nprint string \"B\"\ninc on i\n}", "BBB"),
    ("For loop", "declare byte i\nfor (set 0 on i; i != 3; inc on i) {\nprint string \"C\"\n}", "CCC"),
    ("Break statement", "declare byte i\nset 10 on i\nwhile (i) {\nprint string \"X\"\nbreak\n}", "X"),
    ("Negative number", "declare byte x\nset -1 on x\nmove to x\noutput", chr(255)),
]

for name, code, expected in tests:
    if test(name, code, expected):
        tests_passed += 1
    else:
        tests_failed += 1

print(f"\n{'='*50}")
print(f"SUMMARY")
print(f"{'='*50}")
print(f"Tests passed: {tests_passed}")
print(f"Tests failed: {tests_failed}")
print(f"Total: {tests_passed + tests_failed}")
if tests_passed + tests_failed > 0:
    print(f"Success rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")

import os
if os.path.exists('comp_test.bf'):
    os.remove('comp_test.bf')
