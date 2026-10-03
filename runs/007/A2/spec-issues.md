# Spec Issues and Decisions - tempconv

## Issues Found and Resolutions

### Issue 1: Scientific Notation (Test Case 8: `1e3 C F`)

**Ambiguity:** The specification does not explicitly mention whether scientific notation (e.g., `1e3`, `2.5e-2`) should be accepted as valid numeric input.

**Examples given:** The spec only shows plain decimal numbers without scientific notation.

**Decision:** **REJECTED** - Scientific notation is not accepted.

**Rationale:** 
- The specification does not document scientific notation as an acceptable input format
- Examples show only plain decimal numbers
- Conservative approach: only accept formats explicitly documented
- This matches typical CLI conventions where numeric input is expected in decimal form

**Implementation:** The parser explicitly rejects values containing 'e' or 'E'.

---

### Issue 2: Explicit Positive Sign (Test Case 9: `+5 C F`)

**Ambiguity:** The specification does not explicitly mention whether an explicit positive sign (e.g., `+5`, `+32.1`) should be accepted.

**Examples given:** 
- The spec shows positive numbers like `0`, `32`, `98.6` without a leading `+` sign
- It mentions negative numbers like `-40`, `-273.15`

**Decision:** **REJECTED** - Explicit positive sign is not accepted.

**Rationale:**
- The specification only documents that values "Can be negative" but shows positive values without `+` prefix
- Typical CLI conventions treat `+` as not a standard input format
- Conservative approach: require plain decimal format without explicit `+` sign

**Implementation:** The parser explicitly rejects values starting with '+'.

---

### Issue 3: Decimal Without Integer Part (Test Case 11: `.5 C F`)

**Ambiguity:** The specification does not explicitly mention whether a decimal number without an integer part (e.g., `.5`, `.123`) should be accepted.

**Decision:** **ACCEPTED** - Decimal without integer part is treated as valid (e.g., `.5` → `0.5`).

**Rationale:**
- In most programming languages (Python, JavaScript, etc.), `.5` is a valid float literal representing `0.5`
- This is a natural and common representation in mathematics and scientific contexts
- It's more user-friendly and doesn't introduce unnecessary complexity
- The spec doesn't explicitly forbid it, and it's a standard mathematical notation

**Implementation:** The parser uses Python's standard `float()` function, which naturally handles `.5` as `0.5`.

**Test Case Result:** `.5 C F` converts correctly: 0.5°C × 9/5 + 32 = 32.9°F → `32.90`

---

## Summary

| Test Case | Input | Ambiguity | Decision | Rationale |
|-----------|-------|-----------|----------|-----------|
| 8 | `1e3 C F` | Scientific notation | REJECT | Not documented in spec; only decimal format shown in examples |
| 9 | `+5 C F` | Explicit positive sign | REJECT | Not documented in spec; positive values shown without `+` |
| 11 | `.5 C F` | No integer part | ACCEPT | Standard notation; natural in math/science; not forbidden by spec |

All implementation decisions align with the specification's requirements and typical CLI conventions for numeric input validation.
