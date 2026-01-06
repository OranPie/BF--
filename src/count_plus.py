from bfpp import BrainFuckPlusPlusCompiler

code = """
declare int x
set 0 on x
varout x
"""

comp = BrainFuckPlusPlusCompiler()
bf = comp.compile(code)

# Find first . and count + before it
idx = bf.find('.')
if idx >= 0:
    # Count consecutive + before the .
    count = 0
    i = idx - 1
    while i >= 0 and bf[i] == '+':
        count += 1
        i -= 1
    print(f"First . at position {idx}")
    print(f"Number of consecutive + before it: {count}")
    print(f"ASCII value: {count}")
    print(f"Character: {chr(count) if count < 128 else 'N/A'}")
    
    #  Show more context
    print(f"\nContext (100 before and 50 after):")
    print(bf[max(0,idx-100):idx+50])
