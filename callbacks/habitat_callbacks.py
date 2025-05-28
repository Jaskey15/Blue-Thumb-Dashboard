"""
Habitat callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL

from utils import setup_logging
from .helper_functions import update_site_dropdown, handle_site_selection

# Configure logging
logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register all habitat-related callbacks."""
    
    # Site dropdown callback for habitat tab
    @app.callback(
        [Output('habitat-site-dropdown', 'children'),
        Output('habitat-site-dropdown', 'style')],
        [Input('habitat-site-search-input', 'value')],
        [State('habitat-available-sites', 'data'),
        State('habitat-selected-site-data', 'data')]  
    )
    def update_habitat_site_dropdown(search_value, data_type, selected_site_data): 
        """Update the habitat site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type, selected_site_data)  

    # Site selection callback for habitat tab
    @app.callback(
        [Output('habitat-selected-site-data', 'data'),
         Output('habitat-site-search-input', 'value'),
         Output('habitat-selected-site-display', 'children'),
         Output('habitat-selected-site-display', 'style'),
         Output('habitat-site-clear-button', 'style'),
         Output('habitat-no-site-message', 'style'),
         Output('habitat-controls-content', 'style')],
        [Input({'type': 'site-option', 'index': ALL, 'tab': 'habitat'}, 'n_clicks'),
         Input('habitat-site-clear-button', 'n_clicks')],
        [State('habitat-selected-site-data', 'data')]
    )
    def handle_habitat_site_selection(site_clicks, clear_clicks, current_site):
        """Handle site selection for habitat tab."""
        return handle_site_selection(site_clicks, clear_clicks, current_site, 'habitat')

    # Main habitat display callback
    @app.callback(
        [Output('habitat-graph-container', 'children'),
        Output('habitat-table-container', 'children')],
        [Input('habitat-selected-site-data', 'data')]
    )
    def update_habitat_display_callback(selected_site):
        """
        Update habitat display based on selected site.
        
        Args:
            selected_site: Selected site name
            
        Returns:
            Tuple of (graph_component, table_component)
        """
        if not selected_site:
            return html.Div(), html.Div()
        
        try:
            # Import habitat visualization functions
            from visualizations.habitat_viz import create_habitat_viz, create_habitat_metrics_accordion
            
            # Create graph (you'll need to modify this to accept site parameter)
            graph_component = dcc.Graph(figure=create_habitat_viz())
            
            # Create metrics table
            table_component = create_habitat_metrics_accordion()
            
            return graph_component, table_component
            
        except Exception as e:
            print(f"Error creating habitat display: {e}")
            error_component = html.Div([
                html.Div("Error creating habitat display", className="alert alert-danger"),
                html.Pre(str(e), style={"fontSize": "12px"})
            ])
            return error_component, html.Div()