#!/usr/bin/env python3
"""Basic array feature smoke test."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code


def main():
    code = """
    declare byte arr[3]
    set 65 on arr[0]
    set 66 on arr[1]
    set 67 on arr[2]

    varout arr[0]
    varout arr[1]
    varout arr[2]
    """

    c = BrainFuckPlusPlusCompiler()
    bf = c.compile(code)
    fn = generate_code(bf)
    if fn is None:
        raise RuntimeError("Generated BF has mismatched brackets")

    mem = bytearray(30000)
    fn(mem)


if __name__ == '__main__':
    main()
