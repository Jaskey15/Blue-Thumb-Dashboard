"""
Core callbacks shared across the dashboard.
"""

import dash
from dash.dependencies import Input, Output, State
from utils import setup_logging

# Initialize callback logging
logger = setup_logging("shared_callbacks", category="callbacks")

def register_shared_callbacks(app):
    """Register shared callbacks for modals and navigation."""
    
    # Modal controls
    @app.callback(
        Output("attribution-modal", "is_open"),
        [Input("attribution-link", "n_clicks"), 
        Input("close-attribution", "n_clicks")],
        [State("attribution-modal", "is_open")]
    )
    def toggle_attribution_modal(n1, n2, is_open):
        """Toggle attribution modal visibility."""
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
        """Toggle image credits modal visibility."""
        if n1 or n2:
            return not is_open
        return is_open

    # Map and overview navigation
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
        Route user to appropriate tab based on map clicks and overview links.
        
        Extracts site and parameter info from map clicks to navigate to the correct
        detail tab. Overview links return to the main map view.
        """
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Return to overview map
        if trigger_id in ['chemical-overview-link', 'biological-overview-link', 'habitat-overview-link']:
            return "overview-tab", {'target_tab': None, 'target_site': None}
        
        # Handle map click navigation
        if trigger_id == 'site-map-graph' and click_data and current_parameter:
            try:
                # Extract site from hover text
                hover_text = click_data['points'][0]['text']
                site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
                
                # Route to habitat tab
                if current_parameter == 'habitat:Habitat_Score':
                    logger.info(f"Navigating from habitat map to habitat tab for site: {site_name}")
                    return "habitat-tab", {
                        'target_tab': 'habitat-tab',
                        'target_site': site_name,
                        'source_parameter': current_parameter
                    }
                
                # Route to chemical tab with parameter context
                elif current_parameter.startswith('chem:'):
                    parameter_name = current_parameter.split(':', 1)[1]
                    logger.info(f"Navigating from chemical map to chemical tab for site: {site_name}, parameter: {parameter_name}")
                    return "chemical-tab", {
                        'target_tab': 'chemical-tab',
                        'target_site': site_name,
                        'target_parameter': parameter_name,
                        'source_parameter': current_parameter
                    }
                
                # Route to biological tab with community context
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
                
                return dash.no_update, dash.no_update
                
            except Exception as e:
                logger.error(f"Error handling map click navigation: {e}")
                return dash.no_update, dash.no_update
        
        return dash.no_update, dash.no_update
