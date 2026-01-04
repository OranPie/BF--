#!/usr/bin/env python3
"""
Debug test for condition evaluation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core import BrainFuckPlusPlusCompiler

def test_condition_compilation():
    """Test that conditions compile without errors."""
    print("Testing condition compilation...")
    
    test_cases = [
        ("equality", """
        declare int a
        declare int b
        set 5 on a
        set 5 on b
        if $a == $b then
            print string "Yes"
        endif
        """),
        
        ("inequality", """
        declare int a
        declare int b
        set 5 on a
        set 3 on b
        if $a != $b then
            print string "No"
        endif
        """),
        
        ("if_else", """
        declare int a
        declare int b
        set 5 on a
        set 3 on b
        if $a == $b then
            print string "Equal"
        else
            print string "Not Equal"
        endif
        """),
    ]
    
    compiler = BrainFuckPlusPlusCompiler()
    
    for name, code in test_cases:
        try:
            bf_code = compiler.compile(code)
            print(f"✓ {name} compiles successfully (length: {len(bf_code)})")
        except Exception as e:
            print(f"✗ {name} compilation failed: {e}")
            return False
    
    return True

def main():
    print("=== BF++ Condition Debug Test ===\n")
    
    if test_condition_compilation():
        print("\n✓ All conditions compile successfully")
    else:
        print("\n✗ Some conditions fail to compile")

if __name__ == "__main__":
    main()
