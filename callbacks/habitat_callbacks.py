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
        Output('habitat-content-container', 'children'),
        Input('habitat-site-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_habitat_content(selected_site):
        """Update habitat content based on selected site."""
        if not selected_site:
            return create_empty_state("Select a site above to view habitat assessment data.")
        
        try:
            logger.info(f"Creating habitat display for {selected_site}")
            
            return create_habitat_display(selected_site)
            
        except Exception as e:
            logger.error(f"Error creating habitat display for {selected_site}: {e}")
            return create_error_state(
                "Error Loading Habitat Data",
                f"Could not load habitat data for {selected_site}. Please try again.",
                str(e)
            )

