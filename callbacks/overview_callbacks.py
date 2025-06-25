"""
Overview callbacks for the Blue Thumb Stream Health Dashboard.
This file contains callbacks specific to the overview tab.
"""

import dash
import plotly.graph_objects as go
from dash import Input, Output, State
from .tab_utilities import (
    get_parameter_legend, get_site_count_message, 
    create_map_legend_html
)
from .helper_functions import create_error_state
from utils import setup_logging

# Configure logging
logger = setup_logging("overview_callbacks", category="callbacks")

def register_overview_callbacks(app):
    """Register all callbacks for the overview tab in logical workflow order."""
    
    # ===========================================================================================
    # 1. STATE MANAGEMENT
    # ===========================================================================================
    
    @app.callback(
        Output('overview-tab-state', 'data'),
        [Input('parameter-dropdown', 'value'),
         Input('active-sites-only-toggle', 'value')],
        [State('overview-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_overview_tab_state(parameter_value, active_sites_toggle, current_state):
        """
        Save the current state of overview tab controls to session storage.
        This preserves user selections when they switch tabs and return.
        """
        try:
            # Update the state with current values
            updated_state = current_state.copy() if current_state else {}
            updated_state['selected_parameter'] = parameter_value
            updated_state['active_sites_only'] = active_sites_toggle
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Error saving overview tab state: {e}")
            return current_state or {'selected_parameter': None, 'active_sites_only': False}
    
    # ===========================================================================================
    # 2. MAP INITIALIZATION
    # ===========================================================================================
    
    @app.callback(
        [Output('site-map-graph', 'figure'),
         Output('parameter-dropdown', 'disabled'),
         Output('parameter-dropdown', 'value'),
         Output('active-sites-only-toggle', 'value'),
         Output('map-legend-container', 'children')],
        [Input('main-tabs', 'active_tab')],
        [State('overview-tab-state', 'data')]
    )
    def load_basic_map_on_tab_open(active_tab, overview_state):
        """
        Load the basic map when the Overview tab is opened.
        This shows different shapes and colors for active vs historic sites.
        Enhanced with state restoration to preserve user selections.
        """
        # Only load map when Overview tab is active
        if active_tab != 'overview-tab':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        try:
            from visualizations.map_viz import create_basic_site_map, add_parameter_colors_to_map, get_total_site_count
            
            # Enable the parameter dropdown now that map is loaded
            dropdown_disabled = False
            
            # Check for saved state to restore
            saved_parameter = overview_state.get('selected_parameter') if overview_state else None
            saved_active_only = overview_state.get('active_sites_only', False) if overview_state else False
            
            # If we have a saved parameter, restore it and update map accordingly
            if saved_parameter:
                # Parse parameter selection
                if ':' in saved_parameter:
                    param_type, param_name = saved_parameter.split(':', 1)
                    
                    # Get total count efficiently for legend
                    total_original = get_total_site_count(active_only=False)
                    
                    # Start with basic map
                    basic_map, _, _, _ = create_basic_site_map(active_only=saved_active_only)
                    fig = go.Figure(basic_map)
                    
                    # Add parameter-specific colors with filtering
                    updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(
                        fig, param_type, param_name, sites_df=None, active_only=saved_active_only
                    )
                    
                    # Create parameter legend
                    legend_items = get_parameter_legend(param_type, param_name)
                    legend_items = [item for item in legend_items if "No data" not in item["label"]]
                    
                    # Build count message using unified function
                    if saved_active_only:
                        count_message = get_site_count_message(param_type, param_name, sites_with_data, total_original, active_only=True)
                    else:
                        count_message = get_site_count_message(param_type, param_name, sites_with_data, total_sites)
                    
                    # Create legend using utility function
                    legend_html = create_map_legend_html(legend_items=legend_items, count_message=count_message)
                    
                    return updated_map, dropdown_disabled, saved_parameter, saved_active_only, legend_html
                else:
                    logger.warning(f"Invalid saved parameter format: {saved_parameter}")
            
            # Default behavior - create basic map with saved toggle state
            basic_map, active_count, historic_count, total_count = create_basic_site_map(active_only=saved_active_only)
            
            # Create legend for basic map
            if saved_active_only:
                total_sites_count = get_total_site_count(active_only=False)
                legend_html = create_map_legend_html(total_count=total_count, active_only=saved_active_only, total_sites_count=total_sites_count)
            else:
                legend_html = create_map_legend_html(total_count=total_count, active_only=saved_active_only)
            
            return basic_map, dropdown_disabled, saved_parameter, saved_active_only, legend_html
            
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
            
            return empty_map, True, None, False, error_legend
    
    # ===========================================================================================
    # 3. PARAMETER SELECTION & MAP UPDATES
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
            from visualizations.map_viz import create_basic_site_map, add_parameter_colors_to_map, get_total_site_count
            
            # If no parameter selected, show basic map with filtering applied
            if not parameter_value:
                basic_map, active_count, historic_count, total_count = create_basic_site_map(active_only=active_only_toggle)

                if active_only_toggle:
                    total_sites_count = get_total_site_count(active_only=False)
                    legend_html = create_map_legend_html(total_count=total_count, active_only=active_only_toggle, total_sites_count=total_sites_count)
                else:
                    legend_html = create_map_legend_html(total_count=total_count, active_only=active_only_toggle)
                
                return basic_map, legend_html
            
            # Parse parameter selection
            if ':' not in parameter_value:
                logger.warning(f"Invalid parameter format: {parameter_value}")
                return dash.no_update, create_error_state(
                    "Parameter Error", 
                    "Invalid parameter selection. Please try again."
                )
            
            param_type, param_name = parameter_value.split(':', 1)
            
            # Get total count efficiently for legend
            total_original = get_total_site_count(active_only=False)
            
            # Start with current figure or create basic map
            if current_figure and current_figure.get('data'):
                fig = go.Figure(current_figure)
            else:
                fig = go.Figure()
            
            # Add parameter-specific colors with filtering 
            updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(
                fig, param_type, param_name, sites_df=None, active_only=active_only_toggle
            )
            
            # Create parameter legend
            legend_items = get_parameter_legend(param_type, param_name)
            legend_items = [item for item in legend_items if "No data" not in item["label"]]
            
            # Build count message using unified function
            if active_only_toggle:
                count_message = get_site_count_message(param_type, param_name, sites_with_data, total_original, active_only=True)
            else:
                count_message = get_site_count_message(param_type, param_name, sites_with_data, total_sites)
            
            # Create legend using utility function
            legend_html = create_map_legend_html(legend_items=legend_items, count_message=count_message)
            
            return updated_map, legend_html
            
        except Exception as e:
            logger.error(f"Error updating map with parameter selection: {e}")
            
            error_legend = create_error_state(
                "Map Update Error",
                "Could not update map with selected parameter. Please try again.",
                str(e)
            )
            
            return dash.no_update, error_legend