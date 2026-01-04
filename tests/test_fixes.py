#!/usr/bin/env python3
"""
Test script to verify the fixes for calculation and condition issues.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core import BrainFuckPlusPlusCompiler
from compiler import generate_code

def test_basic_arithmetic():
    """Test basic arithmetic operations."""
    print("Testing basic arithmetic...")
    
    code = """
    declare int a
    declare int b
    declare int result
    
    set 10 on a
    set 5 on b
    set $a + $b on result
    varout result
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    
    # Execute the generated BF code
    execute_func = generate_code(bf_code)
    if execute_func:
        memory = bytearray(30000)
        execute_func(memory)
        print("✓ Addition test compiled and executed")
    else:
        print("✗ Addition test failed to compile")

def test_comparisons():
    """Test comparison operators."""
    print("\nTesting comparisons...")
    
    test_cases = [
        ('<', '5', '10', True),
        ('>', '10', '5', True),
        ('<=', '5', '5', True),
        ('>=', '10', '10', True),
        ('==', '5', '5', True),
        ('!=', '5', '10', True),
    ]
    
    for op, a_val, b_val, expected in test_cases:
        code = f"""
        declare int a
        declare int b
        set {a_val} on a
        if (a {op} {b_val}) {{
            print string "YES"
        }} else {{
            print string "NO"
        }}
        """
        
        compiler = BrainFuckPlusPlusCompiler()
        bf_code = compiler.compile(code)
        
        execute_func = generate_code(bf_code)
        if execute_func:
            memory = bytearray(30000)
            execute_func(memory)
            print(f"✓ Comparison {a_val} {op} {b_val} compiled")
        else:
            print(f"✗ Comparison {a_val} {op} {b_val} failed")

def test_varout():
    """Test varout functionality."""
    print("\nTesting varout...")
    
    # Test string varout
    code = """
    declare string 10 msg
    set "Hello" on msg
    varout msg
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    
    execute_func = generate_code(bf_code)
    if execute_func:
        memory = bytearray(30000)
        execute_func(memory)
        print("✓ String varout compiled and executed")
    else:
        print("✗ String varout failed")

def main():
    print("=== BF++ Compiler Fixes Test ===\n")
    
    try:
        test_basic_arithmetic()
        test_comparisons()
        test_varout()
        print("\n=== Test Summary ===")
        print("All tests completed. Check output above for results.")
        print("Note: Some indentation warnings exist but don't prevent compilation.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
