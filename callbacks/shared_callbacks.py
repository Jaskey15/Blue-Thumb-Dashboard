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
        [Output("main-tabs", "active_tab"),
         Output("navigation-store", "data")],
        [Input("site-map-graph", "clickData"),
         Input("parameter-dropdown", "value"),
         Input("chemical-overview-link", "n_clicks"),
         Input("biological-overview-link", "n_clicks"),
         Input("habitat-overview-link", "n_clicks")],
        prevent_initial_call=True
    )
    def handle_navigation(click_data, current_parameter, chemical_clicks, biological_clicks, habitat_clicks):
        """
        Handle all navigation: map clicks and overview links.
        
        Args:
            click_data: Click data from the map
            current_parameter: Currently selected parameter on the overview map
            chemical_clicks: Number of clicks on chemical tab overview link
            biological_clicks: Number of clicks on biological tab overview link  
            habitat_clicks: Number of clicks on habitat tab overview link
            
        Returns:
            Tuple of (target_tab, navigation_data)
        """
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Handle overview link clicks
        if trigger_id in ['chemical-overview-link', 'biological-overview-link', 'habitat-overview-link']:
            return "overview-tab", {'target_tab': None, 'target_site': None}
        
        # Handle map clicks
        if trigger_id == 'site-map-graph' and click_data and current_parameter:
            try:
                # Extract site name from click data
                hover_text = click_data['points'][0]['text']
                site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
                
                # Handle habitat navigation
                if current_parameter == 'habitat:Habitat_Score':
                    logger.info(f"Navigating from habitat map to habitat tab for site: {site_name}")
                    return "habitat-tab", {
                        'target_tab': 'habitat-tab',
                        'target_site': site_name,
                        'source_parameter': current_parameter
                    }
                
                # Handle chemical navigation  
                elif current_parameter.startswith('chem:'):
                    # Extract parameter name from the format 'chem:parameter_name'
                    parameter_name = current_parameter.split(':', 1)[1]
                    logger.info(f"Navigating from chemical map to chemical tab for site: {site_name}, parameter: {parameter_name}")
                    return "chemical-tab", {
                        'target_tab': 'chemical-tab',
                        'target_site': site_name,
                        'target_parameter': parameter_name,
                        'source_parameter': current_parameter
                    }
                
                # Handle biological navigation  
                elif current_parameter.startswith('bio:'):
                    # Map parameter to community type
                    if current_parameter == 'bio:Fish_IBI':
                        community_type = 'fish'
                    elif current_parameter == 'bio:Macro_Combined':
                        community_type = 'macro'
                    else:
                        logger.warning(f"Unknown biological parameter: {current_parameter}")
                        return dash.no_update, dash.no_update
                    
                    logger.info(f"Navigating from biological map to biological tab for site: {site_name}, community: {community_type}")
                    return "biological-tab", {
                        'target_tab': 'biological-tab',
                        'target_site': site_name,
                        'target_community': community_type,
                        'source_parameter': current_parameter
                    }
                
                # For other parameters, don't navigate yet
                return dash.no_update, dash.no_update
                
            except Exception as e:
                logger.error(f"Error handling map click navigation: {e}")
                return dash.no_update, dash.no_update
        
        return dash.no_update, dash.no_update

    @app.callback(
        Output("navigation-store", "data", allow_duplicate=True),
        Input("main-tabs", "active_tab"),
        [State("navigation-store", "data")],
        prevent_initial_call=True
    )
    def clear_navigation_store_on_tab_change(active_tab, nav_data):
        """Clear navigation store when user manually changes tabs to prevent interference."""
        # Don't clear if we're currently in the middle of navigation
        # This prevents race conditions where map navigation triggers tab change
        # but then immediately clears the navigation data before child tabs can read it
        if nav_data and nav_data.get('target_tab') == active_tab:
            # We're in the middle of map navigation - don't clear yet
            # Let the target tab handle the navigation first
            return dash.no_update
        
        # Clear navigation store for manual tab changes
        return {'target_tab': None, 'target_site': None}