"""
Callbacks package for the Tenmile Creek Water Quality Dashboard.
"""

from .callbacks import register_callbacks
from .overview_callbacks import register_overview_callbacks
from .helper_functions import (
    get_parameter_name, get_parameter_label, get_parameter_legend,
    get_site_count_message
)

# This is the main function that app.py will call
def register_all_callbacks(app):
    """Register all callbacks for the dashboard."""
    register_callbacks(app)
    register_overview_callbacks(app)