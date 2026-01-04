#!/usr/bin/env python3
"""
Test simple BrainFuck code execution.
"""

import subprocess
import tempfile
import os

def test_simple_bf():
    """Test that simple BF code works."""
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
        print("Output:", repr(result.stdout))
        print("Error:", repr(result.stderr))
    finally:
        os.unlink(bf_file)

if __name__ == "__main__":
    test_simple_bf()
