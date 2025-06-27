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
    # 1. STATE MANAGEMENT
    # ===========================
    
    @app.callback(
        Output('habitat-tab-state', 'data'),
        Input('habitat-site-dropdown', 'value'),
        [State('habitat-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_habitat_state(selected_site, current_state):
        """Save habitat tab state when selections change."""
        # Only save valid selections, don't overwrite with None
        if selected_site is not None:
            logger.info(f"Saving habitat state: {selected_site}")
            return {'selected_site': selected_site}
        else:
            # Keep existing state when dropdown is cleared
            return current_state or {'selected_site': None}
    
    # ===========================
    # 2. DROPDOWN POPULATION
    # ===========================
    
    @app.callback(
        [Output('habitat-site-dropdown', 'options'),
         Output('habitat-site-dropdown', 'value', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        [State('habitat-tab-state', 'data')],
        prevent_initial_call=True
    )
    def populate_habitat_sites_and_handle_navigation(active_tab, nav_data, habitat_state):
        """Populate site dropdown options and handle navigation from map or restore from state."""
        if active_tab != 'habitat-tab':
            return [], dash.no_update
        
        # Get the trigger to understand what caused this callback
        ctx = dash.callback_context
        if not ctx.triggered:
            return [], dash.no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            # Get all sites with habitat data
            sites = get_sites_with_data('habitat')
            
            if not sites:
                logger.warning("No sites with habitat data found")
                return [], dash.no_update
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated habitat dropdown with {len(options)} sites")
            
            # Priority 1: Check if we need to set a specific site from navigation (map clicks)
            # Handle navigation data regardless of trigger source
            if (nav_data and nav_data.get('target_tab') == 'habitat-tab' and nav_data.get('target_site')):
                target_site = nav_data.get('target_site')
                if target_site in sites:
                    return options, target_site
                else:
                    logger.warning(f"Navigation target site '{target_site}' not found in available sites")
            
            # Priority 2: Restore from saved state if tab was just activated AND no active navigation
            if (trigger_id == 'main-tabs' and habitat_state and habitat_state.get('selected_site') and
                (not nav_data or not nav_data.get('target_tab'))):
                saved_site = habitat_state.get('selected_site')
                if saved_site in sites:
                    return options, saved_site
                else:
                    logger.warning(f"Saved site '{saved_site}' no longer available in habitat data")
            
            # Ignore navigation-store clearing events (when nav_data is empty/None)
            if trigger_id == 'navigation-store' and (not nav_data or not nav_data.get('target_tab')):
                return options, dash.no_update
            
            return options, dash.no_update
            
        except Exception as e:
            logger.error(f"Error populating habitat sites: {e}")
            return [], dash.no_update
    
    # ===========================
    # 3. DATA VISUALIZATION
    # ===========================
    
    @app.callback(
        Output('habitat-controls-content', 'style'),
        Input('habitat-site-dropdown', 'value')
    )
    def show_habitat_controls(selected_site):
        """Show habitat content when a site is selected."""
        if selected_site:
            logger.info(f"Habitat site selected: {selected_site}")
            return {'display': 'block'}
        return {'display': 'none'}
    
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

