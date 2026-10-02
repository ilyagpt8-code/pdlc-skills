# Ready to Review

I've read and understood the specification at `spec/tempconv.md`. I'm ready to:

1. Review the implementation against the spec
2. Verify all test cases pass
3. Answer questions about the spec interpretation
4. Accept the completed work

Key points I'll validate:
- Correct conversion formulas
- Proper error handling (error codes 1-3)
- Input validation order (args → number → scale → absolute zero)
- Output format (exactly 2 decimal places, no scientific notation)
- Floating-point tolerance for absolute zero boundary (±1e-9)
- Negative zero normalized to `0.00`

Ready when you are.
