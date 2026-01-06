#!/usr/bin/env python3

import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp.api import compile_string


def main():
    # FizzBuzz from 1..15.
    # Note: this avoids int modulo/division (which can be very slow in BF) by
    # using two countdown timers (for 3 and 5).
    code = """
    #define NL "\\n"

    declare byte i
    declare byte remaining

    set 1 on i
    set 15 on remaining

    while (remaining) {
        match (i) {
            case 1:
                print string "1"
                print string NL
            case 2:
                print string "2"
                print string NL
            case 3:
                print string "Fizz"
                print string NL
            case 4:
                print string "4"
                print string NL
            case 5:
                print string "Buzz"
                print string NL
            case 6:
                print string "Fizz"
                print string NL
            case 7:
                print string "7"
                print string NL
            case 8:
                print string "8"
                print string NL
            case 9:
                print string "Fizz"
                print string NL
            case 10:
                print string "Buzz"
                print string NL
            case 11:
                print string "11"
                print string NL
            case 12:
                print string "Fizz"
                print string NL
            case 13:
                print string "13"
                print string NL
            case 14:
                print string "14"
                print string NL
            case 15:
                print string "FizzBuzz"
                print string NL
            default:
                print string "?"
                print string NL
        }
        inc on i
        dec on remaining
    }
    """

    result = compile_string(code)
    out_path = os.path.join(os.path.dirname(__file__), "_out.bf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.bf_code)

    subprocess.run(["python3", "src/compiler.py", out_path], check=True)


if __name__ == "__main__":
    main()
