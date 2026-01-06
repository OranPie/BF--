#!/usr/bin/env python3
"""
Basic test to verify the compiler can at least import and compile simple code.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler

def test_basic_compilation():
    """Test that the compiler can handle basic operations."""
    print("Testing basic compilation...")
    
    # Simple test without complex comparisons
    code = """
    declare int a
    set 10 on a
    print string "Hello"
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    try:
        bf_code = compiler.compile(code)
        print("✓ Basic compilation successful")
        print(f"Generated BF code length: {len(bf_code)}")
        return True
    except Exception as e:
        print(f"✗ Basic compilation failed: {e}")
        return False

def main():
    print("=== BF++ Basic Test ===\n")
    
    success = test_basic_compilation()
    
    if success:
        print("\n✓ Basic functionality is working")
        print("Note: Complex comparison operators need indentation fixes")
    else:
        print("\n✗ Basic functionality is broken")

if __name__ == "__main__":
    main()
