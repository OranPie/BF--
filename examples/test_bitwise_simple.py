#!/usr/bin/env python3
"""Test bitwise operations to see what fails"""
from bfpp import BrainFuckPlusPlusCompiler
import subprocess

def test_bitwise(name, code, timeout=3):
    print(f"\nTest: {name}")
    print(f"Code: {code}")

    try:
        compiler = BrainFuckPlusPlusCompiler()
        bf_code = compiler.compile(code)

        print(f"Generated {len(bf_code)} chars of BF code")

        with open('test_bitwise.bf', 'w') as f:
            f.write(bf_code)

        result = subprocess.run(['python3', 'compiler.py', 'test_bitwise.bf'],
                               capture_output=True, text=True, timeout=timeout)

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

        print(f"Output: '{output.strip()}'")
        return output.strip()

    except subprocess.TimeoutExpired:
        print("TIMEOUT!")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

# Test simple bitwise operations with bytes (not ints)
print("="*60)
print("Testing bitwise operations on BYTES")
print("="*60)

# AND: 5 & 3 = 0101 & 0011 = 0001 = 1
# We'll just output the raw byte value
test_bitwise("Byte AND: 5 & 3 = 1",
    """
    declare byte a
    declare byte b
    declare byte result
    set 5 on a
    set 3 on b
    set $a & $b on result
    move to result
    output
    """)
