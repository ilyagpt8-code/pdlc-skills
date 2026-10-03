# Temperature Converter Utility Specification

## Overview
`tempconv` is a command-line utility for converting temperature values between three scales: Celsius (C), Fahrenheit (F), and Kelvin (K).

## Command Syntax

```
tempconv <value> <from_scale> <to_scale>
```

### Arguments
- `<value>`: A numeric input (integer or decimal)
- `<from_scale>`: Source temperature scale: `C`, `F`, or `K`
- `<to_scale>`: Target temperature scale: `C`, `F`, or `K`

### Examples
```
tempconv 0 C F       → 32
tempconv 100 C K     → 373.15
tempconv 32 F C      → 0
```

## Output Format

### Success Case
- Print the converted temperature value to standard output
- Decimal output: show as much precision as reasonably available (at least 2 decimal places for Kelvin, rounded appropriately for user readability)
- Trailing zeros after decimal point may be omitted for cleaner output
- Exit with code **0**

### Error Cases

#### Invalid input value (not a number)
- Print to stderr: `Error: invalid value`
- Exit code: **1**

#### Invalid scale name
- Print to stderr: `Error: invalid scale`
- Exit code: **2**

#### Temperature below absolute zero (Kelvin)
Only temperatures at or above absolute zero (−273.15°C, 0 K, −459.67°F) are physically valid.
- If the input value, when converted to Kelvin, is negative:
  - Print to stderr: `Error: temperature below absolute zero`
  - Exit code: **3**

#### Wrong number of arguments
- Print to stderr: `Error: invalid arguments`
- Exit code: **4**

## Conversion Formulas

All conversions use the standard formulas:

### Celsius ↔ Fahrenheit
- C → F: `F = (C × 9/5) + 32`
- F → C: `C = (F − 32) × 5/9`

### Celsius ↔ Kelvin
- C → K: `K = C + 273.15`
- K → C: `C = K − 273.15`

### Fahrenheit ↔ Kelvin
- F → K: `K = (F − 32) × 5/9 + 273.15`
- K → F: `F = (K − 273.15) × 9/5 + 32`

## Absolute Zero Validation

The minimum valid temperature is **absolute zero**:
- **0 K** (Kelvin)
- **−273.15 °C** (Celsius)
- **−459.67 °F** (Fahrenheit)

Input values below these thresholds when interpreted in their native scale should trigger error code 3.

## Behavior Notes

1. **Case sensitivity**: Scale names (C, F, K) should be treated as **case-insensitive** (both `C` and `c` are accepted)
2. **Precision**: The utility should maintain sufficient precision in calculations. The exact rounding strategy is left to the implementer, but results should be reasonably accurate to 2 decimal places.
3. **Help and version**: Not required; focus on the core conversion functionality.
4. **Same-scale conversion**: If `from_scale` equals `to_scale`, the output is the input value unchanged (exit 0).

## Exit Codes Summary

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid value (not a number) |
| 2 | Invalid scale (not C, F, or K) |
| 3 | Temperature below absolute zero |
| 4 | Wrong number of arguments |

## Testing Expectations

Tests should verify:
- Basic conversions between all scale pairs
- Boundary cases (absolute zero in all scales)
- Invalid inputs (non-numeric values, unknown scales)
- Output precision and format consistency
- Correct exit codes for all error conditions
- Case-insensitive scale input
