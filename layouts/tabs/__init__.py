"""
Tab creation functions for the Tenmile Creek Water Quality Dashboard.
"""

from .overview import create_overview_tab
from .chemical import create_chemical_tab
from .biological import create_biological_tab
from .habitat import create_habitat_tab
from .protect_streams import create_protect_our_streams_tab
from .source_data import create_source_data_tab

__all__ = [
    'create_overview_tab',
    'create_chemical_tab',
    'create_biological_tab', 
    'create_habitat_tab',
    'create_protect_our_streams_tab',
    'create_source_data_tab'
] 