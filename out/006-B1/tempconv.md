# Temperature Converter Utility - Specification

## Overview

`tempconv` is a command-line utility for converting temperature values between three temperature scales:
- Celsius (C)
- Fahrenheit (F)
- Kelvin (K)

The utility accepts a temperature value and two scale identifiers, then outputs the converted result. It is designed to be scriptable with predictable output and exit codes.

## Command Syntax

```
tempconv <value> <from_scale> <to_scale>
```

### Arguments

- **value**: A numeric temperature value (integer or decimal number using `.` as decimal separator)
- **from_scale**: Source temperature scale (case-insensitive: C, F, or K)
- **to_scale**: Target temperature scale (case-insensitive: C, F, or K)

All arguments are positional and must be provided in the specified order.

## Input Validation

### Numeric Value
- Must be a valid number (integer or decimal)
- Decimal separator must be a period (`.`)
- Examples of valid input: `0`, `100`, `-40`, `32.5`, `-273.15`

### Temperature Scales
- Must be exactly one of: `C`, `F`, `K` (case-insensitive; `c`, `f`, `k` are also valid)

### Absolute Zero Constraints
The utility must validate that the input temperature is not below absolute zero in its respective scale:
- Celsius: minimum temperature is **-273.15°C**
- Fahrenheit: minimum temperature is **-459.67°F**
- Kelvin: minimum temperature is **0 K**

## Output Format

### Successful Conversion
- Output a single number (the converted temperature)
- No units, labels, or additional text
- Output to stdout

### Decimal Precision
- The output must preserve the same number of decimal places as the input value
- If the input is an integer with no decimal point (e.g., `32`), output with 1 decimal place (e.g., `0.0`)
- If the input has N decimal places, output with N decimal places
- Use standard rounding (round to nearest, with .5 rounding away from zero)

### Examples

| Input | Output (to Celsius) | Notes |
|-------|---------------------|-------|
| `32 F C` | `0.0` | Input integer → 1 decimal place |
| `32.0 F C` | `0.0` | Input has 1 decimal place → 1 decimal place |
| `32.50 F C` | `0.00` | Input has 2 decimal places → 2 decimal places |
| `100 C F` | `212.0` | Output precision matches input |
| `0 C K` | `273.2` | Rounded to 1 decimal place |

## Error Handling

All errors must be reported to **stderr** with the format:
```
Error: <description>
```

The program must not output the converted value when an error occurs.

### Error Cases and Exit Codes

| Situation | Exit Code | Error Message |
|-----------|-----------|---------------|
| Invalid argument count (not exactly 3 arguments) | 4 | `Error: Invalid number of arguments. Usage: tempconv <value> <from_scale> <to_scale>` |
| Value is not a valid number | 1 | `Error: Invalid number: <value>` |
| from_scale is not C, F, or K | 2 | `Error: Invalid scale: <scale>` |
| to_scale is not C, F, or K | 2 | `Error: Invalid scale: <scale>` |
| Temperature is below absolute zero in from_scale | 3 | `Error: Temperature <value> is below absolute zero for scale <scale>` |

Exit code 0 is used for successful conversion.

## Conversion Formulas

The utility must use the following formulas for temperature conversions:

- **C → F**: (C × 9/5) + 32
- **C → K**: C + 273.15
- **F → C**: (F - 32) × 5/9
- **F → K**: (F - 32) × 5/9 + 273.15
- **K → C**: K - 273.15
- **K → F**: (K - 273.15) × 9/5 + 32

## Usage Examples

### Successful Conversions

```bash
$ tempconv 0 C F
32.0

$ tempconv 100 C K
373.2

$ tempconv -40 C F
-40.0

$ tempconv 32.50 F C
0.28

$ tempconv 273.15 K C
0.0

$ tempconv 68.5 F K
293.4
```

### Error Cases

```bash
$ tempconv abc C F
Error: Invalid number: abc
[exit code: 1]

$ tempconv 0 X C
Error: Invalid scale: X
[exit code: 2]

$ tempconv -300 C F
Error: Temperature -300 is below absolute zero for scale C
[exit code: 3]

$ tempconv 100
Error: Invalid number of arguments. Usage: tempconv <value> <from_scale> <to_scale>
[exit code: 4]
```

## Implementation Notes

### Rounding Behavior
Implement standard rounding (round half away from zero). For example:
- 0.25 rounded to 1 decimal place = 0.2 (or 0.3 depending on implementation choice, but must be consistent)
- 0.35 rounded to 1 decimal place = 0.4
- This is to ensure that the precision-matching rule produces predictable results

### Negative Numbers
The utility must handle negative temperatures correctly. Input values like `-40` or `-273.15` are valid and should be processed normally (unless they violate absolute zero constraints).

### Case Sensitivity of Scales
Scale arguments (from_scale and to_scale) are case-insensitive. The following are all equivalent:
- `tempconv 0 C F` and `tempconv 0 c f` and `tempconv 0 C f`

### What Is Not Required

The following are implementation choices and are **not** required by this specification:
- Command-line help flag (`--help`)
- Handling of scientific notation (e.g., `1e3`)
- Support for special values (infinity, NaN)
- Whitespace trimming (treat arguments as provided)
- Color output or enhanced formatting
- Multiple conversions in a single invocation

---

**Specification Version**: 1.0  
**Date**: 2026-10-03  
**Status**: Ready for implementation
