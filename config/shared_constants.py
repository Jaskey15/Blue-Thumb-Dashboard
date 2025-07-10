"""
Shared constants and configuration values for the Blue Thumb Dashboard.
"""

# Parameter display names for user-friendly labels
PARAMETER_DISPLAY_NAMES = {
    'do_percent': 'Dissolved Oxygen',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride',
    'fish_ibi': 'Fish IBI',
    'macro_score': 'Macroinvertebrate Score',
    'habitat_score': 'Habitat Score'
}

# Parameter axis labels for charts
PARAMETER_AXIS_LABELS = {
    'do_percent': 'Dissolved Oxygen (%)',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen (mg/L)',
    'Phosphorus': 'Phosphorus (mg/L)',
    'Chloride': 'Chloride (mg/L)',
    'fish_ibi': 'Fish IBI Score',
    'macro_score': 'Macroinvertebrate Score',
    'habitat_score': 'Habitat Score'
}

# Season to month mapping for the month selection buttons
SEASON_MONTHS = {
    "all": list(range(1, 13)),
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "fall": [9, 10, 11],
    "winter": [12, 1, 2]
} 