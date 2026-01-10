import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code

def test_arithmetic_simple():
    code = """
    declare int a
    declare int b
    declare int c
    set 10 on a
    set 3 on b
    set $a + $b on c
    print int c
    print string " "
    set $a - $b on c
    print int c
    print string " "
    set $a * $b on c
    print int c
    print string " "
    set $a / $b on c
    print int c
    print string " "
    set $a % $b on c
    print int c
    print string "\n"
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    try:
        bf_code = compiler.compile(code)
        print(f"BF Code length: {len(bf_code)}")
        
        memory = bytearray(30000)
        func = generate_code(bf_code)
        
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            func(memory)
        output = f.getvalue()
        print(f"Output: {output.strip()}")
        assert output.strip() == "13 7 30 3 1"
        print("Simple arithmetic test passed!")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_arithmetic_simple()
