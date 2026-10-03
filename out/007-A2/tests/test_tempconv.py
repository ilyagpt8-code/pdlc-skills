"""
Comprehensive test suite for tempconv utility.
Tests all 37 cases from tester-checks.md
"""

import subprocess
import sys
import os

# Path to tempconv script
TEMPCONV_PATH = os.path.join(os.path.dirname(__file__), '..', 'tempconv.py')


def run_tempconv(*args):
    """
    Run tempconv with given arguments.
    Returns (stdout, stderr, returncode) tuple.
    """
    cmd = [sys.executable, TEMPCONV_PATH] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestArgumentCount:
    """Test cases for argument count validation."""

    def test_case_1_no_arguments(self):
        """Case 1: No arguments"""
        stdout, stderr, code = run_tempconv()
        assert code == 1
        assert stderr.startswith("Error:")

    def test_case_2_one_argument(self):
        """Case 2: Only value argument"""
        stdout, stderr, code = run_tempconv('0')
        assert code == 1
        assert "insufficient" in stderr.lower() or "Error:" in stderr

    def test_case_3_two_arguments(self):
        """Case 3: Only value and from_scale"""
        stdout, stderr, code = run_tempconv('0', 'C')
        assert code == 1
        assert "insufficient" in stderr.lower() or "Error:" in stderr

    def test_case_4_four_arguments(self):
        """Case 4: Too many arguments (4)"""
        stdout, stderr, code = run_tempconv('0', 'C', 'F', 'extra')
        assert code == 1
        assert "too many" in stderr.lower() or "Error:" in stderr

    def test_case_5_five_arguments(self):
        """Case 5: Too many arguments (5)"""
        stdout, stderr, code = run_tempconv('0', 'C', 'F', 'extra', 'more')
        assert code == 1
        assert "too many" in stderr.lower() or "Error:" in stderr


class TestValueParsing:
    """Test cases for value parsing validation."""

    def test_case_6_non_numeric_letters(self):
        """Case 6: Value is letters"""
        stdout, stderr, code = run_tempconv('abc', 'C', 'F')
        assert code == 1
        assert "not a valid number" in stderr or "Error:" in stderr

    def test_case_7_multiple_decimal_points(self):
        """Case 7: Multiple decimal points"""
        stdout, stderr, code = run_tempconv('12.34.56', 'C', 'F')
        assert code == 1
        assert "not a valid number" in stderr or "Error:" in stderr

    def test_case_8_scientific_notation(self):
        """Case 8: Scientific notation (1e3)"""
        stdout, stderr, code = run_tempconv('1e3', 'C', 'F')
        # Per spec ambiguity - we reject scientific notation
        assert code == 1
        assert "Error:" in stderr

    def test_case_9_positive_sign(self):
        """Case 9: Explicit positive sign (+5)"""
        stdout, stderr, code = run_tempconv('+5', 'C', 'F')
        # Per spec ambiguity - we reject explicit positive sign
        assert code == 1
        assert "Error:" in stderr

    def test_case_10_empty_string(self):
        """Case 10: Empty string (space)"""
        stdout, stderr, code = run_tempconv(' ', 'C', 'F')
        assert code == 1
        assert "not a valid number" in stderr or "Error:" in stderr

    def test_case_11_decimal_without_integer(self):
        """Case 11: Decimal without integer part (.5)"""
        stdout, stderr, code = run_tempconv('.5', 'C', 'F')
        # Per spec ambiguity - we accept this as valid float
        assert code == 0
        # .5 C = .5 * 9/5 + 32 = 32.9
        assert "32.90" in stdout


