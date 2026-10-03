# Specification: tempconv — Temperature Converter Utility

## Overview

`tempconv` is a command-line utility that converts temperature values between three temperature scales: Celsius (C), Fahrenheit (F), and Kelvin (K). The utility accepts a temperature value and source scale as input, optionally specifies a target scale, and outputs the converted value. If no target scale is specified, the utility outputs conversions to all other scales.

## Command Syntax

```
tempconv <value> <from_scale> [to_scale]
```

### Arguments

- `<value>`: A floating-point number representing the temperature value to convert. Must be a valid number (integers and decimals are accepted).
- `<from_scale>`: The source temperature scale. Must be one of: `C`, `F`, or `K` (case-insensitive).
- `[to_scale]`: (Optional) The target temperature scale. Must be one of: `C`, `F`, or `K` (case-insensitive). If omitted, the utility outputs conversions to all scales except the source scale.

## Temperature Scales and Formulas

### Supported Scales

- **Celsius (C)**: Base metric scale used in SI units
- **Fahrenheit (F)**: Scale commonly used in USA
- **Kelvin (K)**: Absolute temperature scale used in physics

### Conversion Formulas

All conversions should use these formulas:

#### From Celsius to other scales:
- **C to F**: `F = (C × 9/5) + 32`
- **C to K**: `K = C + 273.15`

#### From Fahrenheit to other scales:
- **F to C**: `C = (F - 32) × 5/9`
- **F to K**: `K = (F - 32) × 5/9 + 273.15`

#### From Kelvin to other scales:
- **K to C**: `C = K - 273.15`
- **K to F**: `F = (K - 273.15) × 9/5 + 32`

### Special Temperature Points

- **Absolute Zero**: 0 K = -273.15 C = -459.67 F
- **Water Freezing Point**: 273.15 K = 0 C = 32 F
- **Water Boiling Point**: 373.15 K = 100 C = 212 F

## Input Validation

The utility must validate all inputs and respond with appropriate error messages and exit codes.

### Valid Input Rules

1. **Value**: Must be a valid floating-point number
   - Scientific notation (e.g., `1e-3`, `-2.5e2`) is acceptable
   - Negative values are acceptable for C and F, but only non-negative for K

2. **Scale**: Must be exactly one of `C`, `F`, or `K`
   - Case-insensitive (both `C` and `c` are valid)
   - No other values are accepted

3. **Physical Constraints**:
   - For Kelvin: value must be >= 0 (cannot be below absolute zero)
   - For Celsius: value must be >= -273.15 (cannot be below absolute zero)
   - For Fahrenheit: value must be >= -459.67 (cannot be below absolute zero)

### Invalid Input Handling

When the utility encounters invalid input, it must:
1. Print an error message to stderr
2. Exit with a specific exit code
3. Not output a conversion result

## Output Format

### Successful Conversion

When conversion succeeds, output format depends on whether a target scale was specified:

#### Single target scale specified:
```
<result_value> <target_scale>
```

Example: `86 F` or `30.0 C`

#### No target scale specified (all conversions):
Output conversions to all scales except the input scale, one per line, in this order: C, F, K.
```
<value> C
<value> F
<value> K
```

Example output for input "0 C":
```
32 F
273.15 K
```

### Output Value Formatting

- Values should be displayed with sufficient precision to represent the conversion accurately
- Trailing zeros after the decimal point may be omitted (i.e., both `32.0` and `32` are acceptable for 32 F)
- Rounding to 2 decimal places is recommended for human readability, but not required
- Scientific notation is acceptable for very large or very small values

### Error Messages to Stderr

Error messages should be clear and concise. Suggested format:

```
Error: <description>
```

Examples:
- `Error: Invalid temperature value 'abc': not a number`
- `Error: Unknown temperature scale 'R': must be C, F, or K`
- `Error: Temperature -500 C is below absolute zero (-273.15 C)`
- `Error: Missing required argument: temperature value`
- `Error: Too many arguments`

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success: conversion completed and output produced |
| 1 | Usage error: missing arguments, too many arguments, or invalid syntax |
| 2 | Invalid input: temperature value is not a valid number, or scale is unrecognized |
| 3 | Validation error: temperature is below absolute zero for the given scale |

## Usage Examples

### Converting Celsius to Fahrenheit
```
$ tempconv 0 C F
32 F
```

### Converting with no target scale specified
```
$ tempconv 100 C
32 F
273.15 K
```

### Converting Kelvin to Celsius
```
$ tempconv 298.15 K C
25 C
```

### Converting Fahrenheit to multiple scales
```
$ tempconv 212 F
100 C
373.15 K
```

### Error: invalid number
```
$ tempconv abc F C
Error: Invalid temperature value 'abc': not a number
$ echo $?
2
```

### Error: unknown scale
```
$ tempconv 100 Celsius F
Error: Unknown temperature scale 'Celsius': must be C, F, or K
$ echo $?
2
```

### Error: below absolute zero
```
$ tempconv -300 C F
Error: Temperature -300 C is below absolute zero (-273.15 C)
$ echo $?
3
```

### Error: missing argument
```
$ tempconv 100
Error: Missing required argument: target scale (or use 'C', 'F', 'K')
$ echo $?
1
```

## Additional Constraints and Notes

1. **Precision**: For physical validity, Kelvin temperatures must never result in values below 0. The absolute zero boundary (−273.15 °C, −459.67 °F, 0 K) must be enforced during validation.

2. **Rounding**: The implementation may round to any reasonable precision (e.g., 2-15 decimal places). Consistency in rounding approach is more important than a specific number of decimal places.

3. **Case Sensitivity**: Temperature scale inputs must be case-insensitive (C, c, F, f, K, k are all acceptable).

4. **Leading/Trailing Whitespace**: The implementation should handle reasonable whitespace in arguments gracefully.

5. **Large Numbers**: The utility should handle large temperature values that may be represented in scientific notation.

6. **Language**: All output (error messages, scale labels) should be in English.

## Testing Considerations

The implementation should pass tests covering:
- Valid conversions in both directions
- All three scales to all three scales
- Round-trip conversions (verify that converting back yields approximately the original value)
- Boundary conditions (absolute zero, very large numbers)
- Invalid scale names
- Non-numeric inputs
- Missing arguments
- Extra arguments
- Temperatures below absolute zero
- Floating-point precision edge cases

## Notes for Implementer

- This specification describes the functional requirements and behavior
- The choice of programming language, internal architecture, and performance optimizations are left to the implementation team
- Error messages may be worded differently as long as they convey the same information and result in the correct exit code
- The exact number of decimal places in output may vary, but conversions should be mathematically correct to at least 2 decimal places
