#!/usr/bin/env python3

import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp.api import compile_string


def main():
    code = """
    declare int a
    declare int b
    declare int c

    set 40 on a
    set 2 on b
    set $a + $b on c

    if (c == 42) {
        print string "OK\n"
    } else {
        print string "BAD\n"
    }
    """

    result = compile_string(code)
    out_path = os.path.join(os.path.dirname(__file__), "_out.bf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.bf_code)

    subprocess.run(["python3", "src/compiler.py", out_path], check=True)


if __name__ == "__main__":
    main()
