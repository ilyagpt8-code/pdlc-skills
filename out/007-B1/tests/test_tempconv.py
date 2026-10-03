"""Comprehensive test suite for tempconv utility."""

import subprocess
import sys
from pathlib import Path


# Path to the tempconv script
TEMPCONV = str(Path(__file__).parent.parent / "tempconv.py")


def run_tempconv(*args):
    """
    Run tempconv with given arguments.
    Returns (stdout, stderr, exit_code).
    """
    cmd = [sys.executable, TEMPCONV] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestBasicConversions:
    """Test basic temperature conversions between all scale pairs."""

    def test_celsius_to_fahrenheit_zero(self):
        """0°C = 32°F"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        assert stdout == "32.0"

    def test_celsius_to_fahrenheit_hundred(self):
        """100°C = 212°F"""
        stdout, stderr, code = run_tempconv("100", "C", "F")
        assert code == 0
        assert stdout == "212.0"

    def test_celsius_to_fahrenheit_forty_below(self):
        """-40°C = -40°F (special point where C=F)"""
        stdout, stderr, code = run_tempconv("-40", "C", "F")
        assert code == 0
        assert stdout == "-40.0"

    def test_celsius_to_kelvin(self):
        """100°C = 373.15 K ≈ 373.2 K"""
        stdout, stderr, code = run_tempconv("100", "C", "K")
        assert code == 0
        assert stdout == "373.2"

    def test_fahrenheit_to_celsius_integer_input(self):
        """32°F = 0°C (integer input → 1 decimal output)"""
        stdout, stderr, code = run_tempconv("32", "F", "C")
        assert code == 0
        assert stdout == "0.0"

    def test_fahrenheit_to_celsius_one_decimal(self):
        """32.0°F = 0.0°C"""
        stdout, stderr, code = run_tempconv("32.0", "F", "C")
        assert code == 0
        assert stdout == "0.0"

    def test_fahrenheit_to_celsius_two_decimals(self):
        """32.50°F = 0.28°C (2 decimal precision)"""
        stdout, stderr, code = run_tempconv("32.50", "F", "C")
        assert code == 0
        assert stdout == "0.28"

    def test_kelvin_to_celsius(self):
        """273.15 K = 0°C (2 decimal input → 2 decimal output)"""
        stdout, stderr, code = run_tempconv("273.15", "K", "C")
        assert code == 0
        assert stdout == "0.00"

    def test_kelvin_to_fahrenheit(self):
        """0 K = -459.67°F (integer input → 1 decimal output)"""
        stdout, stderr, code = run_tempconv("0", "K", "F")
        assert code == 0
        assert stdout == "-459.7"

    def test_fahrenheit_to_kelvin(self):
        """68.5°F = 293.4 K"""
        stdout, stderr, code = run_tempconv("68.5", "F", "K")
        assert code == 0
        assert stdout == "293.4"


class TestDecimalPrecisionPreservation:
    """Test that output decimal places match input."""

    def test_integer_input_one_decimal_output(self):
        """Integer input (0) → 1 decimal place output (32.0)"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        assert stdout == "32.0"

    def test_one_decimal_input_preserved(self):
        """1 decimal input (0.0) → 1 decimal output (32.0)"""
        stdout, stderr, code = run_tempconv("0.0", "C", "F")
        assert code == 0
        assert stdout == "32.0"

    def test_two_decimal_input_preserved(self):
        """2 decimal input (0.00) → 2 decimal output (32.00)"""
        stdout, stderr, code = run_tempconv("0.00", "C", "F")
        assert code == 0
        assert stdout == "32.00"

    def test_one_decimal_preserved_celsius_to_fahrenheit(self):
        """100.5°C = 212.9°F (1 decimal preserved)"""
        stdout, stderr, code = run_tempconv("100.5", "C", "F")
        assert code == 0
        assert stdout == "212.9"

    def test_two_decimal_preserved_celsius_to_fahrenheit(self):
        """100.50°C = 212.90°F (2 decimals preserved)"""
        stdout, stderr, code = run_tempconv("100.50", "C", "F")
        assert code == 0
        assert stdout == "212.90"


class TestRoundingBehavior:
    """Test custom rounding (round half away from zero)."""

    def test_negative_half_rounding(self):
        """-0.25°C = 31.55°F (2 decimal places, rounding test)"""
        stdout, stderr, code = run_tempconv("-0.25", "C", "F")
        assert code == 0
        assert stdout == "31.55"

    def test_positive_half_rounding(self):
        """0.5°C = 273.65 K ≈ 273.7 K (round away from zero)"""
        stdout, stderr, code = run_tempconv("0.5", "C", "K")
        assert code == 0
        assert stdout == "273.7"

    def test_negative_integer_half_rounding(self):
        """-2.5°C = 27.5°F"""
        stdout, stderr, code = run_tempconv("-2.5", "C", "F")
        assert code == 0
        assert stdout == "27.5"


