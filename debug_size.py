import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from bfpp import BrainFuckPlusPlusCompiler

code = """
declare int a
declare int b
set 5 on a
set 3 on b
set $a + $b on a
if (a == 8) {
    print string "YES"
} else {
    print string "NO"
}
"""

compiler = BrainFuckPlusPlusCompiler()
bf_code = compiler.compile(code)
print(f"BF code length: {len(bf_code)}")
print(f"First 500 chars: {bf_code[:500]}")
