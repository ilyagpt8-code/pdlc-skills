# Specification Issues and Clarifications (B1 Expert Review)

## Issue 1: Ambiguous Rounding Language (RESOLVED)
**Location**: Lines 144-146

**Issue**: The spec mentions "0.25 rounded to 1 decimal place = 0.2 (or 0.3 depending on implementation choice..." but later states "Implement standard rounding (round half away from zero)".

**Clarification**: The requirement is clear: use **round half away from zero**, not banker's rounding. Python's built-in `round()` function uses banker's rounding (round half to even), so custom rounding logic must be implemented.

Examples with .5 away from zero:
- 0.25 → 0.3
- 0.35 → 0.4
- 2.5 → 3
- -2.5 → -3

This differs from Python's default `round()` behavior.

## Issue 2: Decimal Place Preservation (CLARIFIED)
**Location**: Lines 50-52

**Interpretation**: 
- Input `32` (no decimal point) → output with 1 decimal place (e.g., `0.0`)
- Input `32.0` (1 decimal place) → output with 1 decimal place
- Input `32.00` (2 decimal places) → output with 2 decimal places

This is clear and unambiguous. The executor must count the decimal places in the input string.

## Issue 3: Example Verification
**Location**: Lines 59-63

All provided examples have been verified against the conversion formulas and are correct.

## Issue 4: Absolute Zero Validation
**Location**: Line 40

The spec correctly states that for Kelvin, the minimum is 0 K (not below). The validation logic should allow 0 K and reject only negative values.

---

**Decision**: Proceed with implementation. The main implementation challenge is custom rounding logic to support round half away from zero.
