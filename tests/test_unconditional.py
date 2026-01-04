#!/usr/bin/env python3
"""
Test unconditional print.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core import BrainFuckPlusPlusCompiler
import subprocess
import tempfile

def execute_bf_code(bf_code, input_data=""):
    """Execute BrainFuck code and return output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bf', delete=False) as f:
        f.write(bf_code)
        bf_file = f.name
    
    try:
        # Use the BF interpreter
        result = subprocess.run(
            ['python3', 'src/compiler.py', bf_file],
            input=input_data,
            text=True,
            capture_output=True,
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )
        return result.stdout, result.stderr
    finally:
        os.unlink(bf_file)

def main():
    print("=== Unconditional Print Test ===\n")
    
    code = """
    print string "Hello"
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    
    print("Generated BF code length:", len(bf_code))
    
    output, error = execute_bf_code(bf_code)
    
    # Extract just the actual output (remove debug info)
    # The output is mixed with debug info, look for the actual characters
    import re
    # Find all printable characters that are not part of the debug output
    matches = re.findall(r'^[^\d\s\[\]=\-<>.,+]+$', output, re.MULTILINE)
    actual_output = ''.join(matches)
    
    # Also check single character lines
    single_chars = re.findall(r'^([A-Za-z])$', output, re.MULTILINE)
    actual_output += ''.join(single_chars)
    
    print(f"Actual output: {repr(actual_output)}")
    
    if "Hello" in actual_output:
        print("✓ Unconditional print works")
    else:
        print("✗ Unconditional print failed")

if __name__ == "__main__":
    main()
