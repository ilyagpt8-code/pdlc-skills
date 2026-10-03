# Specification Issues for tempconv

## Issue 1: Incorrect Example (Line 143-145)

**Location**: Example "Converting with no target scale specified"

**Problem**: The output shows incorrect values.

Current spec shows:
```
$ tempconv 100 C
32 F
273.15 K
```

**Analysis**: This is incorrect. The conversion of 100 C should be:
- To F: (100 × 9/5) + 32 = 212 F (not 32 F)
- To K: 100 + 273.15 = 373.15 K ✓

The value "32 F" is the correct conversion of **0 C to F**, suggesting this was copy-pasted from the earlier example on line 96-99.

**Resolution**: The correct output should be:
```
$ tempconv 100 C
212 F
373.15 K
```

---

## Clarifications Made (No Changes to Spec)

1. **Missing required argument (Line 188)**: The example "tempconv 100" correctly returns error code 1, as it's missing the required `<from_scale>` argument. The target scale is optional but the source scale is required.

2. **Output ordering**: When no target scale is specified, output conversions in order C, F, K, skipping the source scale. This is consistent across all examples.

3. **Rounding/precision**: Per line 105-106, trailing zeros may be omitted and rounding to 2 decimal places is recommended but not required. This allows flexibility in output formatting.