class TestAbsoluteZeroValidation:
    """Test validation at absolute zero boundaries."""

    def test_celsius_at_absolute_zero(self):
        """-273.15°C is exactly at absolute zero (should work)"""
        stdout, stderr, code = run_tempconv("-273.15", "C", "F")
        assert code == 0
        assert stdout == "-459.67"

    def test_celsius_below_absolute_zero(self):
        """-273.16°C is below absolute zero (should error)"""
        stdout, stderr, code = run_tempconv("-273.16", "C", "F")
        assert code == 3
        assert "below absolute zero" in stderr

    def test_fahrenheit_at_absolute_zero(self):
        """-459.67°F is exactly at absolute zero (should work)"""
        stdout, stderr, code = run_tempconv("-459.67", "F", "C")
        assert code == 0
        assert stdout == "-273.15"

    def test_fahrenheit_below_absolute_zero(self):
        """-459.68°F is below absolute zero (should error)"""
        stdout, stderr, code = run_tempconv("-459.68", "F", "C")
        assert code == 3
        assert "below absolute zero" in stderr

    def test_kelvin_at_absolute_zero(self):
        """0 K is exactly at absolute zero (should work) - integer input gives 1 decimal output"""
        stdout, stderr, code = run_tempconv("0", "K", "C")
        assert code == 0
        assert stdout == "-273.2"

    def test_kelvin_below_absolute_zero(self):
        """-1 K is below absolute zero (should error)"""
        stdout, stderr, code = run_tempconv("-1", "K", "C")
        assert code == 3
        assert "below absolute zero" in stderr


class TestCaseInsensitivity:
    """Test that scale arguments are case-insensitive."""

    def test_lowercase_scales(self):
        """0°c to °f (all lowercase)"""
        stdout, stderr, code = run_tempconv("0", "c", "f")
        assert code == 0
        assert stdout == "32.0"

    def test_mixed_case_scales(self):
        """0°C to °f (mixed case)"""
        stdout, stderr, code = run_tempconv("0", "C", "f")
        assert code == 0
        assert stdout == "32.0"

    def test_lowercase_kelvin(self):
        """0 k to °c (lowercase K) - integer input gives 1 decimal output"""
        stdout, stderr, code = run_tempconv("0", "k", "c")
        assert code == 0
        assert stdout == "-273.2"


class TestInvalidArgumentCount:
    """Test error handling for invalid argument counts."""

    def test_no_arguments(self):
        """No arguments"""
        stdout, stderr, code = run_tempconv()
        assert code == 4
        assert "Invalid number of arguments" in stderr
        assert "Usage: tempconv" in stderr

    def test_one_argument(self):
        """Only 1 argument"""
        stdout, stderr, code = run_tempconv("0")
        assert code == 4
        assert "Invalid number of arguments" in stderr

    def test_two_arguments(self):
        """Only 2 arguments"""
        stdout, stderr, code = run_tempconv("0", "C")
        assert code == 4
        assert "Invalid number of arguments" in stderr

    def test_four_arguments(self):
        """4 arguments (too many)"""
        stdout, stderr, code = run_tempconv("0", "C", "F", "extra")
        assert code == 4
        assert "Invalid number of arguments" in stderr

    def test_five_arguments(self):
        """5 arguments (too many)"""
        stdout, stderr, code = run_tempconv("0", "C", "F", "extra1", "extra2")
        assert code == 4
        assert "Invalid number of arguments" in stderr


class TestInvalidNumericValues:
    """Test error handling for invalid numeric inputs."""

    def test_non_numeric_string(self):
        """Non-numeric string"""
        stdout, stderr, code = run_tempconv("abc", "C", "F")
        assert code == 1
        assert "Invalid number: abc" in stderr

    def test_invalid_number_with_spaces(self):
        """Invalid number with spaces"""
        stdout, stderr, code = run_tempconv("12 34", "C", "F")
        assert code == 1
        assert "Invalid number" in stderr


