# Spec Issues: tempconv

## Issue 1: Handling of Special Float Values (inf, nan)

### Problem

The specification does not explicitly address how to handle special float values like `inf` (infinity) and `nan` (not a number):

1. **Formatting conflict**: Spec requires output formatted to 2 decimal places (line 70), but `inf` and `nan` cannot be formatted to specific decimal places.

2. **Physical plausibility**: Spec states results should be "physically plausible" (line 147), but infinity and NaN are not physically plausible temperatures.

3. **Input validation**: Spec requires validation of numeric input (line 101: "Первый аргумент не является числом"), but Python's `float()` function accepts "inf", "Infinity", "-inf", and "nan" as valid floats.

### Current Behavior

- Input: `tempconv inf F C`
- Output: `inf` with exit code 0
- Expected: Either rejected with error (exit code 1) OR formatted according to spec

### Decision

**These values should be rejected as invalid input with exit code 1 and message "Error: invalid temperature value"**

Justification:
1. Infinity and NaN are mathematical constructs, not valid temperature values
2. They cannot be formatted per spec requirements
3. They violate the "physically plausible" requirement
4. The spirit of the spec is to handle realistic temperature data

### Resolution

The executor should add validation to reject infinity and NaN values:
- Check if `value` is finite using `math.isfinite()` after parsing
- Reject with "Error: invalid temperature value" if not finite
- This brings NaN/inf handling in line with the intent of rejecting non-numeric input

### Test Cases (after fix)

```bash
# Should return exit code 1
tempconv inf F C      # Error: invalid temperature value
tempconv -inf F C     # Error: invalid temperature value
tempconv nan C F      # Error: invalid temperature value
```

### Implementation (Turn 2)

Fix applied in `out/007-A1/tempconv.py`:
```python
import math

# After: value = float(value_str)
if not math.isfinite(value):
    print("Error: invalid temperature value", file=sys.stderr)
    sys.exit(1)
```

Added tests in `out/007-A1/tests/test_tempconv.py`:
- `test_infinity_input()` - verifies `inf` is rejected
- `test_negative_infinity_input()` - verifies `-inf` is rejected
- `test_nan_input()` - verifies `nan` is rejected

All 54 tests pass (51 original + 3 new special value tests).

---

**Status**: RESOLVED in Turn 2
**Implementation**: Used `math.isfinite()` to reject inf/-inf/nan
**Metrics**: Improved from 34/35 to 35/35 test cases passing
**Severity**: Minor (edge case, but affects spec compliance)
**Priority**: Fixed before final acceptance
