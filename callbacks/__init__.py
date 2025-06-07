"""
Main callback registration and helper functions for the Blue Thumb Stream Health Dashboard.
This file orchestrates all callbacks and provides unified access to helper functions.
"""

# ===========================================================================================
# CALLBACK REGISTRATION 
# ===========================================================================================

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

# ===========================================================================================
# UNIFIED HELPER FUNCTION IMPORTS 
# ===========================================================================================

# Import all shared helper functions
from .helper_functions import (
    should_perform_search,
    create_search_results,
    create_empty_state,
    create_error_state,
    create_loading_state,
    create_info_state,
    # Add other shared functions as needed
)

# Import all tab-specific utilities
from .tab_utilities import (
    # Overview utilities
    get_parameter_legend,
    get_parameter_label,
    get_parameter_name,
    get_site_count_message,
    
    # Biological utilities
    create_species_display,
    create_gallery_navigation_callback,
    create_biological_community_display,
    
    # Chemical utilities
    _create_all_parameters_visualization,
    _create_single_parameter_visualization,
    
    # Habitat utilities
    _create_habitat_display,
)

# Make everything available at package level for easy importing
__all__ = [
    # Callback registration
    'register_callbacks',
    
    # Shared helper functions
    'should_perform_search',
    'create_search_results',
    'create_empty_state',
    'create_error_state',
    'create_loading_state',
    'create_info_state',
    
    # Tab-specific utilities
    'get_parameter_legend',
    'get_parameter_label',
    'get_parameter_name',
    'get_site_count_message',
    'create_species_display',
    'create_gallery_navigation_callback',
    'create_biological_community_display',
    '_create_all_parameters_visualization',
    '_create_single_parameter_visualization',
    '_create_habitat_display',
]