class TestScaleValidation:
    """Test cases for scale validation."""

    def test_case_12_invalid_from_scale(self):
        """Case 12: Invalid from scale 'X'"""
        stdout, stderr, code = run_tempconv('0', 'X', 'F')
        assert code == 1
        assert "invalid scale" in stderr.lower() or "Error:" in stderr

    def test_case_13_invalid_to_scale(self):
        """Case 13: Invalid to scale 'X'"""
        stdout, stderr, code = run_tempconv('0', 'C', 'X')
        assert code == 1
        assert "invalid scale" in stderr.lower() or "Error:" in stderr

    def test_case_14_lowercase_from_scale(self):
        """Case 14: Lowercase from scale (case-sensitive)"""
        stdout, stderr, code = run_tempconv('0', 'c', 'F')
        assert code == 1
        assert "invalid scale" in stderr.lower() or "Error:" in stderr

    def test_case_15_lowercase_to_scale(self):
        """Case 15: Lowercase to scale (case-sensitive)"""
        stdout, stderr, code = run_tempconv('0', 'C', 'f')
        assert code == 1
        assert "invalid scale" in stderr.lower() or "Error:" in stderr

    def test_case_16_two_letter_scale(self):
        """Case 16: Two letters for scale"""
        stdout, stderr, code = run_tempconv('0', 'CF', 'K')
        assert code == 1
        assert "invalid scale" in stderr.lower() or "Error:" in stderr


class TestSuccessfulConversions:
    """Test cases for successful conversions."""

    def test_case_17_celsius_to_celsius(self):
        """Case 17: Celsius to Celsius (same scale)"""
        stdout, stderr, code = run_tempconv('0', 'C', 'C')
        assert code == 0
        assert stdout == "0.00"

    def test_case_18_celsius_to_fahrenheit(self):
        """Case 18: Celsius to Fahrenheit"""
        stdout, stderr, code = run_tempconv('0', 'C', 'F')
        assert code == 0
        assert stdout == "32.00"

    def test_case_19_celsius_to_kelvin(self):
        """Case 19: Celsius to Kelvin"""
        stdout, stderr, code = run_tempconv('0', 'C', 'K')
        assert code == 0
        assert stdout == "273.15"

    def test_case_20_fahrenheit_to_celsius(self):
        """Case 20: Fahrenheit to Celsius"""
        stdout, stderr, code = run_tempconv('32', 'F', 'C')
        assert code == 0
        assert stdout == "0.00"

    def test_case_21_fahrenheit_to_fahrenheit(self):
        """Case 21: Fahrenheit to Fahrenheit (same scale)"""
        stdout, stderr, code = run_tempconv('0', 'F', 'F')
        assert code == 0
        assert stdout == "0.00"

    def test_case_22_fahrenheit_to_kelvin(self):
        """Case 22: Fahrenheit to Kelvin"""
        stdout, stderr, code = run_tempconv('0', 'F', 'K')
        assert code == 0
        assert stdout == "255.37"

    def test_case_23_celsius_to_kelvin_absolute_zero(self):
        """Case 23: Celsius to Kelvin at absolute zero"""
        stdout, stderr, code = run_tempconv('-273.15', 'C', 'K')
        assert code == 0
        assert stdout == "0.00"

    def test_case_24_kelvin_to_celsius(self):
        """Case 24: Kelvin to Celsius"""
        stdout, stderr, code = run_tempconv('0', 'K', 'C')
        assert code == 0
        assert stdout == "-273.15"

    def test_case_25_kelvin_to_fahrenheit(self):
        """Case 25: Kelvin to Fahrenheit"""
        stdout, stderr, code = run_tempconv('0', 'K', 'F')
        assert code == 0
        assert stdout == "-459.67"

    def test_case_26_kelvin_to_kelvin(self):
        """Case 26: Kelvin to Kelvin (same scale)"""
        stdout, stderr, code = run_tempconv('0', 'K', 'K')
        assert code == 0
        assert stdout == "0.00"


