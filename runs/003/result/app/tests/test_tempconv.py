#!/usr/bin/env python3
"""
Tests for tempconv utility
"""

import subprocess
import sys
import os


def run_tempconv(*args):
    """
    Run tempconv with given arguments.
    Returns (stdout, stderr, exit_code)
    """
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tempconv.py')] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestBasicConversions:
    """Test standard conversions between all scale pairs."""

    def test_celsius_to_fahrenheit(self):
        """Test C to F conversion."""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "32.00", f"Expected 32.00, got {stdout}"

    def test_fahrenheit_to_celsius(self):
        """Test F to C conversion."""
        stdout, stderr, code = run_tempconv("32", "F", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "0.00", f"Expected 0.00, got {stdout}"

    def test_celsius_to_kelvin(self):
        """Test C to K conversion."""
        stdout, stderr, code = run_tempconv("100", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "373.15", f"Expected 373.15, got {stdout}"

    def test_kelvin_to_celsius(self):
        """Test K to C conversion."""
        stdout, stderr, code = run_tempconv("273.15", "K", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "0.00", f"Expected 0.00, got {stdout}"

    def test_fahrenheit_to_kelvin(self):
        """Test F to K conversion."""
        stdout, stderr, code = run_tempconv("32", "F", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "273.15", f"Expected 273.15, got {stdout}"

    def test_kelvin_to_fahrenheit(self):
        """Test K to F conversion."""
        stdout, stderr, code = run_tempconv("273.15", "K", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "32.00", f"Expected 32.00, got {stdout}"

    def test_celsius_special_negative_40(self):
        """Test C to F conversion at special point -40."""
        stdout, stderr, code = run_tempconv("-40", "C", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "-40.00", f"Expected -40.00, got {stdout}"


class TestSameScaleConversion:
    """Test conversions within the same scale."""

    def test_celsius_to_celsius(self):
        """Test C to C conversion."""
        stdout, stderr, code = run_tempconv("25", "C", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "25.00", f"Expected 25.00, got {stdout}"

    def test_fahrenheit_to_fahrenheit(self):
        """Test F to F conversion."""
        stdout, stderr, code = run_tempconv("77", "F", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "77.00", f"Expected 77.00, got {stdout}"

    def test_kelvin_to_kelvin(self):
        """Test K to K conversion."""
        stdout, stderr, code = run_tempconv("298.15", "K", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "298.15", f"Expected 298.15, got {stdout}"

    def test_same_scale_rounding(self):
        """Test rounding in same-scale conversion."""
        stdout, stderr, code = run_tempconv("0.001", "C", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "0.00", f"Expected 0.00, got {stdout}"


class TestAbsoluteZeroBoundary:
    """Test handling of absolute zero boundaries."""

    def test_celsius_absolute_zero_exact(self):
        """Test exact absolute zero for Celsius."""
        stdout, stderr, code = run_tempconv("-273.15", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "0.00", f"Expected 0.00, got {stdout}"

    def test_fahrenheit_absolute_zero_exact(self):
        """Test exact absolute zero for Fahrenheit."""
        stdout, stderr, code = run_tempconv("-459.67", "F", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "0.00", f"Expected 0.00, got {stdout}"

    def test_kelvin_absolute_zero_exact(self):
        """Test exact absolute zero for Kelvin."""
        stdout, stderr, code = run_tempconv("0", "K", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "-273.15", f"Expected -273.15, got {stdout}"

    def test_celsius_below_absolute_zero(self):
        """Test rejection of temperature below absolute zero in Celsius."""
        stdout, stderr, code = run_tempconv("-273.16", "C", "F")
        assert code == 3, f"Expected exit code 3, got {code}"
        assert stderr == "Error: temperature below absolute zero", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_fahrenheit_below_absolute_zero(self):
        """Test rejection of temperature below absolute zero in Fahrenheit."""
        stdout, stderr, code = run_tempconv("-459.68", "F", "C")
        assert code == 3, f"Expected exit code 3, got {code}"
        assert stderr == "Error: temperature below absolute zero", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_kelvin_below_absolute_zero(self):
        """Test rejection of negative Kelvin."""
        stdout, stderr, code = run_tempconv("-1", "K", "C")
        assert code == 3, f"Expected exit code 3, got {code}"
        assert stderr == "Error: temperature below absolute zero", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"


class TestFloatingPointTolerance:
    """Test floating-point tolerance for absolute zero boundaries."""

    def test_celsius_tolerance_positive(self):
        """Test tolerance just above the minimum for Celsius."""
        stdout, stderr, code = run_tempconv("-273.1500000001", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"

    def test_celsius_tolerance_negative(self):
        """Test tolerance at the edge (should still be acceptable)."""
        # -273.15 - 1e-9 should still be acceptable
        stdout, stderr, code = run_tempconv("-273.15000000001", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"


class TestNegativeZeroNormalization:
    """Test normalization of negative zero to positive zero."""

    def test_negative_zero_output(self):
        """Test that negative zero is output as positive zero."""
        # 32°F to C should give exactly 0°C
        stdout, stderr, code = run_tempconv("32", "F", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "0.00", f"Expected 0.00 (not -0.00), got {stdout}"
        assert not stdout.startswith("-"), "Output should not start with negative sign for zero"


class TestRounding:
    """Test rounding behavior (round-half-up)."""

    def test_rounding_up(self):
        """Test rounding up (0.5 and above)."""
        # We need to find values that round up
        # 0°C = 32°F exactly
        # 0.006°C = 32.0108°F (rounds to 32.01)
        stdout, stderr, code = run_tempconv("0.006", "C", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        # (0.006 * 9/5) + 32 = 0.0108 + 32 = 32.0108, rounds to 32.01
        assert stdout == "32.01", f"Expected 32.01, got {stdout}"

    def test_rounding_down(self):
        """Test rounding down (below 0.5)."""
        # 0.002°C = 32.0036°F (rounds to 32.00)
        stdout, stderr, code = run_tempconv("0.002", "C", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        # (0.002 * 9/5) + 32 = 0.0036 + 32 = 32.0036, rounds to 32.00
        assert stdout == "32.00", f"Expected 32.00, got {stdout}"


class TestLargeAndSmallNumbers:
    """Test handling of very large and very small numbers."""

    def test_large_number_no_scientific_notation(self):
        """Test that large numbers are output in standard format, not scientific."""
        stdout, stderr, code = run_tempconv("1000", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        # 1000 + 273.15 = 1273.15
        assert stdout == "1273.15", f"Expected 1273.15, got {stdout}"
        assert "e" not in stdout.lower(), f"Should not use scientific notation: {stdout}"

    def test_very_small_number_formatting(self):
        """Test that very small numbers are formatted with 2 decimal places."""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "32.00", f"Expected 32.00, got {stdout}"


class TestErrorHandling:
    """Test error conditions and error codes."""

    def test_invalid_number_format(self):
        """Test error on invalid number format."""
        stdout, stderr, code = run_tempconv("abc", "C", "F")
        assert code == 1, f"Expected exit code 1, got {code}"
        assert stderr == "Error: invalid number", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_invalid_from_scale(self):
        """Test error on invalid FROM scale."""
        stdout, stderr, code = run_tempconv("0", "X", "F")
        assert code == 2, f"Expected exit code 2, got {code}"
        assert stderr == "Error: invalid scale", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_invalid_to_scale(self):
        """Test error on invalid TO scale."""
        stdout, stderr, code = run_tempconv("0", "C", "X")
        assert code == 2, f"Expected exit code 2, got {code}"
        assert stderr == "Error: invalid scale", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_lowercase_scales_rejected(self):
        """Test that lowercase scale codes are rejected."""
        stdout, stderr, code = run_tempconv("0", "c", "f")
        assert code == 2, f"Expected exit code 2, got {code}"
        assert stderr == "Error: invalid scale", f"Wrong error message: {stderr}"

    def test_wrong_argument_count_too_few(self):
        """Test error when too few arguments provided."""
        stdout, stderr, code = run_tempconv("0", "C")
        assert code == 1, f"Expected exit code 1, got {code}"
        assert stderr == "Usage: tempconv <value> <from> <to>", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_wrong_argument_count_too_many(self):
        """Test error when too many arguments provided."""
        stdout, stderr, code = run_tempconv("0", "C", "F", "extra")
        assert code == 1, f"Expected exit code 1, got {code}"
        assert stderr == "Usage: tempconv <value> <from> <to>", f"Wrong error message: {stderr}"
        assert stdout == "", f"Expected no stdout, got {stdout}"

    def test_wrong_argument_count_no_args(self):
        """Test error when no arguments provided."""
        stdout, stderr, code = run_tempconv()
        assert code == 1, f"Expected exit code 1, got {code}"
        assert stderr == "Usage: tempconv <value> <from> <to>", f"Wrong error message: {stderr}"


class TestScientificNotationInput:
    """Test that scientific notation in input is accepted."""

    def test_scientific_notation_small(self):
        """Test small number in scientific notation."""
        stdout, stderr, code = run_tempconv("1e-5", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        # 1e-5 + 273.15 = 273.15001, rounds to 273.15
        assert stdout == "273.15", f"Expected 273.15, got {stdout}"

    def test_scientific_notation_large(self):
        """Test large number in scientific notation."""
        stdout, stderr, code = run_tempconv("2.5e2", "C", "K")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        # 2.5e2 = 250, 250 + 273.15 = 523.15
        assert stdout == "523.15", f"Expected 523.15, got {stdout}"


class TestWhitespaceHandling:
    """Test handling of whitespace in input."""

    def test_whitespace_in_value(self):
        """Test that whitespace around VALUE is trimmed."""
        stdout, stderr, code = run_tempconv("  0  ", "C", "F")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "32.00", f"Expected 32.00, got {stdout}"


class TestErrorCheckingOrder:
    """Test that errors are reported in the correct order."""

    def test_argument_count_checked_first(self):
        """Test that argument count is validated first."""
        stdout, stderr, code = run_tempconv("abc")
        assert code == 1, f"Expected exit code 1 (argument count), got {code}"
        assert stderr == "Usage: tempconv <value> <from> <to>", f"Wrong error: {stderr}"

    def test_number_checked_before_scale(self):
        """Test that number validation happens before scale validation."""
        stdout, stderr, code = run_tempconv("abc", "X", "Y")
        assert code == 1, f"Expected exit code 1 (number), got {code}"
        assert stderr == "Error: invalid number", f"Wrong error: {stderr}"

    def test_scale_checked_before_absolute_zero(self):
        """Test that scale validation happens before absolute zero check."""
        stdout, stderr, code = run_tempconv("-500", "X", "F")
        assert code == 2, f"Expected exit code 2 (scale), got {code}"
        assert stderr == "Error: invalid scale", f"Wrong error: {stderr}"


class TestEdgeCases:
    """Test various edge cases."""

    def test_negative_kelvin(self):
        """Test that negative Kelvin is rejected."""
        stdout, stderr, code = run_tempconv("-1", "K", "C")
        assert code == 3, f"Expected exit code 3, got {code}"
        assert stderr == "Error: temperature below absolute zero", f"Wrong error: {stderr}"

    def test_zero_kelvin(self):
        """Test zero Kelvin (absolute zero)."""
        stdout, stderr, code = run_tempconv("0", "K", "C")
        assert code == 0, f"Expected exit code 0, got {code}. stderr: {stderr}"
        assert stdout == "-273.15", f"Expected -273.15, got {stdout}"

    def test_decimal_scales_invalid(self):
        """Test that non-integer scale codes are rejected."""
        stdout, stderr, code = run_tempconv("0", "0.5", "C")
        assert code == 2, f"Expected exit code 2, got {code}"
        assert stderr == "Error: invalid scale", f"Wrong error: {stderr}"

    def test_multiple_character_scales_invalid(self):
        """Test that multi-character scale codes are rejected."""
        stdout, stderr, code = run_tempconv("0", "CC", "F")
        assert code == 2, f"Expected exit code 2, got {code}"
        assert stderr == "Error: invalid scale", f"Wrong error: {stderr}"
