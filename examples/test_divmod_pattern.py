#!/usr/bin/env python3
"""
Simpler bitwise implementation - rewrite from scratch
Uses bit-by-bit checking with powers of 2 from MSB to LSB
"""

from core import BrainFuckPlusPlusCompiler

def test_divmod():
    """Test if the divmod pattern works at all"""
    # Manual BF code to test divmod
    # Start with 5, divide by 2, should get quotient=2, remainder=1
    bf = """
    +++++     # Start with 5
    # Divmod pattern from original code
    [->[->+>+<<]>>[-<<+>>]<<]>[-<+>]<
    # Now position 0 should have quotient (2)
    # Position 1 should have remainder (1)
    # Output position 1 (should be ASCII 1 which is unprintable, so add 48)
    >++++++++++++++++++++++++++++++++++++++++++++++++.
    """

    with open('test_divmod.bf', 'w') as f:
        f.write(bf)

    import subprocess
    result = subprocess.run(['python3', 'compiler.py', 'test_divmod.bf'],
                           capture_output=True, text=True, timeout=3)

    output_lines = result.stdout.split('\n')
    output = ""
    in_output = False
    for line in output_lines:
        if '================' in line:
            if not in_output:
                in_output = True
            else:
                break
        elif in_output:
            output += line

    print(f"Divmod test output: '{output.strip()}'")
    print(f"Expected: '1' (ASCII 49)")
    if output.strip() == '1':
        print("✓ Divmod works!")
    else:
        print("✗ Divmod broken")

test_divmod()
