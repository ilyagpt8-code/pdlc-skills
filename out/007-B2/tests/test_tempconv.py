"""
Comprehensive test suite for tempconv utility.

Tests cover all conversion pairs, boundary cases, error conditions,
and output format requirements.
"""

import subprocess
import sys
import os


# Get the repository root directory
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
TEMPCONV_PATH = os.path.join(REPO_ROOT, 'out', '007-B2', 'tempconv.py')


def run_tempconv(value, from_scale, to_scale):
    """
    Run tempconv utility and return (output, error, exit_code).
    """
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH, str(value), str(from_scale), str(to_scale)],
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_001_celsius_to_fahrenheit_freezing():
    """№1: 0 C F → 32"""
    out, err, code = run_tempconv('0', 'C', 'F')
    assert code == 0, f"Exit code: expected 0, got {code}. stderr: {err}"
    assert out == "32", f"Output: expected '32', got '{out}'"


def test_002_celsius_to_fahrenheit_boiling():
    """№2: 100 C F → 212"""
    out, err, code = run_tempconv('100', 'C', 'F')
    assert code == 0
    assert out == "212", f"Output: expected '212', got '{out}'"


def test_003_fahrenheit_to_celsius_freezing():
    """№3: 32 F C → 0"""
    out, err, code = run_tempconv('32', 'F', 'C')
    assert code == 0
    assert out == "0", f"Output: expected '0', got '{out}'"


def test_004_fahrenheit_to_celsius_boiling():
    """№4: 212 F C → 100"""
    out, err, code = run_tempconv('212', 'F', 'C')
    assert code == 0
    assert out == "100", f"Output: expected '100', got '{out}'"


def test_005_celsius_to_kelvin_freezing():
    """№5: 0 C K → 273.15"""
    out, err, code = run_tempconv('0', 'C', 'K')
    assert code == 0
    # Check value with tolerance for floating point
    value = float(out)
    assert abs(value - 273.15) < 0.01, f"Output: expected ~273.15, got {out}"


def test_006_kelvin_to_celsius_freezing():
    """№6: 273.15 K C → 0"""
    out, err, code = run_tempconv('273.15', 'K', 'C')
    assert code == 0
    value = float(out)
    assert abs(value - 0) < 0.01, f"Output: expected ~0, got {out}"


def test_007_kelvin_to_fahrenheit_freezing():
    """№7: 273.15 K F → 32"""
    out, err, code = run_tempconv('273.15', 'K', 'F')
    assert code == 0
    value = float(out)
    assert abs(value - 32) < 0.01, f"Output: expected ~32, got {out}"


def test_008_fahrenheit_to_kelvin_freezing():
    """№8: 32 F K → 273.15"""
    out, err, code = run_tempconv('32', 'F', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 273.15) < 0.01, f"Output: expected ~273.15, got {out}"


def test_009_room_temp_c_to_f():
    """№9: 25 C F → 77"""
    out, err, code = run_tempconv('25', 'C', 'F')
    assert code == 0
    value = float(out)
    assert abs(value - 77) < 0.01, f"Output: expected ~77, got {out}"


def test_010_room_temp_c_to_k():
    """№10: 20 C K → 293.15"""
    out, err, code = run_tempconv('20', 'C', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 293.15) < 0.01, f"Output: expected ~293.15, got {out}"


def test_011_absolute_zero_k_to_c():
    """№11: 0 K C → -273.15"""
    out, err, code = run_tempconv('0', 'K', 'C')
    assert code == 0
    value = float(out)
    assert abs(value - (-273.15)) < 0.01, f"Output: expected ~-273.15, got {out}"


def test_012_absolute_zero_c_to_k():
    """№12: -273.15 C K → 0"""
    out, err, code = run_tempconv('-273.15', 'C', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 0) < 0.01, f"Output: expected ~0, got {out}"


def test_013_absolute_zero_f_to_k():
    """№13: -459.67 F K → 0"""
    out, err, code = run_tempconv('-459.67', 'F', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 0) < 0.01, f"Output: expected ~0, got {out}"


