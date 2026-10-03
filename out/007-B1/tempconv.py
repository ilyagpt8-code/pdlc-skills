#!/usr/bin/env python3
"""Temperature Converter Utility

Converts temperature values between Celsius, Fahrenheit, and Kelvin scales.
Implements custom rounding (round half away from zero) and preserves input decimal places.
"""

import sys
from decimal import Decimal, ROUND_HALF_UP


def round_half_away_from_zero(value: float, decimal_places: int) -> float:
    """
    Round a number using 'round half away from zero' strategy.

    This is different from Python's default banker's rounding.
    - 0.25 → 0.3 (away from zero)
    - 2.5 → 3 (away from zero)
    - -2.5 → -3 (away from zero)
    """
    if decimal_places < 0:
        raise ValueError("decimal_places must be non-negative")

    # Use Decimal for precise rounding
    d = Decimal(str(value))
    if decimal_places == 0:
        return float(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    else:
        quantize_str = '0.' + '0' * decimal_places
        return float(d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP))


def count_decimal_places(value_str: str) -> int:
    """
    Count the number of decimal places in a numeric string.

    Examples:
    - "32" → 1 (no decimal point means 1 decimal place in output)
    - "32.0" → 1
    - "32.50" → 2
    - "-40" → 1
    - "-273.15" → 2
    """
    if '.' not in value_str:
        return 1  # Integer inputs output with 1 decimal place

    # Remove the decimal point and count digits after it
    parts = value_str.split('.')
    return len(parts[1])


def validate_numeric(value_str: str) -> float:
    """Validate and parse a numeric string."""
    try:
        return float(value_str)
    except ValueError:
        print(f"Error: Invalid number: {value_str}", file=sys.stderr)
        sys.exit(1)


def validate_scale(scale_str: str) -> str:
    """Validate and normalize a scale identifier."""
    scale = scale_str.upper()
    if scale not in ('C', 'F', 'K'):
        print(f"Error: Invalid scale: {scale_str}", file=sys.stderr)
        sys.exit(2)
    return scale


def check_absolute_zero(value: float, scale: str) -> None:
    """Validate that value is not below absolute zero for the given scale."""
    absolute_zero_limits = {
        'C': -273.15,
        'F': -459.67,
        'K': 0.0
    }

    limit = absolute_zero_limits[scale]
    if value < limit:
        print(f"Error: Temperature {value} is below absolute zero for scale {scale}", file=sys.stderr)
        sys.exit(3)


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32


def celsius_to_kelvin(celsius: float) -> float:
    """Convert Celsius to Kelvin."""
    return celsius + 273.15


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32) * 5/9


def fahrenheit_to_kelvin(fahrenheit: float) -> float:
    """Convert Fahrenheit to Kelvin."""
    return (fahrenheit - 32) * 5/9 + 273.15


def kelvin_to_celsius(kelvin: float) -> float:
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15


def kelvin_to_fahrenheit(kelvin: float) -> float:
    """Convert Kelvin to Fahrenheit."""
    return (kelvin - 273.15) * 9/5 + 32


def convert_temperature(value: float, from_scale: str, to_scale: str) -> float:
    """Convert temperature between scales."""
    # If scales are the same, no conversion needed
    if from_scale == to_scale:
        return value

    # Convert to Celsius first as intermediate scale
    if from_scale == 'C':
        celsius = value
    elif from_scale == 'F':
        celsius = fahrenheit_to_celsius(value)
    else:  # from_scale == 'K'
        celsius = kelvin_to_celsius(value)

    # Convert from Celsius to target scale
    if to_scale == 'C':
        return celsius
    elif to_scale == 'F':
        return celsius_to_fahrenheit(celsius)
    else:  # to_scale == 'K'
        return celsius_to_kelvin(celsius)


def main():
    """Main entry point for the temperature converter utility."""
    # Check argument count
    if len(sys.argv) != 4:
        print("Error: Invalid number of arguments. Usage: tempconv <value> <from_scale> <to_scale>", file=sys.stderr)
        sys.exit(4)

    value_str = sys.argv[1]
    from_scale_str = sys.argv[2]
    to_scale_str = sys.argv[3]

    # Validate and parse inputs
    value = validate_numeric(value_str)
    from_scale = validate_scale(from_scale_str)
    to_scale = validate_scale(to_scale_str)

    # Check absolute zero constraints
    check_absolute_zero(value, from_scale)

    # Perform conversion
    result = convert_temperature(value, from_scale, to_scale)

    # Get decimal places from input
    decimal_places = count_decimal_places(value_str)

    # Round and format output
    result_rounded = round_half_away_from_zero(result, decimal_places)

    # Format with proper decimal places
    if decimal_places == 0:
        output = f"{result_rounded:.1f}"
    else:
        output = f"{result_rounded:.{decimal_places}f}"

    print(output)
    sys.exit(0)


if __name__ == '__main__':
    main()
