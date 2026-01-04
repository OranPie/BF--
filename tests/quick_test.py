#!/usr/bin/env python3
"""Quick test suite to verify the fixes"""
from core import BrainFuckPlusPlusCompiler
import subprocess

def test(name, code, expected):
    """Run a quick test"""
    print(f"\n{'='*50}")
    print(f"Test: {name}")
    print(f"{'='*50}")

    try:
        compiler = BrainFuckPlusPlusCompiler()
        bf_code = compiler.compile(code)

        with open('quick_test.bf', 'w') as f:
            f.write(bf_code)

        result = subprocess.run(
            ['python3', 'compiler.py', 'quick_test.bf'],
            capture_output=True,
            text=True,
            timeout=3
        )

        # Extract output
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
            print(f"✓ PASS - Output: '{output}'")
            return True
        else:
            print(f"✗ FAIL - Expected: '{expected}', Got: '{output}'")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ FAIL - Timeout")
        return False
    except Exception as e:
        print(f"✗ FAIL - {e}")
        return False

# Run tests
passed = 0
failed = 0

# Test 1: Simple byte output
if test("Byte variable",
    "declare byte x\nset 65 on x\nmove to x\noutput",
    "A"):
    passed += 1
else:
    failed += 1

# Test 2: If/else (true)
if test("If/else (true)",
    "declare byte x\nset 5 on x\nif (x == 5) {\n    print string \"YES\"\n} else {\n    print string \"NO\"\n}",
    "YES"):
    passed += 1
else:
    failed += 1

# Test 3: If/else (false)
if test("If/else (false)",
    "declare byte x\nset 3 on x\nif (x == 5) {\n    print string \"YES\"\n} else {\n    print string \"NO\"\n}",
    "NO"):
    passed += 1
else:
    failed += 1

# Test 4: While loop
if test("While loop",
    "declare byte c\nset 3 on c\nwhile (c) {\n    print string \"A\"\n    dec on c\n}",
    "AAA"):
    passed += 1
else:
    failed += 1

# Test 5: String varout
if test("String varout",
    "declare string 10 msg\nset \"Hi\" on msg\nvarout msg",
    "Hi"):
    passed += 1
else:
    failed += 1

# Test 6: Break statement
if test("Break statement",
    "declare byte i\nset 10 on i\nwhile (i) {\n    print string \"X\"\n    break\n}",
    "X"):
    passed += 1
else:
    failed += 1

# Test 7: Inc/Dec
if test("Increment",
    "declare byte x\nset 64 on x\nmove to x\ninc\noutput",
    "A"):
    passed += 1
else:
    failed += 1

print(f"\n{'='*50}")
print(f"SUMMARY")
print(f"{'='*50}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Total: {passed + failed}")
print(f"Success rate: {passed/(passed+failed)*100:.1f}%")
