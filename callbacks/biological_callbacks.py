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
    
    # ===========================
    # 1. COMMUNITY SELECTION & DROPDOWN POPULATION
    # ===========================
    
    @app.callback(
        [Output('biological-site-search-section', 'style'),
         Output('biological-site-dropdown', 'disabled'),
         Output('biological-site-dropdown', 'options'),
         Output('biological-site-dropdown', 'value')],
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_site_dropdown(selected_community):
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
                
                return (
                    {'display': 'block', 'marginBottom': '20px'},  # Show section
                    False,  # Enable dropdown
                    options,  # Site options
                    None    # Clear previous selection
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
    # 2. MAIN CONTENT DISPLAY
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
    # 3. GALLERY NAVIGATION
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


