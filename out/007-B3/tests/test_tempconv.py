"""
Tests for tempconv - Temperature Converter Utility

Tests all conversion paths, edge cases, error conditions, and precision.
"""

import subprocess
import sys
import pytest


def run_tempconv(*args):
    """
    Run tempconv with given arguments.

    Returns:
        tuple: (exit_code, stdout, stderr)
    """
    result = subprocess.run(
        [sys.executable, 'out/007-B3/tempconv.py'] + list(args),
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestConversions:
    """Test all six conversion paths."""

    def test_celsius_to_fahrenheit_freezing(self):
        """0°C = 32°F (water freezing point)"""
        code, stdout, stderr = run_tempconv('0', 'C', 'F')
        assert code == 0
        assert stdout == '32'

    def test_celsius_to_fahrenheit_boiling(self):
        """100°C = 212°F (water boiling point)"""
        code, stdout, stderr = run_tempconv('100', 'C', 'F')
        assert code == 0
        assert stdout == '212'

    def test_celsius_to_fahrenheit_room_temp(self):
        """20°C = 68°F (room temperature)"""
        code, stdout, stderr = run_tempconv('20', 'C', 'F')
        assert code == 0
        assert stdout == '68'

    def test_fahrenheit_to_celsius_freezing(self):
        """32°F = 0°C"""
        code, stdout, stderr = run_tempconv('32', 'F', 'C')
        assert code == 0
        assert stdout == '0'

    def test_fahrenheit_to_celsius_boiling(self):
        """212°F = 100°C"""
        code, stdout, stderr = run_tempconv('212', 'F', 'C')
        assert code == 0
        assert stdout == '100'

    def test_celsius_to_kelvin_freezing(self):
        """0°C = 273.15 K"""
        code, stdout, stderr = run_tempconv('0', 'C', 'K')
        assert code == 0
        assert stdout == '273.15'

    def test_celsius_to_kelvin_room_temp(self):
        """20°C = 293.15 K"""
        code, stdout, stderr = run_tempconv('20', 'C', 'K')
        assert code == 0
        assert stdout == '293.15'

    def test_kelvin_to_celsius_freezing(self):
        """273.15 K = 0°C"""
        code, stdout, stderr = run_tempconv('273.15', 'K', 'C')
        assert code == 0
        assert stdout == '0'

    def test_fahrenheit_to_kelvin(self):
        """32°F = 273.15 K"""
        code, stdout, stderr = run_tempconv('32', 'F', 'K')
        assert code == 0
        assert stdout == '273.15'

    def test_kelvin_to_fahrenheit(self):
        """273.15 K = 32°F"""
        code, stdout, stderr = run_tempconv('273.15', 'K', 'F')
        assert code == 0
        assert stdout == '32'


class TestAbsoluteZero:
    """Test absolute zero boundary conditions."""

    def test_absolute_zero_celsius_exact(self):
        """-273.15°C = 0 K"""
        code, stdout, stderr = run_tempconv('-273.15', 'C', 'K')
        assert code == 0
        assert stdout == '0'

    def test_absolute_zero_fahrenheit_exact(self):
        """-459.67°F = 0 K"""
        code, stdout, stderr = run_tempconv('-459.67', 'F', 'K')
        assert code == 0
        assert stdout == '0'

    def test_absolute_zero_kelvin(self):
        """0 K is valid"""
        code, stdout, stderr = run_tempconv('0', 'K', 'C')
        assert code == 0
        assert stdout == '-273.15'

    def test_just_above_absolute_zero_celsius(self):
        """-273.14°C is above absolute zero"""
        code, stdout, stderr = run_tempconv('-273.14', 'C', 'K')
        assert code == 0
        assert float(stdout) > 0

    def test_just_above_absolute_zero_fahrenheit(self):
        """-459.66°F is above absolute zero"""
        code, stdout, stderr = run_tempconv('-459.66', 'F', 'K')
        assert code == 0
        assert float(stdout) > 0

    def test_below_absolute_zero_celsius(self):
        """-300°C is below absolute zero"""
        code, stdout, stderr = run_tempconv('-300', 'C', 'K')
        assert code == 3
        assert 'absolute zero' in stderr.lower()

    def test_below_absolute_zero_fahrenheit(self):
        """-500°F is below absolute zero"""
        code, stdout, stderr = run_tempconv('-500', 'F', 'K')
        assert code == 3
        assert 'absolute zero' in stderr.lower()

    def test_below_absolute_zero_kelvin(self):
        """-1 K is below absolute zero"""
        code, stdout, stderr = run_tempconv('-1', 'K', 'C')
        assert code == 3
        assert 'absolute zero' in stderr.lower()


class TestSameUnitConversion:
    """Test same-unit conversions."""

    def test_celsius_to_celsius(self):
        """25°C = 25°C"""
        code, stdout, stderr = run_tempconv('25', 'C', 'C')
        assert code == 0
        assert stdout == '25'

    def test_fahrenheit_to_fahrenheit(self):
        """98.6°F = 98.6°F"""
        code, stdout, stderr = run_tempconv('98.6', 'F', 'F')
        assert code == 0
        assert stdout == '98.6'

    def test_kelvin_to_kelvin(self):
        """300 K = 300 K"""
        code, stdout, stderr = run_tempconv('300', 'K', 'K')
        assert code == 0
        assert stdout == '300'


class TestCaseInsensitivity:
    """Test case-insensitive unit parsing."""

    def test_lowercase_c(self):
        """Lowercase 'c' should work"""
        code, stdout, stderr = run_tempconv('0', 'c', 'f')
        assert code == 0
        assert stdout == '32'

    def test_uppercase_k(self):
        """Uppercase 'K' should work"""
        code, stdout, stderr = run_tempconv('273.15', 'k', 'c')
        assert code == 0
        assert stdout == '0'

    def test_mixed_case(self):
        """Mixed case units should work"""
        code, stdout, stderr = run_tempconv('100', 'C', 'f')
        assert code == 0
        assert stdout == '212'


class TestErrorHandling:
    """Test error conditions and exit codes."""

    def test_non_numeric_value(self):
        """Non-numeric value should exit with code 1"""
        code, stdout, stderr = run_tempconv('abc', 'C', 'F')
        assert code == 1
        assert 'invalid numeric value' in stderr.lower()

    def test_non_numeric_value_special_chars(self):
        """Special characters in value should error"""
        code, stdout, stderr = run_tempconv('12.34.56', 'C', 'F')
        assert code == 1
        assert 'invalid numeric value' in stderr.lower()

    def test_unknown_from_unit(self):
        """Unknown from_unit should exit with code 2"""
        code, stdout, stderr = run_tempconv('100', 'X', 'F')
        assert code == 2
        assert 'unknown unit' in stderr.lower()

    def test_unknown_to_unit(self):
        """Unknown to_unit should exit with code 2"""
        code, stdout, stderr = run_tempconv('100', 'C', 'Q')
        assert code == 2
        assert 'unknown unit' in stderr.lower()

    def test_missing_argument_count_2(self):
        """Too few arguments should exit with code 1"""
        code, stdout, stderr = run_tempconv('100', 'C')
        assert code == 1
        assert 'usage' in stderr.lower()

    def test_missing_argument_count_1(self):
        """Too few arguments should exit with code 1"""
        code, stdout, stderr = run_tempconv('100')
        assert code == 1
        assert 'usage' in stderr.lower()

    def test_missing_argument_count_0(self):
        """No arguments should exit with code 1"""
        code, stdout, stderr = run_tempconv()
        assert code == 1
        assert 'usage' in stderr.lower()

    def test_excess_arguments(self):
        """Excess arguments should exit with code 1"""
        code, stdout, stderr = run_tempconv('100', 'C', 'F', 'extra')
        assert code == 1
        assert 'usage' in stderr.lower()

    def test_multiple_excess_arguments(self):
        """Multiple excess arguments should exit with code 1"""
        code, stdout, stderr = run_tempconv('100', 'C', 'F', 'a', 'b', 'c')
        assert code == 1
        assert 'usage' in stderr.lower()


class TestNegativeTemperatures:
    """Test negative temperatures (when valid)."""

    def test_negative_celsius_valid(self):
        """-40°C is valid"""
        code, stdout, stderr = run_tempconv('-40', 'C', 'F')
        assert code == 0
        # -40°C = -40°F (interesting point where C and F are equal)
        assert stdout == '-40'

    def test_negative_fahrenheit_valid(self):
        """-40°F is valid"""
        code, stdout, stderr = run_tempconv('-40', 'F', 'C')
        assert code == 0
        assert stdout == '-40'

    def test_negative_kelvin_invalid(self):
        """-10 K is invalid"""
        code, stdout, stderr = run_tempconv('-10', 'K', 'C')
        assert code == 3


class TestFloatingPointPrecision:
    """Test floating-point values and precision."""

    def test_decimal_values_celsius_to_fahrenheit(self):
        """Test decimal conversion: 37.5°C to Fahrenheit"""
        code, stdout, stderr = run_tempconv('37.5', 'C', 'F')
        assert code == 0
        # 37.5 * 9/5 + 32 = 99.5
        assert stdout == '99.5'

    def test_decimal_values_kelvin(self):
        """Test decimal conversion with Kelvin"""
        code, stdout, stderr = run_tempconv('298.15', 'K', 'C')
        assert code == 0
        assert stdout == '25'

    def test_scientific_notation_input(self):
        """Scientific notation should be parsed"""
        code, stdout, stderr = run_tempconv('1e2', 'C', 'F')
        assert code == 0
        # 100°C = 212°F
        assert stdout == '212'

    def test_very_small_decimal(self):
        """Very small decimal values"""
        code, stdout, stderr = run_tempconv('0.01', 'C', 'K')
        assert code == 0
        # 0.01 + 273.15 = 273.16
        assert stdout == '273.16'

    def test_large_values(self):
        """Large temperature values"""
        code, stdout, stderr = run_tempconv('1000', 'C', 'K')
        assert code == 0
        assert stdout == '1273.15'


class TestEdgeCases:
    """Test various edge cases."""

    def test_zero_celsius(self):
        """Zero Celsius"""
        code, stdout, stderr = run_tempconv('0', 'C', 'K')
        assert code == 0
        assert stdout == '273.15'

    def test_zero_fahrenheit(self):
        """Zero Fahrenheit"""
        code, stdout, stderr = run_tempconv('0', 'F', 'C')
        assert code == 0
        # (0 - 32) * 5/9 = -17.78 rounded to -17.78
        assert '-17.78' in stdout

    def test_zero_kelvin(self):
        """Zero Kelvin (absolute zero)"""
        code, stdout, stderr = run_tempconv('0', 'K', 'C')
        assert code == 0
        assert stdout == '-273.15'

    def test_leading_whitespace_in_number(self):
        """Number with leading spaces should still work"""
        code, stdout, stderr = run_tempconv('  100', 'C', 'F')
        assert code == 0
        assert stdout == '212'

    def test_trailing_whitespace_in_number(self):
        """Number with trailing spaces should still work"""
        code, stdout, stderr = run_tempconv('100  ', 'C', 'F')
        assert code == 0
        assert stdout == '212'

    def test_negative_zero_celsius(self):
        """-0°C should be treated as 0°C"""
        code, stdout, stderr = run_tempconv('-0', 'C', 'F')
        assert code == 0
        assert stdout == '32'


class TestRoundingConsistency:
    """Test that rounding is consistent and appropriate."""

    def test_rounding_half_up(self):
        """Test standard rounding behavior"""
        code, stdout, stderr = run_tempconv('32', 'F', 'C')
        assert code == 0
        # (32 - 32) * 5/9 = 0
        assert stdout == '0'

    def test_rounding_preserves_precision(self):
        """Precision should be maintained to 2 decimal places"""
        code, stdout, stderr = run_tempconv('98.6', 'F', 'C')
        assert code == 0
        # (98.6 - 32) * 5/9 = 37
        assert stdout == '37'

    def test_decimal_places_limited(self):
        """Output should use at most 2 decimal places"""
        code, stdout, stderr = run_tempconv('10.555', 'C', 'F')
        assert code == 0
        # 10.555 * 9/5 + 32 = 51
        # Count decimal places
        if '.' in stdout:
            decimal_places = len(stdout.split('.')[1])
            assert decimal_places <= 2


class TestReferencePoints:
    """Test well-known temperature reference points."""

    def test_body_temperature_fahrenheit(self):
        """Human body temperature: 98.6°F = 37°C"""
        code, stdout, stderr = run_tempconv('98.6', 'F', 'C')
        assert code == 0
        assert stdout == '37'

    def test_dry_ice_sublimation(self):
        """Dry ice sublimation: -78.5°C"""
        code, stdout, stderr = run_tempconv('-78.5', 'C', 'K')
        assert code == 0
        # -78.5 + 273.15 = 194.65
        assert stdout == '194.65'

    def test_room_temperature(self):
        """Room temperature: 20°C ≈ 68°F"""
        code, stdout, stderr = run_tempconv('20', 'C', 'F')
        assert code == 0
        assert stdout == '68'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
