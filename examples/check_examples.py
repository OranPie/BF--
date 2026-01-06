#!/usr/bin/env python3

import os
import re
import subprocess
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _extract_program_output(stdout: str) -> str:
    """src/compiler.py prints debug headers + memory dumps.

    The BF program output is printed between:

        =================\n
    and the next line that begins with:

        =================

    If those markers aren't found, return stdout as-is.
    """
    marker = "================\n"
    if marker not in stdout:
        return stdout

    before, after = stdout.split(marker, 1)
    # end marker is printed with a leading newline
    end_marker = "\n================"
    if end_marker in after:
        program_out, _rest = after.split(end_marker, 1)
        return program_out
    return after


def _norm(s: str) -> str:
    return s.replace('\r\n', '\n')


def _run_example(path: str, *, input_data: str | None, timeout_s: float = 10.0) -> dict:
    cmd = ["python3", path]
    try:
        p = subprocess.run(
            cmd,
            input=input_data,
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=timeout_s,
        )
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "returncode": None,
            "stdout": e.stdout or "",
            "stderr": (e.stderr or "") + "\n[TIMEOUT]",
            "timeout": True,
        }


def _fizzbuzz_expected() -> str:
    lines = []
    for i in range(1, 16):
        if i % 15 == 0:
            lines.append("FizzBuzz")
        elif i % 3 == 0:
            lines.append("Fizz")
        elif i % 5 == 0:
            lines.append("Buzz")
        else:
            lines.append(str(i))
    return "\n".join(lines) + "\n"


def main() -> int:
    examples = [
        {
            "file": "examples/00_hello_world.py",
            "input": None,
            "check": lambda out: "Hello from BF++!" in out,
            "expect": "contains 'Hello from BF++!\\n'",
        },
        {
            "file": "examples/01_vars_and_math.py",
            "input": None,
            "check": lambda out: "OK" in out,
            "expect": "contains 'OK\\n'",
        },
        {
            "file": "examples/02_arrays_dicts_runtime_index.py",
            "input": None,
            "check": lambda out: "ARR_OK" in out,
            "expect": "contains 'ARR_OK\\n'",
        },
        {
            "file": "examples/03_control_flow_match.py",
            "input": None,
            "check": lambda out: out.replace("\n", "") == "TWOXXX",
            "expect": "exactly equals 'TWO\\nXXX\\n'",
        },
        {
            "file": "examples/04_input_echo.py",
            "input": "A",
            "check": lambda out: out == "A",
            "expect": "exactly equals 'A'",
        },
        {
            "file": "examples/05_macros.py",
            "input": None,
            "check": lambda out: "OK" in out,
            "expect": "contains 'OK\\n'",
        },
        {
            "file": "examples/06_fizzbuzz.py",
            "input": None,
            "check": lambda out: out == _fizzbuzz_expected(),
            "expect": "exactly equals FizzBuzz output for 1..15",
        },
        {
            "file": "examples/07_caesar_cipher_byte.py",
            "input": "A",
            "check": lambda out: ("Type one character" in out and "Shifted:" in out and "D" in out),
            "expect": "contains prompt and shifted output containing 'D'",
        },
        {
            "file": "examples/08_frequency_table.py",
            "input": "1\n",
            "check": lambda out: ("Counts:" in out and "You chose b" in out),
            "expect": "contains 'Counts:' and 'You chose b'",
        },
    ]

    print("=== BF++ Examples Verification ===")

    any_fail = False
    for ex in examples:
        r = _run_example(ex["file"], input_data=ex["input"], timeout_s=10.0)
        raw_stdout = r["stdout"]
        prog_out = _norm(_extract_program_output(raw_stdout))

        passed = r["ok"] and ex["check"](prog_out)
        status = "PASS" if passed else "FAIL"
        print(f"\n[{status}] {ex['file']}")

        if passed:
            continue

        any_fail = True
        print(f"Expected: {ex['expect']}")
        print(f"Return code: {r['returncode']}  Timeout: {r['timeout']}")

        def trunc(s: str) -> str:
            if len(s) > 2000:
                return s[:2000] + "\n...[truncated]"
            return s

        print("--- program output (extracted) ---")
        print(trunc(prog_out))
        print("--- stderr ---")
        print(trunc(r["stderr"]))

    if any_fail:
        print("\nSome examples FAILED.")
        return 1

    print("\nAll examples passed (output checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
