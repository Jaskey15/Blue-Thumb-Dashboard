"""
Shared callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks that are used across the entire application.
"""

import dash
from dash.dependencies import Input, Output, State
from utils import setup_logging

# Configure logging
logger = setup_logging("shared_callbacks", category="callbacks")

def register_shared_callbacks(app):
    """Register shared callbacks used across the entire dashboard."""
    
    # --------------------------------------------------------------------------------------
    # ATTRIBUTION MODAL CALLBACKS
    # --------------------------------------------------------------------------------------
    
    @app.callback(
        Output("attribution-modal", "is_open"),
        [Input("attribution-link", "n_clicks"), 
        Input("close-attribution", "n_clicks")],
        [State("attribution-modal", "is_open")]
    )
    def toggle_attribution_modal(n1, n2, is_open):
        """
        Toggle the attribution modal open/closed.
        
        Args:
            n1: Number of clicks on the attribution link
            n2: Number of clicks on the close button
            is_open: Current state of the modal
            
        Returns:
            Boolean indicating whether the modal should be open
        """
        if n1 or n2:
            return not is_open
        return is_open

    @app.callback(
        Output("image-credits-modal", "is_open"),
        [Input("image-credits-link", "n_clicks"), 
        Input("close-image-credits", "n_clicks")],
        [State("image-credits-modal", "is_open")]
    )
    def toggle_image_credits_modal(n1, n2, is_open):
        """
        Toggle the image credits modal open/closed.
        
        Args:
            n1: Number of clicks on the image credits link
            n2: Number of clicks on the close button
            is_open: Current state of the modal
            
        Returns:
            Boolean indicating whether the modal should be open
        """
        if n1 or n2:
            return not is_open
        return is_open

    # --------------------------------------------------------------------------------------
    # TAB NAVIGATION CALLBACKS
    # --------------------------------------------------------------------------------------
    
    @app.callback(
        Output("main-tabs", "active_tab"),
        [Input("chemical-overview-link", "n_clicks"),
         Input("biological-overview-link", "n_clicks"),
         Input("habitat-overview-link", "n_clicks")], 
        prevent_initial_call=True
    )
    def navigate_to_overview_tab(chemical_clicks, biological_clicks, habitat_clicks):
        """
        Navigate to overview tab when overview links are clicked from other tabs.
        
        Args:
            chemical_clicks: Number of clicks on chemical tab overview link
            biological_clicks: Number of clicks on biological tab overview link  
            habitat_clicks: Number of clicks on habitat tab overview link
            
        Returns:
            String indicating which tab should be active
        """
        ctx = dash.callback_context
        
        # Check if any of the overview links were clicked
        if ctx.triggered:
            # Any overview link click should navigate to overview tab
            return "overview-tab"
        
        # If no trigger, don't update
        return dash.no_update