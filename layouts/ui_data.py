"""
UI content data for the dashboard
This file contains static content used for layout display including action cards,
gallery items, and diagram information.
"""

# Action cards data

# Home & Yard cards 
HOME_YARD_CARDS = [
    {
        "icon": "fertilizer", 
        "title": "MINIMIZE FERTILIZER USE",
        "why_text": "Excess fertilizers wash into streams causing algal blooms that deplete oxygen needed by fish and other aquatic life.",
        "tips_list": [
            "Test soil before applying fertilizer",
            "Use slow-release, phosphorus-free products",
            "Apply only the recommended amount",
            "Avoid application before rain"
        ]
    },
    {
        "icon": "native-plants", 
        "title": "PLANT NATIVE SPECIES",
        "why_text": "Native plants have deep root systems that filter pollutants, prevent erosion, and provide habitat for beneficial organisms.",
        "tips_list": [
            "Choose plants native to your region",
            "Focus on perennials with deep root systems",
            "Group plants with similar water needs",
            "Reduce lawn area in favor of native plantings"
        ]
    },
    {
        "icon": "rain-garden", 
        "title": "CREATE RAIN GARDENS",
        "why_text": "Rain gardens capture and filter runoff from roofs and driveways, preventing pollutants from reaching waterways.",
        "tips_list": [
            "Place in a natural depression or low area",
            "Use native plants with deep roots",
            "Size garden to handle your roof/driveway runoff",
            "Include a variety of plant types and heights"
        ]
    },
    {
        "icon": "chemicals", 
        "title": "PROPERLY DISPOSE OF HOUSEHOLD CHEMICALS",
        "why_text": "Chemicals poured down drains or onto the ground often end up in waterways, harming aquatic life and contaminating drinking water.",
        "tips_list": [
            "Use community hazardous waste collection events",
            "Never pour chemicals down drains or on ground",
            "Store chemicals in original containers",
            "Use eco-friendly alternatives when possible"
        ]
    },
    {
        "icon": "water", 
        "title": "CONSERVE WATER",
        "why_text": "Conserving water helps maintain adequate flow in streams during dry periods, which is crucial for aquatic life.",
        "tips_list": [
            "Fix leaks promptly",
            "Install water-efficient fixtures",
            "Water lawns and gardens during cool hours",
            "Collect and use rainwater for gardens"
        ]
    },
    {
        "icon": "runoff", 
        "title": "REDUCE IMPERVIOUS SURFACES",
        "why_text": "Hard surfaces like concrete and asphalt prevent water from soaking into the ground, increasing runoff that carries pollutants to streams.",
        "tips_list": [
            "Use permeable pavers for patios and walkways",
            "Consider a permeable driveway material when replacing",
            "Disconnect downspouts from storm drains",
            "Direct runoff to vegetated areas"
        ]
    }
]

