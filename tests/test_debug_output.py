#!/usr/bin/env python3
"""
Debug output extraction.
"""

import subprocess
import tempfile
import os

def test_debug():
    """Test to understand the output format."""
    
    # Simple BF code that prints "A"
    bf_code = "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++."
    
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
        
        print("Full output:")
        print(result.stdout)
        print("\nLines:")
        for i, line in enumerate(result.stdout.split('\n')):
            print(f"{i}: {repr(line)}")
    finally:
        os.unlink(bf_file)

if __name__ == "__main__":
    test_debug()
