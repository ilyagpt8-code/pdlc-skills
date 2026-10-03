#!/usr/bin/env python3
"""
tempconv — Temperature Converter Utility
Converts temperature values between Celsius (C), Fahrenheit (F), and Kelvin (K)
"""

import sys


def main():
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Error: Missing required argument: temperature value and scale", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 4:
        print("Error: Too many arguments", file=sys.stderr)
        sys.exit(1)

    value_str = sys.argv[1]
    from_scale = sys.argv[2].upper()
    to_scale = sys.argv[3].upper() if len(sys.argv) == 4 else None

    # Parse temperature value
    try:
        value = float(value_str)
    except ValueError:
        print(f"Error: Invalid temperature value '{value_str}': not a number", file=sys.stderr)
        sys.exit(2)

    # Validate scales
    valid_scales = {'C', 'F', 'K'}
    if from_scale not in valid_scales:
        print(f"Error: Unknown temperature scale '{from_scale}': must be C, F, or K", file=sys.stderr)
        sys.exit(2)

    if to_scale is not None and to_scale not in valid_scales:
        print(f"Error: Unknown temperature scale '{to_scale}': must be C, F, or K", file=sys.stderr)
        sys.exit(2)

    # Validate temperature against absolute zero
    absolute_zero_thresholds = {
        'C': -273.15,
        'F': -459.67,
        'K': 0.0
    }

    if value < absolute_zero_thresholds[from_scale]:
        print(
            f"Error: Temperature {value} {from_scale} is below absolute zero "
            f"({absolute_zero_thresholds[from_scale]} {from_scale})",
            file=sys.stderr
        )
        sys.exit(3)

    # Convert temperature to Celsius first as base
    def to_celsius(temp, scale):
        if scale == 'C':
            return temp
        elif scale == 'F':
            return (temp - 32) * 5 / 9
        elif scale == 'K':
            return temp - 273.15

    # Convert from Celsius to target scale
    def from_celsius(temp_c, scale):
        if scale == 'C':
            return temp_c
        elif scale == 'F':
            return (temp_c * 9 / 5) + 32
        elif scale == 'K':
            return temp_c + 273.15

    # Convert to Celsius
    celsius_value = to_celsius(value, from_scale)

    # Output results
    if to_scale is not None:
        # Convert to target scale
        result = from_celsius(celsius_value, to_scale)
        # Format the output
        if result == int(result):
            print(f"{int(result)} {to_scale}")
        else:
            # Round to 2 decimal places for readability, but remove trailing zeros
            formatted = f"{result:.2f}".rstrip('0').rstrip('.')
            print(f"{formatted} {to_scale}")
    else:
        # Convert to all scales except the source
        scales_order = ['C', 'F', 'K']
        for scale in scales_order:
            if scale != from_scale:
                result = from_celsius(celsius_value, scale)
                # Format the output
                if result == int(result):
                    print(f"{int(result)} {scale}")
                else:
                    # Round to 2 decimal places for readability, but remove trailing zeros
                    formatted = f"{result:.2f}".rstrip('0').rstrip('.')
                    print(f"{formatted} {scale}")


if __name__ == '__main__':
    main()
