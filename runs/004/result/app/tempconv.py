#!/usr/bin/env python3
"""Temperature conversion utility."""

import sys
from decimal import Decimal, ROUND_HALF_UP

# Absolute zero thresholds
ABSOLUTE_ZERO = {
    'C': Decimal('-273.15'),
    'F': Decimal('-459.67'),
    'K': Decimal('0')
}

# Valid scale codes
VALID_SCALES = {'C', 'F', 'K'}


def parse_number(value_str):
    """Parse a numeric string and return Decimal or None."""
    try:
        # Remove leading/trailing whitespace
        value_str = value_str.strip()
        return Decimal(value_str)
    except:
        return None


def validate_arguments(args):
    """Validate command-line arguments. Returns (value, from_scale, to_scale) or (None, error_code)."""
    if len(args) != 3:
        sys.stderr.write("Usage: tempconv <value> <from> <to>\n")
        sys.exit(1)

    value_str, from_str, to_str = args

    # Validate and parse VALUE
    value = parse_number(value_str)
    if value is None:
        sys.stderr.write("Error: invalid number\n")
        sys.exit(1)

    # Validate FROM and TO
    from_scale = from_str.strip()
    to_scale = to_str.strip()

    if from_scale not in VALID_SCALES:
        sys.stderr.write("Error: invalid scale\n")
        sys.exit(2)

    if to_scale not in VALID_SCALES:
        sys.stderr.write("Error: invalid scale\n")
        sys.exit(2)

    return value, from_scale, to_scale


def validate_absolute_zero(value, from_scale):
    """Check if value is below absolute zero for the given scale."""
    if value < ABSOLUTE_ZERO[from_scale]:
        sys.stderr.write("Error: temperature below absolute zero\n")
        sys.exit(3)


def convert_to_celsius(value, from_scale):
    """Convert value from given scale to Celsius."""
    if from_scale == 'C':
        return value
    elif from_scale == 'F':
        return (value - Decimal('32')) * Decimal('5') / Decimal('9')
    elif from_scale == 'K':
        return value - Decimal('273.15')


def convert_from_celsius(value_c, to_scale):
    """Convert value from Celsius to given scale."""
    if to_scale == 'C':
        return value_c
    elif to_scale == 'F':
        return (value_c * Decimal('9') / Decimal('5')) + Decimal('32')
    elif to_scale == 'K':
        return value_c + Decimal('273.15')


def format_output(value):
    """Format value with exactly 2 decimal places using round-half-up."""
    # Round to 2 decimal places using ROUND_HALF_UP
    rounded = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"


def main():
    """Main entry point."""
    value, from_scale, to_scale = validate_arguments(sys.argv[1:])
    validate_absolute_zero(value, from_scale)

    # Convert through Celsius as intermediate
    value_celsius = convert_to_celsius(value, from_scale)
    result = convert_from_celsius(value_celsius, to_scale)

    # Format and output
    output = format_output(result)
    print(output)


if __name__ == '__main__':
    main()
