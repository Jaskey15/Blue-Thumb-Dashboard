"""
Interactive map visualization and parameter exploration callbacks.
"""

import dash
import plotly.graph_objects as go
from dash import Input, Output, State
from .tab_utilities import get_parameter_legend, get_site_count_message, create_map_legend_html
from .helper_functions import create_error_state
from utils import setup_logging
from visualizations.map_viz import create_basic_site_map, add_parameter_colors_to_map, get_total_site_count

# Initialize callback logging
logger = setup_logging("overview_callbacks", category="callbacks")

def register_overview_callbacks(app):
    """Register callbacks for interactive map exploration and filtering."""
    
    # State persistence
    @app.callback(
        Output('overview-tab-state', 'data'),
        [Input('parameter-dropdown', 'value'),
         Input('active-sites-only-toggle', 'value')],
        [State('overview-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_overview_tab_state(parameter_value, active_sites_toggle, current_state):
        """Preserve user selections between tab switches."""
        try:
            updated_state = current_state.copy() if current_state else {}
            updated_state['selected_parameter'] = parameter_value
            updated_state['active_sites_only'] = active_sites_toggle
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Error saving overview tab state: {e}")
            return current_state or {'selected_parameter': None, 'active_sites_only': False}
    
    # Map initialization
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
        Initialize map visualization with saved state.
        
        Priority order:
        1. Restore saved parameter and filtering
        2. Show basic site map with saved filtering
        3. Default to unfiltered view
        """
        if active_tab != 'overview-tab':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        try:
            
            dropdown_disabled = False
            saved_parameter = overview_state.get('selected_parameter') if overview_state else None
            saved_active_only = overview_state.get('active_sites_only', False) if overview_state else False
            
            # Restore parameter-specific view
            if saved_parameter:
                if ':' in saved_parameter:
                    param_type, param_name = saved_parameter.split(':', 1)
                    
                    total_original = get_total_site_count(active_only=False)
                    basic_map, _, _, _ = create_basic_site_map(active_only=saved_active_only)
                    fig = go.Figure(basic_map)
                    
                    updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(
                        fig, param_type, param_name, sites_df=None, active_only=saved_active_only
                    )
                    
                    legend_items = get_parameter_legend(param_type, param_name)
                    legend_items = [item for item in legend_items if "No data" not in item["label"]]
                    

                    if saved_active_only:
                        count_message = get_site_count_message(param_type, param_name, sites_with_data, total_original, active_only=True)
                    else:
                        count_message = get_site_count_message(param_type, param_name, sites_with_data, total_sites)
                    
                    legend_html = create_map_legend_html(legend_items=legend_items, count_message=count_message)
                    
                    return updated_map, dropdown_disabled, saved_parameter, saved_active_only, legend_html
                else:
                    logger.warning(f"Invalid saved parameter format: {saved_parameter}")
            
            # Show basic map with filtering
            basic_map, active_count, historic_count, total_count = create_basic_site_map(active_only=saved_active_only)
            
            if saved_active_only:
                total_sites_count = get_total_site_count(active_only=False)
                legend_html = create_map_legend_html(total_count=total_count, active_only=saved_active_only, total_sites_count=total_sites_count)
            else:
                legend_html = create_map_legend_html(total_count=total_count, active_only=saved_active_only)
            
            return basic_map, dropdown_disabled, saved_parameter, saved_active_only, legend_html
            
        except Exception as e:
            logger.error(f"Error loading basic map: {e}")
            
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
    
    # Parameter visualization
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
        Update map visualization based on parameter selection and filtering.
        
        Shows:
        - Parameter-specific coloring when parameter selected
        - Basic site map when no parameter selected
        - Filtered view based on active/historic toggle
        """
        try:
            
            # Show basic map when no parameter selected
            if not parameter_value:
                basic_map, active_count, historic_count, total_count = create_basic_site_map(active_only=active_only_toggle)

                if active_only_toggle:
                    total_sites_count = get_total_site_count(active_only=False)
                    legend_html = create_map_legend_html(total_count=total_count, active_only=active_only_toggle, total_sites_count=total_sites_count)
                else:
                    legend_html = create_map_legend_html(total_count=total_count, active_only=active_only_toggle)
                
                return basic_map, legend_html
            
            # Validate parameter format
            if ':' not in parameter_value:
                logger.warning(f"Invalid parameter format: {parameter_value}")
                return dash.no_update, create_error_state(
                    "Parameter Error", 
                    "Invalid parameter selection. Please try again."
                )
            
            param_type, param_name = parameter_value.split(':', 1)
            total_original = get_total_site_count(active_only=False)
            
            # Use existing map or create new one
            fig = go.Figure(current_figure) if current_figure and current_figure.get('data') else go.Figure()
            
            updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(
                fig, param_type, param_name, sites_df=None, active_only=active_only_toggle
            )
            
            legend_items = get_parameter_legend(param_type, param_name)
            legend_items = [item for item in legend_items if "No data" not in item["label"]]
            
            if active_only_toggle:
                count_message = get_site_count_message(param_type, param_name, sites_with_data, total_original, active_only=True)
            else:
                count_message = get_site_count_message(param_type, param_name, sites_with_data, total_sites)
            
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