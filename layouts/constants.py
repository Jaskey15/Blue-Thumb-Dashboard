"""
Layout constants for the Tenmile Creek Water Quality Dashboard.
"""

# Overview tab parameter options
PARAMETER_OPTIONS = [
    {'label': 'Chemical: Dissolved Oxygen', 'value': 'chem:do_percent'},
    {'label': 'Chemical: pH', 'value': 'chem:pH'},
    {'label': 'Chemical: Nitrogen', 'value': 'chem:soluble_nitrogen'},
    {'label': 'Chemical: Phosphorus', 'value': 'chem:Phosphorus'},
    {'label': 'Chemical: Chloride', 'value': 'chem:Chloride'},
    {'label': 'Biological: Fish Community', 'value': 'bio:Fish_IBI'},
    {'label': 'Biological: Macroinvertebrate Community', 'value': 'bio:Macro_Combined'},
    {'label': 'Physical: Habitat Scores', 'value': 'habitat:Habitat_Score'}
]

# Chemical tab parameter options
CHEMICAL_OPTIONS = [
    {'label': 'Dissolved Oxygen', 'value': 'do_percent'},
    {'label': 'pH', 'value': 'pH'},
    {'label': 'Nitrogen', 'value': 'soluble_nitrogen'},
    {'label': 'Phosphorus', 'value': 'Phosphorus'},
    {'label': 'Chloride', 'value': 'Chloride'},
    {'label': 'All Parameters', 'value': 'all_parameters'}
]

# Biological tab parameter options
BIOLOGICAL_OPTIONS = [
    {'label': 'Fish Community', 'value': 'fish'},
    {'label': 'Macroinvertebrate Community', 'value': 'macro'},
]

# Habitat tab parameter options
HABITAT_OPTIONS = [
    {'label': 'Habitat', 'value': 'habitat'}
]

# Tab styles
TAB_STYLES = {
    "standard_margin": "mt-3",
    "small_margin": "mt-1",
    "image_container": "d-flex h-100 align-items-center justify-content-center"
} 