def test_014_absolute_zero_k_to_f():
    """№14: 0 K F → -459.67"""
    out, err, code = run_tempconv('0', 'K', 'F')
    assert code == 0
    value = float(out)
    assert abs(value - (-459.67)) < 0.01, f"Output: expected ~-459.67, got {out}"


def test_015_below_absolute_zero_celsius():
    """№15: -273.16 C K → Error 3"""
    out, err, code = run_tempconv('-273.16', 'C', 'K')
    assert code == 3, f"Exit code: expected 3, got {code}"
    assert "Error: temperature below absolute zero" in err


def test_016_negative_kelvin():
    """№16: -1 K C → Error 3"""
    out, err, code = run_tempconv('-1', 'K', 'C')
    assert code == 3, f"Exit code: expected 3, got {code}"
    assert "Error: temperature below absolute zero" in err


def test_017_below_absolute_zero_fahrenheit():
    """№17: -459.68 F K → Error 3"""
    out, err, code = run_tempconv('-459.68', 'F', 'K')
    assert code == 3, f"Exit code: expected 3, got {code}"
    assert "Error: temperature below absolute zero" in err


def test_018_significantly_below_absolute_zero():
    """№18: -274 C K → Error 3"""
    out, err, code = run_tempconv('-274', 'C', 'K')
    assert code == 3, f"Exit code: expected 3, got {code}"
    assert "Error: temperature below absolute zero" in err


def test_019_same_scale_c_to_c():
    """№19: 25 C C → 25"""
    out, err, code = run_tempconv('25', 'C', 'C')
    assert code == 0
    assert out == "25", f"Output: expected '25', got '{out}'"


def test_020_same_scale_f_to_f():
    """№20: 100 F F → 100"""
    out, err, code = run_tempconv('100', 'F', 'F')
    assert code == 0
    assert out == "100", f"Output: expected '100', got '{out}'"


def test_021_same_scale_k_to_k():
    """№21: 300 K K → 300"""
    out, err, code = run_tempconv('300', 'K', 'K')
    assert code == 0
    assert out == "300", f"Output: expected '300', got '{out}'"


def test_022_invalid_arguments_only_value():
    """№22: tempconv 0 → Error 4"""
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH, '0'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 4
    assert "Error: invalid arguments" in result.stderr


def test_023_invalid_arguments_no_args():
    """№23: tempconv → Error 4"""
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH],
        capture_output=True,
        text=True
    )
    assert result.returncode == 4
    assert "Error: invalid arguments" in result.stderr


def test_024_invalid_arguments_too_many():
    """№24: tempconv 0 C F extra → Error 4"""
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH, '0', 'C', 'F', 'extra'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 4
    assert "Error: invalid arguments" in result.stderr


def test_025_invalid_arguments_missing_to_scale():
    """№25: tempconv 0 C → Error 4"""
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH, '0', 'C'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 4
    assert "Error: invalid arguments" in result.stderr


def test_026_invalid_value_abc():
    """№26: abc C F → Error 1"""
    out, err, code = run_tempconv('abc', 'C', 'F')
    assert code == 1, f"Exit code: expected 1, got {code}"
    assert "Error: invalid value" in err


def test_027_invalid_value_multiple_decimals():
    """№27: 12.34.56 C F → Error 1"""
    out, err, code = run_tempconv('12.34.56', 'C', 'F')
    assert code == 1, f"Exit code: expected 1, got {code}"
    assert "Error: invalid value" in err


