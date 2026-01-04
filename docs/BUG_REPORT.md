# BF++ Compiler Bug Report

**Test Date:** 2025-10-03
**Tests Passed:** 3 / 18 (16.7%)

## Working Operations ✓

1. **Byte variable declaration and set** - Works correctly
2. **Increment/decrement** - Works correctly
3. **Print string literals** - Works correctly

## Critical Bugs Found

### 1. If/Else Statements Execute Both Branches ❌

**Status:** CRITICAL - Control flow broken
**Test:** If statement (true condition), If statement (false condition)

```bf++
declare byte x
set 5 on x
if (x == 5) {
    print string "YES"
} else {
    print string "NO"
}
```

**Expected:** `YES`
**Actual:** `YESNO`

**Issue:** Both the if-block and else-block execute regardless of condition.

**Location:** `core.py` line 633-679 (`_handle_if_statement`)

**Root Cause:** The else-block flag is not being properly cleared, so both branches run.

---

### 2. While Loops Don't Execute ❌

**Status:** CRITICAL - Loops broken
**Test:** While loop

```bf++
declare byte counter
set 3 on counter
while (counter) {
    print string "A"
    dec on counter
}
```

**Expected:** `AAA`
**Actual:** (empty)

**Issue:** Loop body never executes even when condition is true.

**Location:** `core.py` line 681-712 (`_handle_while_loop`)

**Root Cause:** The condition evaluation or loop structure generation is incorrect.

---

### 3. For Loops Cause Infinite Loop/Timeout ❌

**Status:** CRITICAL - Loops broken
**Test:** For loop

```bf++
declare byte i
for (set 0 on i; i != 3; inc on i) {
    print string "B"
}
```

**Expected:** `BBB`
**Actual:** Timeout after 5 seconds

**Issue:** For loop enters infinite loop.

**Location:** `core.py` line 714-758 (`_handle_for_loop`)

**Root Cause:** Loop condition or step execution not working correctly.

---

### 4. Integer Output (varout) Produces No Output ❌

**Status:** CRITICAL - I/O broken for integers
**Test:** Integer declaration and output, Zero integer output, Large integer output

```bf++
declare int x
set 42 on x
varout x
```

**Expected:** `42`
**Actual:** (empty)

**Issue:** `varout` for integers produces no output at all.

**Location:** `core.py` line 973-1097 (`_output_int_as_decimal`)

**Root Cause:** Complex decimal conversion algorithm likely has bugs. The algorithm involves:
- Detecting negative numbers
- Division by 10 to extract digits
- Reversing digit order for output

---

### 5. Bitwise Operations Timeout ❌

**Status:** CRITICAL - All bitwise ops fail
**Test:** Bitwise AND, OR, XOR

```bf++
declare int a
declare int b
declare int result
set 15 on a
set 7 on b
set $a & $b on result
varout result
```

**Expected:** `7`
**Actual:** Timeout after 5 seconds

**Issue:** Bitwise operations enter infinite loops.

**Location:** `core.py` line 506-629 (`_bitwise_byte_operation`)

**Root Cause:** The complex bit extraction and logical operation loop likely has infinite loop bugs. The algorithm processes 8 bits using divmod-by-2 pattern.

---

### 6. Bitwise NOT Produces No Output ❌

**Status:** CRITICAL
**Test:** Bitwise NOT operation

```bf++
declare int a
declare int result
set 0 on a
set ~ $a on result
varout result
```

**Expected:** `-1`
**Actual:** (empty)

**Issue:** Compiles but produces no output.

**Location:** `core.py` line 487-504 (`_perform_bitwise_not`)

**Root Cause:** Either the NOT operation itself is broken, or it's affected by the `varout` bug (#4).

---

### 7. String Variable Output (varout) Produces No Output ❌

**Status:** CRITICAL - String I/O broken
**Test:** String variable output

```bf++
declare string 10 msg
set "Hi" on msg
varout msg
```

**Expected:** `Hi`
**Actual:** (empty)

**Issue:** `varout` for strings produces no output.

**Location:** `core.py` line 958-962

```python
if var_info['type'] in ['string', 'varstring']:
    self._move_to_var(var_name)
    self.bf_code.append('[.>]')  # Output until null
    self._move_to_var(var_name)
```

**Root Cause:** The pointer position after setting the string might be wrong, or the BF pattern `[.>]` isn't working as expected.

---

### 8. Break Statement Doesn't Work ❌

**Status:** HIGH - Loop control broken
**Test:** Break statement in loop

```bf++
declare byte i
set 10 on i
while (i) {
    print string "X"
    break
}
```

**Expected:** `X`
**Actual:** (empty)

**Issue:** Break statement doesn't exit the loop.

**Location:** `core.py` line 760-770 (`_handle_break`)

**Root Cause:** Likely related to the while loop bug (#2). The break clears the condition flag, but the loop itself isn't executing.

---

### 9. Negative Numbers Cannot Be Parsed ❌

**Status:** MEDIUM - Expression parser limitation
**Test:** Negative integer output

```bf++
declare int x
set -5 on x
varout x
```

**Expected:** `-5`
**Actual:** Parse error: `Cannot parse expression: - 5`

**Issue:** The tokenizer/parser treats negative numbers as two tokens: `-` and `5`.

**Location:** `core.py` line 450-459 (`_parse_expression`)

**Root Cause:** Negative literals aren't handled in expression parsing. The parser expects binary operations with two operands, but `-5` becomes two tokens.

**Workaround:** Use two's complement representation or implement unary minus operator.

---

## Summary

**Critical Issues (prevent core functionality):**
- All control flow (if/else, while, for, break)
- All integer operations (varout, bitwise)
- String varout
- Negative number parsing

**Recommendation:** The compiler needs significant debugging, particularly:
1. Fix condition flag management in if/else statements
2. Fix loop execution in while/for statements
3. Debug the integer-to-decimal conversion algorithm
4. Debug the bitwise operation bit processing loops
5. Fix string varout pointer management
6. Add support for negative number literals

The only reliable features currently are:
- Simple byte variables
- Setting literal values on bytes
- Inc/dec operations
- Printing string literals (not variables)
