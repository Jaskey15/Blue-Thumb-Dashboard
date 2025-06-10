"""
Shared constants for the Tenmile Creek Water Quality Dashboard.
This file contains constants used by both layout and callback modules.
"""

# Dictionary mapping parameter codes to their display names
PARAMETER_DISPLAY_NAMES = {
    'do_percent': 'Dissolved Oxygen',
    'pH': 'pH',
    'soluble_nitrogen': 'Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride',
}

# Dictionary mapping parameter codes to their y-axis labels
PARAMETER_AXIS_LABELS = {
    'do_percent': 'DO Saturation (%)',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen (mg/L)',
    'Phosphorus': 'Phosphorus (mg/L)',
    'Chloride': 'Chloride (mg/L)',
}

# Season to month mapping for the month selection buttons
SEASON_MONTHS = {
    "all": list(range(1, 13)),
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "fall": [9, 10, 11],
    "winter": [12, 1, 2]
} 