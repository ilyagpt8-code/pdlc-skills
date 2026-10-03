#!/usr/bin/env python3
"""
Temperature Converter Utility

Converts temperature values between Celsius (C), Fahrenheit (F), and Kelvin (K).
"""

import sys


def parse_arguments(args):
    """
    Parse and validate command-line arguments.

    Returns:
        tuple: (value_str, from_scale, to_scale) if valid
        None: if invalid argument count
    """
    if len(args) != 3:
        return None
    return args[0], args[1], args[2]


def parse_numeric_value(value_str):
    """
    Parse a numeric value from string.

    Returns:
        float: the parsed value
        None: if value is not a valid number
    """
    try:
        return float(value_str)
    except ValueError:
        return None


def validate_scale(scale):
    """
    Validate and normalize scale name.

    Returns:
        str: normalized scale ('C', 'F', or 'K')
        None: if scale is invalid
    """
    if scale.upper() in ('C', 'F', 'K'):
        return scale.upper()
    return None


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32


def fahrenheit_to_celsius(fahrenheit):
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32) * 5/9


def celsius_to_kelvin(celsius):
    """Convert Celsius to Kelvin."""
    return celsius + 273.15


def kelvin_to_celsius(kelvin):
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15


def fahrenheit_to_kelvin(fahrenheit):
    """Convert Fahrenheit to Kelvin."""
    return (fahrenheit - 32) * 5/9 + 273.15


def kelvin_to_fahrenheit(kelvin):
    """Convert Kelvin to Fahrenheit."""
    return (kelvin - 273.15) * 9/5 + 32


def convert(value, from_scale, to_scale):
    """
    Convert temperature from one scale to another.

    Returns:
        float: the converted value
    """
    # If same scale, return unchanged
    if from_scale == to_scale:
        return value

    # Convert to Celsius as intermediate scale
    if from_scale == 'C':
        celsius = value
    elif from_scale == 'F':
        celsius = fahrenheit_to_celsius(value)
    else:  # 'K'
        celsius = kelvin_to_celsius(value)

    # Convert from Celsius to target scale
    if to_scale == 'C':
        return celsius
    elif to_scale == 'F':
        return celsius_to_fahrenheit(celsius)
    else:  # 'K'
        return celsius_to_kelvin(celsius)


def format_output(value):
    """
    Format temperature value for output.

    Removes unnecessary trailing zeros while maintaining precision.
    """
    # Round to reasonable precision (15 significant digits for float)
    # Then format to remove trailing zeros
    result = f"{value:.15g}"

    # Ensure at least 2 decimal places for precision-critical values
    # But only if value has meaningful decimals
    if '.' in result:
        parts = result.split('.')
        if len(parts[1]) == 1:
            # If only 1 decimal place, keep it as is for readability
            pass
        return result
    else:
        return result


def is_below_absolute_zero(celsius):
    """
    Check if temperature is below absolute zero.

    Absolute zero is -273.15°C (0 K).
    """
    return celsius < -273.15


def main():
    """Main entry point."""
    args = sys.argv[1:]

    # Parse arguments
    parsed = parse_arguments(args)
    if parsed is None:
        sys.stderr.write("Error: invalid arguments\n")
        sys.exit(4)

    value_str, from_scale_str, to_scale_str = parsed

    # Parse numeric value
    value = parse_numeric_value(value_str)
    if value is None:
        sys.stderr.write("Error: invalid value\n")
        sys.exit(1)

    # Validate scales
    from_scale = validate_scale(from_scale_str)
    if from_scale is None:
        sys.stderr.write("Error: invalid scale\n")
        sys.exit(2)

    to_scale = validate_scale(to_scale_str)
    if to_scale is None:
        sys.stderr.write("Error: invalid scale\n")
        sys.exit(2)

    # Check for temperatures below absolute zero
    # First convert input to Celsius to check
    if from_scale == 'C':
        celsius_value = value
    elif from_scale == 'F':
        celsius_value = fahrenheit_to_celsius(value)
    else:  # 'K'
        celsius_value = kelvin_to_celsius(value)

    if is_below_absolute_zero(celsius_value):
        sys.stderr.write("Error: temperature below absolute zero\n")
        sys.exit(3)

    # Perform conversion
    result = convert(value, from_scale, to_scale)

    # Format and output
    output = format_output(result)
    print(output)
    sys.exit(0)


if __name__ == '__main__':
    main()
