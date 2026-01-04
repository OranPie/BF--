#!/usr/bin/env python3
"""Test bitwise operations on integers"""
from core import BrainFuckPlusPlusCompiler
import subprocess

def test_bitwise(name, code, timeout=10):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")

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

# Test bitwise AND
# 5 & 3 = 0101 & 0011 = 0001 = 1
result = test_bitwise("INT AND: 5 & 3 = 1",
    """
    declare int a
    declare int b
    declare int result
    set 5 on a
    set 3 on b
    set $a & $b on result
    move to result
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    inc
    output
    """)

if result == '1':
    print("✓ AND works!")
else:
    print(f"✗ AND failed - expected '1', got '{result}'")

# Test bitwise OR
# 4 | 2 = 0100 | 0010 = 0110 = 6
result = test_bitwise("INT OR: 4 | 2 = 6",
    """
    declare int a
    declare int b
    declare int result
    set 4 on a
    set 2 on b
    set $a | $b on result
    move to result
    """ + "inc\n" * 48 + "output")

if result == '6':
    print("✓ OR works!")
else:
    print(f"✗ OR failed")

# Test bitwise XOR
# 5 ^ 3 = 0101 ^ 0011 = 0110 = 6
result = test_bitwise("INT XOR: 5 ^ 3 = 6",
    """
    declare int a
    declare int b
    declare int result
    set 5 on a
    set 3 on b
    set $a ^ $b on result
    move to result
    """ + "inc\n" * 48 + "output")

if result == '6':
    print("✓ XOR works!")
else:
    print(f"✗ XOR failed")

# Test bitwise NOT
# ~5 = ~00000101 = 11111010 = 250 (for a byte)
# But for int it's  ~00000000...00000101 = 11111111...11111010
# In two's complement that's -6
# But we do bitwise NOT which is 255-5=250 for each byte
# So first byte is 250
result = test_bitwise("INT NOT: ~5",
    """
    declare int a
    declare int result
    set 5 on a
    set ~ $a on result
    move to result
    output
    """)

# First byte should be 250
if result and ord(result[0]) == 250:
    print("✓ NOT works!")
else:
    print(f"✗ NOT failed - expected byte value 250, got {ord(result[0]) if result else 'None'}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
