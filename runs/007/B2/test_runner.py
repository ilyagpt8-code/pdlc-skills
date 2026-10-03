#!/usr/bin/env python3
"""
Test runner for tempconv implementation.
Tests all cases from tester-checks.md against the implementation.
"""

import subprocess
import sys
import os

os.chdir('/home/user/pdlc-skills')

# Test cases: (number, args, expected_output, expected_exit, description, check_type)
# check_type: 'exact', 'contains', 'not_contains'
test_cases = [
    # Basic conversions
    (1, "0 C F", "32", 0, "C to F at freezing", "exact"),
    (2, "100 C F", "212", 0, "C to F at boiling", "exact"),
    (3, "32 F C", "0", 0, "F to C at freezing", "exact"),
    (4, "212 F C", "100", 0, "F to C at boiling", "exact"),
    (5, "0 C K", "273.15", 0, "C to K at freezing", "exact"),
    (6, "273.15 K C", "0", 0, "K to C at freezing", "exact"),
    (7, "273.15 K F", "32", 0, "K to F at freezing", "exact"),
    (8, "32 F K", "273.15", 0, "F to K at freezing", "exact"),
    (9, "25 C F", "77", 0, "Room temp C to F", "exact"),
    (10, "20 C K", "293.15", 0, "Room temp C to K", "exact"),

    # Absolute zero boundaries
    (11, "0 K C", "-273.15", 0, "Absolute zero K to C", "exact"),
    (12, "-273.15 C K", "0", 0, "Absolute zero C to K", "exact"),
    (13, "-459.67 F K", "0", 0, "Absolute zero F to K", "exact"),
    (14, "0 K F", "-459.67", 0, "Absolute zero K to F", "exact"),

    # Below absolute zero - should fail
    (15, "-273.16 C K", "Error: temperature below absolute zero", 3, "Below absolute zero -0.01C", "stderr"),
    (16, "-1 K C", "Error: temperature below absolute zero", 3, "Negative Kelvin", "stderr"),
    (17, "-459.68 F K", "Error: temperature below absolute zero", 3, "Below absolute zero -0.01F", "stderr"),
    (18, "-274 C K", "Error: temperature below absolute zero", 3, "Below absolute zero significantly", "stderr"),

    # Same-scale conversions
    (19, "25 C C", "25", 0, "Same scale C to C", "exact"),
    (20, "100 F F", "100", 0, "Same scale F to F", "exact"),
    (21, "300 K K", "300", 0, "Same scale K to K", "exact"),

    # Invalid argument count
    (22, "0", "Error: invalid arguments", 4, "Missing scales (1 arg)", "stderr"),
    (23, "", "Error: invalid arguments", 4, "No arguments", "stderr"),
    (24, "0 C F extra", "Error: invalid arguments", 4, "Too many arguments (4)", "stderr"),
    (25, "0 C", "Error: invalid arguments", 4, "Missing target scale", "stderr"),

    # Invalid value (not a number)
    (26, "abc C F", "Error: invalid value", 1, "Non-numeric value", "stderr"),
    (27, "12.34.56 C F", "Error: invalid value", 1, "Multiple decimal points", "stderr"),

    # Invalid scales
    (30, "0 X F", "Error: invalid scale", 2, "Unknown scale X", "stderr"),
    (31, "0 C X", "Error: invalid scale", 2, "Unknown target scale X", "stderr"),
    (32, "0 CC F", "Error: invalid scale", 2, "Double scale letter", "stderr"),
    (33, "0 c f", "32", 0, "Lowercase scales", "exact"),
    (34, "0 C f", "32", 0, "Mixed case scales", "exact"),

    # Output format and precision
    (35, "0.5 C F", "32.9", 0, "Decimal result (0.5C to F)", "exact"),
    (36, "1.5 C K", "274.65", 0, "Kelvin decimal", "exact"),
    (37, "98.6 F C", "37", 0, "Result rounds to integer", "exact"),

    # Negative values
    (38, "-40 C F", "-40", 0, "Negative C to F (-40 special case)", "exact"),
    (39, "-200 C K", "73.15", 0, "Negative C to K", "exact"),
    (40, "-10 K C", "Error: temperature below absolute zero", 3, "Negative Kelvin", "stderr"),

    # Edge cases
    (41, "0 F C", "-17.77", 0, "F to C repeating decimal", "contains"),
    (42, "273.15 K K", "273.15", 0, "Same scale K to K decimal", "exact"),
]

def run_test(case_num, args, expected, expected_exit, description, check_type):
    """Run a single test case."""
    cmd = f"python out/007-B2/tempconv.py {args}" if args else "python out/007-B2/tempconv.py"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Determine if it's an error case
    is_error_case = expected_exit != 0

    # Check exit code
    if result.returncode != expected_exit:
        return False, f"Exit code mismatch: expected {expected_exit}, got {result.returncode}"

    # Check output
    if is_error_case:
        # For error cases, check stderr
        output = result.stderr.strip()
    else:
        # For success cases, check stdout
        output = result.stdout.strip()

    if check_type == "exact":
        if output != expected:
            return False, f"Output mismatch: expected '{expected}', got '{output}'"
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

for case in test_cases:
    success, message = run_test(*case)
    if success:
        passed += 1
    else:
        failed += 1
        failures.append((case[0], case[1], case[4], message))

print(f"Test Results: {passed} passed, {failed} failed out of {len(test_cases)} cases")
print()

if failures:
    print("FAILURES:")
    for case_num, args, desc, message in failures:
        print(f"№{case_num} `{args}` - {desc}")
        print(f"  {message}")
        print()
else:
    print("ALL TESTS PASSED!")

sys.exit(0 if failed == 0 else 1)
