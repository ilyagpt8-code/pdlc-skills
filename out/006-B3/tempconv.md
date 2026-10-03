# tempconv — Temperature Converter Utility Specification

## Overview
`tempconv` is a command-line utility that converts temperature values between three temperature scales: Celsius (C), Fahrenheit (F), and Kelvin (K). It is designed to be simple, fast, and suitable for both interactive use and integration into shell scripts.

## Command Syntax

```
tempconv <value> <from_unit> <to_unit>
```

### Arguments
- `<value>`: A numeric temperature value (integer or floating-point). Must be parseable as a number.
- `<from_unit>`: The source temperature unit. Must be one of: **C**, **F**, **K** (case-insensitive).
- `<to_unit>`: The target temperature unit. Must be one of: **C**, **F**, **K** (case-insensitive).

### Examples
```bash
tempconv 0 C F        # Converts 0°C to Fahrenheit → outputs: 32
tempconv 32 F C       # Converts 32°F to Celsius → outputs: 0
tempconv 273.15 C K   # Converts 273.15°C to Kelvin → outputs: 546.3
tempconv 0 K C        # Converts 0 K to Celsius → outputs: -273.15
```

## Conversion Formulas

The utility must implement these conversion formulas:

### Celsius ↔ Fahrenheit
- C to F: `F = C × (9/5) + 32`
- F to C: `C = (F - 32) × (5/9)`

### Celsius ↔ Kelvin
- C to K: `K = C + 273.15`
- K to C: `C = K - 273.15`

### Fahrenheit ↔ Kelvin
- F to K: `K = (F - 32) × (5/9) + 273.15` or equivalently `K = C_temp + 273.15` where `C_temp = (F - 32) × (5/9)`
- K to F: `F = (K - 273.15) × (9/5) + 32` or equivalently `F = C_temp × (9/5) + 32` where `C_temp = K - 273.15`

## Output Format

### Success Case
- Output a single number (the converted temperature) followed by a newline.
- The number may be an integer or floating-point value.
- No additional text, labels, or units in the output.
- Precision: Implementation may choose appropriate decimal precision and rounding method (e.g., nearest integer, 2 decimal places). This is an implementation detail.

Example output:
```
32
0
273.15
```

### Edge Cases for Output
- **Same-unit conversion** (e.g., `tempconv 25 C C`): Treat as valid; convert the value to the target unit (which is the same as the source). Should output `25` (or equivalent after rounding).
- **Zero values**: Must be handled correctly. E.g., `tempconv 0 C K` should output `273.15`.

## Error Handling

The utility must detect and report the following error conditions. Each error condition has a specific exit code.

### Error: Non-Numeric Input
- **Condition**: The `<value>` argument cannot be parsed as a valid number.
- **Example**: `tempconv abc C F`
- **Behavior**: Print an error message to stderr explaining that the value is not a valid number.
- **Exit Code**: 1

### Error: Unknown Unit
- **Condition**: The `<from_unit>` or `<to_unit>` is not one of the recognized units (C, F, K).
- **Example**: `tempconv 100 X F` or `tempconv 100 C Q`
- **Behavior**: Print an error message to stderr explaining that the unit is unrecognized. The message should indicate which unit(s) are valid.
- **Exit Code**: 2

### Error: Temperature Below Absolute Zero
- **Condition**: The input temperature is below the absolute zero threshold for any temperature scale:
  - **Kelvin**: K < 0
  - **Celsius**: C < -273.15
  - **Fahrenheit**: F < -459.67
- **Example**: `tempconv -300 C K` (because -300°C is below absolute zero)
- **Behavior**: Print an error message to stderr explaining that the temperature is below absolute zero.
- **Exit Code**: 3
- **Note**: This check applies to the **input** value only. If the input is valid but would convert to below absolute zero (which is mathematically impossible with valid conversion formulas), the utility does not need to check the output.

