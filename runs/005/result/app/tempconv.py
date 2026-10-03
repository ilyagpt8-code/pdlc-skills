#!/usr/bin/env python3
"""
Temperature Converter Utility
Converts temperature values between Celsius (C), Fahrenheit (F), and Kelvin (K).
"""

import sys


def format_output(value):
    """
    Format the output value with minimal necessary decimal places (up to 2).
    Removes all trailing zeros after the decimal point.

    Examples:
        32.0 -> "32"
        98.6 -> "98.6"
        273.15 -> "273.15"
        0.5 -> "0.5"
    """
    # Round to 2 decimal places
    rounded = round(value, 2)

    # Format with up to 2 decimal places
    if rounded == int(rounded):
        return str(int(rounded))
    else:
        # Format and remove trailing zeros
        formatted = f"{rounded:.2f}".rstrip('0').rstrip('.')
        return formatted


def validate_arguments(value_str, from_scale, to_scale):
    """
    Validate all three arguments.
    Returns (value, from_scale, to_scale) on success.
    Raises ValueError on any validation error.
    """
    # Validate value is a number
    try:
        value = float(value_str)
    except ValueError:
        raise ValueError("Value is not a valid number")

    # Validate scales are valid (case-sensitive)
    valid_scales = {'C', 'F', 'K'}

    if from_scale not in valid_scales:
        raise ValueError(f"Invalid scale '{from_scale}': must be C, F, or K")

    if to_scale not in valid_scales:
        raise ValueError(f"Invalid scale '{to_scale}': must be C, F, or K")

    # Validate Kelvin input is non-negative
    if from_scale == 'K' and value < 0:
        raise ValueError(f"Temperature in Kelvin cannot be negative: {value}K")

    return value, from_scale, to_scale


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit"""
    return (celsius * 9/5) + 32


def celsius_to_kelvin(celsius):
    """Convert Celsius to Kelvin"""
    return celsius + 273.15


def fahrenheit_to_celsius(fahrenheit):
    """Convert Fahrenheit to Celsius"""
    return (fahrenheit - 32) * 5/9


def fahrenheit_to_kelvin(fahrenheit):
    """Convert Fahrenheit to Kelvin"""
    return (fahrenheit - 32) * 5/9 + 273.15


def kelvin_to_celsius(kelvin):
    """Convert Kelvin to Celsius"""
    return kelvin - 273.15


def kelvin_to_fahrenheit(kelvin):
    """Convert Kelvin to Fahrenheit"""
    return (kelvin - 273.15) * 9/5 + 32


def convert(value, from_scale, to_scale):
    """
    Convert temperature from one scale to another.
    Returns the converted value.
    Raises ValueError if the conversion results in negative Kelvin.
    """
    # If converting to the same scale, return the value as-is
    if from_scale == to_scale:
        return value

    # Convert to Celsius first as intermediate scale
    if from_scale == 'C':
        celsius = value
    elif from_scale == 'F':
        celsius = fahrenheit_to_celsius(value)
    elif from_scale == 'K':
        celsius = kelvin_to_celsius(value)

    # Convert from Celsius to target scale
    if to_scale == 'C':
        result = celsius
    elif to_scale == 'F':
        result = celsius_to_fahrenheit(celsius)
    elif to_scale == 'K':
        result = celsius_to_kelvin(celsius)

    # Validate result is not negative Kelvin
    if to_scale == 'K' and result < 0:
        raise ValueError(f"Conversion results in temperature below absolute zero: {round(result, 2)}K")

    return result


def main():
    """Main entry point"""
    # Check for correct number of arguments
    if len(sys.argv) != 4:
        print("Error: Invalid number of arguments", file=sys.stderr)
        sys.exit(1)

    value_str, from_scale, to_scale = sys.argv[1:4]

    try:
        # Validate all arguments
        value, from_scale, to_scale = validate_arguments(value_str, from_scale, to_scale)

        # Perform conversion
        result = convert(value, from_scale, to_scale)

        # Output result with proper formatting
        print(format_output(result))
        sys.exit(0)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
