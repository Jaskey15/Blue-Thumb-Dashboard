"""
Biological callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the biological data tab.
"""

import json
import dash
from dash import html, Input, Output, State, ALL
from utils import setup_logging
from .helper_functions import create_biological_community_display, create_gallery_navigation_callback

# Configure logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register all biological-related callbacks."""
    
    # Site dropdown callback for biological tab
    @app.callback(
        [Output('biological-site-dropdown', 'children'),
        Output('biological-site-dropdown', 'style')],
        [Input('biological-site-search-input', 'value')],
        [State('biological-available-sites', 'data'),
        State('biological-selected-site-data', 'data')] 
    )
    def update_biological_site_dropdown(search_value, data_type, selected_site_data):  
        """Update the biological site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type, selected_site_data) 

    # Site selection callback for biological tab
    @app.callback(
        [Output('biological-selected-site-data', 'data'),
         Output('biological-site-search-input', 'value'),
         Output('biological-selected-site-display', 'children'),
         Output('biological-selected-site-display', 'style'),
         Output('biological-site-clear-button', 'style'),
         Output('biological-no-site-message', 'style'),
         Output('biological-controls-content', 'style')],
        [Input({'type': 'site-option', 'index': ALL, 'tab': 'fish'}, 'n_clicks'),
         Input('biological-site-clear-button', 'n_clicks')],
        [State('biological-selected-site-data', 'data')]
    )
    def handle_biological_site_selection(site_clicks, clear_clicks, current_site):
        """Handle site selection for biological tab."""
        return handle_site_selection(site_clicks, clear_clicks, current_site, 'biological')

    # Main biological content callback
    @app.callback(
        Output('biological-content-container', 'children'),
        [Input('biological-community-dropdown', 'value'),
        Input('biological-selected-site-data', 'data')]
    )
    def update_biological_display_callback(selected_community, selected_site):
        """
        Update biological display based on selected community and site.
        
        Args:
            selected_community: Selected biological community ('fish' or 'macro')
            selected_site: Selected site name
            
        Returns:
            Dash HTML component with the biological display
        """
        if not selected_community or not selected_site:
            return html.Div("Please select a biological community from the dropdown.")
        
        return create_biological_community_display(selected_community, selected_site)

    # Fish gallery navigation callback
    @app.callback(
        [Output('fish-gallery-container', 'children'),
        Output('current-fish-index', 'data')],
        [Input('prev-fish-button', 'n_clicks'),
        Input('next-fish-button', 'n_clicks')],
        [State('current-fish-index', 'data')]
    )
    def update_fish_gallery_callback(prev_clicks, next_clicks, current_index):
        """
        Update fish gallery based on navigation buttons.
        
        Args:
            prev_clicks: Number of clicks on previous button
            next_clicks: Number of clicks on next button
            current_index: Current index in the gallery
            
        Returns:
            Tuple of (gallery_display, new_index)
        """
        return create_gallery_navigation_callback('fish')(prev_clicks, next_clicks, current_index)

    # Macro gallery navigation callback
    @app.callback(
        [Output('macro-gallery-container', 'children'),
        Output('current-macro-index', 'data')],
        [Input('prev-macro-button', 'n_clicks'),
        Input('next-macro-button', 'n_clicks')],
        [State('current-macro-index', 'data')]
    )
    def update_macro_gallery_callback(prev_clicks, next_clicks, current_index):
        """
        Update macroinvertebrate gallery based on navigation buttons.
        
        Args:
            prev_clicks: Number of clicks on previous button
            next_clicks: Number of clicks on next button
            current_index: Current index in the gallery
            
        Returns:
            Tuple of (gallery_display, new_index)
        """
        return create_gallery_navigation_callback('macro')(prev_clicks, next_clicks, current_index)