class TestAbsoluteZero:
    """Test cases for absolute zero boundary conditions."""

    def test_case_27_exactly_absolute_zero(self):
        """Case 27: Exactly at absolute zero"""
        stdout, stderr, code = run_tempconv('-273.15', 'C', 'K')
        assert code == 0
        assert stdout == "0.00"

    def test_case_28_slightly_below_absolute_zero(self):
        """Case 28: Slightly below absolute zero"""
        stdout, stderr, code = run_tempconv('-273.16', 'C', 'K')
        assert code == 2
        assert "absolute zero" in stderr.lower() or "Error:" in stderr

    def test_case_29_significantly_below_absolute_zero_celsius(self):
        """Case 29: Significantly below absolute zero from Celsius"""
        stdout, stderr, code = run_tempconv('-300', 'C', 'K')
        assert code == 2
        assert "absolute zero" in stderr.lower() or "Error:" in stderr
        # Result should be -26.85 K

    def test_case_30_significantly_below_absolute_zero_fahrenheit(self):
        """Case 30: Significantly below absolute zero from Fahrenheit"""
        stdout, stderr, code = run_tempconv('-500', 'F', 'K')
        assert code == 2
        assert "absolute zero" in stderr.lower() or "Error:" in stderr
        # Result should be -259.26 K


class TestRounding:
    """Test cases for away-from-zero rounding."""

    def test_case_31_normal_rounding(self):
        """Case 31: Normal rounding (98.6 F to C)"""
        stdout, stderr, code = run_tempconv('98.6', 'F', 'C')
        assert code == 0
        assert stdout == "37.00"

    def test_case_32_rounding_below_half(self):
        """Case 32: Rounding below .5"""
        stdout, stderr, code = run_tempconv('273.154', 'C', 'C')
        assert code == 0
        assert stdout == "273.15"

    def test_case_33_rounding_at_half(self):
        """Case 33: Rounding at .5 (away from zero)"""
        stdout, stderr, code = run_tempconv('273.145', 'C', 'C')
        assert code == 0
        assert stdout == "273.15"

    def test_case_34_rounding_above_half(self):
        """Case 34: Rounding above .5"""
        stdout, stderr, code = run_tempconv('273.156', 'C', 'C')
        assert code == 0
        assert stdout == "273.16"

    def test_case_35_rounding_negative_at_half(self):
        """Case 35: Negative rounding at .5 (away from zero)"""
        stdout, stderr, code = run_tempconv('-123.145', 'C', 'C')
        assert code == 0
        assert stdout == "-123.15"


class TestOutputFormat:
    """Test cases for output format."""

    def test_case_36_zeros_format(self):
        """Case 36: Zero values with 2 decimal places"""
        stdout, stderr, code = run_tempconv('0', 'C', 'C')
        assert code == 0
        assert stdout == "0.00"

    def test_case_37_negative_format(self):
        """Case 37: Negative result format"""
        stdout, stderr, code = run_tempconv('-40', 'C', 'F')
        assert code == 0
        assert stdout == "-40.00"


class TestAdditionalCases:
    """Additional edge cases and verification tests."""

    def test_example_100_celsius_to_fahrenheit(self):
        """From spec: 100 C to F should be 212.00"""
        stdout, stderr, code = run_tempconv('100', 'C', 'F')
        assert code == 0
        assert stdout == "212.00"

    def test_example_negative_40_celsius(self):
        """From spec: -40 C to F should be -40.00"""
        stdout, stderr, code = run_tempconv('-40', 'C', 'F')
        assert code == 0
        assert stdout == "-40.00"

    def test_large_positive_value(self):
        """Large positive temperature"""
        stdout, stderr, code = run_tempconv('5000', 'K', 'C')
        assert code == 0
        # 5000 - 273.15 = 4726.85
        assert stdout == "4726.85"

    def test_very_small_positive_kelvin(self):
        """Very small positive Kelvin value"""
        stdout, stderr, code = run_tempconv('0.01', 'K', 'C')
        assert code == 0
        # 0.01 - 273.15 = -273.14
        assert stdout == "-273.14"

    def test_no_stderr_on_success(self):
        """Verify no stderr output on successful conversion"""
        stdout, stderr, code = run_tempconv('0', 'C', 'K')
        assert code == 0
        assert stderr == ""

    def test_no_stdout_on_error(self):
        """Verify no stdout output on error"""
        stdout, stderr, code = run_tempconv('abc', 'C', 'F')
        assert code == 1
        assert stdout == ""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
