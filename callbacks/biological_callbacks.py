"""
Biological callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the biological data tab using the new search pattern.
"""

import json
import dash
from dash import html, Input, Output, State, ALL
from utils import setup_logging, get_sites_with_data
from .helper_functions import create_biological_community_display

# Configure logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register all biological-related callbacks."""
    
    # Community selection callback - shows/hides search section
    @app.callback(
        [Output('biological-site-search-section', 'style'),
         Output('biological-search-input', 'disabled'),
         Output('biological-search-button', 'disabled'),
         Output('biological-search-input', 'value'),
         Output('biological-selected-site', 'data'),
         Output('biological-search-results', 'style'),
         Output('biological-search-results', 'children')],
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_search_visibility(selected_community):
        """
        Show/hide search section based on community selection.
        Clear any previous selections when community changes.
        """
        if selected_community and selected_community != '':
            # Show search section, enable inputs, clear previous selections
            search_section_style = {'display': 'block', 'position': 'relative', 'marginBottom': '20px'}
            input_disabled = False
            button_disabled = False
            search_value = ""
            selected_site = None
            results_style = {'display': 'none'}
            results_children = []
            
            return search_section_style, input_disabled, button_disabled, search_value, selected_site, results_style, results_children
        else:
            # Hide search section, disable inputs
            search_section_style = {'display': 'none'}
            input_disabled = True
            button_disabled = True
            search_value = ""
            selected_site = None
            results_style = {'display': 'none'}
            results_children = []
            
            return search_section_style, input_disabled, button_disabled, search_value, selected_site, results_style, results_children
    
    # Search results callback
    @app.callback(
        [Output('biological-search-results', 'children', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input('biological-search-button', 'n_clicks')],
        [State('biological-search-input', 'value'),
         State('biological-community-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_biological_search_results(n_clicks, search_value, selected_community):
        """
        Filter and display sites based on search input and selected community type.
        """
        if not n_clicks or not search_value or not selected_community:
            return [], {'display': 'none'}
        
        try:
            # Get sites for the selected community type
            available_sites = get_sites_with_data(selected_community)
            
            if not available_sites:
                return [html.Div("No sites found for this community type.", 
                               className="p-2 text-muted")], {'display': 'block'}
            
            # Filter sites based on search input
            filtered_sites = [
                site for site in available_sites 
                if search_value.lower() in site.lower()
            ]
            
            if not filtered_sites:
                return [html.Div("No sites match your search.", 
                               className="p-2 text-muted")], {'display': 'block'}
            
            # Create clickable site options
            site_options = []
            for site in filtered_sites[:10]:  # Limit to first 10 results
                site_options.append(
                    html.Div(
                        site,
                        id={'type': 'biological-site-option', 'site': site},
                        className="p-2 border-bottom clickable-site",
                        style={
                            'cursor': 'pointer',
                            'backgroundColor': 'white',
                            'borderBottom': '1px solid #eee'
                        }
                    )
                )
            
            return site_options, {
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
            logger.error(f"Error in biological search: {e}")
            return [html.Div("Error loading sites.", 
                           className="p-2 text-danger")], {'display': 'block'}
    
    # Site selection callback
    @app.callback(
        [Output('biological-selected-site', 'data', allow_duplicate=True),
         Output('biological-search-input', 'value', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input({'type': 'biological-site-option', 'site': ALL}, 'n_clicks')],
        [State('biological-selected-site', 'data')],
        prevent_initial_call=True
    )
    def handle_biological_site_selection(site_clicks, current_site):
        """
        Handle site selection from search results.
        """
        # Check if any site was clicked
        if not any(site_clicks) or not any(click for click in site_clicks if click):
            return current_site, dash.no_update, dash.no_update
        
        # Find which site was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return current_site, dash.no_update, dash.no_update
        
        try:
            # Extract site name from the triggered component
            triggered_id = ctx.triggered[0]['prop_id']
            site_info = json.loads(triggered_id.split('.')[0])
            selected_site = site_info['site']
            
            logger.info(f"Biological site selected: {selected_site}")
            
            # Update UI: show selected site, hide results
            return (
                selected_site,  # Store selected site
                selected_site,  # Update search input to show selected site
                {'display': 'none'}  # Hide search results
            )
        
        except Exception as e:
            logger.error(f"Error in biological site selection: {e}")
            return current_site, dash.no_update, dash.no_update
    
    # Main biological content callback
    @app.callback(
        Output('biological-content-container', 'children'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-selected-site', 'data')]
    )
    def update_biological_display(selected_community, selected_site):
        """
        Update biological display based on selected community and site.
        """
        if not selected_community or not selected_site:
            return html.Div([
                html.P("Please select a community type and site to view biological data.", 
                       className="text-muted mt-3")
            ])
        
        try:
            # Create the biological community display
            return create_biological_community_display(selected_community, selected_site)
        
        except Exception as e:
            logger.error(f"Error creating biological display: {e}")
            return html.Div([
                html.Div(f"Error loading {selected_community} data for {selected_site}.", 
                        className="alert alert-danger mt-3"),
                html.P("Please try selecting a different site or refresh the page.")
            ])