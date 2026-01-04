#!/usr/bin/env python3
"""
Test actual execution of compiled BF++ code.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core import BrainFuckPlusPlusCompiler
import subprocess
import tempfile

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

def test_simple_output():
    """Test simple string output."""
    print("Testing simple output...")
    
    code = """
    print string "Hello"
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code(bf_code)
    
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
    output, error = execute_bf_code(bf_code)
    
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
    varout a
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    output, error = execute_bf_code(bf_code)
    
    if "8" in output:
        print("✓ Addition result works")
        return True
    else:
        print(f"✗ Addition result failed. Output: {output}, Error: {error}")
        return False

def main():
    print("=== BF++ Execution Test ===\n")
    
    tests = [
        test_simple_output,
        test_integer_output,
        test_arithmetic_result,
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
