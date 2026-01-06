#!/usr/bin/env python3
from bfpp import BrainFuckPlusPlusCompiler

code = """
declare byte i
for (set 0 on i; i != 3; inc on i) {
    print string "B"
}
"""

compiler = BrainFuckPlusPlusCompiler()

# Add debugging to for loop
import bfpp.compiler

original_handle_for = bfpp.compiler.BrainFuckPlusPlusCompiler._handle_for_loop

def debug_handle_for(self, tokens, lines, line_idx):
    print(f"_handle_for_loop called")
    print(f"  tokens: {tokens}")

    loop_parts = "".join(self._extract_parentheses_content(tokens))
    print(f"  loop_parts: '{loop_parts}'")

    parts = loop_parts.split(';')
    print(f"  parts after split: {parts}")

    init_tokens = self._tokenize(parts[0].strip())
    cond_tokens = self._tokenize(parts[1].strip())
    step_tokens = self._tokenize(parts[2].strip())

    print(f"  init_tokens: {init_tokens}")
    print(f"  cond_tokens: {cond_tokens}")
    print(f"  step_tokens: {step_tokens}")

    return original_handle_for(self, tokens, lines, line_idx)

bfpp.compiler.BrainFuckPlusPlusCompiler._handle_for_loop = debug_handle_for

bf_code = compiler.compile(code)
print(f"\nGenerated {len(bf_code)} chars")
