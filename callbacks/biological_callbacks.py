"""
Biological callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the biological data tab.
"""

import dash
from dash import html, Input, Output, State
from utils import setup_logging
from .tab_utilities import create_biological_community_display, create_gallery_navigation_callback
from .helper_functions import create_empty_state, create_error_state

# Configure logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register all biological-related callbacks in logical workflow order."""
    
    # ==================================================
    # 1. NAVIGATION AND DROPDOWN POPULATION  
    # ==================================================
    
    @app.callback(
        [Output('biological-community-dropdown', 'value', allow_duplicate=True),
         Output('biological-site-dropdown', 'options', allow_duplicate=True),
         Output('biological-site-dropdown', 'value', allow_duplicate=True),
         Output('biological-site-search-section', 'style', allow_duplicate=True),
         Output('biological-site-dropdown', 'disabled', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        prevent_initial_call=True
    )
    def handle_biological_navigation_and_initial_load(active_tab, nav_data):
        """Handle navigation from map and initial tab loading."""
        if active_tab != 'biological-tab':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Handle navigation from map
        if (nav_data and nav_data.get('target_tab') == 'biological-tab' and 
            nav_data.get('target_community') and nav_data.get('target_site')):
            
            target_community = nav_data.get('target_community')
            target_site = nav_data.get('target_site')
            
            try:
                # Get sites for the target community type
                from utils import get_sites_with_data
                available_sites = get_sites_with_data(target_community)
                
                if not available_sites:
                    logger.warning(f"No sites found for community type: {target_community}")
                    return (
                        target_community,  # Set community
                        [],  # No site options
                        None,  # No site value
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False  # Enable dropdown
                    )
                
                # Create dropdown options
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                
                # Verify target site is available for this community
                if target_site in available_sites:
                    logger.info(f"Navigation: Setting community to {target_community} and site to {target_site}")
                    return (
                        target_community,  # Set community
                        options,  # Site options
                        target_site,  # Set target site
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False  # Enable dropdown
                    )
                else:
                    logger.warning(f"Target site '{target_site}' not found in available sites for {target_community}")
                    return (
                        target_community,  # Set community
                        options,  # Site options
                        None,  # No site value
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False  # Enable dropdown
                    )
                    
            except Exception as e:
                logger.error(f"Error handling navigation for {target_community}: {e}")
                return (
                    target_community,  # Set community
                    [],  # No options
                    None,  # No site value
                    {'display': 'none'},  # Hide section
                    True  # Disable dropdown
                )
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # ==================================================
    # 2. COMMUNITY SELECTION & SITE DROPDOWN POPULATION
    # ==================================================
    
    @app.callback(
        [Output('biological-site-search-section', 'style'),
         Output('biological-site-dropdown', 'disabled'),
         Output('biological-site-dropdown', 'options'),
         Output('biological-site-dropdown', 'value')],
        [Input('biological-community-dropdown', 'value')],
        [State('biological-site-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_biological_site_dropdown(selected_community, current_site_value):
        """Show site dropdown and populate options when community is selected."""
        if selected_community:
            try:
                # Get sites for the selected community type
                from utils import get_sites_with_data
                available_sites = get_sites_with_data(selected_community)
                
                if not available_sites:
                    logger.warning(f"No sites found for community type: {selected_community}")
                    return (
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False,  # Enable dropdown
                        [],     # No options
                        None    # Clear value
                    )
                
                # Create dropdown options
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                logger.info(f"Populated {selected_community} dropdown with {len(options)} sites")
                
                # Preserve existing site value if it's valid for this community (from navigation)
                site_value_to_set = None
                if current_site_value and current_site_value in available_sites:
                    site_value_to_set = current_site_value
                    logger.info(f"Preserving existing site selection: {current_site_value}")
                
                return (
                    {'display': 'block', 'marginBottom': '20px'},  # Show section
                    False,  # Enable dropdown
                    options,  # Site options
                    site_value_to_set    # Preserve existing selection or clear
                )
                
            except Exception as e:
                logger.error(f"Error populating {selected_community} sites: {e}")
                return (
                    {'display': 'block', 'marginBottom': '20px'},  # Show section
                    False,  # Enable dropdown
                    [],     # No options
                    None    # Clear value
                )
        else:
            # Hide section and disable dropdown when no community selected
            return (
                {'display': 'none'},  # Hide section
                True,   # Disable dropdown
                [],     # Clear options
                None    # Clear value
            )
    
    # ===========================
    # 3. MAIN CONTENT DISPLAY
    # ===========================
    
    @app.callback(
        Output('biological-content-container', 'children'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-site-dropdown', 'value')]
    )
    def update_biological_display(selected_community, selected_site):
        """Update biological display based on selected community and site."""
        if not selected_community or not selected_site:
            return create_empty_state("Please select a community type and site to view biological data.")
        
        try:
            logger.info(f"Creating biological display for {selected_community} at {selected_site}")
            return create_biological_community_display(selected_community, selected_site)
        except Exception as e:
            logger.error(f"Error creating biological display: {e}")
            return create_error_state(
                f"Error Loading {selected_community.title()} Data",
                f"Could not load {selected_community} data for {selected_site}. Please try again.",
                str(e)
            )

    # ===========================
    # 4. GALLERY NAVIGATION
    # ===========================
    
    @app.callback(
        [Output('fish-gallery-container', 'children'),
         Output('current-fish-index', 'data')],
        [Input('prev-fish-button', 'n_clicks'),
         Input('next-fish-button', 'n_clicks')],
        [State('current-fish-index', 'data')]
    )
    def update_fish_gallery(prev_clicks, next_clicks, current_index):
        """Handle fish gallery navigation."""
        update_gallery = create_gallery_navigation_callback('fish')
        return update_gallery(prev_clicks, next_clicks, current_index)
    
    @app.callback(
        [Output('macro-gallery-container', 'children'),
         Output('current-macro-index', 'data')],
        [Input('prev-macro-button', 'n_clicks'),
         Input('next-macro-button', 'n_clicks')],
        [State('current-macro-index', 'data')]
    )
    def update_macro_gallery(prev_clicks, next_clicks, current_index):
        """Handle macroinvertebrate gallery navigation."""
        update_gallery = create_gallery_navigation_callback('macro')
        return update_gallery(prev_clicks, next_clicks, current_index)


