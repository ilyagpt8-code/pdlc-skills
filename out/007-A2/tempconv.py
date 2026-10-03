#!/usr/bin/env python3
"""
Temperature conversion utility - tempconv
Converts temperatures between Celsius, Fahrenheit, and Kelvin scales.
"""

import sys
from decimal import Decimal, ROUND_HALF_UP


def parse_value(value_str):
    """
    Parse a temperature value string into a float.
    Rejects scientific notation and explicit positive signs.
    Returns (float, error_message) tuple.
    """
    # Check for empty string
    if not value_str or value_str.isspace():
        return None, "value is not a valid number"

    # Reject scientific notation (e or E)
    if 'e' in value_str.lower():
        return None, "value is not a valid number"

    # Reject explicit positive sign (but allow negative)
    if value_str.startswith('+'):
        return None, "value is not a valid number"

    # Try to parse as float
    try:
        # Use Decimal for accurate parsing
        value = float(value_str)
        return value, None
    except ValueError:
        return None, "value is not a valid number"


def validate_scale(scale):
    """
    Validate that scale is one of C, F, K (case-sensitive).
    Returns (is_valid, error_message) tuple.
    """
    if scale not in ('C', 'F', 'K'):
        return False, f"invalid scale '{scale}' (expected C, F, or K)"
    return True, None


def convert_temperature(value, from_scale, to_scale):
    """
    Convert temperature from one scale to another.
    Returns (result, error_message) tuple where result is in target scale or None if error.
    """
    # If converting to same scale, return as-is
    if from_scale == to_scale:
        return value, None

    # Convert to Celsius first (intermediate scale)
    if from_scale == 'C':
        celsius = value
    elif from_scale == 'F':
        celsius = (value - 32) * 5 / 9
    elif from_scale == 'K':
        celsius = value - 273.15

    # Convert from Celsius to target scale
    if to_scale == 'C':
        result = celsius
    elif to_scale == 'F':
        result = celsius * 9 / 5 + 32
    elif to_scale == 'K':
        result = celsius + 273.15

    # Check for absolute zero violation (result in target scale must be >= 0 K)
    if to_scale == 'K' and result < 0:
        return None, f"temperature below absolute zero (result would be {format_output(result)} K)"

    return result, None


def format_output(value):
    """
    Format a float value to exactly 2 decimal places using away-from-zero rounding.
    """
    # Use Decimal for precise rounding
    d = Decimal(str(value))
    # Round to 2 decimal places, away from zero
    rounded = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    # Format with exactly 2 decimal places
    return f"{float(rounded):.2f}"


def main():
    """Main entry point for tempconv utility."""
    # Check argument count
    if len(sys.argv) != 4:
        if len(sys.argv) < 4:
            error_msg = "insufficient number of arguments"
        else:
            error_msg = "too many arguments"
        sys.stderr.write(f"Error: {error_msg}\n")
        sys.exit(1)

    value_str = sys.argv[1]
    from_scale = sys.argv[2]
    to_scale = sys.argv[3]

    # Parse value
    value, error = parse_value(value_str)
    if error:
        sys.stderr.write(f"Error: {error}\n")
        sys.exit(1)

    # Validate scales
    is_valid, error = validate_scale(from_scale)
    if not is_valid:
        sys.stderr.write(f"Error: {error}\n")
        sys.exit(1)

    is_valid, error = validate_scale(to_scale)
    if not is_valid:
        sys.stderr.write(f"Error: {error}\n")
        sys.exit(1)

    # Convert temperature
    result, error = convert_temperature(value, from_scale, to_scale)
    if error:
        sys.stderr.write(f"Error: {error}\n")
        sys.exit(2)

    # Output result
    output = format_output(result)
    sys.stdout.write(f"{output}\n")
    sys.exit(0)


if __name__ == '__main__':
    main()
