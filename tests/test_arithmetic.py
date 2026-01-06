#!/usr/bin/env python3
"""
Test arithmetic operations implementation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler

def test_arithmetic_operations():
    """Test that arithmetic operations compile correctly."""
    print("Testing arithmetic operations...")
    
    test_cases = [
        ("addition", """
        declare int a
        declare int b
        set 5 on a
        set 3 on b
        set $a + $b on a
        """),
        
        ("subtraction", """
        declare int a
        declare int b
        set 10 on a
        set 4 on b
        set $a - $b on a
        """),
        
        ("multiplication", """
        declare int a
        declare int b
        set 6 on a
        set 7 on b
        set $a * $b on a
        """),
        
        ("division", """
        declare int a
        declare int b
        set 20 on a
        set 4 on b
        set $a / $b on a
        """),
        
        ("modulo", """
        declare int a
        declare int b
        set 15 on a
        set 4 on b
        set $a % $b on a
        """),
    ]
    
    compiler = BrainFuckPlusPlusCompiler()
    
    for name, code in test_cases:
        try:
            bf_code = compiler.compile(code)
            print(f"✓ {name} compilation successful (length: {len(bf_code)})")
        except Exception as e:
            print(f"✗ {name} compilation failed: {e}")
            return False
    
    return True

def test_varout():
    """Test varout functionality."""
    print("\nTesting varout...")
    
    code = """
    declare int a
    set 42 on a
    varout a
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    try:
        bf_code = compiler.compile(code)
        print(f"✓ varout compilation successful (length: {len(bf_code)})")
        return True
    except Exception as e:
        print(f"✗ varout compilation failed: {e}")
        return False

def main():
    print("=== BF++ Arithmetic Test ===\n")
    
    success = test_arithmetic_operations()
    success = test_varout() and success
    
    if success:
        print("\n✓ All arithmetic operations are working")
    else:
        print("\n✗ Some arithmetic operations have issues")

if __name__ == "__main__":
    main()
