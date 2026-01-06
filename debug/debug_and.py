from bfpp import BrainFuckPlusPlusCompiler

code = """
declare byte a
declare byte b
declare byte result

set 1 on a
set 1 on b
set $a & $b on result

move to result
output
"""

comp = BrainFuckPlusPlusCompiler()
bf = comp.compile(code)

print(f"Generated {len(bf)} chars of BF code")
print(f"\nVariables:")
for name, info in comp.variables.items():
    print(f"  {name}: pos={info['pos']}, type={info['type']}, size={info['size']}")

# Save and show last 200 chars
print(f"\nLast 200 chars of BF code:")
print(bf[-200:])
