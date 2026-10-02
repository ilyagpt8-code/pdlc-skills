#!/usr/bin/env python3
"""
tempconv - Temperature Converter Utility

Converts temperature values between Celsius (C), Fahrenheit (F), and Kelvin (K).
"""

import sys
import math


def main():
    """Main entry point for tempconv utility."""

    # Check argument count (must be exactly 3)
    if len(sys.argv) != 4:
        print("Usage: tempconv <value> <from> <to>", file=sys.stderr)
        sys.exit(1)

    value_str = sys.argv[1].strip()
    from_scale = sys.argv[2]
    to_scale = sys.argv[3]

    # Parse VALUE as a number
    try:
        value = float(value_str)
    except ValueError:
        print("Error: invalid number", file=sys.stderr)
        sys.exit(1)

    # Validate FROM and TO scales
    valid_scales = {'C', 'F', 'K'}
    if from_scale not in valid_scales or to_scale not in valid_scales:
        print("Error: invalid scale", file=sys.stderr)
        sys.exit(2)

    # Validate absolute zero constraint for the source scale
    absolute_zero_min = {
        'C': -273.15,
        'F': -459.67,
        'K': 0.0
    }

    tolerance = 1e-9
    min_allowed = absolute_zero_min[from_scale]

    # Allow floating-point tolerance of ±1e-9
    if value < min_allowed - tolerance:
        print("Error: temperature below absolute zero", file=sys.stderr)
        sys.exit(3)

    # Perform conversion
    if from_scale == to_scale:
        # Same-scale conversion: just return the value
        result = value
    else:
        # Convert through Celsius as intermediate scale
        if from_scale == 'C':
            celsius = value
        elif from_scale == 'F':
            celsius = (value - 32) * 5 / 9
        else:  # from_scale == 'K'
            celsius = value - 273.15

        # Convert from Celsius to target scale
        if to_scale == 'C':
            result = celsius
        elif to_scale == 'F':
            result = (celsius * 9 / 5) + 32
        else:  # to_scale == 'K'
            result = celsius + 273.15

    # Format output: exactly 2 decimal places
    # Handle negative zero: normalize to positive zero
    if result == 0:
        result = 0.0  # Ensure positive zero

    # Format with exactly 2 decimal places using standard rounding
    output = f"{result:.2f}"

    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
