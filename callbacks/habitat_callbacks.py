"""
Habitat callbacks for the Blue Thumb Stream Health Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
from dash import html, Input, Output, State
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
        [Output('habitat-site-dropdown', 'options'),
         Output('habitat-site-dropdown', 'value', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        prevent_initial_call=True
    )
    def populate_habitat_sites_and_handle_navigation(active_tab, nav_data):
        """Populate site dropdown options and handle navigation from map."""
        if active_tab != 'habitat-tab':
            return [], dash.no_update
        
        try:
            # Get all sites with habitat data
            sites = get_sites_with_data('habitat')
            
            if not sites:
                logger.warning("No sites with habitat data found")
                return [], dash.no_update
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated habitat dropdown with {len(options)} sites")
            
            # Check if we need to set a specific site from navigation
            if nav_data and nav_data.get('target_tab') == 'habitat-tab' and active_tab == 'habitat-tab':
                target_site = nav_data.get('target_site')
                if target_site and target_site in sites:
                    logger.info(f"Setting dropdown value to {target_site} from navigation")
                    return options, target_site
                elif target_site:
                    logger.warning(f"Navigation target site '{target_site}' not found in available sites")
            
            return options, dash.no_update
            
        except Exception as e:
            logger.error(f"Error populating habitat sites: {e}")
            return [], dash.no_update
    
    # ===========================
    # 2. DATA VISUALIZATION
    # ===========================
    
    @app.callback(
        Output('habitat-content-container', 'children'),
        Input('habitat-site-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_habitat_content(selected_site):
        """Update habitat content based on selected site."""        
        # Handle site selection
        if selected_site:
            try:
                logger.info(f"Creating habitat display for {selected_site}")
                content = create_habitat_display(selected_site)
                return content
            except Exception as e:
                logger.error(f"Error creating habitat display for {selected_site}: {e}")
                error_content = create_error_state(
                    "Error Loading Habitat Data",
                    f"Could not load habitat data for {selected_site}. Please try again.",
                    str(e)
                )
                return error_content
        
        # Default case - no site selected
        empty_content = create_empty_state("Select a site above to view habitat assessment data.")
        return empty_content

