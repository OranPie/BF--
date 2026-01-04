#!/usr/bin/env python3
"""
Test simple condition with manual BF code.
"""

import subprocess
import tempfile
import os

def test_manual_condition():
    """Test condition with manually written BF code."""
    
    # Manually write BF code that:
    # 1. Sets cell 0 to 1 (condition flag)
    # 2. If cell 0 is non-zero, print "A" (ASCII 65)
    bf_code = "+[+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++.[-]]"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bf', delete=False) as f:
        f.write(bf_code)
        bf_file = f.name
    
    try:
        result = subprocess.run(
            ['python3', 'src/compiler.py', bf_file],
            text=True,
            capture_output=True,
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        )
        
        # Extract actual output
        import re
        # Look for any letters in the output
        letters = re.findall(r'[A-Za-z]', result.stdout)
        actual_output = ''.join(letters)
        
        print(f"Manual condition test output: {repr(actual_output)}")
        if "Y" in actual_output:
            print("✓ Manual condition works")
        else:
            print("✗ Manual condition failed")
    finally:
        os.unlink(bf_file)

if __name__ == "__main__":
    test_manual_condition()
