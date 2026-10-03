# Task Assignment: Temperature Converter Implementation

## Specification
Your task is to implement the `tempconv` utility according to the specification in `/home/user/pdlc-skills/out/006-B1/tempconv.md`.

**Output paths**:
- Implementation: `/home/user/pdlc-skills/out/007-B1/tempconv.py`
- Tests: `/home/user/pdlc-skills/out/007-B1/tests/`
- Run command: `python out/007-B1/tempconv.py <value> <from_scale> <to_scale>` (paths from repo root)

## Critical Implementation Notes

### 1. Custom Rounding Logic (CRITICAL)
The specification requires **round half away from zero**, NOT Python's default banker's rounding:
- 0.25 → 0.3 (not 0.2)
- 2.5 → 3 (not 2)
- -2.5 → -3 (not -2)

Python's built-in `round()` uses banker's rounding, so you must implement custom rounding.

### 2. Decimal Place Preservation
Match the input's decimal places in the output:
- `32` (integer) → 1 decimal place (e.g., `0.0`)
- `32.5` (1 place) → 1 decimal place (e.g., `212.9`)
- `32.50` (2 places) → 2 decimal places (e.g., `0.28`)

Count decimal places by parsing the input string.

### 3. Case-Insensitive Scales
Scale arguments (C, F, K) are case-insensitive but must be normalized internally.

### 4. Error Handling
Exact error messages and exit codes are specified:
- Exit 1: Invalid number
- Exit 2: Invalid scale
- Exit 3: Below absolute zero
- Exit 4: Wrong number of arguments

## What You Need to Do

1. Write `/home/user/pdlc-skills/out/007-B1/tempconv.py` with full implementation
2. Create comprehensive tests in `/home/user/pdlc-skills/out/007-B1/tests/` using pytest
3. Run all tests to verify they pass
4. Send a message when done with location and test results

## Specification Clarifications
See `/home/user/pdlc-skills/runs/007/B1/spec-issues.md` for my detailed review of any ambiguities.

Once you complete the implementation and tests pass, I will validate that the behavior matches the specification.