# Rural & Agricultural cards
RURAL_CARDS = [
    {
        "icon": "buffer", 
        "title": "MAINTAIN RIPARIAN BUFFERS",
        "why_text": "Vegetated buffers filter pollutants, stabilize banks, provide wildlife habitat, and shade the stream.",
        "tips_list": [
            "Leave at least 30 feet of natural vegetation along streams",
            "Plant native trees and shrubs if buffer is degraded",
            "Avoid mowing, grazing, or farming in the buffer zone",
            "Control invasive species that might take over"
        ]
    },
    {
        "icon": "livestock", 
        "title": "CONTROL LIVESTOCK ACCESS TO STREAMS",
        "why_text": "Direct livestock access to streams causes bank erosion, sediment pollution, and bacterial contamination from waste.",
        "tips_list": [
            "Fence livestock out of streams and riparian areas",
            "Install off-stream watering systems",
            "Create designated crossing points if necessary",
            "Develop shade areas away from streams"
        ]
    },
    {
        "icon": "no-till", 
        "title": "PRACTICE NO-TILL OR REDUCED TILL FARMING",
        "why_text": "Tilling disrupts soil structure and increases erosion and runoff. No-till farming maintains soil health and reduces sedimentation in streams.",
        "tips_list": [
            "Leave crop residue on fields after harvest",
            "Use specialized equipment designed for no-till",
            "Manage weeds with careful crop rotation",
            "Consider cover crops between cash crops"
        ]
    },
    {
        "icon": "cover-crops", 
        "title": "PLANT COVER CROPS",
        "why_text": "Cover crops protect bare soil from erosion, improve soil health, and filter pollutants in runoff during off-seasons.",
        "tips_list": [
            "Select appropriate species for your climate and soil",
            "Plant immediately after harvesting main crop",
            "Consider mixes of different cover crop types",
            "Properly terminate before planting next cash crop"
        ]
    },
    {
        "icon": "grazing", 
        "title": "IMPLEMENT ROTATIONAL GRAZING",
        "why_text": "Overgrazing removes vegetation needed to filter runoff and prevent erosion, while rotational grazing allows recovery.",
        "tips_list": [
            "Divide pastures into smaller paddocks",
            "Move livestock regularly to prevent overgrazing",
            "Allow adequate rest periods for vegetation recovery",
            "Monitor forage height and adjust grazing accordingly"
        ]
    },
    {
        "icon": "pesticides", 
        "title": "APPLY PESTICIDES AND HERBICIDES RESPONSIBLY",
        "why_text": "Agricultural chemicals can contaminate waterways through drift and runoff, harming aquatic life and water quality.",
        "tips_list": [
            "Follow label directions carefully",
            "Never apply before predicted rain events",
            "Maintain buffer zones near water bodies",
            "Consider integrated pest management techniques"
        ]
    }
]

# Recreation cards 
RECREATION_CARDS = [
    {
        "icon": "boating", 
        "title": "PRACTICE RESPONSIBLE BOATING",
        "why_text": "Boat engines can leak fuel and oil, while boats moved between waterways can spread invasive species.",
        "tips_list": [
            "Maintain engines to prevent leaks and spills",
            "Clean boats thoroughly between waterways",
            "Dispose of waste properly, never in water",
            "Operate at no-wake speeds near shorelines"
        ]
    },
    {
        "icon": "access-points", 
        "title": "USE DESIGNATED ACCESS POINTS",
        "why_text": "Entering streams at undesignated locations damages sensitive banks and vegetation, increasing erosion.",
        "tips_list": [
            "Look for established boat ramps and entry points",
            "Stay on designated paths to reach the water",
            "Avoid trampling streamside vegetation",
            "Report damaged access areas to local authorities"
        ]
    },
    {
        "icon": "trash", 
        "title": "PACK OUT TRASH",
        "why_text": "Litter in and near streams harms wildlife, degrades water quality, and diminishes recreational experiences.",
        "tips_list": [
            "Bring a bag for collecting your waste",
            "Pick up any trash you find, even if it isn't yours",
            "Secure items that might blow away",
            "Participate in organized stream cleanups"
        ]
    },
    {
        "icon": "trails", 
        "title": "STAY ON ESTABLISHED TRAILS",
        "why_text": "Off-trail hiking near streams compacts soil, damages vegetation, and increases erosion and runoff.",
        "tips_list": [
            "Follow designated trails even if shortcuts tempt you",
            "Avoid creating new paths to water access points",
            "Stay back from undercut or unstable banks",
            "Cross streams only at established crossings"
        ]
    },
    {
        "icon": "fishing", 
        "title": "PRACTICE RESPONSIBLE FISHING",
        "why_text": "Fishing line, hooks, and other gear can entangle and harm wildlife long after being discarded.",
        "tips_list": [
            "Properly dispose of fishing line and hooks",
            "Use barbless hooks for catch-and-release",
            "Follow catch-and-release best practices",
            "Know and follow local fishing regulations"
        ]
    },
    {
        "icon": "camping", 
        "title": "CAMP RESPONSIBLY NEAR WATERWAYS",
        "why_text": "Poor camping practices can damage riparian areas, introduce pollutants, and disturb sensitive wildlife habitat.",
        "tips_list": [
            "Camp at least 200 feet from the water's edge",
            "Use established campsites when available",
            "Use biodegradable soaps for washing",
            "Dispose of human waste properly using pit toilets or by burying it at least 200 feet from water"
        ]
    }
]

