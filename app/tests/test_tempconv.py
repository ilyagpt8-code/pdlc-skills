"""
Comprehensive test suite for tempconv utility.
Tests conversions, error handling, and edge cases.
"""

import pytest
import subprocess
import sys


def run_tempconv(*args):
    """
    Run tempconv utility and return (stdout, stderr, exit_code).
    """
    result = subprocess.run(
        [sys.executable, 'app/tempconv.py'] + list(args),
        capture_output=True,
        text=True,
        cwd='/home/user/pdlc-skills'
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestConversionCorrectness:
    """Test correct conversions according to specification"""

    def test_self_conversion_celsius(self):
        """tempconv 0 C C -> 0"""
        stdout, stderr, code = run_tempconv('0', 'C', 'C')
        assert code == 0
        assert stdout == '0'

    def test_celsius_to_fahrenheit_freezing(self):
        """tempconv 0 C F -> 32"""
        stdout, stderr, code = run_tempconv('0', 'C', 'F')
        assert code == 0
        assert stdout == '32'

    def test_fahrenheit_to_celsius_freezing(self):
        """tempconv 32 F C -> 0"""
        stdout, stderr, code = run_tempconv('32', 'F', 'C')
        assert code == 0
        assert stdout == '0'

    def test_celsius_to_kelvin_freezing(self):
        """tempconv 0 C K -> 273.15"""
        stdout, stderr, code = run_tempconv('0', 'C', 'K')
        assert code == 0
        assert stdout == '273.15'

    def test_kelvin_to_celsius_freezing(self):
        """tempconv 273.15 K C -> 0"""
        stdout, stderr, code = run_tempconv('273.15', 'K', 'C')
        assert code == 0
        assert stdout == '0'

    def test_fahrenheit_to_celsius_body_temp(self):
        """tempconv 98.6 F C -> 37"""
        stdout, stderr, code = run_tempconv('98.6', 'F', 'C')
        assert code == 0
        assert stdout == '37'

    def test_celsius_to_fahrenheit_body_temp(self):
        """tempconv 37 C F -> 98.6"""
        stdout, stderr, code = run_tempconv('37', 'C', 'F')
        assert code == 0
        assert stdout == '98.6'

    def test_celsius_to_kelvin_boiling(self):
        """tempconv 100 C K -> 373.15"""
        stdout, stderr, code = run_tempconv('100', 'C', 'K')
        assert code == 0
        assert stdout == '373.15'

    def test_kelvin_to_celsius_boiling(self):
        """tempconv 373.15 K C -> 100"""
        stdout, stderr, code = run_tempconv('373.15', 'K', 'C')
        assert code == 0
        assert stdout == '100'

    def test_celsius_to_fahrenheit_minus_40(self):
        """tempconv -40 C F -> -40"""
        stdout, stderr, code = run_tempconv('-40', 'C', 'F')
        assert code == 0
        assert stdout == '-40'

    def test_fahrenheit_to_celsius_minus_40(self):
        """tempconv -40 F C -> -40"""
        stdout, stderr, code = run_tempconv('-40', 'F', 'C')
        assert code == 0
        assert stdout == '-40'

    def test_fahrenheit_to_kelvin_freezing(self):
        """tempconv 32 F K -> 273.15"""
        stdout, stderr, code = run_tempconv('32', 'F', 'K')
        assert code == 0
        assert stdout == '273.15'

    def test_celsius_to_fahrenheit_boiling(self):
        """tempconv 100 C F -> 212"""
        stdout, stderr, code = run_tempconv('100', 'C', 'F')
        assert code == 0
        assert stdout == '212'


class TestBoundaryConditions:
    """Test boundary conditions and absolute zero"""

    def test_absolute_zero_celsius_to_kelvin(self):
        """tempconv -273.15 C K -> 0"""
        stdout, stderr, code = run_tempconv('-273.15', 'C', 'K')
        assert code == 0
        assert stdout == '0'

    def test_below_absolute_zero_celsius_to_kelvin(self):
        """tempconv -273.16 C K -> error (exit 1)"""
        stdout, stderr, code = run_tempconv('-273.16', 'C', 'K')
        assert code == 1
        assert 'Error:' in stderr
        assert 'below absolute zero' in stderr


class TestErrorHandling:
    """Test error handling and validation"""

    def test_invalid_value_non_numeric(self):
        """tempconv abc C F -> error"""
        stdout, stderr, code = run_tempconv('abc', 'C', 'F')
        assert code == 1
        assert 'Error: Value is not a valid number' in stderr

    def test_invalid_from_scale(self):
        """tempconv 0 X F -> error"""
        stdout, stderr, code = run_tempconv('0', 'X', 'F')
        assert code == 1
        assert "Error: Invalid scale 'X'" in stderr

    def test_invalid_to_scale(self):
        """tempconv 0 C Z -> error"""
        stdout, stderr, code = run_tempconv('0', 'C', 'Z')
        assert code == 1
        assert "Error: Invalid scale 'Z'" in stderr

    def test_negative_kelvin_input(self):
        """tempconv -1 K C -> error"""
        stdout, stderr, code = run_tempconv('-1', 'K', 'C')
        assert code == 1
        assert 'Error: Temperature in Kelvin cannot be negative' in stderr

    def test_lowercase_from_scale(self):
        """tempconv 0 c f -> error (case-sensitive)"""
        stdout, stderr, code = run_tempconv('0', 'c', 'f')
        assert code == 1
        assert 'Error:' in stderr

    def test_lowercase_to_scale(self):
        """tempconv 0 C f -> error (case-sensitive)"""
        stdout, stderr, code = run_tempconv('0', 'C', 'f')
        assert code == 1
        assert 'Error:' in stderr

    def test_missing_arguments(self):
        """tempconv 0 C -> error (missing argument)"""
        stdout, stderr, code = run_tempconv('0', 'C')
        assert code == 1

    def test_too_many_arguments(self):
        """tempconv 0 C F extra -> error (too many arguments)"""
        stdout, stderr, code = run_tempconv('0', 'C', 'F', 'extra')
        assert code == 1


class TestPrecisionFormatting:
    """Test output formatting with minimal decimal places"""

    def test_integer_output(self):
        """Integer results should not have decimal point"""
        stdout, stderr, code = run_tempconv('0', 'C', 'C')
        assert code == 0
        assert stdout == '0'
        assert '.' not in stdout

    def test_single_decimal_place(self):
        """Results with one decimal place"""
        stdout, stderr, code = run_tempconv('98.6', 'F', 'C')
        assert code == 0
        assert stdout == '37'

    def test_two_decimal_places(self):
        """Results with two decimal places"""
        stdout, stderr, code = run_tempconv('0', 'C', 'K')
        assert code == 0
        assert stdout == '273.15'

    def test_no_trailing_zeros(self):
        """Trailing zeros should be removed"""
        # 0C = 32F, which is an integer
        stdout, stderr, code = run_tempconv('0', 'C', 'F')
        assert code == 0
        assert stdout == '32'
        # No trailing zeros
        assert stdout.count('.') == 0 or not stdout.endswith('0')


class TestNegativeTemperatures:
    """Test handling of negative temperatures"""

    def test_negative_celsius(self):
        """Negative Celsius should be allowed"""
        stdout, stderr, code = run_tempconv('-50', 'C', 'F')
        assert code == 0
        # -50C = -58F
        assert stdout == '-58'

    def test_negative_fahrenheit(self):
        """Negative Fahrenheit should be allowed"""
        stdout, stderr, code = run_tempconv('-58', 'F', 'C')
        assert code == 0
        assert stdout == '-50'


class TestLargeNumbers:
    """Test handling of large temperature values"""

    def test_large_celsius_to_kelvin(self):
        """Large positive Celsius values"""
        stdout, stderr, code = run_tempconv('1000', 'C', 'K')
        assert code == 0
        assert stdout == '1273.15'

    def test_large_kelvin_to_celsius(self):
        """Large Kelvin values"""
        stdout, stderr, code = run_tempconv('1273.15', 'K', 'C')
        assert code == 0
        assert stdout == '1000'


class TestDecimalInputs:
    """Test handling of decimal input values"""

    def test_decimal_celsius_to_fahrenheit(self):
        """Decimal Celsius input"""
        stdout, stderr, code = run_tempconv('36.5', 'C', 'F')
        assert code == 0
        # 36.5C = 97.7F
        assert stdout == '97.7'

    def test_decimal_kelvin_input(self):
        """Decimal Kelvin input"""
        stdout, stderr, code = run_tempconv('273.15', 'K', 'C')
        assert code == 0
        assert stdout == '0'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
