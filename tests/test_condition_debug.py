#!/usr/bin/env python3
"""
Debug condition evaluation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler

def main():
    print("=== Condition Debug Test ===\n")
    
    # Test 1: Simple equality that should be true
    code1 = """
    declare int a
    set 5 on a
    if a == 5 then
        print string "Yes"
    endif
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code1 = compiler.compile(code1)
    
    print("Test 1: a == 5 (should be true)")
    print("BF code length:", len(bf_code1))
    
    # Find the condition part
    # Look for the pattern that checks the condition
    if '>' in bf_code1 and '[' in bf_code1:
        print("Found condition check pattern")
    
    # Test 2: Simple equality that should be false
    code2 = """
    declare int a
    set 5 on a
    if a == 3 then
        print string "No"
    endif
    """
    
    bf_code2 = compiler.compile(code2)
    print("\nTest 2: a == 3 (should be false)")
    print("BF code length:", len(bf_code2))
    
    # Compare the two
    if bf_code1 == bf_code2:
        print("\n⚠️  Both conditions generate the same BF code!")
        print("This suggests the condition value is not being used correctly.")
    else:
        print("\n✓ Conditions generate different BF code")

if __name__ == "__main__":
    main()