# Community Action cards 
COMMUNITY_CARDS = [
    {
        "icon": "monitoring", 
        "title": "VOLUNTEER WITH MONITORING PROGRAMS",
        "why_text": "Regular monitoring helps track stream health, identify problems early, and measure improvement over time.",
        "tips_list": [
            "Join local stream monitoring programs like Blue Thumb",
            "Learn proper sampling and assessment techniques",
            "Consistently monitor the same location over time",
            "Report unusual conditions or concerns to authorities"
        ]
    },
        {
        "icon": "restoration", 
        "title": "PARTICIPATE IN STREAM RESTORATION",
        "why_text": "Community-based restoration efforts can significantly improve stream health by repairing damaged habitat and addressing pollution sources.",
        "tips_list": [
            "Join local watershed associations or conservation districts",
            "Volunteer for tree planting events along streams",
            "Help with invasive species removal projects",
            "Assist with bank stabilization and in-stream habitat improvements"
        ]
    },
    {
        "icon": "education", 
        "title": "EDUCATE OTHERS",
        "why_text": "Many water quality issues stem from lack of awareness about how individual actions affect streams.",
        "tips_list": [
            "Share what you learn about stream health",
            "Use social media to spread awareness",
            "Involve children in stream exploration and conservation",
            "Support water education in local schools"
        ]
    },
    {
        "icon": "cleanups", 
        "title": "ORGANIZE STREAM CLEANUPS",
        "why_text": "Trash and debris in waterways harm wildlife, degrade water quality, and can cause blockages that lead to flooding.",
        "tips_list": [
            "Partner with local conservation groups",
            "Focus on high-traffic areas like parks and bridges",
            "Sort collected waste for proper recycling",
            "Document your findings to track improvements"
        ]
    },
    {
        "icon": "policies", 
        "title": "SUPPORT WATER-FRIENDLY POLICIES",
        "why_text": "Local policies and ordinances can either protect or harm stream health on a community-wide scale.",
        "tips_list": [
            "Advocate for riparian buffer requirements",
            "Support limits on impervious surfaces in developments",
            "Attend public meetings about water resource decisions",
            "Encourage green infrastructure in community planning"
        ]
    },
    {
        "icon": "storm-drains", 
        "title": "MARK STORM DRAINS",
        "why_text": "Many people don't realize storm drains flow directly to waterways, often without treatment.",
        "tips_list": [
            "Contact local authorities about marking programs",
            "Use approved markers or stencils",
            "Distribute educational materials to neighbors",
            "Adopt storm drains in your neighborhood for monitoring"
        ]
    }
]

# Species gallery data

# Fish gallery data
FISH_DATA = [
    {
        "id": 0,
        "name": "Bluegill Sunfish",
        "image": "/assets/images/fish/bluegill_sunfish.jpg",
        "description": "Bluegill Sunfish have a deep, compressed body with blue and orange coloration."
    },
    {
        "id": 1,
        "name": "Longear Sunfish",
        "image": "/assets/images/fish/longear_sunfish.jpg",
        "description": "Longear Sunfish are known for their vibrant colors and distinctive long ear flap."
    },
    {
        "id": 2,
        "name": "Mosquitofish",
        "image": "/assets/images/fish/mosquitofish.jpg",
        "description": "Mosquitofish are small fish that help control mosquito populations by eating their larvae."
    },
    {
        "id": 3,
        "name": "Red Shiner",
        "image": "/assets/images/fish/red_shiner.jpg",
        "description": "Red shiners are small, colorful minnows known for their adaptability and vibrant breeding colors."
    }
]

