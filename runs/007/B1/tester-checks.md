# Tester Checks for tempconv - Version 2

**Total cases**: 37  
**Created**: 2026-10-03  
**Updated**: 2026-10-03 (Round 2 - corrections to test expectations)

## Test Cases

### Basic Conversions (All Scale Pairs)
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 1 | `0 C F` | `32.0` | 0 | Basic C→F |
| 2 | `100 C F` | `212.0` | 0 | C→F |
| 3 | `100 C K` | `373.2` | 0 | C→K, rounding test |
| 4 | `-40 C F` | `-40.0` | 0 | Special point where C=F |
| 5 | `32 F C` | `0.0` | 0 | Basic F→C, integer input → 1 decimal |
| 6 | `32.0 F C` | `0.0` | 0 | F→C with 1 decimal input |
| 7 | `32.50 F C` | `0.28` | 0 | F→C with 2 decimal input, shows precision preservation |
| 8 | `273.15 K C` | `0.00` | 0 | K→C boundary (2 decimals in input) |
| 9 | `0 K F` | `-459.7` | 0 | K→F (integer input → 1 decimal rounding) |
| 10 | `68.5 F K` | `293.4` | 0 | F→K |

### Decimal Precision Preservation
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 11 | `0 C F` | `32.0` | 0 | No decimals in input → 1 decimal output |
| 12 | `0.0 C F` | `32.0` | 0 | 1 decimal in input → 1 decimal output |
| 13 | `0.00 C F` | `32.00` | 0 | 2 decimals in input → 2 decimals output |
| 14 | `100.5 C F` | `212.9` | 0 | 1 decimal preserved |
| 15 | `100.50 C F` | `212.90` | 0 | 2 decimals preserved |

### Rounding Tests (Round Half Away from Zero)
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 16 | `-0.25 C F` | `31.55` | 0 | Negative input, proper conversion |
| 17 | `0.5 C K` | `273.7` | 0 | Half rounding away from zero |
| 18 | `-2.5 C F` | `27.5` | 0 | Negative input conversion |

### Absolute Zero Validation
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 19 | `-273.15 C F` | `−459.67` | 0 | Exactly at absolute zero for C (should work) |
| 20 | `-273.16 C F` | Error | 3 | Below absolute zero for C |
| 21 | `-459.67 F C` | `-273.15` | 0 | Exactly at absolute zero for F (should work) |
| 22 | `-459.68 F C` | Error | 3 | Below absolute zero for F |
| 23 | `0 K C` | `-273.2` | 0 | Exactly at absolute zero for K (integer input → 1 decimal rounding) |
| 24 | `-1 K C` | Error | 3 | Below absolute zero for K (negative Kelvin) |

### Case Insensitivity
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 25 | `0 c f` | `32.0` | 0 | Lowercase scales |
| 26 | `0 C f` | `32.0` | 0 | Mixed case scales |
| 27 | `0 k c` | `-273.2` | 0 | Lowercase K (integer input → 1 decimal rounding) |

### Invalid Argument Count
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 28 | `tempconv` | Error message | 4 | No arguments |
| 29 | `tempconv 0 C` | Error message | 4 | Only 2 arguments |
| 30 | `tempconv 0 C F extra` | Error message | 4 | 4 arguments (too many) |
| 31 | `tempconv 0 C F extra1 extra2` | Error message | 4 | 5 arguments (too many) |

### Invalid Numeric Values
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 32 | `abc C F` | Error: Invalid number: abc | 1 | Non-numeric string |

### Invalid Scale Values
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 33 | `0 X C` | Error: Invalid scale: X | 2 | Invalid source scale |
| 34 | `0 C X` | Error: Invalid scale: X | 2 | Invalid target scale |
| 35 | `0 CC F` | Error: Invalid scale: CC | 2 | Multiple letters |

### Edge Cases - Additional Coverage
| # | Input | Expected Output | Exit | Notes |
|---|-------|-----------------|------|-------|
| 36 | `-0 C F` | `32.0` | 0 | Negative zero |
| 37 | `0.0 K F` | `-459.7` | 0 | Zero Kelvin to Fahrenheit (1 decimal rounding) |

