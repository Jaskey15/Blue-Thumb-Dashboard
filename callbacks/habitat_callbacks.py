"""
Habitat callbacks for the Blue Thumb Stream Health Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
from dash import html, dcc, Input, Output, State, ALL
from utils import setup_logging, get_sites_with_data
from visualizations.habitat_viz import create_habitat_viz, create_habitat_metrics_accordion
from .helper_functions import (
    should_perform_search, is_item_clicked, extract_selected_item,
    create_empty_state, create_error_state, create_search_results
)

# Configure logging
logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register all habitat-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. SITE SEARCH & SELECTION
    # ===========================
    
    @app.callback(
        [Output('habitat-search-results', 'children'),
         Output('habitat-search-results', 'style')],
        [Input('habitat-search-button', 'n_clicks'),
         Input('habitat-search-input', 'n_submit')],
        [State('habitat-search-input', 'value')],
        prevent_initial_call=True
    )
    def update_habitat_search_results(button_clicks, enter_presses, search_value):
        """Filter and display sites based on search input."""
        if not should_perform_search(button_clicks, enter_presses, search_value, True):
            return [], {'display': 'none'}
        
        try:
            # Get all sites with habitat data
            available_sites = get_sites_with_data('habitat')
            
            if not available_sites:
                return [html.Div("No habitat data available.", 
                            className="p-2 text-warning")], {'display': 'block'}
            
            # Filter sites based on search term (case-insensitive)
            search_term_lower = search_value.lower()
            matching_sites = [
                site for site in available_sites 
                if search_term_lower in site.lower()
            ]
            
            # Use shared function to create consistent search results
            return create_search_results(matching_sites, 'habitat', search_value)
            
        except Exception as e:
            logger.error(f"Error in habitat search: {e}")
            return [html.Div("Error performing search.", 
                        className="p-2 text-danger")], {'display': 'block'}
    
    @app.callback(
        [Output('habitat-selected-site', 'data'),
         Output('habitat-search-input', 'value'),
         Output('habitat-search-results', 'style', allow_duplicate=True)],
        [Input({'type': 'habitat-site-option', 'site': ALL}, 'n_clicks')],
        [State('habitat-selected-site', 'data')],
        prevent_initial_call=True
    )
    def select_habitat_site(site_clicks, current_site):
        """Handle site selection from search results."""
        if not is_item_clicked(site_clicks):
            return current_site, dash.no_update, dash.no_update
        
        try:
            selected_site = extract_selected_item('site')
            
            logger.info(f"Habitat site selected: {selected_site}")
            
            return (
                selected_site,  # Store selected site
                selected_site,  # Update search input to show selected site
                {'display': 'none'}  # Hide search results
            )
            
        except Exception as e:
            logger.error(f"Error in habitat site selection: {e}")
            return current_site, dash.no_update, dash.no_update
    
    @app.callback(
        [Output('habitat-search-input', 'value', allow_duplicate=True),
         Output('habitat-selected-site', 'data', allow_duplicate=True),
         Output('habitat-search-results', 'style', allow_duplicate=True)],
        [Input('habitat-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_habitat_search(n_clicks):
        """Clear search input and reset all selections."""
        if n_clicks:
            logger.info("Habitat search cleared")
            return (
                "",  # Clear search input
                None,  # Clear selected site
                {'display': 'none'}  # Hide search results
            )
        return dash.no_update, dash.no_update, dash.no_update
    
    # ===========================
    # 2. DATA VISUALIZATION
    # ===========================
    
    @app.callback(
        Output('habitat-content-container', 'children'),
        Input('habitat-selected-site', 'data'),
        prevent_initial_call=True
    )
    def update_habitat_content(selected_site):
        """Update habitat content based on selected site."""
        if not selected_site:
            return create_empty_state("Select a site above to view habitat assessment data.")
        
        try:
            logger.info(f"Creating habitat display for {selected_site}")
            
            return _create_habitat_display(selected_site)
            
        except Exception as e:
            logger.error(f"Error creating habitat display for {selected_site}: {e}")
            return create_error_state(
                "Error Loading Habitat Data",
                f"Could not load habitat data for {selected_site}. Please try again.",
                str(e)
            )

