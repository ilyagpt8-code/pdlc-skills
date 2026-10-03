# Expert to Executor: Specification Summary and Requirements

## Overview
Build a `tempconv` temperature converter utility that converts between Celsius (C), Fahrenheit (F), and Kelvin (K).

## Key Implementation Requirements

### Command Format
```
python out/007-A3/tempconv.py <value> <from_scale> [to_scale]
```

- `<value>`: floating-point number (accepts scientific notation like 1e-3, -2.5e2)
- `<from_scale>`: Required. C, F, or K (case-insensitive)
- `[to_scale]`: Optional. C, F, or K (case-insensitive)

### Conversion Formulas (Use Exactly As Specified)
- **C to F**: F = (C × 9/5) + 32
- **C to K**: K = C + 273.15
- **F to C**: C = (F - 32) × 5/9
- **F to K**: K = (F - 32) × 5/9 + 273.15
- **K to C**: C = K - 273.15
- **K to F**: F = (K - 273.15) × 9/5 + 32

### Output Behavior

**With target scale specified:**
```
<result_value> <target_scale>
```

**Without target scale (all conversions):**
Output all scales except source, in order: C, F, K (one per line)

Example: `tempconv 0 C` outputs:
```
32 F
273.15 K
```

### Physical Constraints (Absolute Zero Checks)
Must validate and reject temperatures below absolute zero:
- Kelvin: must be >= 0
- Celsius: must be >= -273.15
- Fahrenheit: must be >= -459.67

### Error Handling

Print error to stderr and exit with correct code (no conversion output):

| Exit Code | Condition |
|-----------|-----------|
| 0 | Success |
| 1 | Usage error (missing required args, too many args) |
| 2 | Invalid input (non-numeric value, unknown scale) |
| 3 | Validation error (below absolute zero) |

Error message format (suggested):
```
Error: <description>
```

### Output Value Formatting
- Precision: sufficient to represent conversion accurately
- Trailing zeros may be omitted (32.0 and 32 both acceptable)
- Rounding to 2 decimal places recommended but not required
- Scientific notation acceptable for very large/small values

### Specification Issues Found
See `runs/007/A3/spec-issues.md` for one identified issue in the examples (non-critical, spec logic is sound).

## Deliverables
- Code: `out/007-A3/tempconv.py`
- Tests: `out/007-A3/tests/` (pytest)
- Program must not crash on any input
- Paths are from repository root

## Notes
- Use Python 3 standard library only
- Make conversions mathematically correct to at least 2 decimal places
- Handle edge cases: large numbers, negative temps, float precision
- Ensure case-insensitivity for scale inputs
