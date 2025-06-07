"""
Habitat callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
from dash import html, Input, Output, State, ALL
from utils import setup_logging, get_sites_with_data
from .helper_functions import (
    should_perform_search, is_item_clicked, extract_selected_item
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
            
            # Filter sites based on search input (case-insensitive)
            search_term = search_value.lower().strip()
            matching_sites = [site for site in available_sites 
                            if search_term in site.lower()]
            
            if not matching_sites:
                return [html.Div(f"No sites found matching '{search_value}'.", 
                            className="p-2 text-muted")], {'display': 'block'}
            
            # Create clickable list items with consistent styling
            result_items = []
            for site in matching_sites[:10]:  # Limit to 10 results
                result_items.append(
                    html.Div(
                        site,
                        id={'type': 'habitat-site-option', 'site': site},
                        style={
                            'padding': '8px 12px',
                            'cursor': 'pointer',
                            'borderBottom': '1px solid #eee'
                        },
                        className="site-option",
                        n_clicks=0
                    )
                )
            
            logger.info(f"Habitat search for '{search_value}' found {len(matching_sites)} sites")
            return result_items, {
                'display': 'block',
                'position': 'absolute',
                'top': '100%',
                'left': '0',
                'right': '0',
                'backgroundColor': 'white',
                'border': '1px solid #ccc',
                'borderTop': 'none',
                'maxHeight': '200px',
                'overflowY': 'auto',
                'zIndex': '1000',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }
            
        except Exception as e:
            logger.error(f"Error in habitat search: {e}")
            return [html.Div("Error searching sites.", 
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
            return _create_empty_state("Select a site above to view habitat assessment data.")
        
        try:
            logger.info(f"Creating habitat display for {selected_site}")
            
            # Import and use the existing helper function
            from callbacks.helper_functions import create_habitat_display
            return create_habitat_display(selected_site)
            
        except Exception as e:
            logger.error(f"Error creating habitat display for {selected_site}: {e}")
            return _create_error_state(
                "Error Loading Habitat Data",
                f"Could not load habitat data for {selected_site}. Please try again.",
                str(e)
            )

# ===========================
# HELPER FUNCTIONS
# ===========================

def _create_empty_state(message):
    """Create a consistent empty state display."""
    return html.Div(
        html.P(message, className="text-center text-muted mt-5"),
        style={'minHeight': '300px', 'display': 'flex', 'alignItems': 'center'}
    )

def _create_error_state(title, message, error_details):
    """Create a consistent error state display."""
    return html.Div([
        html.H4(title, className="text-danger"),
        html.P(message),
        html.Details([
            html.Summary("Error Details"),
            html.Pre(error_details, style={"fontSize": "12px", "color": "red"})
        ])
    ])