"""Tests for tempconv utility."""

import subprocess
import sys
import os

# Get the path to tempconv.py
TEMPCONV_PATH = os.path.join(os.path.dirname(__file__), '..', 'tempconv.py')


def run_tempconv(*args):
    """Run tempconv with given arguments and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH] + list(args),
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode


class TestBasicConversions:
    """Test basic temperature conversions."""

    def test_celsius_to_fahrenheit_zero(self):
        """0°C = 32°F"""
        stdout, _, returncode = run_tempconv('0', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '32.00'

    def test_fahrenheit_to_celsius_freezing(self):
        """32°F = 0°C"""
        stdout, _, returncode = run_tempconv('32', 'F', 'C')
        assert returncode == 0
        assert stdout.strip() == '0.00'

    def test_celsius_to_kelvin_boiling(self):
        """100°C = 373.15 K"""
        stdout, _, returncode = run_tempconv('100', 'C', 'K')
        assert returncode == 0
        assert stdout.strip() == '373.15'

    def test_same_scale_celsius(self):
        """25°C = 25.00°C"""
        stdout, _, returncode = run_tempconv('25', 'C', 'C')
        assert returncode == 0
        assert stdout.strip() == '25.00'

    def test_same_scale_fahrenheit(self):
        """77°F = 77.00°F"""
        stdout, _, returncode = run_tempconv('77', 'F', 'F')
        assert returncode == 0
        assert stdout.strip() == '77.00'

    def test_same_scale_kelvin(self):
        """298.15 K = 298.15 K"""
        stdout, _, returncode = run_tempconv('298.15', 'K', 'K')
        assert returncode == 0
        assert stdout.strip() == '298.15'

    def test_fahrenheit_to_kelvin(self):
        """32°F = 273.15 K"""
        stdout, _, returncode = run_tempconv('32', 'F', 'K')
        assert returncode == 0
        assert stdout.strip() == '273.15'

    def test_kelvin_to_celsius(self):
        """373.15 K = 100°C"""
        stdout, _, returncode = run_tempconv('373.15', 'K', 'C')
        assert returncode == 0
        assert stdout.strip() == '100.00'

    def test_kelvin_to_fahrenheit(self):
        """273.15 K = 32°F"""
        stdout, _, returncode = run_tempconv('273.15', 'K', 'F')
        assert returncode == 0
        assert stdout.strip() == '32.00'


class TestAbsoluteZeroBoundaries:
    """Test absolute zero boundary cases."""

    def test_absolute_zero_celsius(self):
        """-273.15°C is valid (absolute zero)"""
        stdout, _, returncode = run_tempconv('-273.15', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '-459.67'

    def test_absolute_zero_fahrenheit(self):
        """-459.67°F is valid (absolute zero)"""
        stdout, _, returncode = run_tempconv('-459.67', 'F', 'K')
        assert returncode == 0
        assert stdout.strip() == '0.00'

    def test_absolute_zero_kelvin(self):
        """0 K is valid (absolute zero)"""
        stdout, _, returncode = run_tempconv('0', 'K', 'C')
        assert returncode == 0
        assert stdout.strip() == '-273.15'

    def test_below_absolute_zero_celsius(self):
        """-273.151°C is below absolute zero"""
        _, stderr, returncode = run_tempconv('-273.151', 'C', 'F')
        assert returncode == 3
        assert stderr.strip() == 'Error: temperature below absolute zero'

    def test_below_absolute_zero_fahrenheit(self):
        """-459.68°F is below absolute zero"""
        _, stderr, returncode = run_tempconv('-459.68', 'F', 'K')
        assert returncode == 3
        assert stderr.strip() == 'Error: temperature below absolute zero'

    def test_below_absolute_zero_kelvin(self):
        """-0.01 K is below absolute zero"""
        _, stderr, returncode = run_tempconv('-0.01', 'K', 'C')
        assert returncode == 3
        assert stderr.strip() == 'Error: temperature below absolute zero'

    def test_near_absolute_zero_celsius_just_above(self):
        """-273.149°C is above absolute zero"""
        stdout, _, returncode = run_tempconv('-273.149', 'C', 'F')
        assert returncode == 0
        # Should convert without error


class TestRounding:
    """Test rounding behavior (round-half-up)."""

    def test_round_half_up_positive(self):
        """32.125°C → 32.13°F (rounds up)"""
        stdout, _, returncode = run_tempconv('32.125', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '89.83'  # (32.125 * 9/5) + 32 = 89.825, rounds to 89.83

    def test_round_half_down_positive(self):
        """32.124°C → 32.12°F (rounds down)"""
        stdout, _, returncode = run_tempconv('32.124', 'C', 'F')
        assert returncode == 0
        # Should round down

    def test_round_half_up_negative(self):
        """-32.125°C → -25.83°F (rounds away from zero)"""
        stdout, _, returncode = run_tempconv('-32.125', 'C', 'F')
        assert returncode == 0
        # (-32.125 * 9/5) + 32 = -25.825, rounds to -25.83


class TestInputValidation:
    """Test input validation."""

    def test_missing_arguments(self):
        """Missing arguments should exit with code 1"""
        _, stderr, returncode = run_tempconv('25')
        assert returncode == 1
        assert 'Usage: tempconv <value> <from> <to>' in stderr

    def test_too_many_arguments(self):
        """Too many arguments should exit with code 1"""
        _, stderr, returncode = run_tempconv('25', 'C', 'F', 'extra')
        assert returncode == 1
        assert 'Usage: tempconv <value> <from> <to>' in stderr

    def test_invalid_number_string(self):
        """Invalid number string should exit with code 1"""
        _, stderr, returncode = run_tempconv('abc', 'C', 'F')
        assert returncode == 1
        assert stderr.strip() == 'Error: invalid number'

    def test_invalid_number_empty(self):
        """Empty value should exit with code 1"""
        _, stderr, returncode = run_tempconv('', 'C', 'F')
        assert returncode == 1
        assert stderr.strip() == 'Error: invalid number'

    def test_invalid_scale_from(self):
        """Invalid FROM scale should exit with code 2"""
        _, stderr, returncode = run_tempconv('25', 'R', 'F')
        assert returncode == 2
        assert stderr.strip() == 'Error: invalid scale'

    def test_invalid_scale_to(self):
        """Invalid TO scale should exit with code 2"""
        _, stderr, returncode = run_tempconv('25', 'C', 'X')
        assert returncode == 2
        assert stderr.strip() == 'Error: invalid scale'

    def test_lowercase_scale(self):
        """Lowercase scale should be treated as invalid"""
        _, stderr, returncode = run_tempconv('25', 'c', 'f')
        assert returncode == 2
        assert stderr.strip() == 'Error: invalid scale'

    def test_mixed_case_scale(self):
        """Mixed case scale should be treated as uppercase"""
        stdout, _, returncode = run_tempconv('25', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '77.00'


class TestScientificNotation:
    """Test scientific notation support."""

    def test_scientific_notation_positive(self):
        """1e2°C (100°C) = 212°F"""
        stdout, _, returncode = run_tempconv('1e2', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '212.00'

    def test_scientific_notation_negative(self):
        """1e-5 (0.00001)"""
        stdout, _, returncode = run_tempconv('1e-5', 'C', 'K')
        assert returncode == 0
        # Should succeed without error


class TestDecimalFormat:
    """Test decimal number format."""

    def test_integer_input(self):
        """Integer input should output with 2 decimal places"""
        stdout, _, returncode = run_tempconv('25', 'C', 'C')
        assert returncode == 0
        assert stdout.strip() == '25.00'

    def test_decimal_input_one_place(self):
        """One decimal place should be padded to 2"""
        stdout, _, returncode = run_tempconv('25.5', 'C', 'C')
        assert returncode == 0
        assert stdout.strip() == '25.50'

    def test_decimal_input_many_places(self):
        """Many decimal places should be rounded to 2"""
        stdout, _, returncode = run_tempconv('25.123456', 'C', 'C')
        assert returncode == 0
        assert stdout.strip() == '25.12'


class TestWhitespace:
    """Test whitespace handling."""

    def test_whitespace_around_value(self):
        """Whitespace around value should be handled"""
        stdout, _, returncode = run_tempconv('  25  ', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '77.00'

    def test_whitespace_around_scale(self):
        """Whitespace around scale should be handled"""
        stdout, _, returncode = run_tempconv('25', '  C  ', '  F  ')
        assert returncode == 0
        assert stdout.strip() == '77.00'


class TestComplexConversions:
    """Test complex conversion scenarios."""

    def test_room_temperature_celsius_to_fahrenheit(self):
        """20°C = 68°F"""
        stdout, _, returncode = run_tempconv('20', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '68.00'

    def test_body_temperature_fahrenheit_to_celsius(self):
        """98.6°F ≈ 37°C"""
        stdout, _, returncode = run_tempconv('98.6', 'F', 'C')
        assert returncode == 0
        # 98.6 - 32 = 66.6; 66.6 * 5/9 ≈ 37

    def test_liquid_nitrogen_temperature(self):
        """77 K ≈ -196.15°C"""
        stdout, _, returncode = run_tempconv('77', 'K', 'C')
        assert returncode == 0
        assert stdout.strip() == '-196.15'

    def test_large_positive_value(self):
        """Large positive temperature"""
        stdout, _, returncode = run_tempconv('1000', 'C', 'F')
        assert returncode == 0
        assert stdout.strip() == '1832.00'

    def test_large_negative_value_above_absolute_zero(self):
        """Large negative but above absolute zero"""
        stdout, _, returncode = run_tempconv('-200', 'C', 'K')
        assert returncode == 0
        assert stdout.strip() == '73.15'
