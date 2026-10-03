# Specification: tempconv - Temperature Converter Utility

## Overview

`tempconv` is a command-line utility that converts temperature values between Celsius (C), Fahrenheit (F), and Kelvin (K) scales. It performs a single conversion per invocation and provides consistent, scriptable output with clear error reporting.

## Command Syntax

```
tempconv <value> <from-scale> <to-scale>
```

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `<value>` | number | The temperature value to convert. Can be an integer or decimal (e.g., 0, -40, 98.6, 273.15). |
| `<from-scale>` | char | Source temperature scale: `C`, `F`, or `K` (case-sensitive). |
| `<to-scale>` | char | Target temperature scale: `C`, `F`, or `K` (case-sensitive). |

## Supported Scales

- **C** — Celsius (useful range: typical weather -50 to +50°C)
- **F** — Fahrenheit (useful range: typical weather -58 to +122°F)
- **K** — Kelvin (absolute scale; valid only for values ≥ 0, representing absolute zero at 0K = -273.15°C)

## Conversion Formulas

All conversions are performed using these formulas:

| From → To | Formula |
|-----------|---------|
| C → F | F = (C × 9/5) + 32 |
| C → K | K = C + 273.15 |
| F → C | C = (F − 32) × 5/9 |
| F → K | K = (F − 32) × 5/9 + 273.15 |
| K → C | C = K − 273.15 |
| K → F | F = (K − 273.15) × 9/5 + 32 |

## Output Format

### Success (Exit Code 0)

On successful conversion, output a single line containing the result as a decimal number:

- **Precision**: The result is printed with **up to 2 decimal places**. Trailing zeros after the decimal point are removed, except trailing zeros after the first decimal place are kept for consistency.
  - Example outputs: `32` (not `32.00`), `98.6`, `0.5`, `273.15`
- **No extra text**: Only the number is printed to stdout. No units, labels, or confirmation messages.
- **Newline**: Output ends with a newline character.

### Error (Exit Code 1)

On validation failure, output an error message to stderr and exit with code 1:

Error messages follow this format:
```
Error: <reason>
```

Possible error reasons:
1. **Invalid value format**: "Value is not a valid number" (when the value cannot be parsed as a number)
2. **Invalid from-scale**: "Invalid scale 'X': must be C, F, or K" (when `<from-scale>` is not C, F, or K)
3. **Invalid to-scale**: "Invalid scale 'X': must be C, F, or K" (when `<to-scale>` is not C, F, or K)
4. **Absolute zero violation (input)**: "Temperature in Kelvin cannot be negative: <value>K" (when `<from-scale>` is K and value < 0)
5. **Absolute zero violation (output)**: "Conversion results in temperature below absolute zero: <result>K" (when the result in Kelvin < 0, regardless of input scale)

## Edge Cases and Notes

- **Self-conversion**: Converting a value to the same scale is valid and returns the input value (with output precision rules applied).
  - Example: `tempconv 0 C C` → `0`
- **Very large numbers**: Output is printed as-is with the precision rules. No scientific notation is used.
- **Negative temperatures**: Negative values are allowed in Celsius and Fahrenheit; they indicate sub-freezing temperatures.
- **Zero Kelvin (−273.15°C)**: Represents absolute zero. Conversions that result in negative Kelvin are an error.
  - Example: `tempconv -300 C K` should produce an error because -300°C = -26.85K (negative).

## Examples

### Successful Conversions

| Command | Output | Notes |
|---------|--------|-------|
| `tempconv 0 C F` | `32` | Freezing point of water |
| `tempconv 100 C F` | `212` | Boiling point of water |
| `tempconv 98.6 F C` | `37` | Human body temperature (rounded) |
| `tempconv 0 C K` | `273.15` | Freezing point in Kelvin |
| `tempconv 273.15 K C` | `0` | Freezing point from Kelvin |
| `tempconv -40 C F` | `-40` | Equal in both scales |
| `tempconv -40 F C` | `-40` | Equal in both scales |
| `tempconv 32 F K` | `273.15` | Freezing point via Fahrenheit |

### Error Cases

| Command | Exit | Error Message |
|---------|------|---------------|
| `tempconv abc C F` | 1 | `Error: Value is not a valid number` |
| `tempconv 0 X F` | 1 | `Error: Invalid scale 'X': must be C, F, or K` |
| `tempconv 0 C Z` | 1 | `Error: Invalid scale 'Z': must be C, F, or K` |
| `tempconv -1 K C` | 1 | `Error: Temperature in Kelvin cannot be negative: -1K` |
| `tempconv -300 C K` | 1 | `Error: Conversion results in temperature below absolute zero: -26.85K` |
| `tempconv 0 C` | 1 | (Missing required argument - implementation-specific error) |

## Implementation Notes

1. **Rounding and Precision**: Implementations may use standard floating-point rounding. When displaying results with the specified precision (up to 2 decimal places), round-half-up is acceptable.
2. **Floating-Point Accuracy**: Due to floating-point arithmetic, results may have minor rounding differences. Implementations should aim for accuracy to at least 2 decimal places for typical temperature ranges.
3. **Argument Validation**: Validate all three arguments before performing any conversion. Report the first validation error encountered.
4. **Case Sensitivity**: Scale letters are case-sensitive. `tempconv 0 c f` is invalid; must use capital letters.

## Test Cases

Implementations should pass the following test cases:

### Conversion Correctness Tests

1. `tempconv 0 C C` → `0` (exit 0)
2. `tempconv 0 C F` → `32` (exit 0)
3. `tempconv 32 F C` → `0` (exit 0)
4. `tempconv 0 C K` → `273.15` (exit 0)
5. `tempconv 273.15 K C` → `0` (exit 0)
6. `tempconv 98.6 F C` → `37` (exit 0)
7. `tempconv 37 C F` → `98.6` (exit 0)
8. `tempconv 100 C K` → `373.15` (exit 0)
9. `tempconv 373.15 K C` → `100` (exit 0)
10. `tempconv -40 C F` → `-40` (exit 0)
11. `tempconv -40 F C` → `-40` (exit 0)

### Boundary Tests

12. `tempconv -273.15 C K` → `0` (exit 0) — absolute zero
13. `tempconv -273.16 C K` → error (exit 1) — below absolute zero

### Error Handling Tests

14. `tempconv abc C F` → error (exit 1) — non-numeric value
15. `tempconv 0 X F` → error (exit 1) — invalid source scale
16. `tempconv 0 C Z` → error (exit 1) — invalid target scale
17. `tempconv -1 K C` → error (exit 1) — negative Kelvin input
18. `tempconv 0 c f` → error (exit 1) — lowercase scales (if case-sensitivity enforced)

## Exit Codes

- **Exit code 0**: Conversion succeeded; valid result printed to stdout.
- **Exit code 1**: Validation error or invalid input; error message printed to stderr.

## Future Considerations

- Additional scales (Rankine, Réaumur) could be added by extending the scale validation and formula set.
- Batch conversion (multiple values in one invocation) could be added with a different flag syntax.
- Precision control via command-line flags (e.g., `--precision 4`) is not required for the initial version.
