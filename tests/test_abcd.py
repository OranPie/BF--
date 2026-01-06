#!/usr/bin/env python3
"""ABCD expansion smoke test.

Covers:
- runtime subscripts: arr[$i] and m[$k]
- varout formatting: sep/end
- string arrays and string dicts
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code


def run(code: str):
    c = BrainFuckPlusPlusCompiler()
    bf = c.compile(code)
    fn = generate_code(bf)
    if fn is None:
        raise RuntimeError("Generated BF has mismatched brackets")
    mem = bytearray(30000)
    fn(mem)


def main():
    code = r'''
    // Runtime array indexing (byte index)
    declare byte i
    declare byte arr[3]

    set 0 on i
    set 65 on arr[$i]
    set 1 on i
    set 66 on arr[$i]
    set 2 on i
    set 67 on arr[$i]

    varout arr end "\n"

    // Runtime dict indexing (slot id) using dict byte
    declare byte k
    declare dict byte m { a, b, c }

    set 0 on k
    set 88 on m[$k]
    set 1 on k
    set 89 on m[$k]
    set 2 on k
    set 90 on m[$k]

    varout m sep "-" end "\n"

    // String array
    declare string 6 sarr[2]
    set "hi" on sarr[0]
    set "yo" on sarr[1]
    varout sarr sep "," end "\n"

    // String dict (fixed keys)
    declare dict string 6 sm { left, right }
    set "L" on sm[left]
    set "R" on sm[right]
    varout sm sep ":" end "\n"
    '''

    run(code)


if __name__ == '__main__':
    main()