# Macroinvertebrate gallery data with dual life stages
MACRO_DATA = [
    {
        "id": 0,
        "name": "Caddisfly",
        "larval_image": "/assets/images/macroinvertebrates/caddisfly_larval.jpeg",
        "adult_image": "/assets/images/macroinvertebrates/caddisfly_adult.jpg",
        "description": "Caddisflies build protective cases from materials in their environment and are sensitive to pollution - making them indicators of good water quality"
    },
    {
        "id": 1,
        "name": "Mayfly",
        "larval_image": "/assets/images/macroinvertebrates/mayfly_larval.jpeg",
        "adult_image": "/assets/images/macroinvertebrates/mayfly_adult.jpeg",
        "description": "Mayflies are known for their distinctive multi-tailed nymphs and are excellent indicators of healthy streams"
    },
    {
        "id": 2,
        "name": "Riffle Beetle",
        "larval_image": "/assets/images/macroinvertebrates/riffle_beetle_larval.jpeg",
        "adult_image": "/assets/images/macroinvertebrates/riffle_beetle_adult.jpeg",
        "description": "Riffle beetles are small aquatic beetles that indicate good water quality as they require high oxygen levels"
    },
    {
        "id": 3,
        "name": "Stonefly",
        "larval_image": "/assets/images/macroinvertebrates/stonefly_larval.jpg",
        "adult_image": "/assets/images/macroinvertebrates/stonefly_adult.jpg",
        "description": "Stoneflies are very sensitive to pollution and are excellent indicators of pristine water conditions"
    }
]

# Chemical diagram data

# Chemical parameter diagram mapping
CHEMICAL_DIAGRAMS = {
    'do_percent': '/assets/images/chemical_diagrams/dissolved_oxygen_graphic.jpg',
    'pH': '/assets/images/chemical_diagrams/pH_graphic.jpg',
    'soluble_nitrogen': '/assets/images/chemical_diagrams/nitrogen_cycle.jpg',
    'Phosphorus': '/assets/images/chemical_diagrams/phosphorous_cycle.jpg',
    'Chloride': '/assets/images/chemical_diagrams/chloride_graphic.jpg',
}

# Dictionary of captions for chemical diagrams
CHEMICAL_DIAGRAM_CAPTIONS = {
    'do_percent': 'The oxygen balance in aquatic environments: atmospheric diffusion and photosynthesis add oxygen to water, while plant, animal, and bacterial respiration deplete it.',
    'pH': 'The pH scale ranges from highly acidic (0) to highly alkaline (14), with neutral water at 7. For Oklahoma streams, maintaining pH between 6.5-9 is essential for supporting diverse aquatic communities and preventing harm to sensitive species.',
    'soluble_nitrogen': 'Nitrogen in aquatic ecosystems cycles through various compounds (ammonia, nitrite, nitrate) as it moves through plants, animals, and microorganisms.',
    'Phosphorus': 'Illustration of phosphorus movement through aquatic ecosystems, from external inputs to algae, animals, microbes, and sediment.',
    'Chloride': 'Sources of chloride in streams include road salt, water softeners, and agricultural inputs. Excessive concentrations have a negative impact on stream health.'
}

# Habitat diagram data

# Habitat diagram mapping
HABITAT_DIAGRAMS = {
    'habitat_assessment': '/assets/images/stream_habitat_diagram.jpg',
}

# Dictionary of captions for habitat diagrams
HABITAT_DIAGRAM_CAPTIONS = {
    'habitat_assessment': 'Essential stream habitat features: riffles provide oxygenated water for feeding, runs offer deeper water for fish movement, pools create refuges during low flows, and riparian corridors provide shade and bank stability.'
} 