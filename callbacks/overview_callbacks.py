"""
Overview callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the overview tab.
"""

import dash
import plotly.graph_objects as go
from dash import html, Input, Output, State  
from visualizations.map_viz import create_site_map
from .helper_functions import get_parameter_legend, get_site_count_message, get_parameter_label
from utils import setup_logging

# Configure logging
logger = setup_logging("overview_callbacks", category="callbacks")

def register_overview_callbacks(app):
    """Register all callbacks for the overview tab."""
    
    @app.callback(
        [Output('site-map-graph', 'figure'),
         Output('parameter-dropdown', 'disabled'),
         Output('map-legend-container', 'children')],
        [Input('main-tabs', 'active_tab')]
    )
    def load_basic_map_on_tab_open(active_tab):
        """
        Load the basic map when the Overview tab is opened.
        This shows blue dots immediately without parameter-specific data.
        """
        # Only load map when Overview tab is active
        if active_tab != 'overview-tab':
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            from visualizations.map_viz import create_basic_site_map
            
            # Create basic map with blue markers - NO CACHING, direct call
            basic_map = create_basic_site_map()
            
            # Enable the parameter dropdown now that map is loaded
            dropdown_disabled = False
            
            # No legend needed for basic map
            legend_html = html.Div()
            
            return basic_map, dropdown_disabled, legend_html
            
        except Exception as e:
            logger.error(f"Error loading basic map: {e}")  # Using logger instead of print
            
            # Return empty map and keep dropdown disabled
            empty_map = {
                'data': [],
                'layout': {
                    'title': 'Error loading map',
                    'xaxis': {'visible': False},
                    'yaxis': {'visible': False}
                }
            }
            
            return empty_map, True, html.Div()
        
    @app.callback(
        [Output('site-map-graph', 'figure', allow_duplicate=True),
         Output('map-legend-container', 'children', allow_duplicate=True)],
        [Input('parameter-dropdown', 'value')],
        [State('site-map-graph', 'figure')],
        prevent_initial_call=True
    )
    def update_map_with_parameter_selection(parameter_value, current_figure):
        """
        Update the map with parameter-specific color coding when user selects a parameter.
        """
        try:
            from visualizations.map_viz import create_basic_site_map, add_parameter_colors_to_map
            
            # If no parameter selected, show basic map
            if not parameter_value:
                basic_map = create_basic_site_map()
                return basic_map, html.Div()
            
            # Split the parameter value to get type and parameter
            param_type, param_name = parameter_value.split(':')
            
            # Start with current figure or create basic map
            if current_figure and current_figure.get('data'):
                # Use plotly's graph_objects to recreate the figure
                fig = go.Figure(current_figure)
            else:
                fig = create_basic_site_map()
            
            # Add parameter-specific colors and get site counts - NO CACHING, direct call
            updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(fig, param_type, param_name)
            
            # Create appropriate legend based on parameter type and name (excluding "No data")
            legend_items = get_parameter_legend(param_type, param_name)
            # Remove "No data" entries from legend
            legend_items = [item for item in legend_items if "No data" not in item["label"]]
            
            # Build the legend HTML with site count
            legend_content = [
                # Site count display
                html.Div(
                    get_site_count_message(param_type, param_name, sites_with_data, total_sites),
                    className="text-center mb-2",
                    style={"font-weight": "bold", "color": "#666"}
                ),
                # Legend items wrapper
                html.Div([
                    html.Div([
                        html.Span("● ", style={"color": item["color"], "font-size": "20px"}),
                        html.Span(item["label"], className="mr-3")
                    ], style={"display": "inline-block", "margin-right": "15px"})
                    for item in legend_items
                ])
            ]

            legend_html = html.Div(legend_content, className="text-center mt-2 mb-4")

            return updated_map, legend_html
            
        except Exception as e:
            logger.error(f"Error updating map with parameter selection: {e}")  # Using logger instead of print
            return dash.no_update, html.Div(
                html.Div("Error updating map. Please try again.", className="text-danger"),
                className="text-center mt-2 mb-4"
            )