import sys
import os

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Add src to path relative to the script location
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'src'))

from bfpp.compiler import BrainFuckPlusPlusCompiler

def test_expfloat_compilation():
    compiler = BrainFuckPlusPlusCompiler()
    
    test_cases = [
        ("Simple expfloat", 'declare expfloat x; set 1.234 on x; varout x'),
        ("Scientific notation", 'declare expfloat x; set 1.5e2 on x; varout x'),
        ("Expfloat addition", 'declare expfloat a; declare expfloat b; declare expfloat c; set 1.1 on a; set 2.2 on b; set $a + $b on c; varout c'),
        ("Expfloat negative", 'declare expfloat x; set -5.67e-1 on x; varout x'),
    ]
    
    for name, code in test_cases:
        print(f"Testing {name}...")
        try:
            bf = compiler.compile(code)
            print(f"  OK. BF length: {len(bf)}")
        except Exception as e:
            print(f"  FAILED: {e}")

def test_error_classification():
    compiler = BrainFuckPlusPlusCompiler()
    
    error_cases = [
        ("ParseError (unknown var)", 'set 1 on unknown_var', "ParseError"),
        ("TypeError (assign num to string)", 'declare string 10 s; set 123 on s', "TypeError"),
        ("NotImplementedError (expfloat mult)", 'declare expfloat x; set $x * $x on x', "NotImplementedError"),
    ]
    
    for name, code, expected_kind in error_cases:
        print(f"Testing {name}...")
        try:
            compiler.compile(code)
            print("  FAILED: Expected error but compiled successfully")
        except Exception as e:
            err_str = str(e)
            if expected_kind in err_str:
                print(f"  OK. Found {expected_kind}")
            else:
                print(f"  FAILED: Expected {expected_kind} but got:\n{err_str}")

if __name__ == "__main__":
    print("=== Testing expfloat ===")
    test_expfloat_compilation()
    print("\n=== Testing Error Classification ===")
    test_error_classification()
