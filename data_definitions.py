"""
Data definitions for the Tenmile Creek Water Quality Dashboard.
This file contains static data structures used across the dashboard.
"""

# Fish gallery data
FISH_DATA = [
    {
        "id": 0,
        "name": "Bluegill Sunfish",
        "image": "/assets/images/fish/Bluegill_Sunfish.jpg",
        "description": "Bluegill Sunfish have a deep, compressed body with blue and orange coloration."
    },
    {
        "id": 1,
        "name": "Longear Sunfish",
        "image": "/assets/images/fish/Longear_Sunfish.jpeg",
        "description": "Longear Sunfish are known for their vibrant colors and distinctive long ear flap."
    },
    {
        "id": 2,
        "name": "Mosquitofish",
        "image": "/assets/images/fish/Mosquitofish.jpg",
        "description": "Mosquitofish are small fish that help control mosquito populations by eating their larvae."
    },
    {
        "id": 3,
        "name": "Redfin Shiner",
        "image": "/assets/images/fish/Redfin_Shiner.jpg",
        "description": "Redfin Shiners have silvery bodies with reddish fins, particularly noticeable during breeding season."
    }
]

# Macroinvertebrate gallery data
MACRO_DATA = [
    {
        "id": 0,
        "name": "Caddisfly",
        "image": "/assets/images/macroinvertebrates/Caddisfly.png",
        "description": "Caddisflies are sensitive to pollution and build protective cases from materials in their environment."
    },
    {
        "id": 1,
        "name": "Non-biting Midge",
        "image": "/assets/images/macroinvertebrates/Non-biting_Midge.jpg",
        "description": "Non-biting midges are small, mosquito-like insects whose larvae are an important food source for fish."
    },
    {
        "id": 2,
        "name": "Riffle Beetle",
        "image": "/assets/images/macroinvertebrates/Riffle_Beetle.jpg",
        "description": "Riffle beetles are small aquatic beetles that indicate good water quality as they require high oxygen levels."
    },
    {
        "id": 3,
        "name": "Stonefly",
        "image": "/assets/images/macroinvertebrates/Stonefly.png",
        "description": "Stoneflies are very sensitive to pollution and are excellent indicators of pristine water conditions."
    }
]

# Chemical parameter diagram mapping
CHEMICAL_DIAGRAMS = {
    'DO_Percent': '/assets/images/chemical_diagrams/dissolved_oxygen_graphic.jpg',
    'pH': '/assets/images/chemical_diagrams/pH_graphic.png',
    'Soluble_Nitrogen': '/assets/images/chemical_diagrams/nitrogen_cycle.png',
    'Phosphorus': '/assets/images/chemical_diagrams/phosphorous_cycle.png',
    'Chloride': '/assets/images/chemical_diagrams/chloride_graphic.png',
}

# Dictionary of captions for chemical diagrams
CHEMICAL_DIAGRAM_CAPTIONS = {
    'DO_Percent': 'The oxygen balance in aquatic environments: atmospheric diffusion and photosynthesis add oxygen to water, while plant, animal, and bacterial respiration deplete it.',
    'pH': 'The pH scale ranges from highly acidic (0) to highly alkaline (14), with neutral water at 7. For Oklahoma streams, maintaining pH between 6.5-9 is essential for supporting diverse aquatic communities and preventing harm to sensitive species.',
    'Soluble_Nitrogen': 'Nitrogen in aquatic ecosystems cycles through various compounds (ammonia, nitrite, nitrate) as it moves through plants, animals, and microorganisms.',
    'Phosphorus': 'Illustration of phosphorus movement through aquatic ecosystems, from external inputs to algae, animals, microbes, and sediment.',
    'Chloride': 'Sources of chloride in streams include road salt, water softeners, and agricultural inputs. Excessive concentrations have a negative impact on stream health.'
}

# Dictionary mapping parameter codes to their display names
PARAMETER_DISPLAY_NAMES = {
    'DO_Percent': 'Dissolved Oxygen',
    'pH': 'pH',
    'Soluble_Nitrogen': 'Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride',
}

# Dictionary mapping parameter codes to their y-axis labels
PARAMETER_AXIS_LABELS = {
    'DO_Percent': 'DO Saturation (%)',
    'pH': 'pH',
    'Soluble_Nitrogen': 'Soluble Nitrogen (mg/L)',
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