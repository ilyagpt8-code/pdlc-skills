#!/usr/bin/env python3
"""
tempconv - Temperature Converter Utility

A simple command-line utility to convert temperatures between
Celsius (C), Fahrenheit (F), and Kelvin (K).
"""

import sys


def parse_arguments(args):
    """
    Parse and validate command-line arguments.

    Returns:
        tuple: (value, from_unit, to_unit) if valid
        None: if arguments are invalid

    Exits with code 1 if argument count is wrong.
    """
    if len(args) != 3:
        print("Usage: tempconv <value> <from_unit> <to_unit>", file=sys.stderr)
        sys.exit(1)

    value_str, from_unit, to_unit = args

    # Try to parse the value
    try:
        value = float(value_str)
    except ValueError:
        print(f"Error: invalid numeric value '{value_str}'", file=sys.stderr)
        sys.exit(1)

    # Normalize units to uppercase
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()

    return value, from_unit, to_unit


def validate_unit(unit):
    """
    Validate that a unit is one of C, F, K.

    Args:
        unit: Unit string (already uppercase)

    Returns:
        bool: True if valid, False otherwise
    """
    return unit in ('C', 'F', 'K')


def validate_temperature(value, unit):
    """
    Validate that temperature is not below absolute zero.

    Args:
        value: Temperature value
        unit: Unit (C, F, or K)

    Returns:
        bool: True if valid, False otherwise
    """
    absolute_zero = {
        'C': -273.15,
        'F': -459.67,
        'K': 0.0
    }

    return value >= absolute_zero[unit]


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    return celsius * (9/5) + 32


def fahrenheit_to_celsius(fahrenheit):
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32) * (5/9)


def celsius_to_kelvin(celsius):
    """Convert Celsius to Kelvin."""
    return celsius + 273.15


def kelvin_to_celsius(kelvin):
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15


def fahrenheit_to_kelvin(fahrenheit):
    """Convert Fahrenheit to Kelvin."""
    celsius = fahrenheit_to_celsius(fahrenheit)
    return celsius_to_kelvin(celsius)


def kelvin_to_fahrenheit(kelvin):
    """Convert Kelvin to Fahrenheit."""
    celsius = kelvin_to_celsius(kelvin)
    return celsius_to_fahrenheit(celsius)


def convert_temperature(value, from_unit, to_unit):
    """
    Convert temperature from one unit to another.

    Args:
        value: Temperature value
        from_unit: Source unit (C, F, or K)
        to_unit: Target unit (C, F, or K)

    Returns:
        float: Converted temperature value
    """
    # If converting to the same unit, return as-is
    if from_unit == to_unit:
        return value

    # Map conversion functions
    converters = {
        ('C', 'F'): celsius_to_fahrenheit,
        ('C', 'K'): celsius_to_kelvin,
        ('F', 'C'): fahrenheit_to_celsius,
        ('F', 'K'): fahrenheit_to_kelvin,
        ('K', 'C'): kelvin_to_celsius,
        ('K', 'F'): kelvin_to_fahrenheit,
    }

    key = (from_unit, to_unit)
    if key in converters:
        return converters[key](value)

    # Should never reach here if units are validated
    raise ValueError(f"Unknown conversion: {from_unit} to {to_unit}")


def format_output(value):
    """
    Format the output value.

    Args:
        value: The temperature value

    Returns:
        str: Formatted output
    """
    # Round to 2 decimal places
    rounded = round(value, 2)

    # Format as integer if it's a whole number, otherwise as float
    if rounded == int(rounded):
        return str(int(rounded))
    else:
        return str(rounded)


def main():
    """Main entry point."""
    value, from_unit, to_unit = parse_arguments(sys.argv[1:])

    # Validate units
    if not validate_unit(from_unit):
        print(
            f"Error: unknown unit '{from_unit}'; valid units are C, F, K",
            file=sys.stderr
        )
        sys.exit(2)

    if not validate_unit(to_unit):
        print(
            f"Error: unknown unit '{to_unit}'; valid units are C, F, K",
            file=sys.stderr
        )
        sys.exit(2)

    # Validate temperature is not below absolute zero
    if not validate_temperature(value, from_unit):
        absolute_zero = {
            'C': -273.15,
            'F': -459.67,
            'K': 0.0
        }
        print(
            f"Error: temperature {value} {from_unit} is below absolute zero "
            f"(minimum {absolute_zero[from_unit]} {from_unit})",
            file=sys.stderr
        )
        sys.exit(3)

    # Convert the temperature
    result = convert_temperature(value, from_unit, to_unit)

    # Output the result
    print(format_output(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
