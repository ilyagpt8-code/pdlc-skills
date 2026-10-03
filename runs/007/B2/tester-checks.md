# Test Cases for tempconv (Version 1)

## Overview
Comprehensive test cases derived from specification in `out/006-B2/tempconv.md`.
Tests cover: conversions, boundaries, invalid inputs, exit codes, output format, case sensitivity.
Target: 20-30 cases

---

## Test Cases

### Basic Conversions (All Scale Pairs)

**№1** `0 C F` → Expected: `32` (exit 0)
- Basic Celsius to Fahrenheit conversion at water freezing point

**№2** `100 C F` → Expected: `212` (exit 0)
- Celsius to Fahrenheit at water boiling point

**№3** `32 F C` → Expected: `0` (exit 0)
- Fahrenheit to Celsius at water freezing point

**№4** `212 F C` → Expected: `100` (exit 0)
- Fahrenheit to Celsius at water boiling point

**№5** `0 C K` → Expected: `273.15` (exit 0)
- Celsius to Kelvin at water freezing point

**№6** `273.15 K C` → Expected: `0` (exit 0)
- Kelvin to Celsius at water freezing point

**№7** `273.15 K F` → Expected: `32` (exit 0)
- Kelvin to Fahrenheit at water freezing point

**№8** `32 F K` → Expected: `273.15` (exit 0)
- Fahrenheit to Kelvin at water freezing point

**№9** `25 C F` → Expected: `77` (exit 0)
- Room temperature conversion C to F

**№10** `20 C K` → Expected: `293.15` (exit 0)
- Room temperature conversion C to K

### Boundary Cases - Absolute Zero

**№11** `0 K C` → Expected: `-273.15` (exit 0)
- Absolute zero in Kelvin to Celsius

**№12** `-273.15 C K` → Expected: `0` (exit 0)
- Absolute zero in Celsius to Kelvin

**№13** `-459.67 F K` → Expected: `0` (exit 0)
- Absolute zero in Fahrenheit to Kelvin

**№14** `0 K F` → Expected: `-459.67` (exit 0)
- Absolute zero in Kelvin to Fahrenheit

### Boundary Cases - Just Below Absolute Zero (Should Fail)

**№15** `-273.16 C K` → Expected: Error stderr `Error: temperature below absolute zero`, exit 3
- Temperature below absolute zero by 0.01°C

**№16** `-1 K C` → Expected: Error stderr `Error: temperature below absolute zero`, exit 3
- Negative Kelvin input

**№17** `-459.68 F K` → Expected: Error stderr `Error: temperature below absolute zero`, exit 3
- Temperature below absolute zero by 0.01°F

**№18** `-274 C K` → Expected: Error stderr `Error: temperature below absolute zero`, exit 3
- Temperature significantly below absolute zero

### Same-Scale Conversion

**№19** `25 C C` → Expected: `25` (exit 0)
- Same scale C to C

**№20** `100 F F` → Expected: `100` (exit 0)
- Same scale F to F

**№21** `300 K K` → Expected: `300` (exit 0)
- Same scale K to K

### Invalid Arguments - Wrong Count

**№22** `python tempconv.py 0` → Expected: Error stderr `Error: invalid arguments`, exit 4
- Only value provided, no scales

**№23** `python tempconv.py` → Expected: Error stderr `Error: invalid arguments`, exit 4
- No arguments

**№24** `python tempconv.py 0 C F extra` → Expected: Error stderr `Error: invalid arguments`, exit 4
- Too many arguments (4 instead of 3)

**№25** `python tempconv.py 0 C` → Expected: Error stderr `Error: invalid arguments`, exit 4
- Missing target scale

### Invalid Input Value (Not a Number)

**№26** `abc C F` → Expected: Error stderr `Error: invalid value`, exit 1
- Non-numeric value

**№27** `12.34.56 C F` → Expected: Error stderr `Error: invalid value`, exit 1
- Multiple decimal points

**№28** `C F` → Expected: Error stderr `Error: invalid arguments`, exit 4
- Scale name as value

**№29** `1e100 C K` → Expected: Check if scientific notation is accepted or `Error: invalid value`, exit 1
- Scientific notation (ambiguous in spec)

### Invalid Scale Names

**№30** `0 X F` → Expected: Error stderr `Error: invalid scale`, exit 2
- Unknown scale 'X'

**№31** `0 C X` → Expected: Error stderr `Error: invalid scale`, exit 2
- Unknown target scale 'X'

**№32** `0 CC F` → Expected: Error stderr `Error: invalid scale`, exit 2
- Double scale letter

**№33** `0 c f` → Expected: `32` (exit 0)
- Case-insensitive lowercase scales

**№34** `0 C f` → Expected: `32` (exit 0)
- Case-insensitive mixed case scales

### Output Format and Precision

**№35** `0.5 C F` → Expected: `32.9` (exit 0)
- Decimal result (0.5°C = 32.9°F)
- Check rounding at x.x5 boundary

**№36** `1.5 C K` → Expected: `274.65` (exit 0)
- Kelvin decimal output maintains precision

**№37** `98.6 F C` → Expected: `37` (exit 0)
- Result that may round to integer

### Negative Input Values

**№38** `-40 C F` → Expected: `-40` (exit 0)
- Negative value (valid, above absolute zero)
- Special case: -40°C = -40°F

**№39** `-200 C K` → Expected: `73.15` (exit 0)
- Negative Celsius still converts (above absolute zero)

**№40** `-10 K C` → Expected: Error stderr `Error: temperature below absolute zero`, exit 3
- Negative Kelvin must be caught

### Additional Edge Cases

**№41** `0 F C` → Expected: `-17.777...` or rounded value (exit 0)
- Verify rounding strategy for repeating decimals

**№42** `273.15 K K` → Expected: `273.15` (exit 0)
- Same-scale with Kelvin decimal

---

## Statistics
- Total cases: 42
- Conversion tests: 10 (basic pairs)
- Boundary tests: 8 (absolute zero)
- Invalid argument tests: 5
- Invalid value tests: 3
- Invalid scale tests: 5
- Same-scale tests: 3
- Edge cases (format, precision, negatives): 7
- Special cases: 1

## Notes for Implementation Checking
1. Verify exit codes are exactly as specified (0, 1, 2, 3, 4)
2. Verify error messages are exactly as specified (stderr output)
3. Check output precision: spec says "at least 2 decimal places for Kelvin" and "rounded appropriately for user readability"
4. Trailing zeros may be omitted, but at least 2 decimal places for some outputs
5. Case insensitivity of scales is required
6. Program must not crash with traceback on any input
7. Order of checks: arguments → value parsing → scale validation → absolute zero check
