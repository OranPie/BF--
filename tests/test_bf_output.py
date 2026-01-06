#!/usr/bin/env python3
"""
Test to see the actual BF code generated.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler

def main():
    print("=== BF Code Output Test ===\n")
    
    code = """
    declare int a
    set 5 on a
    if $a == 5 then
        print string "Yes"
    endif
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    
    print("Generated BF code:")
    print("=" * 50)
    print(bf_code)
    print("=" * 50)
    print(f"Length: {len(bf_code)}")

if __name__ == "__main__":
    main()
