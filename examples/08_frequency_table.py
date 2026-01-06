#!/usr/bin/env python3

import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp.api import compile_string


def main():
    # Real-world-ish example: count occurrences of three categories using a dict.
    # Input is a single byte index (0,1,2) and we increment the chosen bucket.
    # Demonstrates:
    # - dict declaration
    # - runtime subscripts m[$k]
    # - semicolon-separated statements
    # - match on byte
    code = """
    #define NL "\\n"

    declare dict int counts { a, b, c }
    declare byte k

    // initialize all counts to 0
    set 0 on counts

    print string "Enter bucket id (0/1/2) then Enter: "
    input on k

    // Decode ASCII digit input and increment the chosen bucket.
    // After this, k becomes numeric 0..2 (or 255 for invalid input).
    match (k) {
        case 48:
            set 0 on k
            inc on counts[$k]
        case 49:
            set 1 on k
            inc on counts[$k]
        case 50:
            set 2 on k
            inc on counts[$k]
        default:
            set 255 on k
    }

    print string "Counts: "
    varout counts sep "," end NL

    // Show which bucket was selected
    match (k) {
        case 0:
            print string "You chose a"
            print string NL
        case 1:
            print string "You chose b"
            print string NL
        case 2:
            print string "You chose c"
            print string NL
        default:
            print string "Unknown"
            print string NL
    }
    """

    result = compile_string(code)
    out_path = os.path.join(os.path.dirname(__file__), "_out.bf")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.bf_code)

    subprocess.run(["python3", "src/compiler.py", out_path], check=True)


if __name__ == "__main__":
    main()
