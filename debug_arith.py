
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from bfpp.compiler import BrainFuckPlusPlusCompiler
from bfi import interpret

def test_add():
    compiler = BrainFuckPlusPlusCompiler()
    # 64-bit addition: 1 + 2 = 3
    code = """
    declare int64 a
    declare int64 b
    declare int64 c
    set 1 on a
    set 2 on b
    c = a + b
    varout c
    """
    bf_code = compiler.compile(code)
    print("Testing 1 + 2...")
    output = interpret(bf_code, input_data="")
    print(f"Output: {output}")

def test_add_carry():
    compiler = BFPPCompiler()
    # 8-bit wrap: 255 + 1 = 0 (low byte)
    code = """
    declare int64 a
    declare int64 b
    declare int64 c
    set 255 on a
    set 1 on b
    c = a + b
    varout c
    """
    bf_code = compiler.compile(code)
    print("Testing 255 + 1...")
    output = interpret(bf_code, input_data="")
    # Should be 256, which is [0, 1, 0, 0, 0, 0, 0, 0]
    print(f"Output: {output}")

if __name__ == "__main__":
    test_add()
    test_add_carry()
