#!/usr/bin/env python3
"""
Complete test runner for tempconv - all 42 test cases from tester-checks.md
"""

import subprocess
import sys
import os

os.chdir('/home/user/pdlc-skills')

# Test cases with full specification
# Format: (number, args, expected_output, expected_exit, description, check_type, notes)
test_cases = [
    # Basic conversions (10 cases)
    (1, "0 C F", "32", 0, "C to F at freezing", "exact", "Basic"),
    (2, "100 C F", "212", 0, "C to F at boiling", "exact", "Basic"),
    (3, "32 F C", "0", 0, "F to C at freezing", "exact", "Basic"),
    (4, "212 F C", "100", 0, "F to C at boiling", "exact", "Basic"),
    (5, "0 C K", "273.15", 0, "C to K at freezing", "exact", "Basic"),
    (6, "273.15 K C", "0", 0, "K to C at freezing", "exact", "Basic"),
    (7, "273.15 K F", "32", 0, "K to F at freezing", "exact", "Basic"),
    (8, "32 F K", "273.15", 0, "F to K at freezing", "exact", "Basic"),
    (9, "25 C F", "77", 0, "Room temp C to F", "exact", "Basic"),
    (10, "20 C K", "293.15", 0, "Room temp C to K", "exact", "Basic"),

    # Boundary cases - absolute zero (8 cases)
    (11, "0 K C", "-273.15", 0, "Absolute zero K to C", "exact", "Boundary"),
    (12, "-273.15 C K", "0", 0, "Absolute zero C to K", "exact", "Boundary"),
    (13, "-459.67 F K", "0", 0, "Absolute zero F to K", "exact", "Boundary"),
    (14, "0 K F", "-459.67", 0, "Absolute zero K to F", "exact", "Boundary"),

    # Below absolute zero (4 cases)
    (15, "-273.16 C K", "Error: temperature below absolute zero", 3, "Below abs zero -0.01C", "stderr", "Boundary"),
    (16, "-1 K C", "Error: temperature below absolute zero", 3, "Negative Kelvin", "stderr", "Boundary"),
    (17, "-459.68 F K", "Error: temperature below absolute zero", 3, "Below abs zero -0.01F", "stderr", "Boundary"),
    (18, "-274 C K", "Error: temperature below absolute zero", 3, "Below abs zero significantly", "stderr", "Boundary"),

    # Same-scale conversions (3 cases)
    (19, "25 C C", "25", 0, "Same scale C to C", "exact", "Same-scale"),
    (20, "100 F F", "100", 0, "Same scale F to F", "exact", "Same-scale"),
    (21, "300 K K", "300", 0, "Same scale K to K", "exact", "Same-scale"),

    # Invalid argument count (5 cases)
    (22, "0", "Error: invalid arguments", 4, "Only value (1 arg)", "stderr", "Invalid args"),
    (23, "", "Error: invalid arguments", 4, "No arguments", "stderr", "Invalid args"),
    (24, "0 C F extra", "Error: invalid arguments", 4, "Too many (4 args)", "stderr", "Invalid args"),
    (25, "0 C", "Error: invalid arguments", 4, "Missing target scale", "stderr", "Invalid args"),
    (28, "C F", "Error: invalid arguments", 4, "Scale names as values (2 args)", "stderr", "Invalid args"),

    # Invalid value (not a number) (3 cases)
    (26, "abc C F", "Error: invalid value", 1, "Non-numeric value", "stderr", "Invalid value"),
    (27, "12.34.56 C F", "Error: invalid value", 1, "Multiple decimals", "stderr", "Invalid value"),
    (29, "1e100 C K", "", 0, "Scientific notation", "flex", "Ambiguous: spec doesn't forbid"),

    # Invalid scales (5 cases)
    (30, "0 X F", "Error: invalid scale", 2, "Unknown scale X", "stderr", "Invalid scale"),
    (31, "0 C X", "Error: invalid scale", 2, "Unknown target X", "stderr", "Invalid scale"),
    (32, "0 CC F", "Error: invalid scale", 2, "Double scale CC", "stderr", "Invalid scale"),
    (33, "0 c f", "32", 0, "Lowercase c f", "exact", "Case-insensitive"),
    (34, "0 C f", "32", 0, "Mixed case C f", "exact", "Case-insensitive"),

    # Output format and precision (3 cases)
    (35, "0.5 C F", "32.9", 0, "Decimal 0.5C to F", "exact", "Precision"),
    (36, "1.5 C K", "274.65", 0, "Decimal K result", "exact", "Precision"),
    (37, "98.6 F C", "37", 0, "Result as integer", "exact", "Precision"),

    # Negative values (3 cases)
    (38, "-40 C F", "-40", 0, "Negative -40C special case", "exact", "Negative"),
    (39, "-200 C K", "73.15", 0, "Negative C to K", "exact", "Negative"),
    (40, "-10 K C", "Error: temperature below absolute zero", 3, "Negative Kelvin invalid", "stderr", "Negative"),

    # Edge cases (2 cases)
    (41, "0 F C", "-17.77", 0, "F to C repeating decimal", "contains", "Precision"),
    (42, "273.15 K K", "273.15", 0, "Same K with decimal", "exact", "Precision"),
]

def run_test(case_num, args, expected, expected_exit, description, check_type, notes):
    """Run a single test case."""
    cmd = f"python out/007-B2/tempconv.py {args}" if args else "python out/007-B2/tempconv.py"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    is_error_case = expected_exit != 0

    # Check exit code
    if result.returncode != expected_exit:
        return False, f"Exit {result.returncode} (expected {expected_exit})"

    # Check output
    if check_type == "flex":
        # For ambiguous cases, just check exit code is correct
        return True, "Pass (ambiguous spec, exit code correct)"

    if is_error_case:
        output = result.stderr.strip()
    else:
        output = result.stdout.strip()

    if check_type == "exact":
        if output != expected:
            return False, f"Got '{output}' (expected '{expected}')"
    elif check_type == "contains":
        if expected not in output:
            return False, f"Output should contain '{expected}', got '{output}'"
    elif check_type == "stderr":
        if expected not in output:
            return False, f"Stderr should contain '{expected}', got '{output}'"

    return True, "Pass"

# Run all tests
passed = 0
failed = 0
failures = []
passed_cases = []
failed_cases = []

for case in test_cases:
    success, message = run_test(*case)
    case_num = case[0]
    args = case[1]
    desc = case[4]
    notes = case[7]

    if success:
        passed += 1
        passed_cases.append(case_num)
    else:
        failed += 1
        failures.append((case_num, args, desc, message, notes))
        failed_cases.append(case_num)

print(f"{'='*70}")
print(f"VERIFICATION RESULTS FOR TEMPCONV IMPLEMENTATION")
print(f"{'='*70}")
print(f"\nTotal: {passed} PASSED, {failed} FAILED out of {len(test_cases)} test cases")
print(f"Success rate: {100*passed//len(test_cases)}%")

if failures:
    print(f"\n{'='*70}")
    print("FAILURES/ISSUES:")
    print(f"{'='*70}")
    for case_num, args, desc, message, notes in failures:
        print(f"\n№{case_num} `{args}`")
        print(f"  Description: {desc}")
        if notes:
            print(f"  Notes: {notes}")
        print(f"  Issue: {message}")
else:
    print(f"\n{'='*70}")
    print("ALL TESTS PASSED!")
    print(f"{'='*70}")

print(f"\nPassed cases: {sorted(passed_cases)}")
if failed_cases:
    print(f"Failed cases: {sorted(failed_cases)}")
