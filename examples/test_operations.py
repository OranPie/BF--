#!/usr/bin/env python3
"""
Test suite for BF++ compiler operations
"""

from bfpp import BrainFuckPlusPlusCompiler
import subprocess
import sys

def test_case(name, code, expected_output=None, should_fail=False):
    """Run a test case and report results"""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    print(f"Code:\n{code}\n")

    try:
        compiler = BrainFuckPlusPlusCompiler()
        bf_code = compiler.compile(code)

        print(f"✓ Compilation successful ({len(bf_code)} chars)")
        print(f"Variables: {compiler.variables}")

        # Write to temp file and execute
        with open('test_temp.bf', 'w') as f:
            f.write(bf_code)

        result = subprocess.run(
            ['python3', 'compiler.py', 'test_temp.bf'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Extract output between the separator lines
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
        print(f"Output: '{output}'")

        if expected_output is not None:
            if output == expected_output:
                print(f"✓ Output matches expected")
                return True
            else:
                print(f"✗ Output mismatch! Expected: '{expected_output}'")
                return False

        return True

    except Exception as e:
        if should_fail:
            print(f"✓ Expected failure: {e}")
            return True
        else:
            print(f"✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

# Run tests
tests_passed = 0
tests_failed = 0

# Test 1: Simple byte variable
if test_case("Byte variable set and output",
    """
    declare byte x
    set 65 on x
    move to x
    output
    """,
    expected_output="A"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 2: Increment operation
if test_case("Increment operation",
    """
    declare byte x
    set 64 on x
    move to x
    inc
    output
    """,
    expected_output="A"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 3: Decrement operation
if test_case("Decrement operation",
    """
    declare byte x
    set 66 on x
    move to x
    dec
    output
    """,
    expected_output="A"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 4: Simple if statement
if test_case("If statement (true condition)",
    """
    declare byte x
    set 5 on x
    if (x == 5) {
        print string "YES"
    } else {
        print string "NO"
    }
    """,
    expected_output="YES"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 5: If statement false
if test_case("If statement (false condition)",
    """
    declare byte x
    set 3 on x
    if (x == 5) {
        print string "YES"
    } else {
        print string "NO"
    }
    """,
    expected_output="NO"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 6: While loop
if test_case("While loop",
    """
    declare byte counter
    set 3 on counter
    while (counter) {
        print string "A"
        dec on counter
    }
    """,
    expected_output="AAA"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 7: For loop
if test_case("For loop",
    """
    declare byte i
    for (set 0 on i; i != 3; inc on i) {
        print string "B"
    }
    """,
    expected_output="BBB"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 8: Integer variable
if test_case("Integer declaration and output",
    """
    declare int x
    set 42 on x
    varout x
    """,
    expected_output="42"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 9: Negative integer
if test_case("Negative integer output",
    """
    declare int x
    set -5 on x
    varout x
    """,
    expected_output="-5"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 10: Bitwise AND
if test_case("Bitwise AND operation",
    """
    declare int a
    declare int b
    declare int result
    set 15 on a
    set 7 on b
    set $a & $b on result
    varout result
    """,
    expected_output="7"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 11: Bitwise OR
if test_case("Bitwise OR operation",
    """
    declare int a
    declare int b
    declare int result
    set 8 on a
    set 4 on b
    set $a | $b on result
    varout result
    """,
    expected_output="12"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 12: Bitwise XOR
if test_case("Bitwise XOR operation",
    """
    declare int a
    declare int b
    declare int result
    set 15 on a
    set 10 on b
    set $a ^ $b on result
    varout result
    """,
    expected_output="5"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 13: Bitwise NOT
if test_case("Bitwise NOT operation",
    """
    declare int a
    declare int result
    set 0 on a
    set ~ $a on result
    varout result
    """,
    expected_output="-1"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 14: String variable
if test_case("String variable output",
    """
    declare string 10 msg
    set "Hi" on msg
    varout msg
    """,
    expected_output="Hi"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 15: Variable copy (int)
if test_case("Integer variable copy",
    """
    declare int a
    declare int b
    set 123 on a
    set $a on b
    varout b
    """,
    expected_output="123"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 16: Break statement
if test_case("Break statement in loop",
    """
    declare byte i
    set 10 on i
    while (i) {
        print string "X"
        break
    }
    """,
    expected_output="X"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 17: Zero value output
if test_case("Zero integer output",
    """
    declare int x
    set 0 on x
    varout x
    """,
    expected_output="0"):
    tests_passed += 1
else:
    tests_failed += 1

# Test 18: Large number
if test_case("Large integer output",
    """
    declare int x
    set 12345 on x
    varout x
    """,
    expected_output="12345"):
    tests_passed += 1
else:
    tests_failed += 1

# Summary
print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Tests passed: {tests_passed}")
print(f"Tests failed: {tests_failed}")
print(f"Total: {tests_passed + tests_failed}")
print(f"Success rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")

# Cleanup
import os
if os.path.exists('test_temp.bf'):
    os.remove('test_temp.bf')

sys.exit(0 if tests_failed == 0 else 1)