class TestInvalidScaleValues:
    """Test error handling for invalid scale arguments."""

    def test_invalid_source_scale(self):
        """Invalid source scale"""
        stdout, stderr, code = run_tempconv("0", "X", "C")
        assert code == 2
        assert "Invalid scale: X" in stderr

    def test_invalid_target_scale(self):
        """Invalid target scale"""
        stdout, stderr, code = run_tempconv("0", "C", "X")
        assert code == 2
        assert "Invalid scale: X" in stderr

    def test_multiple_letter_scale(self):
        """Multiple letter scale"""
        stdout, stderr, code = run_tempconv("0", "CC", "F")
        assert code == 2
        assert "Invalid scale: CC" in stderr


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_negative_zero(self):
        """-0°C = 32.0°F"""
        stdout, stderr, code = run_tempconv("-0", "C", "F")
        assert code == 0
        assert stdout == "32.0"

    def test_zero_kelvin_to_fahrenheit(self):
        """0 K = -459.67°F (1 decimal input gives 1 decimal output)"""
        stdout, stderr, code = run_tempconv("0.0", "K", "F")
        assert code == 0
        assert stdout == "-459.7"

    def test_same_scale_conversion(self):
        """Converting to the same scale"""
        stdout, stderr, code = run_tempconv("100.5", "C", "C")
        assert code == 0
        assert stdout == "100.5"

    def test_large_positive_number(self):
        """Large positive temperature"""
        stdout, stderr, code = run_tempconv("1000", "C", "F")
        assert code == 0
        # 1000°C = 1832°F
        assert stdout == "1832.0"

    def test_three_decimal_places(self):
        """Input with 3 decimal places"""
        stdout, stderr, code = run_tempconv("32.125", "F", "C")
        assert code == 0
        # 32.125°F = 0.069°C (approximately)
        assert "." in stdout
        # Should have 3 decimal places
        decimal_part = stdout.split(".")[1] if "." in stdout else ""
        assert len(decimal_part) == 3

    def test_very_small_decimal(self):
        """Very small decimal value"""
        stdout, stderr, code = run_tempconv("0.001", "C", "K")
        assert code == 0
        assert "273.151" in stdout


class TestErrorMessages:
    """Test exact error message format."""

    def test_error_format_invalid_number(self):
        """Error message format for invalid number"""
        stdout, stderr, code = run_tempconv("notanumber", "C", "F")
        assert code == 1
        assert stderr == "Error: Invalid number: notanumber"

    def test_error_format_invalid_scale(self):
        """Error message format for invalid scale"""
        stdout, stderr, code = run_tempconv("0", "Q", "C")
        assert code == 2
        assert stderr == "Error: Invalid scale: Q"

    def test_error_format_below_absolute_zero(self):
        """Error message format for below absolute zero"""
        stdout, stderr, code = run_tempconv("-300", "C", "F")
        assert code == 3
        assert "Error: Temperature" in stderr
        assert "below absolute zero" in stderr
        assert "scale C" in stderr

    def test_error_format_argument_count(self):
        """Error message format for invalid argument count"""
        stdout, stderr, code = run_tempconv("0", "C")
        assert code == 4
        assert "Error: Invalid number of arguments" in stderr
        assert "Usage: tempconv" in stderr


class TestConversionAccuracy:
    """Test accuracy of temperature conversion formulas."""

    def test_formula_c_to_f(self):
        """Test C → F formula: (C × 9/5) + 32"""
        # 0°C → 32°F
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert stdout == "32.0"

    def test_formula_c_to_k(self):
        """Test C → K formula: C + 273.15"""
        # 0°C → 273.15 K (truncated to 1 decimal: 273.2)
        stdout, stderr, code = run_tempconv("0", "C", "K")
        assert stdout == "273.2"

    def test_formula_f_to_c(self):
        """Test F → C formula: (F - 32) × 5/9"""
        # 212°F → 100°C
        stdout, stderr, code = run_tempconv("212", "F", "C")
        assert stdout == "100.0"

    def test_formula_f_to_k(self):
        """Test F → K formula: (F - 32) × 5/9 + 273.15"""
        # 32°F → 273.15 K (truncated to 1 decimal: 273.2)
        stdout, stderr, code = run_tempconv("32", "F", "K")
        assert stdout == "273.2"

    def test_formula_k_to_c(self):
        """Test K → C formula: K - 273.15"""
        # 273.15 K → 0°C (2 decimal input gives 2 decimal output)
        stdout, stderr, code = run_tempconv("273.15", "K", "C")
        assert stdout == "0.00"

    def test_formula_k_to_f(self):
        """Test K → F formula: (K - 273.15) × 9/5 + 32"""
        # 273.15 K → 32°F (2 decimal input gives 2 decimal output)
        stdout, stderr, code = run_tempconv("273.15", "K", "F")
        assert stdout == "32.00"


if __name__ == "__main__":
    # This allows running tests with: python -m pytest test_tempconv.py
    pass
