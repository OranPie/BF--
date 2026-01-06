#!/usr/bin/env python3

import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp.api import compile_string


def main():
    # Educational example: Caesar-shift a single input byte (ASCII) by 3.
    # This is intentionally minimal and demonstrates:
    # - byte input
    # - byte arithmetic via repeated inc
    # - macro usage for small code reuse
    code = """
    #define NL "\n"

    declare byte c

    print string "Type one character then press Enter: "
    input on c

    // shift by 3: c = c + 3
    inc on c ; inc on c ; inc on c

    print string "Shifted: "
    varout c
    print string NL
    """

    result = compile_string(code)
    out_path = os.path.join(os.path.dirname(__file__), "_out.bf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.bf_code)

    subprocess.run(["python3", "src/compiler.py", out_path], check=True)


if __name__ == "__main__":
    main()
