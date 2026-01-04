import sys
import time
import mmap
import ctypes
from typing import Callable, List, Optional


def is_code_char(ch: str) -> bool:
    return ch in '+-<>[].,'


def generate_code(source: str) -> Optional[Callable[[bytearray], None]]:
    # Filter the source code
    filtered = [c for c in source if is_code_char(c)]
    filtered_str = ''.join(filtered)
    i = 0
    length = len(filtered_str)

    memory = bytearray(30000)
    ptr = 0
    stack = []
    jump_table = {}

    # Preprocess jump table for loops
    temp_stack = []
    for pos, cmd in enumerate(filtered_str):
        if cmd == '[':
            temp_stack.append(pos)
        elif cmd == ']':
            if not temp_stack:
                return None  # Mismatched brackets
            start = temp_stack.pop()
            jump_table[start] = pos
            jump_table[pos] = start

    if temp_stack:
        return None  # Mismatched brackets

    def execute(mem: bytearray) -> None:
        nonlocal ptr
        mem_len = len(mem)
        i = 0
        while i < length:

            cmd = filtered_str[i]

            if cmd == '+':
                mem[ptr] = (mem[ptr] + 1) & 0xFF
            elif cmd == '-':
                mem[ptr] = (mem[ptr] - 1) & 0xFF
            elif cmd == '>':
                ptr += 1
                if ptr >= mem_len:
                    ptr = 0
            elif cmd == '<':
                ptr -= 1
                if ptr < 0:
                    ptr = mem_len - 1
            elif cmd == '.':
                sys.stdout.write(chr(mem[ptr]))
                sys.stdout.flush()
            elif cmd == ',':
                char = sys.stdin.read(1)
                mem[ptr] = ord(char) if char else 0
            elif cmd == '[':
                if mem[ptr] == 0:
                    i = jump_table[i]
            elif cmd == ']':
                if mem[ptr] != 0:
                    i = jump_table[i]
            i += 1

    return execute


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [filename]")
        return 1

    try:
        with open(sys.argv[1], 'r') as f:
            code = f.read()
    except FileNotFoundError:
        print("Couldn't find file")
        return 1

    start = time.time()
    func = generate_code(code)
    end = time.time()

    if func is None:
        print("Error: Mismatched brackets in Brainfuck code")
        return 1

    print(f"Compilation took {(end - start) * 1000:.2f} ms")

    if len(code) < 1024:
        print(code)

    print("================")

    memory = bytearray(30000)
    start = time.time()
    func(memory)
    end = time.time()

    print("\n================")
    print(f"Execution took {(end - start) * 1000:.2f} ms")
    print(*[" ".join(map(str, [int(b) for b in memory[:100].strip()][i:i+8])) + "\n" for i in range(0, 100, 8)])


if __name__ == "__main__":
    main()