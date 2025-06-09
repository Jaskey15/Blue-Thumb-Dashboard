"""
Chemical callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the chemical data tab.
"""

import dash
from dash import html, dcc, Input, Output, State, ALL
from utils import setup_logging
from data_processing.chemical_processing import process_chemical_data
from .tab_utilities import create_all_parameters_visualization, create_single_parameter_visualization
from .helper_functions import (
    should_perform_search, is_item_clicked, extract_selected_item,
    create_empty_state, create_error_state, create_loading_state,
    create_search_results
)

# Configure logging
logger = setup_logging("chemical_callbacks", category="callbacks")

def register_chemical_callbacks(app):
    """Register all chemical-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. SITE SEARCH & SELECTION
    # ===========================
    
    @app.callback(
        [Output('chemical-search-results', 'children'),
         Output('chemical-search-results', 'style')],
        [Input('chemical-search-button', 'n_clicks'),
         Input('chemical-search-input', 'n_submit')],
        [State('chemical-search-input', 'value')],
        prevent_initial_call=True
    )
    def update_chemical_search_results(button_clicks, enter_presses, search_value):
        """Filter and display sites based on search input."""
        if not should_perform_search(button_clicks, enter_presses, search_value, True):
            return [], {'display': 'none'}
        
        try:
            # Get all sites with chemical data
            from data_processing.data_queries import get_sites_with_chemical_data
            all_sites = get_sites_with_chemical_data()
            
            if not all_sites:
                return [html.Div("No chemical data available.", 
                            className="p-2 text-warning")], {'display': 'block'}
            
            # Filter sites based on search term (case-insensitive)
            search_term_lower = search_value.lower()
            matching_sites = [
                site for site in all_sites 
                if search_term_lower in site.lower()
            ]
            
            # Use shared function to create consistent search results
            return create_search_results(matching_sites, 'chemical', search_value)
            
        except Exception as e:
            logger.error(f"Error in chemical search: {e}")
            return [html.Div("Error performing search.", 
                        className="p-2 text-danger")], {'display': 'block'}
    
    @app.callback(
        [Output('chemical-selected-site', 'data'),
         Output('chemical-search-input', 'value'),
         Output('chemical-search-results', 'style', allow_duplicate=True),
         Output('chemical-controls-content', 'style')],
        [Input({'type': 'chemical-site-option', 'site': ALL}, 'n_clicks')],
        [State('chemical-selected-site', 'data')],
        prevent_initial_call=True
    )
    def select_chemical_site(site_clicks, current_site):
        """Handle site selection from search results."""
        if not is_item_clicked(site_clicks):
            return current_site, dash.no_update, dash.no_update, dash.no_update
        
        try:
            selected_site = extract_selected_item('site')
            logger.info(f"Chemical site selected: {selected_site}")
            
            return (
                selected_site,           # Store selected site
                selected_site,           # Update search input to show selected site
                {'display': 'none'},     # Hide search results
                {'display': 'block'}     # Show parameter controls
            )
            
        except Exception as e:
            logger.error(f"Error in chemical site selection: {e}")
            return current_site, dash.no_update, dash.no_update, dash.no_update
    
    @app.callback(
        [Output('chemical-search-input', 'value', allow_duplicate=True),
         Output('chemical-selected-site', 'data', allow_duplicate=True),
         Output('chemical-search-results', 'style', allow_duplicate=True),
         Output('chemical-controls-content', 'style', allow_duplicate=True)],
        [Input('chemical-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_chemical_search(n_clicks):
        """Clear search input and reset all selections."""
        if n_clicks:
            logger.info("Chemical search cleared")
            return (
                "",                     # Clear search input
                None,                   # Clear selected site
                {'display': 'none'},    # Hide search results
                {'display': 'none'}     # Hide parameter controls
            )
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # ================================
    # 2. DATA VISUALIZATION & FILTERS
    # ================================
    
    @app.callback(
        Output('month-checklist', 'value'),
        [Input('select-all-months', 'n_clicks'),
         Input('select-spring', 'n_clicks'),
         Input('select-summer', 'n_clicks'), 
         Input('select-fall', 'n_clicks'),
         Input('select-winter', 'n_clicks')],
        prevent_initial_call=True
    )
    def update_month_selection(all_clicks, spring_clicks, summer_clicks, fall_clicks, winter_clicks):
        """Update month selection based on season button clicks."""
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return dash.no_update
        
        # Get which button was clicked
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Define season mappings
        season_months = {
            'select-all-months': list(range(1, 13)),  # All months
            'select-spring': [3, 4, 5],      # March, April, May
            'select-summer': [6, 7, 8],      # June, July, August  
            'select-fall': [9, 10, 11],      # September, October, November
            'select-winter': [12, 1, 2],     # December, January, February
        }
        
        return season_months.get(button_id, dash.no_update)
    
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
    def update_chemical_display(selected_parameter, year_range, selected_months, 
                              highlight_thresholds, selected_site):
        """Update chemical parameter visualization based on user selections."""
        
        # Validate inputs
        if not selected_site:
            return create_empty_state("Please search for and select a site to view data."), html.Div(), html.Div()
        
        if not selected_parameter:
            return create_empty_state("Please select a parameter to visualize."), html.Div(), html.Div()
        
        try:
            logger.info(f"Creating chemical visualization for {selected_site}, parameter: {selected_parameter}")
            
            # Get processed data
            df_filtered, key_parameters, reference_values = process_chemical_data(
                site_name=selected_site, use_db=True
            )
            
            # Filter by year range and months
            if not df_filtered.empty:
                df_filtered = df_filtered[
                    (df_filtered['Year'] >= year_range[0]) & 
                    (df_filtered['Year'] <= year_range[1])
                ]
                
                if selected_months:
                    df_filtered = df_filtered[df_filtered['Month'].isin(selected_months)]
            
            # Create visualization based on parameter selection
            if selected_parameter == 'all_parameters':
                graph, explanation, diagram = create_all_parameters_visualization(
                    df_filtered, key_parameters, reference_values, highlight_thresholds
                )
            else:
                graph, explanation, diagram = create_single_parameter_visualization(
                    df_filtered, selected_parameter, reference_values, highlight_thresholds
                )
                
            return graph, explanation, diagram
                
        except Exception as e:
            logger.error(f"Error creating chemical visualization: {e}")
            error_state = create_error_state(
                "Error Loading Chemical Data",
                f"Could not load chemical data for {selected_site}. Please try again.",
                str(e)
            )
            return error_state, html.Div(), html.Div()


