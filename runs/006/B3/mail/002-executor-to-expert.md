# Executor's Decisions on Design Questions

Thank you for the detailed requirements. I'm addressing your three questions:

## 1. Unit Name Format
**Decision: Single-letter units only** (C, F, K)

Rationale: Single letters are simpler, faster to type, and align with the utility's purpose as a quick converter. The `--from Celsius` style would require more parsing and is unnecessarily verbose for a simple converter.

**In the spec**: I'll note that future versions could support full names, but this is out of scope for the initial release.

## 2. Same Unit Conversion (C to C)
**Decision: Allow without error**

Rationale: Converting C to C should return the input value unchanged. This is the most user-friendly and doesn't add complexity. It's a valid operation (identity function) rather than an error case.

**In the spec**: The utility will allow and correctly handle same-unit conversions.

## 3. Output Format
**Decision: Number only (just the value)**

Rationale: Scripts and other tools can more easily pipe and parse a bare number. If a unit label is needed, the calling script can add it. This follows Unix philosophy (do one thing well).

**Example**: `tempconv 32 F C` outputs `0` (not `0 C`)

**In the spec**: Output will be a single number with optional trailing decimal point and newline.

---

I'm ready to write the specification with these decisions locked in. Any objections or changes to these choices?
