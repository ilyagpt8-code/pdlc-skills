"""
Comprehensive tests for tempconv temperature converter utility.
"""

import pytest
import subprocess
import sys
from pathlib import Path


# Path to the tempconv script
TEMPCONV_PATH = Path(__file__).parent.parent / "tempconv.py"


def run_tempconv(*args):
    """Run tempconv and return (stdout, stderr, exit_code)"""
    result = subprocess.run(
        [sys.executable, str(TEMPCONV_PATH)] + list(args),
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


class TestBasicConversions:
    """Test cases 1-6: Basic conversions between scales"""

    def test_celsius_to_fahrenheit(self):
        """Case 1: 0 C to F should be 32 F"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        assert "32" in stdout
        assert "F" in stdout

    def test_fahrenheit_to_celsius(self):
        """Case 2: 32 F to C should be 0 C"""
        stdout, stderr, code = run_tempconv("32", "F", "C")
        assert code == 0
        assert "0" in stdout
        assert "C" in stdout

    def test_celsius_to_kelvin(self):
        """Case 3: 0 C to K should be 273.15 K"""
        stdout, stderr, code = run_tempconv("0", "C", "K")
        assert code == 0
        assert "273.15" in stdout
        assert "K" in stdout

    def test_kelvin_to_celsius(self):
        """Case 4: 273.15 K to C should be 0 C"""
        stdout, stderr, code = run_tempconv("273.15", "K", "C")
        assert code == 0
        assert "0" in stdout
        assert "C" in stdout

    def test_fahrenheit_to_kelvin(self):
        """Case 5: 32 F to K should be 273.15 K"""
        stdout, stderr, code = run_tempconv("32", "F", "K")
        assert code == 0
        assert "273.15" in stdout
        assert "K" in stdout

    def test_kelvin_to_fahrenheit(self):
        """Case 6: 273.15 K to F should be 32 F"""
        stdout, stderr, code = run_tempconv("273.15", "K", "F")
        assert code == 0
        assert "32" in stdout
        assert "F" in stdout


class TestAllConversions:
    """Test cases 7-9: Converting to all scales when to_scale not specified"""

    def test_celsius_all_scales(self):
        """Case 7: 0 C should output F and K lines (no C)"""
        stdout, stderr, code = run_tempconv("0", "C")
        assert code == 0
        lines = stdout.split('\n')
        assert len(lines) == 2
        # Should have F and K, but not C
        has_f = any("F" in line for line in lines)
        has_k = any("K" in line for line in lines)
        has_c = any(line.endswith("C") for line in lines)  # Only C at end
        assert has_f
        assert has_k
        assert not has_c

    def test_fahrenheit_all_scales(self):
        """Case 8: 32 F should output C and K lines (no F)"""
        stdout, stderr, code = run_tempconv("32", "F")
        assert code == 0
        lines = stdout.split('\n')
        assert len(lines) == 2
        # Should have C and K, but not F
        has_c = any("C" in line for line in lines)
        has_k = any("K" in line for line in lines)
        has_f = any(line.endswith("F") for line in lines)  # Only F at end
        assert has_c
        assert has_k
        assert not has_f

    def test_kelvin_all_scales(self):
        """Case 9: 273.15 K should output C and F lines (no K)"""
        stdout, stderr, code = run_tempconv("273.15", "K")
        assert code == 0
        lines = stdout.split('\n')
        assert len(lines) == 2
        # Should have C and F, but not K
        has_c = any("C" in line for line in lines)
        has_f = any("F" in line for line in lines)
        has_k = any(line.endswith("K") for line in lines)  # Only K at end
        assert has_c
        assert has_f
        assert not has_k


class TestBoundaryValues:
    """Test cases 10-14: Boundary values (absolute zero, boiling point)"""

    def test_absolute_zero_celsius_to_fahrenheit(self):
        """Case 10: -273.15 C to F should be -459.67 F"""
        stdout, stderr, code = run_tempconv("-273.15", "C", "F")
        assert code == 0
        assert "-459.67" in stdout or "-459.67" in stdout.replace(" ", "")

    def test_absolute_zero_fahrenheit_to_celsius(self):
        """Case 11: -459.67 F to C should be -273.15 C"""
        stdout, stderr, code = run_tempconv("-459.67", "F", "C")
        assert code == 0
        assert "-273.15" in stdout or "-273.15" in stdout.replace(" ", "")

    def test_absolute_zero_kelvin_to_celsius(self):
        """Case 12: 0 K to C should be -273.15 C"""
        stdout, stderr, code = run_tempconv("0", "K", "C")
        assert code == 0
        assert "-273.15" in stdout or "-273.15" in stdout.replace(" ", "")

    def test_water_boiling_point_celsius(self):
        """Case 13: 100 C to F should be 212 F"""
        stdout, stderr, code = run_tempconv("100", "C", "F")
        assert code == 0
        assert "212" in stdout

    def test_water_boiling_point_fahrenheit(self):
        """Case 14: 212 F to C should be 100 C"""
        stdout, stderr, code = run_tempconv("212", "F", "C")
        assert code == 0
        assert "100" in stdout


class TestNegativeValues:
    """Test cases 15-17: Negative temperatures"""

    def test_negative_celsius(self):
        """Case 15: -50 C to F should work"""
        stdout, stderr, code = run_tempconv("-50", "C", "F")
        assert code == 0
        # -50 C = (-50 * 9/5) + 32 = -90 + 32 = -58 F
        assert "-58" in stdout

    def test_negative_fahrenheit(self):
        """Case 16: -50 F to C should work"""
        stdout, stderr, code = run_tempconv("-50", "F", "C")
        assert code == 0
        # -50 F = (-50 - 32) * 5/9 = -82 * 5/9 ≈ -45.56 C
        assert "-45" in stdout

    def test_negative_celsius_near_absolute_zero(self):
        """Case 17: -100 C to F should work"""
        stdout, stderr, code = run_tempconv("-100", "C", "F")
        assert code == 0
        # -100 C = (-100 * 9/5) + 32 = -180 + 32 = -148 F
        assert "-148" in stdout


class TestScientificNotation:
    """Test cases 18-21: Scientific notation and small values"""

    def test_scientific_notation_100(self):
        """Case 18: 1e2 C to F should work (1e2 = 100)"""
        stdout, stderr, code = run_tempconv("1e2", "C", "F")
        assert code == 0
        assert "212" in stdout

    def test_small_decimal(self):
        """Case 19: 0.5 C to F should work"""
        stdout, stderr, code = run_tempconv("0.5", "C", "F")
        assert code == 0
        # 0.5 C = (0.5 * 9/5) + 32 = 0.9 + 32 = 32.9 F
        assert "32.9" in stdout or "32.90" in stdout

    def test_very_small_decimal(self):
        """Case 20: 0.001 C to F should work"""
        stdout, stderr, code = run_tempconv("0.001", "C", "F")
        assert code == 0

    def test_scientific_notation_small(self):
        """Case 21: 1.5e-3 C to F should work"""
        stdout, stderr, code = run_tempconv("1.5e-3", "C", "F")
        assert code == 0


class TestCaseInsensitivity:
    """Test cases 22-25: Case-insensitive scale input"""

    def test_lowercase_from_scale(self):
        """Case 22: 0 c F should work"""
        stdout, stderr, code = run_tempconv("0", "c", "F")
        assert code == 0
        assert "32" in stdout

    def test_lowercase_to_scale(self):
        """Case 23: 0 C f should work"""
        stdout, stderr, code = run_tempconv("0", "C", "f")
        assert code == 0
        assert "32" in stdout

    def test_lowercase_both_scales(self):
        """Case 24: 0 c f should work"""
        stdout, stderr, code = run_tempconv("0", "c", "f")
        assert code == 0
        assert "32" in stdout

    def test_uppercase_both_scales(self):
        """Case 25: 0 C F should work (baseline)"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        assert "32" in stdout


class TestInvalidNumber:
    """Test cases 26-28: Invalid number format"""

    def test_non_numeric_value(self):
        """Case 26: 'abc C F' should error with code 2"""
        stdout, stderr, code = run_tempconv("abc", "C", "F")
        assert code == 2
        assert "Error" in stderr

    def test_invalid_number_format(self):
        """Case 27: '1.2.3 C F' should error with code 2"""
        stdout, stderr, code = run_tempconv("1.2.3", "C", "F")
        assert code == 2
        assert "Error" in stderr

    def test_plus_sign_number(self):
        """Case 28: '+1.5 C F' - implementation may accept or reject"""
        stdout, stderr, code = run_tempconv("+1.5", "C", "F")
        # Python's float() accepts +1.5, so this should work
        assert code == 0


class TestInvalidScale:
    """Test cases 29-32: Invalid scale input"""

    def test_unknown_from_scale(self):
        """Case 29: '0 R F' should error with code 2"""
        stdout, stderr, code = run_tempconv("0", "R", "F")
        assert code == 2
        assert "Error" in stderr

    def test_unknown_to_scale(self):
        """Case 30: '0 C R' should error with code 2"""
        stdout, stderr, code = run_tempconv("0", "C", "R")
        assert code == 2
        assert "Error" in stderr

    def test_full_word_scale(self):
        """Case 31: '0 Celsius F' should error with code 2"""
        stdout, stderr, code = run_tempconv("0", "Celsius", "F")
        assert code == 2
        assert "Error" in stderr

    def test_multiple_char_scale(self):
        """Case 32: '0 CC F' should error with code 2"""
        stdout, stderr, code = run_tempconv("0", "CC", "F")
        assert code == 2
        assert "Error" in stderr


class TestAbsoluteZeroViolation:
    """Test cases 33-35: Temperatures below absolute zero"""

    def test_below_absolute_zero_celsius(self):
        """Case 33: '-300 C F' should error with code 3"""
        stdout, stderr, code = run_tempconv("-300", "C", "F")
        assert code == 3
        assert "Error" in stderr
        assert "absolute zero" in stderr.lower()

    def test_below_absolute_zero_fahrenheit(self):
        """Case 34: '-500 F C' should error with code 3"""
        stdout, stderr, code = run_tempconv("-500", "F", "C")
        assert code == 3
        assert "Error" in stderr
        assert "absolute zero" in stderr.lower()

    def test_below_absolute_zero_kelvin(self):
        """Case 35: '-1 K C' should error with code 3"""
        stdout, stderr, code = run_tempconv("-1", "K", "C")
        assert code == 3
        assert "Error" in stderr
        assert "absolute zero" in stderr.lower()


class TestArgumentErrors:
    """Test cases 36-38: Argument count errors"""

    def test_missing_from_scale(self):
        """Case 36: '100' should error with code 1"""
        stdout, stderr, code = run_tempconv("100")
        assert code == 1
        assert "Error" in stderr

    def test_too_many_arguments(self):
        """Case 37: '100 C F K' should error with code 1"""
        stdout, stderr, code = run_tempconv("100", "C", "F", "K")
        assert code == 1
        assert "Error" in stderr

    def test_no_arguments(self):
        """Case 38: no args should error with code 1"""
        stdout, stderr, code = run_tempconv()
        assert code == 1
        assert "Error" in stderr


class TestPrecisionAndEdgeCases:
    """Test cases 39-40: Precision and special cases"""

    def test_fractional_precision(self):
        """Case 39: '0.125 C F' should work with proper precision"""
        stdout, stderr, code = run_tempconv("0.125", "C", "F")
        assert code == 0
        # 0.125 C = (0.125 * 9/5) + 32 = 0.225 + 32 = 32.225 F
        assert "32" in stdout

    def test_same_scale_conversion(self):
        """Case 40: '32 F F' - same from and to scale"""
        stdout, stderr, code = run_tempconv("32", "F", "F")
        # Specification doesn't forbid this
        assert code == 0
        assert "32" in stdout
        assert "F" in stdout


class TestOutputFormat:
    """Additional tests for output format correctness"""

    def test_single_scale_output_format(self):
        """Verify output format is '<value> <scale>'"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        # Should have exactly one line with value and scale
        lines = stdout.split('\n')
        assert len(lines) == 1
        parts = lines[0].split()
        assert len(parts) == 2
        assert parts[1] == 'F'

    def test_all_scales_output_order(self):
        """Verify output order is C, F, K when no target specified"""
        stdout, stderr, code = run_tempconv("0", "C")
        assert code == 0
        lines = stdout.split('\n')
        assert len(lines) == 2
        # First line should be F (32 F)
        assert "F" in lines[0]
        # Second line should be K (273.15 K)
        assert "K" in lines[1]

    def test_no_stderr_on_success(self):
        """Successful runs should have empty stderr"""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0
        assert stderr == ""

    def test_stderr_on_error(self):
        """Errors should write to stderr, not stdout"""
        stdout, stderr, code = run_tempconv("abc", "C", "F")
        assert code == 2
        assert "Error" in stderr
        assert stdout == ""


class TestRoundTripConversions:
    """Verify that converting back yields approximately the original value"""

    def test_celsius_roundtrip(self):
        """Convert C->F->C and check result"""
        # 25 C
        stdout1, _, code1 = run_tempconv("25", "C", "F")
        assert code1 == 0
        # Extract F value (should be around 77)
        f_value = float(stdout1.split()[0])
        # Convert back F->C
        stdout2, _, code2 = run_tempconv(str(f_value), "F", "C")
        assert code2 == 0
        c_value = float(stdout2.split()[0])
        # Should be approximately 25 C
        assert abs(c_value - 25) < 0.01

    def test_fahrenheit_roundtrip(self):
        """Convert F->C->F and check result"""
        # 68 F
        stdout1, _, code1 = run_tempconv("68", "F", "C")
        assert code1 == 0
        c_value = float(stdout1.split()[0])
        # Convert back C->F
        stdout2, _, code2 = run_tempconv(str(c_value), "C", "F")
        assert code2 == 0
        f_value = float(stdout2.split()[0])
        # Should be approximately 68 F
        assert abs(f_value - 68) < 0.01

    def test_kelvin_roundtrip(self):
        """Convert K->C->K and check result"""
        # 300 K
        stdout1, _, code1 = run_tempconv("300", "K", "C")
        assert code1 == 0
        c_value = float(stdout1.split()[0])
        # Convert back C->K
        stdout2, _, code2 = run_tempconv(str(c_value), "C", "K")
        assert code2 == 0
        k_value = float(stdout2.split()[0])
        # Should be approximately 300 K
        assert abs(k_value - 300) < 0.01


class TestMixedCase:
    """Test various case combinations"""

    def test_mixed_case_scales(self):
        """Test Ff, Kk, etc."""
        stdout, stderr, code = run_tempconv("0", "C", "F")
        assert code == 0

        stdout, stderr, code = run_tempconv("0", "c", "f")
        assert code == 0

        stdout, stderr, code = run_tempconv("0", "K", "c")
        assert code == 0
