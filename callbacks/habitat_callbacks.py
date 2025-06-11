"""
Habitat callbacks for the Blue Thumb Stream Health Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
from dash import html, Input, Output
from utils import setup_logging, get_sites_with_data
from .tab_utilities import create_habitat_display
from .helper_functions import create_empty_state, create_error_state

# Configure logging
logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register all habitat-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. DROPDOWN POPULATION
    # ===========================
    
    @app.callback(
        Output('habitat-site-dropdown', 'options'),
        Input('main-tabs', 'active_tab')
    )
    def populate_habitat_sites(active_tab):
        """Populate site dropdown options when habitat tab is opened."""
        if active_tab != 'habitat-tab':
            return []
        
        try:
            # Get all sites with habitat data
            sites = get_sites_with_data('habitat')
            
            if not sites:
                logger.warning("No sites with habitat data found")
                return []
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated habitat dropdown with {len(options)} sites")
            
            return options
            
        except Exception as e:
            logger.error(f"Error populating habitat sites: {e}")
            return []
    
    # ===========================
    # 2. DATA VISUALIZATION
    # ===========================
    
    @app.callback(
        [Output('habitat-site-dropdown', 'value'),
         Output('habitat-content-container', 'children')],
        [Input('habitat-site-dropdown', 'value'),
         Input('navigation-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=True
    )
    def update_habitat_content_and_navigation(selected_site, nav_data, active_tab):
        """Update habitat content based on selected site or navigation from map."""
        ctx = dash.callback_context
        
        # Handle navigation from map
        if nav_data and nav_data.get('target_tab') == 'habitat-tab' and active_tab == 'habitat-tab':
            target_site = nav_data.get('target_site')
            if target_site:
                logger.info(f"Navigation triggered: Setting habitat site to {target_site}")
                try:
                    content = create_habitat_display(target_site)
                    return target_site, content
                except Exception as e:
                    logger.error(f"Error creating habitat display for {target_site}: {e}")
                    error_content = create_error_state(
                        "Error Loading Habitat Data",
                        f"Could not load habitat data for {target_site}. Please try again.",
                        str(e)
                    )
                    return target_site, error_content
        
        # Handle normal dropdown selection
        if selected_site:
            try:
                logger.info(f"Creating habitat display for {selected_site}")
                content = create_habitat_display(selected_site)
                return dash.no_update, content
            except Exception as e:
                logger.error(f"Error creating habitat display for {selected_site}: {e}")
                error_content = create_error_state(
                    "Error Loading Habitat Data",
                    f"Could not load habitat data for {selected_site}. Please try again.",
                    str(e)
                )
                return dash.no_update, error_content
        
        # Default case - no site selected
        empty_content = create_empty_state("Select a site above to view habitat assessment data.")
        return dash.no_update, empty_content

