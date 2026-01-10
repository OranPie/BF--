from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code
import sys
import io

def test():
    code = """
    declare int a
    declare int b
    set 5 on a
    set 3 on b
    set $a + $b on a
    print string "Value of a: "
    varout a
    print string "\\n"
    if (a == 8) {
        print string "Condition check: YES\\n"
    } else {
        print string "Condition check: NO\\n"
    }
    """
    compiler = BrainFuckPlusPlusCompiler()
    bf_code = compiler.compile(code)
    print(f"BF Code length: {len(bf_code)}")
    
    # We want to see what happens during 'set $a + $b on a'
    # The first few instructions are 'set 5 on a' and 'set 3 on b'
    
    execute_func = generate_code(bf_code)
    memory = bytearray(30000)
    stdout = io.StringIO()
    
    print("Initial memory (after setup):")
    # Execute partially if possible? No, generate_code returns a full func.
    # We'll just run it and see the final state more carefully.
    
    import contextlib
    with contextlib.redirect_stdout(stdout):
        execute_func(memory)
    
    print(f"Output: {stdout.getvalue()}")
    print(f"Memory a (0-7): {list(memory[0:8])}")
    print(f"Memory b (8-15): {list(memory[8:16])}")
    
    # Check if 'a' was changed at all
    a_val = int.from_bytes(memory[0:8], 'little', signed=True)
    b_val = int.from_bytes(memory[8:16], 'little', signed=True)
    print(f"Final a: {a_val}, Final b: {b_val}")

if __name__ == "__main__":
    test()
