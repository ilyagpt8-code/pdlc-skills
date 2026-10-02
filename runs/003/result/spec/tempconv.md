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

- **Success**: Output the converted temperature to stdout as a decimal number with exactly 2 decimal places
- **Error**: Output error message to stderr
- **No output on error**: Only the message goes to stderr; nothing to stdout

### Output Examples

- `32.00` (normal conversion result)
- `0.00` (zero, always normalized without minus sign)
- `1000000.00` (very large number, always with 2 decimal places, never scientific notation)
- `0.00` (very small number like 1e-10, always exactly 2 decimal places)

### Output Format Details

- Output precision: always exactly 2 decimal places, even for very large or very small numbers
- Negative zero (-0.00) is normalized to `0.00` (without minus sign)
- Examples: `1000000.00`, `0.00`, `-273.15`
- No scientific notation in output (always standard decimal format)

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

Same-scale conversions (e.g., C to C) should return the input value in the standard output format (exactly 2 decimal places). For example, if input is `0.001 C C`, the output should be `0.00` (rounded to 2 decimal places).

## Special Cases and Notes

### Argument Parsing

- Whitespace around VALUE is trimmed before parsing
- Exact positioning: first argument is VALUE, second is FROM, third is TO
- No flag-based syntax (no `--from`, `--to`, etc.)

### Precision and Rounding

- Output precision: 2 decimal places using round-half-up method (standard rounding: 0.5 and above rounds away from zero)
- Examples of rounding: 32.125°F → 32.13 (round up), 32.124°F → 32.12 (round down), 32.115°F → 32.12 (round up)
- Intermediate calculations should maintain precision (use double-precision floating-point or equivalent)

### Error Behavior

- Errors are printed to stderr
- Only one error is reported per invocation
- Error checking order (report first error encountered):
  1. Argument count (must be exactly 3)
  2. VALUE numeric format (must be parseable as a number)
  3. Scale codes (FROM and TO must be in {C, F, K})
  4. Absolute zero constraint (VALUE must not be below minimum for its scale)

### Absolute Zero Validation

The absolute zero constraint is checked after understanding which scale the input uses (FROM scale). The utility must reject inputs that fall below the absolute zero minimum for their scale.

**Validation rule**: Input temperature must not be below the minimum for its scale:
- Celsius: must be ≥ -273.15
- Fahrenheit: must be ≥ -459.67
- Kelvin: must be ≥ 0

**Floating-point tolerance**: Floating-point representation errors within ±1e-9 of the boundary are acceptable. This allows boundary values like -273.15°C to be accepted even if floating-point arithmetic produces -273.1500000001.

**Examples**:
- `-273.15` C → Accepted (exactly at boundary)
- `-273.1500000001` C → Accepted (within ±1e-9 tolerance)
- `-273.16` C → Rejected (clearly below minimum)
- `-459.67` F → Accepted (exactly at boundary)
- `0` K → Accepted (exactly at boundary)

## Implementation Notes

These details are left to the implementation team:

- Choice of programming language
- Arithmetic precision handling (IEEE 754 double vs. other methods)
- Error message formatting variations (exact wording, capitalization, etc.)
- Argument parsing method (getopt, manual parsing, etc.)
- Handling of trailing/leading whitespace in scale codes (may trim or reject)

## Testing Expectations

Implementations should include tests covering:

- Standard conversions between all scale pairs
- Edge cases at absolute zero for each scale
- Invalid inputs (non-numeric, unknown scales, out-of-range values)
- Argument count errors
- Precision and rounding of results
