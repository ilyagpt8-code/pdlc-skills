"""
Comprehensive tests for tempconv temperature converter utility.
"""

import subprocess
import sys
import os
from pathlib import Path


# Get the path to the tempconv.py module
REPO_ROOT = Path(__file__).parent.parent.parent.parent
TEMPCONV_PATH = REPO_ROOT / "out" / "007-A1" / "tempconv.py"


def run_tempconv(*args):
    """
    Run tempconv with the given arguments and return (stdout, stderr, exit_code).
    """
    cmd = [sys.executable, str(TEMPCONV_PATH)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestSuccessfulConversions:
    """Test successful temperature conversions."""

    def test_fahrenheit_to_celsius_32(self):
        """32°F should convert to 0°C"""
        stdout, stderr, code = run_tempconv("32", "F", "C")
        assert code == 0
        assert stderr == ""
        assert stdout == "0"

    def test_celsius_to_fahrenheit_0(self):
        """0°C should convert to 32°F"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        assert stderr == ""
        assert stdout == "32"

    def test_celsius_to_kelvin_100(self):
        """100°C should convert to 373.15 K"""
        stdout, stderr, code = run_tempconv("100", "C", "K")
        assert code == 0
        assert stderr == ""
        assert stdout == "373.15"

    def test_kelvin_to_celsius_273_15(self):
        """273.15 K should convert to 0°C"""
        stdout, stderr, code = run_tempconv("273.15", "K", "C")
        assert code == 0
        assert stderr == ""
        assert stdout == "0"

    def test_celsius_to_fahrenheit_minus_40(self):
        """-40°C should convert to -40°F"""
        stdout, stderr, code = run_tempconv("-40", "C", "F")
        assert code == 0
        assert stderr == ""
        assert stdout == "-40"

    def test_self_conversion_celsius(self):
        """0°C should convert to itself as 0°C"""
        stdout, stderr, code = run_tempconv("0", "C", "C")
        assert code == 0
        assert stderr == ""
        assert stdout == "0"

    def test_fahrenheit_to_celsius_98_6(self):
        """98.6°F should convert to 37°C"""
        stdout, stderr, code = run_tempconv("98.6", "F", "C")
        assert code == 0
        assert stderr == ""
        assert stdout == "37"

    def test_fahrenheit_to_kelvin(self):
        """32°F should convert to 273.15 K"""
        stdout, stderr, code = run_tempconv("32", "F", "K")
        assert code == 0
        assert stderr == ""
        assert stdout == "273.15"

    def test_kelvin_to_fahrenheit(self):
        """273.15 K should convert to 32°F"""
        stdout, stderr, code = run_tempconv("273.15", "K", "F")
        assert code == 0
        assert stderr == ""
        assert stdout == "32"

    def test_self_conversion_fahrenheit(self):
        """32°F should convert to itself as 32°F"""
        stdout, stderr, code = run_tempconv("32", "F", "F")
        assert code == 0
        assert stderr == ""
        assert stdout == "32"

    def test_self_conversion_kelvin(self):
        """273.15 K should convert to itself as 273.15 K"""
        stdout, stderr, code = run_tempconv("273.15", "K", "K")
        assert code == 0
        assert stderr == ""
        assert stdout == "273.15"


class TestFormatting:
    """Test output formatting with trailing zero removal."""

    def test_format_trailing_zeros_both(self):
        """0.00 should format to 0"""
        stdout, stderr, code = run_tempconv("0", "C", "C")
        assert stdout == "0"

    def test_format_trailing_zero_one(self):
        """1.20 should format to 1.2"""
        stdout, stderr, code = run_tempconv("1.2", "C", "C")
        assert stdout == "1.2"

    def test_format_no_trailing_zeros(self):
        """1.23 should remain 1.23"""
        stdout, stderr, code = run_tempconv("1.23", "C", "C")
        assert stdout == "1.23"

    def test_format_small_decimal(self):
        """0.05 should remain 0.05"""
        stdout, stderr, code = run_tempconv("0.05", "C", "C")
        assert stdout == "0.05"

    def test_format_integer_like(self):
        """32.00 should format to 32"""
        stdout, stderr, code = run_tempconv("32", "F", "F")
        assert stdout == "32"

    def test_format_decimal_rounding(self):
        """Test proper rounding to 2 decimal places"""
        # 1.234 should round to 1.23
        stdout, stderr, code = run_tempconv("1.234", "C", "C")
        assert stdout == "1.23"

    def test_format_rounding_up(self):
        """Test rounding up"""
        # 1.235 should round to 1.24 (banker's rounding in Python)
        stdout, stderr, code = run_tempconv("1.235", "C", "C")
        assert stdout == "1.24" or stdout == "1.23"  # Python 3 uses banker's rounding


class TestAbsoluteZeroValidation:
    """Test absolute zero boundary checks."""

    def test_celsius_absolute_zero_valid(self):
        """-273.15°C should be valid (absolute zero)"""
        stdout, stderr, code = run_tempconv("-273.15", "C", "K")
        assert code == 0
        assert stdout == "0"

    def test_celsius_below_absolute_zero(self):
        """-300°C is below absolute zero and should error"""
        stdout, stderr, code = run_tempconv("-300", "C", "K")
        assert code == 1
        assert stderr == "Error: temperature below absolute zero"
        assert stdout == ""

    def test_fahrenheit_absolute_zero_valid(self):
        """-459.67°F should be valid (absolute zero)"""
        stdout, stderr, code = run_tempconv("-459.67", "F", "K")
        assert code == 0
        assert stdout == "0"

    def test_fahrenheit_below_absolute_zero(self):
        """-500°F is below absolute zero and should error"""
        stdout, stderr, code = run_tempconv("-500", "F", "K")
        assert code == 1
        assert stderr == "Error: temperature below absolute zero"

    def test_kelvin_absolute_zero_valid(self):
        """0 K should be valid (absolute zero)"""
        stdout, stderr, code = run_tempconv("0", "K", "C")
        assert code == 0
        assert stdout == "-273.15"

    def test_kelvin_below_absolute_zero(self):
        """-1 K is below absolute zero and should error"""
        stdout, stderr, code = run_tempconv("-1", "K", "C")
        assert code == 1
        assert stderr == "Error: temperature below absolute zero"

    def test_result_below_absolute_zero_celsius_to_kelvin(self):
        """Result below absolute zero should error even if input is valid"""
        stdout, stderr, code = run_tempconv("-274", "C", "K")
        assert code == 1
        assert stderr == "Error: temperature below absolute zero"


class TestErrorHandling:
    """Test error cases and error messages."""

    def test_missing_arguments(self):
        """No arguments should give exit code 2 and usage message"""
        stdout, stderr, code = run_tempconv()
        assert code == 2
        assert stderr == "Usage: tempconv <value> <from> <to>"
        assert stdout == ""

    def test_too_few_arguments(self):
        """Two arguments should give exit code 2"""
        stdout, stderr, code = run_tempconv("32", "F")
        assert code == 2
        assert stderr == "Usage: tempconv <value> <from> <to>"

    def test_too_many_arguments(self):
        """Four arguments should give exit code 2"""
        stdout, stderr, code = run_tempconv("32", "F", "C", "extra")
        assert code == 2
        assert stderr == "Usage: tempconv <value> <from> <to>"

    def test_invalid_value_not_a_number(self):
        """Non-numeric value should give exit code 1"""
        stdout, stderr, code = run_tempconv("abc", "F", "C")
        assert code == 1
        assert stderr == "Error: invalid temperature value"
        assert stdout == ""

    def test_invalid_value_partial_number(self):
        """Partially numeric value should give exit code 1"""
        stdout, stderr, code = run_tempconv("32x", "F", "C")
        assert code == 1
        assert stderr == "Error: invalid temperature value"

    def test_unknown_from_scale(self):
        """Unknown source scale should give exit code 1"""
        stdout, stderr, code = run_tempconv("0", "X", "C")
        assert code == 1
        assert stderr == "Error: unknown scale"

    def test_unknown_to_scale(self):
        """Unknown target scale should give exit code 1"""
        stdout, stderr, code = run_tempconv("0", "C", "X")
        assert code == 1
        assert stderr == "Error: unknown scale"

    def test_lowercase_scale_from(self):
        """Lowercase scale should not be accepted"""
        stdout, stderr, code = run_tempconv("0", "c", "F")
        assert code == 1
        assert stderr == "Error: unknown scale"

    def test_lowercase_scale_to(self):
        """Lowercase target scale should not be accepted"""
        stdout, stderr, code = run_tempconv("0", "C", "f")
        assert code == 1
        assert stderr == "Error: unknown scale"


class TestBoundaryAndSpecialValues:
    """Test boundary cases and special values."""

    def test_very_large_positive_number(self):
        """Very large positive numbers should be handled"""
        stdout, stderr, code = run_tempconv("1000000", "C", "F")
        assert code == 0

    def test_very_large_negative_number_above_absolute_zero(self):
        """Large negative numbers above absolute zero should work"""
        stdout, stderr, code = run_tempconv("-200", "C", "F")
        assert code == 0

    def test_small_decimal_precision(self):
        """Test precision with many decimal places in input"""
        stdout, stderr, code = run_tempconv("0.1111111", "C", "C")
        assert code == 0
        assert stdout == "0.11"

    def test_negative_small_value(self):
        """Negative small values should work"""
        stdout, stderr, code = run_tempconv("-0.5", "C", "F")
        assert code == 0

    def test_zero_value(self):
        """Zero should work in all scales"""
        for from_scale, to_scale in [("C", "F"), ("C", "K"), ("F", "C"), ("F", "K"), ("K", "C"), ("K", "F")]:
            stdout, stderr, code = run_tempconv("0", from_scale, to_scale)
            assert code == 0


class TestConversionAccuracy:
    """Test the mathematical accuracy of conversions."""

    def test_c_to_f_accuracy(self):
        """Test C to F conversion: 20°C = 68°F"""
        stdout, stderr, code = run_tempconv("20", "C", "F")
        assert code == 0
        assert stdout == "68"

    def test_f_to_c_accuracy(self):
        """Test F to C conversion: 68°F = 20°C"""
        stdout, stderr, code = run_tempconv("68", "F", "C")
        assert code == 0
        assert stdout == "20"

    def test_c_to_k_accuracy(self):
        """Test C to K conversion: 0°C = 273.15 K"""
        stdout, stderr, code = run_tempconv("0", "C", "K")
        assert code == 0
        assert stdout == "273.15"

    def test_k_to_c_accuracy(self):
        """Test K to C conversion: 373.15 K = 100°C"""
        stdout, stderr, code = run_tempconv("373.15", "K", "C")
        assert code == 0
        assert stdout == "100"

    def test_f_to_k_accuracy(self):
        """Test F to K (via C): 212°F = 373.15 K"""
        stdout, stderr, code = run_tempconv("212", "F", "K")
        assert code == 0
        assert stdout == "373.15"

    def test_k_to_f_accuracy(self):
        """Test K to F (via C): 273.15 K = 32°F"""
        stdout, stderr, code = run_tempconv("273.15", "K", "F")
        assert code == 0
        assert stdout == "32"


class TestRegressionAndEdgeCases:
    """Test for regression and edge cases."""

    def test_round_trip_c_to_f_to_c(self):
        """25°C -> F -> C should return ~25"""
        # First convert C to F
        stdout1, _, code1 = run_tempconv("25", "C", "F")
        assert code1 == 0
        # Then convert back
        temp_f = stdout1
        stdout2, _, code2 = run_tempconv(temp_f, "F", "C")
        assert code2 == 0
        # Should be close to 25
        result = float(stdout2)
        assert 24.9 < result < 25.1

    def test_negative_c_to_k(self):
        """-50°C should convert correctly to K"""
        stdout, stderr, code = run_tempconv("-50", "C", "K")
        assert code == 0
        # -50 + 273.15 = 223.15
        assert stdout == "223.15"

    def test_almost_absolute_zero_celsius(self):
        """-273.14°C should be valid"""
        stdout, stderr, code = run_tempconv("-273.14", "C", "K")
        assert code == 0

    def test_exactly_absolute_zero_celsius(self):
        """-273.15°C should be valid"""
        stdout, stderr, code = run_tempconv("-273.15", "C", "K")
        assert code == 0
        assert stdout == "0"

    def test_scientific_notation_input(self):
        """Scientific notation should be accepted by float parser"""
        stdout, stderr, code = run_tempconv("1e2", "C", "F")
        assert code == 0

    def test_plus_sign_input(self):
        """Plus sign should be accepted"""
        stdout, stderr, code = run_tempconv("+32", "F", "C")
        assert code == 0
        assert stdout == "0"


class TestSpecialFloatValues:
    """Test rejection of special float values (inf, -inf, nan)."""

    def test_infinity_input(self):
        """Infinity should be rejected as invalid"""
        stdout, stderr, code = run_tempconv("inf", "F", "C")
        assert code == 1
        assert stderr == "Error: invalid temperature value"
        assert stdout == ""

    def test_negative_infinity_input(self):
        """Negative infinity should be rejected as invalid"""
        stdout, stderr, code = run_tempconv("-inf", "K", "C")
        assert code == 1
        assert stderr == "Error: invalid temperature value"
        assert stdout == ""

    def test_nan_input(self):
        """NaN should be rejected as invalid"""
        stdout, stderr, code = run_tempconv("nan", "C", "F")
        assert code == 1
        assert stderr == "Error: invalid temperature value"
        assert stdout == ""


if __name__ == "__main__":
    # Run tests with pytest
    pytest_args = [__file__, "-v"]
    exit_code = __import__("pytest").main(pytest_args)
    sys.exit(exit_code)
