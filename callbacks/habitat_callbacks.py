"""
Habitat callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
from dash import html, Input, Output, State, dcc
import dash_bootstrap_components as dbc
from utils import setup_logging, get_sites_with_data

# Configure logging
logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register all habitat-related callbacks."""
    
    # Callback 1: Search results - show matching sites when search button is clicked
    @app.callback(
        Output('habitat-search-results', 'children'),
        Input('habitat-search-button', 'n_clicks'),
        State('habitat-search-input', 'value'),
        prevent_initial_call=True
    )
    def update_habitat_search_results(n_clicks, search_value):
        """Update search results based on search input."""
        if not search_value or not search_value.strip():
            return html.P("Please enter a search term.", className="text-muted")
        
        try:
            # Get all sites with habitat data
            available_sites = get_sites_with_data('habitat')
            
            if not available_sites:
                return html.P("No habitat data available.", className="text-warning")
            
            # Filter sites based on search input (case-insensitive)
            search_term = search_value.lower().strip()
            matching_sites = [site for site in available_sites 
                            if search_term in site.lower()]
            
            if not matching_sites:
                return html.P(f"No sites found matching '{search_value}'.", 
                            className="text-muted")
            
            # Create clickable buttons for each matching site
            site_buttons = []
            for site in matching_sites[:10]:  # Limit to 10 results
                button = dbc.Button(
                    site,
                    id={'type': 'habitat-site-button', 'site': site},
                    color="outline-primary",
                    size="sm",
                    className="me-2 mb-2"
                )
                site_buttons.append(button)
            
            return html.Div([
                html.P(f"Found {len(matching_sites)} matching sites:", 
                      className="text-success mb-2"),
                html.Div(site_buttons)
            ])
            
        except Exception as e:
            logger.error(f"Error in habitat search: {e}")
            return html.P("Error searching sites. Please try again.", 
                        className="text-danger")
    
    # Callback 2: Site selection - handle clicking on a site button
    @app.callback(
        Output('habitat-selected-site', 'data'),
        Input({'type': 'habitat-site-button', 'site': dash.dependencies.ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_habitat_site_selection(n_clicks_list):
        """Handle site selection from search results."""
        # Get which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # Extract site name from the triggered button
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id:
            import json
            button_data = json.loads(button_id)
            selected_site = button_data['site']
            logger.info(f"Habitat site selected: {selected_site}")
            return selected_site
        
        return dash.no_update
    
    # Clear button callback
    @app.callback(
        [Output('habitat-search-input', 'value'),
        Output('habitat-selected-site', 'data', allow_duplicate=True),
        Output('habitat-search-results', 'children', allow_duplicate=True)],
        [Input('habitat-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_habitat_search(n_clicks):
        """Clear the habitat search input and reset selections"""
        if n_clicks:
            return (
                "",  # Clear search input
                None,  # Clear selected site
                [html.P("Enter a search term and click 'Search' to find monitoring sites.", 
                    className="text-muted")]  # Reset search results
            )
        return dash.no_update, dash.no_update, dash.no_update
    
    # Callback 3: Main display - show habitat visualization when site is selected
    @app.callback(
        Output('habitat-content-container', 'children'),
        Input('habitat-selected-site', 'data'),
        prevent_initial_call=True
    )
    def update_habitat_content(selected_site):
        """Update habitat content based on selected site."""
        if not selected_site:
            return html.P("Select a site above to view habitat assessment data.", 
                        className="text-center text-muted mt-5")
        
        try:
            # Import helper function to create the display
            from callbacks.helper_functions import create_habitat_display
            return create_habitat_display(selected_site)
            
        except Exception as e:
            logger.error(f"Error creating habitat display for {selected_site}: {e}")
            return html.Div([
                html.H4("Error Loading Data", className="text-danger"),
                html.P(f"Could not load habitat data for {selected_site}. Please try again."),
                html.Details([
                    html.Summary("Error Details"),
                    html.Pre(str(e), style={"fontSize": "12px", "color": "red"})
                ])
            ])