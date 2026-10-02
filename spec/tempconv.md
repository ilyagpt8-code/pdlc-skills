# tempconv — Temperature Converter Utility

## Overview

`tempconv` is a command-line utility that converts temperature values between three temperature scales: Celsius (C), Fahrenheit (F), and Kelvin (K). It reads a temperature value and two scale identifiers, performs the conversion, and outputs the result.

## Command Syntax

```
tempconv <VALUE> <FROM> <TO>
```

Where:
- `<VALUE>` — Temperature value to convert (number)
- `<FROM>` — Source scale (one of: C, F, K)
- `<TO>` — Target scale (one of: C, F, K)

## Usage Examples

```bash
$ tempconv 0 C F
32.00

$ tempconv 32 F C
0.00

$ tempconv 273.15 K C
0.00

$ tempconv 100 C K
373.15

$ tempconv -40 C F
-40.00
```

## Supported Temperature Scales

| Scale | Code | Range |
|-------|------|-------|
| Celsius | C | ≥ -273.15 |
| Fahrenheit | F | ≥ -459.67 |
| Kelvin | K | ≥ 0 |

## Input Validation

### VALUE (Temperature Number)

- Must be a valid number (integer or decimal)
- Scientific notation is supported (e.g., `1e-5`, `2.5e2`)
- Whitespace around the number is trimmed
- Invalid formats result in error code 1

### FROM and TO (Temperature Scales)

- Must be one of: `C`, `F`, `K`
- Case-sensitive (only uppercase letters accepted)
- Invalid scales result in error code 2

### Absolute Zero Constraint

The utility must validate that input temperature does not fall below absolute zero for its scale:

- **Celsius**: Minimum -273.15°C
- **Fahrenheit**: Minimum -459.67°F
- **Kelvin**: Minimum 0 K

If the input temperature is below absolute zero after conversion to the source scale, return error code 3.

## Output Format

- **Success**: Output the converted temperature to stdout as a decimal number with 2 decimal places (default)
- **Error**: Output error message to stderr
- **No output on error**: Only the message goes to stderr; nothing to stdout

### Output Examples

- `32.00` (normal conversion result)
- `-273.15` (very cold temperature)
- `1.23e2` (if output uses scientific notation, though standard decimal is preferred)

## Exit Codes and Error Messages

| Scenario | Exit Code | stderr Message | Notes |
|----------|-----------|----------------|-------|
| Successful conversion | 0 | (no output) | Result printed to stdout |
| Invalid number format | 1 | `Error: invalid number` | VALUE is not a valid number |
| Invalid temperature scale | 2 | `Error: invalid scale` | FROM or TO is not C, F, or K |
| Temperature below absolute zero | 3 | `Error: temperature below absolute zero` | Input violates absolute zero constraint |
| Wrong number of arguments | 1 | `Usage: tempconv <value> <from> <to>` | Not exactly 3 arguments provided |

## Conversion Formulas

All conversions must use these standard formulas:

| From | To | Formula |
|------|----|---------| 
| C | F | `(C × 9/5) + 32` |
| F | C | `(F - 32) × 5/9` |
| C | K | `C + 273.15` |
| K | C | `K - 273.15` |
| F | K | `((F - 32) × 5/9) + 273.15` |
| K | F | `(K - 273.15) × 9/5 + 32` |

Same-scale conversions (e.g., C to C) should return the input value unchanged.

## Special Cases and Notes

### Argument Parsing

- Whitespace around VALUE is trimmed before parsing
- Exact positioning: first argument is VALUE, second is FROM, third is TO
- No flag-based syntax (no `--from`, `--to`, etc.)

### Precision

- Output precision: 2 decimal places by default
- Intermediate calculations should maintain precision (use double-precision floating-point or equivalent)
- Rounding follows standard rules (round to nearest, half away from zero, or implementation-defined for edge cases)

### Error Behavior

- Errors are printed to stderr
- Only one error is reported per invocation
- Error checking order: argument count → number format → scale validity → absolute zero constraint

### Absolute Zero Validation

The absolute zero constraint is checked after understanding which scale the input uses (FROM scale). The utility must reject inputs that, when converted to the FROM scale internally or conceptually, would violate the absolute zero limit.

Example: If a user provides `K -100 C`, the utility recognizes that -100 K is below absolute zero (Kelvin scale) and rejects it with error code 3.

## Implementation Notes

These details are left to the implementation team:

- Choice of programming language
- Arithmetic precision handling (IEEE 754 double vs. other methods)
- Exact boundary behavior for -273.15°C and -459.67°F
- Error message formatting variations
- Argument parsing method (getopt, manual parsing, etc.)
- Handling of trailing/leading whitespace in scales (should be accepted or rejected)
- Behavior with very large numbers or extreme scientific notation

## Testing Expectations

Implementations should include tests covering:

- Standard conversions between all scale pairs
- Edge cases at absolute zero for each scale
- Invalid inputs (non-numeric, unknown scales, out-of-range values)
- Argument count errors
- Precision and rounding of results
