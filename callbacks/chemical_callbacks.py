"""
Chemical callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the chemical data tab.
"""

import json
import dash
from dash import html, Input, Output, State, ALL
from utils import setup_logging
# REMOVED: cache_utils_future imports - caching disabled for now
from config.data_definitions import SEASON_MONTHS
from .helper_functions import (
    create_all_parameters_view, create_single_parameter_view
)

# Configure logging
logger = setup_logging("chemical_callbacks", category="callbacks")

def register_chemical_callbacks(app):
    """Register all chemical-related callbacks."""
    
    # Search results callback
    @app.callback(
        [Output('chemical-search-results', 'children'),
        Output('chemical-search-results', 'style')],
        [Input('chemical-search-button', 'n_clicks'),
        Input('chemical-search-input', 'n_submit')],  
        [State('chemical-search-input', 'value')],
        prevent_initial_call=True
    )
    def update_search_results(button_clicks, enter_presses, search_term):
        """Show search results when search button is clicked OR Enter is pressed"""
        
        # Check if either the button was clicked or Enter was pressed
        if not button_clicks and not enter_presses:
            return [], {'display': 'none'}
        
        # Check if we have a search term
        if not search_term:
            return [], {'display': 'none'}
        
        try:
            # Get all sites with chemical data
            from data_processing.chemical_processing import get_sites_with_chemical_data
            all_sites = get_sites_with_chemical_data()
            
            # Filter sites based on search term (case-insensitive)
            search_term_lower = search_term.lower()
            matching_sites = [
                site for site in all_sites 
                if search_term_lower in site.lower()
            ]
            
            # If no matches, show "no results"
            if not matching_sites:
                return [
                    html.Div(
                        "No sites found",
                        style={'padding': '8px 12px', 'color': '#6c757d'}
                    )
                ], {
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
            
            # Create clickable list items
            result_items = []
            for site in matching_sites[:10]:  # Limit to 10 results
                result_items.append(
                    html.Div(
                        site,
                        id={'type': 'chemical-site-option', 'site': site},
                        style={
                            'padding': '8px 12px',
                            'cursor': 'pointer',
                            'borderBottom': '1px solid #eee'
                        },
                        className="site-option",
                        n_clicks=0
                    )
                )
            
            logger.info(f"Chemical search for '{search_term}' found {len(matching_sites)} sites")
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
            logger.error(f"Error in chemical site search: {e}")
            return [], {'display': 'none'}

    # Site selection callback
    @app.callback(
        [Output('chemical-selected-site', 'data'),
         Output('chemical-search-input', 'value'),
         Output('chemical-search-results', 'style', allow_duplicate=True),
         Output('chemical-controls-content', 'style')],
        [Input({'type': 'chemical-site-option', 'site': ALL}, 'n_clicks')],
        [State('chemical-selected-site', 'data')],
        prevent_initial_call=True
    )
    def handle_site_selection(site_clicks, current_site):
        """Handle when user clicks on a site from search results"""
        ctx = dash.callback_context
        
        if not ctx.triggered or not any(site_clicks):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Find which site was clicked
        triggered_id = ctx.triggered[0]['prop_id']
        site_info = json.loads(triggered_id.split('.')[0])
        selected_site = site_info['site']
        
        logger.info(f"Selected site: {selected_site}")
        
        return (
            selected_site,  # Store selected site
            selected_site,  # Update search input to show selected site
            {'display': 'none'},  # Hide search results
            {'display': 'block'}  # Show controls
        )
    
    # Clear button callback
    @app.callback(
        [Output('chemical-search-input', 'value', allow_duplicate=True),
        Output('chemical-selected-site', 'data', allow_duplicate=True),
        Output('chemical-search-results', 'style', allow_duplicate=True),
        Output('chemical-controls-content', 'style', allow_duplicate=True)],
        [Input('chemical-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_chemical_search(n_clicks):
        """Clear the chemical search input and reset selections"""
        if n_clicks:
            return (
                "",  # Clear search input
                None,  # Clear selected site
                {'display': 'none'},  # Hide search results
                {'display': 'none'}  # Hide controls
            )
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Main display callback - SIMPLIFIED: No caching, direct data processing
    @app.callback(
        [Output('chemical-graph-container', 'children'),
         Output('chemical-explanation-container', 'children'),
         Output('chemical-diagram-container', 'children')],
        [Input('chemical-parameter-dropdown', 'value'),
         Input('year-range-slider', 'value'),
         Input('month-checklist', 'value'),
         Input('highlight-thresholds-switch', 'value'),
         Input('chemical-selected-site', 'data')]
    )
    def update_chemical_display(selected_parameter, year_range, selected_months, highlight_thresholds, selected_site):
        """
        Update chemical parameter graph and explanations based on user selections.
        SIMPLIFIED: Direct data processing without caching.
        """
        try:
            # If no site selected, return empty
            if not selected_site:
               return html.Div([
                   html.Div("Please search for and select a site to view data.", 
                           className="alert alert-info")
               ]), html.Div(), html.Div()

            logger.info(f"Processing chemical data for site: {selected_site}")
            
            # DIRECT DATA PROCESSING - no cache checking
            from data_processing.chemical_processing import process_chemical_data
            
            # Get and filter chemical data by site
            df_clean, key_parameters, reference_values = process_chemical_data(site_name=selected_site)
            
            # Check if we have any data for this site
            if df_clean.empty:
                no_data_message = html.Div([
                    html.Div(f"No chemical data available for site: {selected_site}", 
                            className="alert alert-warning")
                ])
                return no_data_message, html.Div(), html.Div()
            
            # Filter by year range 
            year_min, year_max = year_range
            df_filtered = df_clean[(df_clean['Year'] >= year_min) & (df_clean['Year'] <= year_max)]
            
            # Filter by selected months 
            if selected_months and len(selected_months) < 12:
                df_filtered = df_filtered[df_filtered['Month'].isin(selected_months)]
            
            # Check if we have data after filtering 
            if len(df_filtered) == 0:
                no_data_message = html.Div([
                    html.Div("No data available for the selected time range.", 
                            className="alert alert-warning")
                ])
                return no_data_message, html.Div(), html.Div()
            
            # Handle "all parameters" view differently 
            if selected_parameter == 'all_parameters':
                graph_component = create_all_parameters_view(
                    df_filtered, 
                    key_parameters, 
                    reference_values, 
                    highlight_thresholds
                )
                explanation_component = html.Div()
                diagram_component = html.Div()
            else:
                # Create components for single parameter view 
                graph_component, explanation_component, diagram_component = create_single_parameter_view(
                    df_filtered, 
                    selected_parameter, 
                    reference_values, 
                    highlight_thresholds
                )
            
            # DIRECT RETURN - no cache storage
            logger.info(f"Successfully processed chemical data for {selected_site}")
            return graph_component, explanation_component, diagram_component
            
        except Exception as e:
            logger.error(f"Error updating chemical display: {e}")
            error_message = html.Div([
                html.Div("Error updating chemical display", className="alert alert-danger"),
                html.Pre(str(e), style={"fontSize": "12px"})
            ])
            return error_message, html.Div(), html.Div()

    # Month selection callback
    @app.callback(
        Output('month-checklist', 'value'),
        [Input('select-all-months', 'n_clicks'),
        Input('select-spring', 'n_clicks'),
        Input('select-summer', 'n_clicks'),
        Input('select-fall', 'n_clicks'),
        Input('select-winter', 'n_clicks')],
        prevent_initial_call=True
    )
    def update_months_selection(all_clicks, spring_clicks, summer_clicks, fall_clicks, winter_clicks):
        """
        Update month selection based on season buttons.
        
        Args:
            all_clicks: Number of clicks on 'All' button
            spring_clicks: Number of clicks on 'Spring' button
            summer_clicks: Number of clicks on 'Summer' button
            fall_clicks: Number of clicks on 'Fall' button
            winter_clicks: Number of clicks on 'Winter' button
            
        Returns:
            List of selected month numbers
        """
        ctx = dash.callback_context
        if not ctx.triggered:
            return SEASON_MONTHS["all"]  # Default to all months
        
        # Determine which button was clicked
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Return month list based on button
        if button_id == "select-all-months":
            return SEASON_MONTHS["all"]
        elif button_id == "select-spring":
            return SEASON_MONTHS["spring"]
        elif button_id == "select-summer":
            return SEASON_MONTHS["summer"]
        elif button_id == "select-fall":
            return SEASON_MONTHS["fall"]
        elif button_id == "select-winter":
            return SEASON_MONTHS["winter"]
        
        # Fallback to all months if something unexpected happens
        return SEASON_MONTHS["all"]