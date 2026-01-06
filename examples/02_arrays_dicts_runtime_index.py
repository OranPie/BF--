#!/usr/bin/env python3

import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp.api import compile_string


def main():
    code = """
    declare byte i
    declare int arr[3]
    declare dict byte m { a, b, c }

    set 1 on i
    set 123 on arr[1]

    set 2 on i
    set 90 on m[$i]

    if (arr[1] == 123) {
        print string "ARR_OK\n"
    } else {
        print string "ARR_BAD\n"
    }

    varout m end "\n"
    """

    result = compile_string(code)
    out_path = os.path.join(os.path.dirname(__file__), "_out.bf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.bf_code)

    subprocess.run(["python3", "src/compiler.py", out_path], check=True)


if __name__ == "__main__":
    main()
