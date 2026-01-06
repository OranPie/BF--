import sys
import os
from bfpp.compiler import BrainFuckPlusPlusCompiler

def run_test(name, code, expected_output):
    print(f"Running test: {name}")
    compiler = BrainFuckPlusPlusCompiler()
    try:
        bf_code = compiler.compile(code)
        # Use a simple BF interpreter or just check if it compiles for now
        # Since we don't have a reliable BF interpreter here, we'll just check if it compiles without error
        # and maybe print a bit of the BF code.
        print(f"  [OK] Compiled {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        return False

def main():
    # Add src to path
    sys.path.append(os.path.abspath("src"))
    
    test_cases = [
        ("int16 declaration and set", "declare int16 a; set 12345 on a; varout a;", ""),
        ("int64 declaration and set", "declare int64 b; set 123456789012345 on b; varout b;", ""),
        ("int16 arithmetic", "declare int16 a; set 1000 on a; set a + 500 on a; varout a;", ""),
        ("int64 arithmetic", "declare int64 b; set 1000000 on b; set b - 500000 on b; varout b;", ""),
        ("int16 comparison", "declare int16 a; set 100 on a; if (a > 50) { varout \"GT\"; }", ""),
        ("int64 comparison", "declare int64 b; set -100 on b; if (b < 0) { varout \"NEG\"; }", ""),
        ("match int16", "declare int16 a; set 10 on a; match (a) { case 10: varout \"TEN\"; default: varout \"OTHER\"; }", ""),
    ]

    all_ok = True
    for name, code, expected in test_cases:
        if not run_test(name, code, expected):
            all_ok = False
            
    if all_ok:
        print("\nAll compilation tests passed!")
    else:
        print("\nSome tests failed.")

if __name__ == "__main__":
    main()
