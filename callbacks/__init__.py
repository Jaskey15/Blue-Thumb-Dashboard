"""
Main callback registration for the Blue Thumb Stream Health Dashboard.
This file orchestrates all callbacks for the dashboard.
"""

# Import callback registration functions
from .overview_callbacks import register_overview_callbacks
from .chemical_callbacks import register_chemical_callbacks
from .biological_callbacks import register_biological_callbacks
from .habitat_callbacks import register_habitat_callbacks
from .shared_callbacks import register_shared_callbacks

def register_callbacks(app):
    """Register all callbacks for the dashboard."""
    
    # Register callbacks from all modules
    register_overview_callbacks(app)
    register_chemical_callbacks(app)
    register_biological_callbacks(app)
    register_habitat_callbacks(app)
    register_shared_callbacks(app)