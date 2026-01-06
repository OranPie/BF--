#!/usr/bin/env python3
"""
Test to see the BF code for condition.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler

def main():
    print("=== Condition BF Code Test ===\n")
    
    code = """
    declare int a
    set 5 on a
    if a == 5 then
        print string "Yes"
    endif
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    
    print("Generated BF code:")
    print("=" * 50)
    print(bf_code)
    print("=" * 50)
    
    # Count the output characters
    print(f"\nNumber of '.' (output) commands: {bf_code.count('.')}")
    print("Positions of '.' commands:")
    for i, c in enumerate(bf_code):
        if c == '.':
            print(f"  Position {i}")

if __name__ == "__main__":
    main()
