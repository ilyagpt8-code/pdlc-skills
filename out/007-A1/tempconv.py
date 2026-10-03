#!/usr/bin/env python3
"""
tempconv - Temperature converter utility
Converts temperature values between Celsius (C), Fahrenheit (F), and Kelvin (K)
"""

import sys


def format_output(value: float) -> str:
    """
    Format the output value with proper precision and trailing zero removal.
    Rules:
    - Round to 2 decimal places
    - Remove trailing zeros after the decimal point
    - If both decimals are zero, output as integer
    """
    # Round to 2 decimal places
    rounded = round(value, 2)

    # Format with 2 decimal places
    formatted = f"{rounded:.2f}"

    # Remove trailing zeros after decimal point
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.')

    return formatted


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit: F = C × 9/5 + 32"""
    return celsius * 9 / 5 + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius: C = (F − 32) × 5/9"""
    return (fahrenheit - 32) * 5 / 9


def celsius_to_kelvin(celsius: float) -> float:
    """Convert Celsius to Kelvin: K = C + 273.15"""
    return celsius + 273.15


def kelvin_to_celsius(kelvin: float) -> float:
    """Convert Kelvin to Celsius: C = K − 273.15"""
    return kelvin - 273.15


def convert(value: float, from_scale: str, to_scale: str) -> float:
    """
    Convert temperature from one scale to another.

    Supported scales: C (Celsius), F (Fahrenheit), K (Kelvin)

    Returns the converted temperature value.
    """
    # If converting to the same scale, return the value unchanged
    if from_scale == to_scale:
        return value

    # Convert to Celsius first (as intermediate step)
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

    return result


def check_absolute_zero(value: float, scale: str) -> bool:
    """
    Check if a temperature value is below absolute zero for the given scale.

    Absolute zero values:
    - Celsius: -273.15°C
    - Fahrenheit: -459.67°F
    - Kelvin: 0 K

    Returns True if valid (>= absolute zero), False if below absolute zero.
    """
    if scale == 'C':
        return value >= -273.15
    elif scale == 'F':
        return value >= -459.67
    elif scale == 'K':
        return value >= 0

    return True  # Should not reach here if input is validated


def main():
    """Main entry point for the tempconv utility."""
    # Check argument count
    if len(sys.argv) != 4:
        print("Usage: tempconv <value> <from> <to>", file=sys.stderr)
        sys.exit(2)

    value_str, from_scale, to_scale = sys.argv[1], sys.argv[2], sys.argv[3]

    # Parse the temperature value
    try:
        value = float(value_str)
    except ValueError:
        print("Error: invalid temperature value", file=sys.stderr)
        sys.exit(1)

    # Validate the scales
    valid_scales = {'C', 'F', 'K'}
    if from_scale not in valid_scales:
        print("Error: unknown scale", file=sys.stderr)
        sys.exit(1)
    if to_scale not in valid_scales:
        print("Error: unknown scale", file=sys.stderr)
        sys.exit(1)

    # Check if the input value is above absolute zero
    if not check_absolute_zero(value, from_scale):
        print("Error: temperature below absolute zero", file=sys.stderr)
        sys.exit(1)

    # Perform the conversion
    result = convert(value, from_scale, to_scale)

    # Check if the result is above absolute zero
    if not check_absolute_zero(result, to_scale):
        print("Error: temperature below absolute zero", file=sys.stderr)
        sys.exit(1)

    # Format and output the result
    output = format_output(result)
    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
