"""
Habitat callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import json
import dash
from dash import html, Input, Output, State, dcc, ALL
import dash_bootstrap_components as dbc
from utils import setup_logging, get_sites_with_data

# Configure logging
logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register all habitat-related callbacks."""
    
    # Callback 1: Search results - show matching sites when search button is clicked OR Enter is pressed
    @app.callback(
        [Output('habitat-search-results', 'children'),
        Output('habitat-search-results', 'style')],
        [Input('habitat-search-button', 'n_clicks'),
        Input('habitat-search-input', 'n_submit')],
        State('habitat-search-input', 'value'),
        prevent_initial_call=True
    )
    def update_habitat_search_results(button_clicks, enter_presses, search_value):
        """Update search results based on search input."""
        if (not button_clicks and not enter_presses) or not search_value or not search_value.strip():
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
            
            # Create clickable list items (like chemical/biological tabs)
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
    
    # Callback 2: Site selection - handle clicking on a site from search results
    @app.callback(
        [Output('habitat-selected-site', 'data'),
        Output('habitat-search-input', 'value'),
        Output('habitat-search-results', 'style', allow_duplicate=True)],
        [Input({'type': 'habitat-site-option', 'site': dash.dependencies.ALL}, 'n_clicks')],
        [State('habitat-selected-site', 'data')],
        prevent_initial_call=True
    )
    def handle_habitat_site_selection(site_clicks, current_site):
        """Handle site selection from search results."""
        # Check if any site was clicked
        if not any(site_clicks) or not any(click for click in site_clicks if click):
            return current_site, dash.no_update, dash.no_update
        
        # Get which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return current_site, dash.no_update, dash.no_update
        
        # Extract site name from the triggered button
        triggered_id = ctx.triggered[0]['prop_id']
        import json
        button_data = json.loads(triggered_id.split('.')[0])
        selected_site = button_data['site']
        
        logger.info(f"Habitat site selected: {selected_site}")
        
        return (
            selected_site,  # Store selected site
            selected_site,  # Update search input to show selected site
            {'display': 'none'}  # Hide search results
        )
        
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
    
    # Callback 4: Clear button - clear search input and reset selections
    @app.callback(
        [Output('habitat-search-input', 'value', allow_duplicate=True),
         Output('habitat-selected-site', 'data', allow_duplicate=True),
         Output('habitat-search-results', 'style', allow_duplicate=True)],
        [Input('habitat-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_habitat_search(n_clicks):
        """Clear the habitat search input and reset selections"""
        if n_clicks:
            return (
                "",  # Clear search input
                None,  # Clear selected site
                {'display': 'none'}  # Hide search results
            )
        return dash.no_update, dash.no_update, dash.no_update