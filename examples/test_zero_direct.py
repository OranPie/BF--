#!/usr/bin/env python3
from core import BrainFuckPlusPlusCompiler

code = """
declare int x
set 0 on x
varout x
"""

comp = BrainFuckPlusPlusCompiler()
bf = comp.compile(code)

# Check specific patterns
print(f"Total BF code length: {len(bf)}")
print(f"Number of . (output) commands: {bf.count('.')}")
print(f"Number of [ commands: {bf.count('[')}")
print(f"Number of ] commands: {bf.count(']')}")

# Find the first output command and show context
idx = bf.find('.')
if idx >= 0:
    print(f"\nFirst . at position {idx}")
    print(f"Context (50 chars before and after):")
    print(bf[max(0,idx-50):idx+50])
    
# Show last 200 chars
print(f"\nLast 200 chars of BF code:")
print(bf[-200:])
