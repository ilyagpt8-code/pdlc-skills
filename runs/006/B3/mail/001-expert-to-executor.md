# Expert's Initial Requirements for tempconv

## Core Design Decisions

### 1. Command Syntax
The utility should use a positional argument format:
```
tempconv <value> <from_unit> <to_unit>
```

Example: `tempconv 100 C F` converts 100 Celsius to Fahrenheit.

### 2. Unit Identifiers
- Accept single-letter identifiers: **C** (Celsius), **F** (Fahrenheit), **K** (Kelvin)
- Should be **case-insensitive** (accept both 'c' and 'C') for user convenience
- Consider also accepting full names (Celsius, Fahrenheit, Kelvin) as variations—you decide

### 3. Output Format
- Output format should be: **a single number followed by a newline**
- The number should be the converted temperature value
- You may optionally include the target unit label (e.g., "25.0 F") instead of just the number

### 4. Error Handling Strategy
- **Non-numeric input** (e.g., `tempconv abc C F`): Display error message, exit code 1
- **Unknown unit** (e.g., `tempconv 100 X F`): Display error message, exit code 2
- **Invalid operation** (e.g., same unit): You decide—should this be allowed or an error?
- **Temperature below absolute zero**: Display error message, exit code 3 (key requirement)
- **Missing arguments**: Display usage help, exit code 1
- **Success**: Exit code 0

### 5. Boundary Conditions
- Absolute zero is 0 K = -273.15°C = -459.67°F
- Reject any input that would result in a temperature below absolute zero after conversion

## What You Decide
You have freedom on:
- Exact error message wording
- Decimal precision and rounding method
- Whether to output unit labels with the result
- Whether the tool should support long-form unit names
- Details of the help/usage message format
- Any additional features (e.g., batch processing, reading from stdin)

## Questions for You
Before you start writing the spec, please clarify:
1. Should the tool support full unit names (like `--from Celsius --to Fahrenheit`) or only single letters?
2. Should converting C to C (same unit) be allowed and return the same value, or should it error?
3. For output, do you prefer just the number, or should it include the unit label?

I'm ready to answer any other questions as you work on the specification.