### Error: Missing or Excess Arguments
- **Condition**: The utility is invoked with fewer than 3 positional arguments or more than 3 positional arguments.
- **Example**: `tempconv 100 C` (missing target unit) or `tempconv 100 C F extra` (excess arguments)
- **Behavior**: Print a usage/help message to stderr showing the correct command syntax.
- **Exit Code**: 1

### Success
- **Condition**: All arguments are valid and no error conditions are met.
- **Exit Code**: 0

## Error Message Guidelines

Error messages should be:
- **Clear and informative**: Explain what went wrong, not just the error code.
- **Concise**: No unnecessary verbosity.
- **Actionable**: When possible, suggest the correct format.

Example error messages:
- `Error: invalid numeric value 'abc'`
- `Error: unknown unit 'X'; valid units are C, F, K`
- `Error: temperature -300 C is below absolute zero (minimum -273.15 C)`
- `Usage: tempconv <value> <from_unit> <to_unit>`

## Absolute Zero Reference Values

For boundary validation:
- **Kelvin**: 0 K is absolute zero
- **Celsius**: -273.15 °C is absolute zero
- **Fahrenheit**: -459.67 °F is absolute zero

Any input temperature at or above these values is considered valid.

## Precision and Rounding

The specification does **not** mandate specific decimal precision or rounding behavior. The implementing team may choose:
- Decimal precision (e.g., nearest integer, 2 decimal places, full floating-point precision)
- Rounding method (e.g., round-to-nearest, truncate, floor, ceil)

**Constraint**: The behavior must be consistent and documented. The chosen precision must not introduce errors larger than 0.01 degrees in any scale for typical conversions.

## Implementation Notes

1. **Unit case-insensitivity**: All unit comparisons must be case-insensitive. `c`, `C`, `celsius` (if supported), and `CELSIUS` should be treated equivalently.
2. **Floating-point arithmetic**: Use standard floating-point arithmetic. Be aware of typical precision limitations.
3. **No whitespace trimming required**: The specification does not require the utility to trim leading/trailing whitespace from arguments, though implementations may do so.
4. **No interactive mode**: The utility is command-line only; no interactive prompts or REPL.
5. **Localization**: Output should use the period (.) as the decimal separator, not locale-specific separators (e.g., comma in some European locales).

## Testing Considerations

Implementers should test:
1. All six conversion paths (C→F, F→C, C→K, K→C, F→K, K→F)
2. Edge cases: values at absolute zero, values just above absolute zero
3. Common reference points (water's freezing/boiling points, room temperature, etc.)
4. Each error condition individually
5. Same-unit conversions
6. Negative temperatures (when valid)
7. Large and small values
8. Floating-point precision edge cases

## Example Test Cases

| Command | Expected Output | Exit Code | Notes |
|---------|-----------------|-----------|-------|
| `tempconv 0 C F` | `32` | 0 | Water freezing point |
| `tempconv 100 C F` | `212` | 0 | Water boiling point |
| `tempconv 32 F C` | `0` | 0 | Reverse of freezing |
| `tempconv 0 C K` | `273.15` | 0 | Freezing point in Kelvin |
| `tempconv 25 C C` | `25` | 0 | Same-unit conversion |
| `tempconv -273.15 C K` | `0` | 0 | Absolute zero |
| `tempconv -300 C K` | Error message | 3 | Below absolute zero |
| `tempconv abc C F` | Error message | 1 | Non-numeric input |
| `tempconv 100 X F` | Error message | 2 | Unknown unit |
| `tempconv 100 C` | Usage message | 1 | Missing argument |

## Scope and Future Enhancements

This specification covers the core functionality. The following features are **out of scope** for the initial release:
- Long-form unit names (e.g., `--from Celsius --to Fahrenheit`)
- Batch conversion or multiple conversions in one invocation
- Reading from stdin or files
- Output formatting options (e.g., significant figures, scientific notation)
- Additional temperature scales (Rankine, Reaumur, etc.)

These may be added in future versions without modifying the core behavior specified here.