def test_028_scale_name_as_value():
    """№28: C F → Error 4 (invalid arguments, not enough args)"""
    result = subprocess.run(
        [sys.executable, TEMPCONV_PATH, 'C', 'F'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 4
    assert "Error: invalid arguments" in result.stderr


def test_029_scientific_notation():
    """№29: 1e100 C K → Check if accepted"""
    # Scientific notation should be accepted as valid float
    out, err, code = run_tempconv('1e100', 'C', 'K')
    # This is an extremely large temperature, far above room temp
    # It should convert successfully or fail on scientific notation parsing
    # Python's float() accepts scientific notation, so this should work
    assert code == 0 or code == 1, f"Unexpected exit code: {code}"


def test_030_invalid_scale_x_from():
    """№30: 0 X F → Error 2"""
    out, err, code = run_tempconv('0', 'X', 'F')
    assert code == 2, f"Exit code: expected 2, got {code}"
    assert "Error: invalid scale" in err


def test_031_invalid_scale_x_to():
    """№31: 0 C X → Error 2"""
    out, err, code = run_tempconv('0', 'C', 'X')
    assert code == 2, f"Exit code: expected 2, got {code}"
    assert "Error: invalid scale" in err


def test_032_invalid_scale_double_letter():
    """№32: 0 CC F → Error 2"""
    out, err, code = run_tempconv('0', 'CC', 'F')
    assert code == 2, f"Exit code: expected 2, got {code}"
    assert "Error: invalid scale" in err


def test_033_case_insensitive_lowercase():
    """№33: 0 c f → 32 (case-insensitive)"""
    out, err, code = run_tempconv('0', 'c', 'f')
    assert code == 0
    assert out == "32", f"Output: expected '32', got '{out}'"


def test_034_case_insensitive_mixed():
    """№34: 0 C f → 32 (case-insensitive)"""
    out, err, code = run_tempconv('0', 'C', 'f')
    assert code == 0
    assert out == "32", f"Output: expected '32', got '{out}'"


def test_035_decimal_result_precision():
    """№35: 0.5 C F → 32.9"""
    out, err, code = run_tempconv('0.5', 'C', 'F')
    assert code == 0
    value = float(out)
    assert abs(value - 32.9) < 0.01, f"Output: expected ~32.9, got {out}"


def test_036_kelvin_decimal_output():
    """№36: 1.5 C K → 274.65"""
    out, err, code = run_tempconv('1.5', 'C', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 274.65) < 0.01, f"Output: expected ~274.65, got {out}"


def test_037_result_rounding_to_integer():
    """№37: 98.6 F C → 37"""
    out, err, code = run_tempconv('98.6', 'F', 'C')
    assert code == 0
    value = float(out)
    assert abs(value - 37) < 0.01, f"Output: expected ~37, got {out}"


def test_038_negative_but_valid_special_case():
    """№38: -40 C F → -40 (special case: -40°C = -40°F)"""
    out, err, code = run_tempconv('-40', 'C', 'F')
    assert code == 0
    value = float(out)
    assert abs(value - (-40)) < 0.01, f"Output: expected ~-40, got {out}"


def test_039_negative_celsius_above_absolute_zero():
    """№39: -200 C K → 73.15"""
    out, err, code = run_tempconv('-200', 'C', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 73.15) < 0.01, f"Output: expected ~73.15, got {out}"


def test_040_negative_kelvin():
    """№40: -10 K C → Error 3"""
    out, err, code = run_tempconv('-10', 'K', 'C')
    assert code == 3, f"Exit code: expected 3, got {code}"
    assert "Error: temperature below absolute zero" in err


def test_041_fahrenheit_zero_to_celsius():
    """№41: 0 F C → Check rounding for repeating decimal"""
    out, err, code = run_tempconv('0', 'F', 'C')
    assert code == 0
    value = float(out)
    # 0°F = -17.777...°C (repeating)
    assert abs(value - (-17.777)) < 0.01, f"Output: expected ~-17.777, got {out}"


def test_042_same_scale_kelvin_decimal():
    """№42: 273.15 K K → 273.15"""
    out, err, code = run_tempconv('273.15', 'K', 'K')
    assert code == 0
    value = float(out)
    assert abs(value - 273.15) < 0.01, f"Output: expected ~273.15, got {out}"


if __name__ == '__main__':
    # Run with pytest
    pytest_args = [__file__, '-v']
    import pytest
    pytest.main(pytest_args)
