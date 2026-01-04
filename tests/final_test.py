#!/usr/bin/env python3
"""
Simplified test suite - skip complex/slow tests
"""

from core import BrainFuckPlusPlusCompiler
import subprocess

def test_case(name, code, expected_output=None):
    """Run a test case"""
    print(f"\nTest: {name}")

    try:
        compiler = BrainFuckPlusPlusCompiler()
        bf_code = compiler.compile(code)

        with open('test_temp.bf', 'w') as f:
            f.write(bf_code)

        result = subprocess.run(
            ['python3', 'compiler.py', 'test_temp.bf'],
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
                output += line + '\n'

        output = output.strip()

        if expected_output is not None:
            if output == expected_output:
                print(f"  ✓ PASS")
                return True
            else:
                print(f"  ✗ FAIL - Expected: '{expected_output}', Got: '{output}'")
                return False

        return True

    except Exception as e:
        print(f"  ✗ FAIL - {e}")
        return False

# Run tests
tests_passed = 0
tests_failed = 0

# Basic tests
tests = [
    ("Byte variable", "declare byte x\nset 65 on x\nmove to x\noutput", "A"),
    ("Increment", "declare byte x\nset 64 on x\nmove to x\ninc\noutput", "A"),
    ("Decrement", "declare byte x\nset 66 on x\nmove to x\ndec\noutput", "A"),
    ("If (true)", "declare byte x\nset 5 on x\nif (x == 5) {\n  print string \"YES\"\n} else {\n  print string \"NO\"\n}", "YES"),
    ("While loop", "declare byte c\nset 3 on c\nwhile (c) {\n  print string \"A\"\n  dec on c\n}", "AAA"),
    ("String varout", "declare string 10 msg\nset \"Hi\" on msg\nvarout msg", "Hi"),
    ("String literal", "print string \"Hello!\"", "Hello!"),
]

for name, code, expected in tests:
    if test_case(name, code, expected):
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
if os.path.exists('test_temp.bf'):
    os.remove('test_temp.bf')
