import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code

def test_arithmetic():
    code = """
    declare int64 a
    declare int64 b
    declare int64 c
    set 100 on a
    set 30 on b
    set $a + $b on c
    print int c
    print string "\\n"
    set $a - $b on c
    print int c
    print string "\\n"
    set $a * $b on c
    print int c
    print string "\\n"
    set $a / $b on c
    print int c
    print string "\\n"
    set $a % $b on c
    print int c
    print string "\\n"
    """
    
    compiler = BrainFuckPlusPlusCompiler()
    start = time.time()
    bf_code = compiler.compile(code)
    compile_time = time.time() - start
    print(f"BF Compilation took {compile_time*1000:.2f} ms")
    print(f"BF Code length: {len(bf_code)}")
    
    memory = bytearray(30000)
    func = generate_code(bf_code)
    
    start = time.time()
    func(memory)
    exec_time = time.time() - start
    print(f"Execution took {exec_time*1000:.2f} ms")

if __name__ == "__main__":
    test_arithmetic()
