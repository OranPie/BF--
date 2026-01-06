#!/usr/bin/env python3

import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp.api import compile_string


def main():
    code = """
    declare byte a
    set 2 on a

    match (a) {
        case 1:
            print string "ONE\n"
        case 2:
            print string "TWO\n"
        default:
            print string "OTHER\n"
    }

    declare byte counter
    set 3 on counter
    while (counter) {
        print string "X"
        dec on counter
    }
    print string "\n"
    """

    result = compile_string(code)
    out_path = os.path.join(os.path.dirname(__file__), "_out.bf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.bf_code)

    subprocess.run(["python3", "src/compiler.py", out_path], check=True)


if __name__ == "__main__":
    main()
