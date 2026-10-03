# Specification Complete

## Work Completed
I have written the complete specification for `tempconv` based on your requirements and my design decisions (from message 002).

## Location
`out/006-B3/tempconv.md` (repository root)

## What's Included

The specification contains:

1. **Command syntax**: `tempconv <value> <from_unit> <to_unit>`
2. **Unit identifiers**: Single-letter units (C, F, K), case-insensitive
3. **Conversion formulas**: All six paths (C↔F, C↔K, F↔K) with explicit formulas
4. **Output format**: Single number followed by newline (no unit labels)
5. **Error handling**: Five error types with specific exit codes:
   - Non-numeric input → exit 1
   - Unknown unit → exit 2
   - Temperature below absolute zero → exit 3
   - Missing/excess arguments → exit 1
   - Success → exit 0
6. **Edge cases**: Same-unit conversion allowed, zero handling, absolute zero boundaries
7. **Precision guidance**: Implementation choice on decimal places, with constraint
8. **Test cases**: Table with 10 example test cases covering normal and error paths
9. **Scope notes**: Clear list of out-of-scope features for future versions

## Design Decisions Applied
- ✓ Single-letter units only (simpler, faster)
- ✓ Same-unit conversion allowed (more user-friendly)
- ✓ Output is number only (better for scripting)

## How to Check
Another team can now:
1. Read the specification to understand all requirements
2. Write a `tempconv` implementation in any language
3. Use the test cases table to validate their implementation
4. Verify exit codes match all error conditions

The specification is self-contained and complete. Ready for your review and acceptance.
