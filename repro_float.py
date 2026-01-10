from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code
import sys
import io
import contextlib

def test_float():
    code = """
    declare int i
    set 2 on i
    declare float x
    set $i on x
    set $x + 1.250 on x
    set $x - 0.250 on x
    varout x
    """
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    print(f"BF Code length: {len(bf_code)}")
    
    execute_func = generate_code(bf_code)
    memory = bytearray(30000)
    stdout = io.StringIO()
    
    with contextlib.redirect_stdout(stdout):
        execute_func(memory)
    
    output = stdout.getvalue()
    print(f"Output: {output}")
    
    # Float is at pos 8 (int i is at 0-7)
    x_bytes = memory[8:16]
    x_val = int.from_bytes(x_bytes, 'little', signed=True)
    print(f"Memory x (8-15): {list(x_bytes)}")
    print(f"Scaled value: {x_val}")
    print(f"Unscaled: {x_val / 1000.0}")

if __name__ == "__main__":
    test_float()
