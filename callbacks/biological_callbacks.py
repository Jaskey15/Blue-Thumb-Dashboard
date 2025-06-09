"""
Biological callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the biological data tab.
"""

import dash
from dash import html, Input, Output, State, ALL
from utils import setup_logging
from .tab_utilities import create_biological_community_display, create_gallery_navigation_callback
from .helper_functions import (
    should_perform_search, is_item_clicked, extract_selected_item,
    create_empty_state, create_error_state, create_search_results
)

# Configure logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register all biological-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. COMMUNITY SELECTION
    # ===========================
    
    @app.callback(
        [Output('biological-site-search-section', 'style'),
         Output('biological-search-input', 'disabled'),
         Output('biological-search-button', 'disabled'),
         Output('biological-clear-button', 'disabled'),  
         Output('biological-search-input', 'value'),
         Output('biological-selected-site', 'data'),
         Output('biological-search-results', 'style'),
         Output('biological-search-results', 'children')],
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_search_visibility(selected_community):
        """Show/hide search section and reset state when community is selected."""
        if selected_community:
            # Show search section and enable inputs
            return (
                {'display': 'block', 'position': 'relative', 'marginBottom': '20px'},  # search_section_style
                False,  # input_disabled
                False,  # button_disabled
                False,  # clear_disabled
                "",     # search_value (clear)
                None,   # selected_item (clear)
                {'display': 'none'},  # results_style
                []      # results_children (clear)
            )
        else:
            # Hide search section and disable inputs
            return (
                {'display': 'none'},  # search_section_style
                True,   # input_disabled
                True,   # button_disabled
                True,   # clear_disabled
                "",     # search_value (clear)
                None,   # selected_item (clear)
                {'display': 'none'},  # results_style
                []      # results_children (clear)
            )
    
    # ===========================
    # 2. SITE SEARCH & SELECTION
    # ===========================
    
    @app.callback(
        [Output('biological-search-results', 'children', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input('biological-search-button', 'n_clicks'),
         Input('biological-search-input', 'n_submit')],
        [State('biological-search-input', 'value'),
         State('biological-community-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_biological_search_results(button_clicks, enter_presses, search_value, selected_community):
        """Filter and display sites based on search input."""
        if not should_perform_search(button_clicks, enter_presses, search_value, selected_community):
            return [], {'display': 'none'}
        
        try:
            # Get sites for the selected community type
            from utils import get_sites_with_data
            available_sites = get_sites_with_data(selected_community)
            
            if not available_sites:
                return [html.Div("No sites found for this community type.", 
                            className="p-2 text-muted")], {'display': 'block'}
            
            # Filter sites based on search
            search_term = search_value.lower().strip()
            matching_sites = [
                site for site in available_sites 
                if search_term in site.lower()
            ]
            
            # Use shared function to create consistent search results
            return create_search_results(matching_sites, 'biological', search_value)
            
        except Exception as e:
            logger.error(f"Error in biological search: {e}")
            return [html.Div("Error performing search.", 
                        className="p-2 text-danger")], {'display': 'block'}
    
    @app.callback(
        [Output('biological-selected-site', 'data', allow_duplicate=True),
         Output('biological-search-input', 'value', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input({'type': 'biological-site-option', 'site': ALL}, 'n_clicks')],
        [State('biological-selected-site', 'data')],
        prevent_initial_call=True
    )
    def select_biological_site(site_clicks, current_site):
        """Handle site selection from search results."""
        if not is_item_clicked(site_clicks):
            return current_site, dash.no_update, dash.no_update
        
        try:
            selected_site = extract_selected_item('site')
            logger.info(f"Biological site selected: {selected_site}")
            
            return (
                selected_site,           # Store selected site
                selected_site,           # Update search input
                {'display': 'none'}      # Hide search results
            )
        except Exception as e:
            logger.error(f"Error in biological site selection: {e}")
            return current_site, dash.no_update, dash.no_update
    
    @app.callback(
        [Output('biological-search-input', 'value', allow_duplicate=True),
         Output('biological-selected-site', 'data', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input('biological-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_biological_search(n_clicks):
        """Clear search input and reset selections."""
        if n_clicks:
            logger.info("Biological search cleared")
            return "", None, {'display': 'none'}
        return dash.no_update, dash.no_update, dash.no_update
    
    # ===========================
    # 3. MAIN CONTENT DISPLAY
    # ===========================
    
    @app.callback(
        Output('biological-content-container', 'children'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-selected-site', 'data')]
    )
    def update_biological_display(selected_community, selected_site):
        """Update biological display based on selected community and site."""
        if not selected_community or not selected_site:
            return create_empty_state("Please select a community type and site to view biological data.")
        
        try:
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


