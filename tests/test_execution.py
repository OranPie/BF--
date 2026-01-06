#!/usr/bin/env python3
"""
Test actual execution of compiled BF++ code.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code
import subprocess
import tempfile
import io
import contextlib

def execute_bf_code(bf_code, input_data=""):
    """Execute BrainFuck code and return output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bf', delete=False) as f:
        f.write(bf_code)
        bf_file = f.name
    
    try:
        # Use the BF interpreter
        result = subprocess.run(
            ['python3', 'src/compiler.py', bf_file],
            input=input_data,
            text=True,
            capture_output=True,
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )
        return result.stdout, result.stderr
    finally:
        os.unlink(bf_file)


def execute_bf_code_inprocess(bf_code, input_data=""):
    execute_func = generate_code(bf_code)
    if execute_func is None:
        raise RuntimeError("Failed to generate BF execution function")

    memory = bytearray(30000)
    stdout = io.StringIO()
    stdin = io.StringIO(input_data)

    old_stdin = sys.stdin
    try:
        sys.stdin = stdin
        with contextlib.redirect_stdout(stdout):
            execute_func(memory)
    finally:
        sys.stdin = old_stdin

    return stdout.getvalue(), ""

def test_simple_output():
    """Test simple string output."""
    print("Testing simple output...")
    
    code = """
    print string "Hello"
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)
    
    if "Hello" in output:
        print("✓ Simple output works")
        return True
    else:
        print(f"✗ Simple output failed. Output: {output}, Error: {error}")
        return False

def test_integer_output():
    """Test integer variable output."""
    print("\nTesting integer output...")
    
    code = """
    declare int a
    set 42 on a
    varout a
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)
    
    if "42" in output:
        print("✓ Integer output works")
        return True
    else:
        print(f"✗ Integer output failed. Output: {output}, Error: {error}")
        return False

def test_arithmetic_result():
    """Test arithmetic operation result."""
    print("\nTesting arithmetic result...")
    
    code = """
    declare int a
    declare int b
    set 5 on a
    set 3 on b
    set $a + $b on a
    if (a == 8) {
        print string "YES"
    } else {
        print string "NO"
    }
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)
    
    if "YES" in output:
        print("✓ Addition result works")
        return True
    else:
        print(f"✗ Addition result failed. Output: {output}, Error: {error}")
        return False


def test_int_inc_carry():
    """Test that inc on int propagates carry across bytes (255 -> 256)."""
    print("\nTesting int inc carry...")

    code = """
    declare int a
    set 255 on a
    inc on a
    if (a == 256) {
        print string "YES"
    } else {
        print string "NO"
    }
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)

    if "YES" in output:
        print("✓ int inc carry works")
        return True
    else:
        print(f"✗ int inc carry failed. Output: {output}, Error: {error}")
        return False


def test_int_dec_borrow():
    """Test that dec on int propagates borrow across bytes (0 -> -1)."""
    print("\nTesting int dec borrow...")

    code = """
    declare int a
    set 0 on a
    dec on a
    if (a == -1) {
        print string "YES"
    } else {
        print string "NO"
    }
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)

    if "YES" in output:
        print("✓ int dec borrow works")
        return True
    else:
        print(f"✗ int dec borrow failed. Output: {output}, Error: {error}")
        return False


def test_runtime_subscript_condition_int():
    print("\nTesting runtime-subscript condition (int)...")

    code = """
    declare byte i
    declare int arr[3]
    set 1 on i
    set 123 on arr[1]
    if (arr[$i] == 123) {
        print string "YES"
    } else {
        print string "NO"
    }
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)

    if "YES" in output:
        print("✓ runtime-subscript int comparison works")
        return True
    print(f"✗ runtime-subscript int comparison failed. Output: {output}, Error: {error}")
    return False


def test_runtime_subscript_expression_operand():
    print("\nTesting runtime-subscript expression operand...")

    code = """
    declare byte i
    declare int arr[3]
    declare int b
    declare int c
    set 1 on i
    set 40 on arr[1]
    set 2 on b
    set $arr[$i] + $b on c
    if (c == 42) {
        print string "YES"
    } else {
        print string "NO"
    }
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)

    if "YES" in output:
        print("✓ runtime-subscript expression operand works")
        return True
    print(f"✗ runtime-subscript expression operand failed. Output: {output}, Error: {error}")
    return False


def test_input_on_byte():
    print("\nTesting input on byte...")

    code = """
    declare byte c
    input on c
    varout c
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code, input_data="A")

    if output == "A":
        print("✓ input on byte works")
        return True
    print(f"✗ input on byte failed. Output: {output}, Error: {error}")
    return False


def test_input_on_string():
    print("\nTesting input on string...")

    code = """
    declare string 10 s
    input on s
    varout s
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code, input_data="Hi\n")

    if output == "Hi":
        print("✓ input on string works")
        return True
    print(f"✗ input on string failed. Output: {output}, Error: {error}")
    return False


def test_match_statement():
    print("\nTesting match statement...")

    code = """
    declare int a
    set 2 on a

    match (a) {
        case 1:
            print string "ONE"
        case 2:
            print string "TWO"
        default:
            print string "OTHER"
    }
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)

    if "TWO" in output:
        print("✓ match statement works")
        return True
    print(f"✗ match statement failed. Output: {output}, Error: {error}")
    return False


def test_match_statement_byte():
    print("\nTesting match statement (byte)...")

    code = """
    declare byte a
    set 2 on a

    match (a) {
        case 1:
            print string "ONE"
        case 2:
            print string "TWO"
        default:
            print string "OTHER"
    }
    """

    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code_inprocess(bf_code)

    if "TWO" in output:
        print("✓ match statement (byte) works")
        return True
    print(f"✗ match statement (byte) failed. Output: {output}, Error: {error}")
    return False

def main():
    print("=== BF++ Execution Test ===\n")
    
    tests = [
        test_simple_output,
        test_integer_output,
        test_arithmetic_result,
        test_int_inc_carry,
        test_int_dec_borrow,
        test_runtime_subscript_condition_int,
        test_runtime_subscript_expression_operand,
        test_input_on_byte,
        test_input_on_string,
        test_match_statement,
        test_match_statement_byte,
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    if all_passed:
        print("\n✓ All execution tests passed")
    else:
        print("\n✗ Some execution tests failed")

if __name__ == "__main__":
    main()
