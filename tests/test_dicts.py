#!/usr/bin/env python3
"""Basic dict feature smoke test."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bfpp import BrainFuckPlusPlusCompiler
from compiler import generate_code


def main():
    code = """
    declare dict byte m { a, b, "c" }

    set 65 on m[a]
    set 66 on m[b]
    set 67 on m["c"]

    varout m[a]
    varout m[b]
    varout m["c"]
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
