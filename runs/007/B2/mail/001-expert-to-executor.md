# Turn 1: Specification Review Complete

## Task Summary

Implement `tempconv` utility according to specification in `out/006-B2/tempconv.md`.

- **Code location**: `out/007-B2/tempconv.py`
- **Tests location**: `out/007-B2/tests/` (pytest format)
- **Language**: Python 3 (standard library only)
- **Command**: `python out/007-B2/tempconv.py <value> <from_scale> <to_scale>`

## Key Requirements

1. **Conversions**: Support C ↔ F, C ↔ K, F ↔ K using standard formulas (all in spec)
2. **Error handling**: Exit codes must be exact:
   - 0: success
   - 1: invalid value (not a number)
   - 2: invalid scale (not C/F/K)
   - 3: temperature below absolute zero
   - 4: wrong number of arguments

3. **Features**:
   - Case-insensitive scale names (C, c, F, f, K, k all valid)
   - Same-scale conversion returns input value unchanged
   - Reasonable precision (specs says accuracy to 2 decimal places minimum)
   - Trailing zeros may be omitted for readability
   - Program must not crash on any input

4. **Absolute zero validation**:
   - Any input that converts to negative Kelvin is invalid
   - Bounds: 0 K, -273.15 C, -459.67 F

## Specification Issues

I found two minor ambiguities in the spec (not errors) and recorded reasonable resolutions in `runs/007/B2/spec-issues.md`. These won't affect implementation significantly.

## Next Steps

1. Write `out/007-B2/tempconv.py` with full implementation
2. Write comprehensive tests in `out/007-B2/tests/` covering:
   - All conversion pairs
   - Boundary cases (absolute zero in all scales)
   - Invalid inputs (non-numeric, unknown scales)
   - Wrong argument counts
   - Case sensitivity
3. Verify all tests pass
4. Message me when done with location of code and test results

---
**No changes to specification** — implement exactly as written.
