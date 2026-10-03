# Specification Issues and Resolutions

## Issue 1: Decimal precision and trailing zeros contradiction

**Problem**: Specification says "at least 2 decimal places for Kelvin" but also says "Trailing zeros after decimal point may be omitted for cleaner output". These seem contradictory.

Example: When converting 0 C to K, result is 273.15 (OK). But 100 C to K gives 373.15 (OK). However, 273 C to K gives 546.15 (OK). What about a value that becomes 373.0 K?

**Resolution**: 
- Interpret "at least 2 decimal places for Kelvin" as "sufficient precision to display at least 2 meaningful decimal places when the conversion produces them"
- If the result naturally has fewer significant decimals (like 273.0), trailing zeros may be omitted
- For Celsius and Fahrenheit, show appropriate precision (at least 1 decimal place for readability)
- General rule: show results with reasonable precision, minimum 2 decimals for precision-critical conversions, but omit unnecessary trailing zeros

## Issue 2: "Reasonably accurate to 2 decimal places"

**Problem**: Unclear if this means "round all outputs to 2 decimal places" or "maintain accuracy such that result is valid to 2 decimals"

**Resolution**: Interpret as "maintain sufficient precision in calculations such that results are accurate when shown to 2 decimal places". This allows for naturally higher precision when appropriate.

## Decision on output format:
- Python's default float formatting (str() or f-string with minimal decimals) will be used
- For cleaner output: use round() strategically or format to remove trailing zeros
- Example implementations:
  - 32.0 → "32" or "32.0" (context-dependent, but omit trailing .0 for whole numbers)
  - 373.15 → "373.15"
  - 0.0 → "0"
