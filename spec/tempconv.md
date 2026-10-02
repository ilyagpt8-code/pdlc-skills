# Specification: tempconv — Temperature Converter Utility

## Overview

`tempconv` is a command-line utility that converts temperature values between three temperature scales: Celsius (C), Fahrenheit (F), and Kelvin (K). The utility reads a temperature value in one scale and outputs its equivalent in another scale with consistent formatting.

## Command Syntax

```
tempconv <VALUE> <FROM> <TO>
```

### Arguments

- **VALUE**: A numeric temperature value (integer, decimal, or scientific notation)
- **FROM**: Source temperature scale code (C, F, or K)
- **TO**: Target temperature scale code (C, F, or K)

### Examples

```bash
tempconv 0 C F        # Output: 32.00
tempconv 32 F C       # Output: 0.00
tempconv 100 C K      # Output: 373.15
tempconv 25 C C       # Output: 25.00
```

## Supported Temperature Scales

| Code | Name | Description |
|------|------|-------------|
| C | Celsius | Standard metric temperature scale |
| F | Fahrenheit | Temperature scale used primarily in the United States |
| K | Kelvin | Absolute temperature scale used in science |

## Input Validation

### VALUE (Numeric Input)

- **Format**: Must be a valid number (integer or decimal)
- **Scientific notation**: Supported (e.g., `1e-5`, `1.5e2`)
- **Whitespace**: Leading and trailing whitespace is ignored
- **Invalid cases**:
  - Non-numeric input → Error (see Error Handling section)
  - Missing or empty value → Error

### FROM and TO (Scale Codes)

- **Valid values**: Must be exactly one of: `C`, `F`, `K`
- **Case sensitivity**: Only uppercase letters are recognized (lowercase `c`, `f`, `k` are invalid)
- **Whitespace**: Leading and trailing whitespace around the scale codes is ignored (e.g., ` C ` is treated as `C`)
- **Invalid cases**:
  - Unknown scale code (e.g., `R`, `X`) → Error
  - Missing or empty scale → Error
  - Scale code with embedded whitespace (e.g., `C C`) → Error

### Absolute Zero Validation

The utility must reject temperatures below the absolute zero for the source scale:

| Scale | Absolute Zero | Validation |
|-------|---------------|------------|
| Celsius | −273.15°C | Input must satisfy: VALUE ≥ −273.15 |
| Fahrenheit | −459.67°F | Input must satisfy: VALUE ≥ −459.67 |
| Kelvin | 0 K | Input must satisfy: VALUE ≥ 0 |

**Validation rule**: If the input VALUE is strictly less than the absolute zero threshold for the FROM scale, the utility must reject it with error code 3. Values exactly at the threshold (e.g., −273.15 for Celsius) are valid. Values above the threshold (even by a tiny amount like −273.149°C) are valid. The boundaries are strict numeric comparisons, not tolerances.

## Output Format

### Success Output

- **Target**: stdout
- **Format**: Decimal number with exactly 2 digits after the decimal point
- **Examples**: `32.00`, `0.00`, `373.15`, `25.00`
- **No additional text**: Only the numeric value is printed

### Error Output

- **Target**: stderr
- **Format**: Error message (see Error Handling section)
- **Exit code**: Non-zero (see Error Handling section)

## Error Handling

The utility must handle errors with appropriate exit codes and messages to stderr.

### Error Messages Format

Error messages must be printed to stderr exactly as specified in the table below. The format is fixed:
- Messages starting with "Error:" must use uppercase `E` and followed by a colon and space
- The message text must match exactly (case-sensitive)
- Each error message is terminated with a newline character

| Situation | Exit Code | stderr Message (exact) |
|-----------|-----------|------------------------|
| Incorrect number of arguments | 1 | `Usage: tempconv <value> <from> <to>` |
| Invalid number (not a valid numeric format) | 1 | `Error: invalid number` |
| Invalid scale code (not C, F, or K) | 2 | `Error: invalid scale` |
| Temperature below absolute zero | 3 | `Error: temperature below absolute zero` |
| Success | 0 | (no output to stderr) |

## Conversion Formulas

The utility must use the following standard conversion formulas:

### Celsius as Reference

- **C → F**: `(C × 9/5) + 32`
- **C → K**: `C + 273.15`

### From Fahrenheit

- **F → C**: `(F − 32) × 5/9`
- **F → K**: `((F − 32) × 5/9) + 273.15`

### From Kelvin

- **K → C**: `K − 273.15`
- **K → F**: `(K − 273.15) × 9/5 + 32`

### Same-Scale Conversion

- **Same scale**: Return the input value formatted with 2 decimal places (e.g., `tempconv 25 C C` outputs `25.00`)

## Edge Cases and Special Behavior

### Absolute Zero at Boundaries

- `tempconv -273.15 C F` must output `−459.67` (absolute zero in Fahrenheit)
- `tempconv 0 K C` must output `−273.15` (absolute zero in Celsius)
- `tempconv -459.67 F K` must output `0.00` (absolute zero in Kelvin)

### Precision and Rounding

- All calculations must use standard floating-point arithmetic
- Output must be rounded (not truncated) to exactly 2 decimal places
- **Rounding method**: Use standard round-half-up (round half away from zero). Examples:
  - 32.124 → 32.12 (rounds down)
  - 32.125 → 32.13 (rounds up, halfway case)
  - 32.126 → 32.13 (rounds up)
  - −32.125 → −32.13 (rounds away from zero for negative numbers)

### Numeric Precision Limits

- Implementation team decides acceptable precision and floating-point error tolerance
- Expected: results should match standard formulas within reasonable floating-point precision

### Boundary Cases Near Absolute Zero

- Values exactly at the absolute zero boundary are valid (e.g., −273.15°C, −459.67°F, 0 K)
- Values above the absolute zero boundary are valid, even by tiny amounts (e.g., −273.149°C, −273.14999°C)
- Values below the absolute zero boundary must be rejected with error code 3
- Example: `tempconv -273.151 C F` should reject with error code 3, but `tempconv -273.149 C F` should succeed

## Usage Context

This utility is designed for:
- Interactive command-line use for quick temperature conversions
- Integration into shell scripts that need temperature conversion functionality
- Reliable output format and exit codes for programmatic parsing

## Implementation Notes (Not Specified Here)

The following decisions are left to the implementation team:

- **Programming language**: Any language that can build a standalone CLI tool
- **Argument parsing**: Implementation approach (manual parsing, getopt, command-line library, etc.)
- **Floating-point precision**: How to achieve round-half-up behavior in the chosen language (standard library functions, custom rounding logic, etc.)
- **Additional features**: Whether to support options like `--help`, `--version`, or alternative input formats (not required by this spec)

## Testing Expectations

Tests should verify:

1. **Correct conversions** between all scale pairs
2. **Proper error handling** for invalid input across all error categories
3. **Consistent output format** (always 2 decimal places)
4. **Correct exit codes** for all error scenarios
5. **Boundary behavior** at absolute zero values
6. **Argument parsing** (valid and invalid argument counts)
