"""
Layout functions for the dashboard.
"""

# Import modal creation functions
from .modals import create_icon_attribution_modal, create_image_credits_modal
from .tabs.biological import create_biological_tab
from .tabs.chemical import create_chemical_tab
from .tabs.habitat import create_habitat_tab

# Import all tab creation functions
from .tabs.overview import create_overview_tab
from .tabs.protect_streams import create_protect_our_streams_tab
from .tabs.source_data import create_source_data_tab

# Import constants and helpers for internal use

__all__ = [
    'create_overview_tab',
    'create_chemical_tab', 
    'create_biological_tab',
    'create_habitat_tab',
    'create_protect_our_streams_tab',
    'create_source_data_tab',
    'create_icon_attribution_modal',
    'create_image_credits_modal'
] 