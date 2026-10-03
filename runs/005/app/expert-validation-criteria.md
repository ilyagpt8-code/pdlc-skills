# Expert Validation Criteria for tempconv Implementation

## Overview
This document lists all validation criteria the expert will use to accept the executor's implementation of `tempconv`.

## Implementation Requirements

### 1. Directory and File Structure
- [ ] Code in `app/tempconv.py`
- [ ] Tests in `app/tests/` using pytest
- [ ] Executable as: `python app/tempconv.py <value> <from-scale> <to-scale>`

### 2. Conversion Correctness (13 core test cases)

#### Basic Conversions
- [ ] `tempconv 0 C C` → `0` (exit 0)
- [ ] `tempconv 0 C F` → `32` (exit 0)
- [ ] `tempconv 32 F C` → `0` (exit 0)
- [ ] `tempconv 0 C K` → `273.15` (exit 0)
- [ ] `tempconv 273.15 K C` → `0` (exit 0)
- [ ] `tempconv 98.6 F C` → `37` (exit 0)
- [ ] `tempconv 37 C F` → `98.6` (exit 0)
- [ ] `tempconv 100 C K` → `373.15` (exit 0)
- [ ] `tempconv 373.15 K C` → `100` (exit 0)
- [ ] `tempconv -40 C F` → `-40` (exit 0)
- [ ] `tempconv -40 F C` → `-40` (exit 0)

#### Boundary Tests (Absolute Zero)
- [ ] `tempconv -273.15 C K` → `0` (exit 0) — absolute zero
- [ ] `tempconv -273.16 C K` → error (exit 1) — below absolute zero

### 3. Error Handling (5 error test cases)

- [ ] `tempconv abc C F` → "Error: Value is not a valid number" (stderr, exit 1)
- [ ] `tempconv 0 X F` → "Error: Invalid scale 'X': must be C, F, or K" (stderr, exit 1)
- [ ] `tempconv 0 C Z` → "Error: Invalid scale 'Z': must be C, F, or K" (stderr, exit 1)
- [ ] `tempconv -1 K C` → "Error: Temperature in Kelvin cannot be negative: -1K" (stderr, exit 1)
- [ ] `tempconv -300 C K` → "Error: Conversion results in temperature below absolute zero: -26.85K" (stderr, exit 1)

### 4. Missing Arguments
- [ ] `tempconv 0 C` → error (exit 1) — implementation-specific message acceptable

### 5. Case Sensitivity
- [ ] `tempconv 0 c f` → error (exit 1) — lowercase scales must be rejected
- [ ] `tempconv 0 C F` → `32` (exit 0) — uppercase must work

### 6. Output Formatting

#### Trailing Zeros Removal
- [ ] `tempconv 0 C F` outputs `32` (not `32.00`)
- [ ] `tempconv 98.6 F C` outputs `37` (not `37.00`)
- [ ] `tempconv 98.6 F K` outputs `309.75` (not `309.7500`)
- [ ] Values like `0.5` are acceptable with one decimal place

#### Decimal Precision
- [ ] Maximum 2 decimal places shown
- [ ] Trailing zeros removed
- [ ] All results match provided examples within 2 decimal place precision
- [ ] No scientific notation used (even for very large numbers)

### 7. Argument Validation Order
Validate in this order, report first error:
1. Value format (is it a valid number?)
2. From-scale (is it C, F, or K?)
3. To-scale (is it C, F, or K?)
4. Kelvin input constraint (if from-scale is K, value >= 0)
5. Conversion execution
6. Kelvin output constraint (if result in K, >= 0)

### 8. Exit Codes
- [ ] Exit code 0 on successful conversion
- [ ] Exit code 1 on any error

### 9. Output Routing
- [ ] Success: result printed to stdout with newline
- [ ] Error: message printed to stderr with "Error: " prefix
- [ ] No extra text, labels, or confirmation messages on success

## Additional Test Cases to Consider

### Wide Range of Values
- [ ] Very large positive numbers
- [ ] Very large negative numbers  
- [ ] Very small differences in output
- [ ] Values very close to absolute zero

### Floating-Point Precision
- [ ] Results should be accurate to at least 2 decimal places
- [ ] Rounding method (half-up or half-even) is acceptable as long as examples match

## Acceptance Criteria

The implementation is accepted when:
1. All 13 core test cases pass ✓
2. All 5 error cases produce correct error messages and exit code 1 ✓
3. Missing arguments handled with exit code 1 ✓
4. Case sensitivity enforced (uppercase only) ✓
5. Output formatting correct (trailing zeros removed, max 2 decimals) ✓
6. Exit codes correct (0 for success, 1 for error) ✓
7. Output routing correct (stdout for results, stderr for errors) ✓
8. Pytest test suite provided and passes ✓

---

**Expert Ready**: Awaiting notification from executor when implementation is ready for review.
