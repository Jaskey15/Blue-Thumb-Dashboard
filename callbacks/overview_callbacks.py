"""
Overview callbacks for the Blue Thumb Stream Health Dashboard.
This file contains callbacks specific to the overview tab.
"""

import dash
import plotly.graph_objects as go
from dash import html, Input, Output, State  
from config.data_definitions import PARAMETER_DISPLAY_NAMES
from .tab_utilities import (
    get_parameter_legend, get_site_count_message, 
    create_basic_map_legend_html, create_map_legend_html
)
from .helper_functions import create_error_state
from visualizations.map_viz import add_site_marker
from utils import setup_logging

# Configure logging
logger = setup_logging("overview_callbacks", category="callbacks")

def register_overview_callbacks(app):
    """Register all callbacks for the overview tab in logical workflow order."""
    
    # ===========================================================================================
    # 1. MAP INITIALIZATION
    # ===========================================================================================
    
    @app.callback(
        [Output('site-map-graph', 'figure'),
         Output('parameter-dropdown', 'disabled'),
         Output('map-legend-container', 'children')],
        [Input('main-tabs', 'active_tab')]
    )
    def load_basic_map_on_tab_open(active_tab):
        """
        Load the basic map when the Overview tab is opened.
        This shows different shapes and colors for active vs historic sites.
        """
        # Only load map when Overview tab is active
        if active_tab != 'overview-tab':
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            from visualizations.map_viz import create_basic_site_map
            
            # Create basic map with site counts (without filtering for initial load)
            basic_map, active_count, historic_count, total_count = create_basic_site_map(active_only=False)
            
            # Enable the parameter dropdown now that map is loaded
            dropdown_disabled = False
            
            # Create legend for basic map using utility function
            legend_html = create_basic_map_legend_html(total_count)
            
            return basic_map, dropdown_disabled, legend_html
            
        except Exception as e:
            logger.error(f"Error loading basic map: {e}")
            
            # Return empty map and keep dropdown disabled
            empty_map = {
                'data': [],
                'layout': {
                    'title': 'Error loading map',
                    'xaxis': {'visible': False},
                    'yaxis': {'visible': False}
                }
            }
            
            error_legend = create_error_state(
                "Map Loading Error",
                "Could not load the monitoring sites map. Please refresh the page.",
                str(e)
            )
            
            return empty_map, True, error_legend
    
    # ===========================================================================================
    # 2. PARAMETER SELECTION & MAP UPDATES
    # ===========================================================================================
    
    @app.callback(
        [Output('site-map-graph', 'figure', allow_duplicate=True),
         Output('map-legend-container', 'children', allow_duplicate=True)],
        [Input('parameter-dropdown', 'value'),
         Input('active-sites-only-toggle', 'value')],
        [State('site-map-graph', 'figure')],
        prevent_initial_call=True
    )
    def update_map_with_parameter_selection(parameter_value, active_only_toggle, current_figure):
        """
        Update the map with parameter-specific color coding when user selects a parameter
        or toggles the active sites filter.
        """
        try:
            from visualizations.map_viz import (
                create_basic_site_map, add_parameter_colors_to_map, 
                filter_sites_by_active_status, MONITORING_SITES
            )
            
            # If no parameter selected, show basic map with filtering applied
            if not parameter_value:
                # Use the updated create_basic_site_map function with filtering
                basic_map, active_count, historic_count, total_count = create_basic_site_map(active_only=active_only_toggle)
                
                # Create legend using utility function
                legend_html = create_basic_map_legend_html(total_count)
                
                return basic_map, legend_html
            
            # Parse parameter selection
            if ':' not in parameter_value:
                logger.warning(f"Invalid parameter format: {parameter_value}")
                return dash.no_update, create_error_state(
                    "Parameter Error", 
                    "Invalid parameter selection. Please try again."
                )
            
            param_type, param_name = parameter_value.split(':', 1)
            
            # Filter sites based on toggle state
            filtered_sites, active_count, historic_count, total_original = filter_sites_by_active_status(
                MONITORING_SITES, active_only_toggle
            )
            
            # Start with current figure or create basic map
            if current_figure and current_figure.get('data'):
                fig = go.Figure(current_figure)
            else:
                fig = go.Figure()
            
            # Add parameter-specific colors with filtered sites
            updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(
                fig, param_type, param_name, filtered_sites
            )
            
            # Create parameter legend
            legend_items = get_parameter_legend(param_type, param_name)
            legend_items = [item for item in legend_items if "No data" not in item["label"]]
            
            # Build count message based on filtering state
            if active_only_toggle:
                count_message = f"Showing {sites_with_data} of {total_original} monitoring sites (active only) with {PARAMETER_DISPLAY_NAMES.get(param_name, param_name)} data"
            else:
                count_message = get_site_count_message(param_type, param_name, sites_with_data, total_sites)
            
            # Create legend using utility function
            legend_html = create_map_legend_html(legend_items, count_message)
            
            return updated_map, legend_html
            
        except Exception as e:
            logger.error(f"Error updating map with parameter selection: {e}")
            
            error_legend = create_error_state(
                "Map Update Error",
                "Could not update map with selected parameter. Please try again.",
                str(e)
            )
            
            return dash.no_update, error_legend