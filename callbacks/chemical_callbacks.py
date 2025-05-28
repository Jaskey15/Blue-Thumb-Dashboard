"""
Chemical callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the chemical data tab.
"""

import dash
from dash import html
from dash.dependencies import Input, Output, State, ALL

from utils import setup_logging
from cache_utils import (
    get_cache_key, get_cached_data, set_cache_data, clear_expired_cache
)
from data_definitions import SEASON_MONTHS
from .helper_functions import (
    update_site_dropdown, handle_site_selection,
    create_all_parameters_view, create_single_parameter_view
)

# Configure logging
logger = setup_logging("chemical_callbacks", category="callbacks")

def register_chemical_callbacks(app):
    """Register all chemical-related callbacks."""
    
    # Site dropdown callback for chemical tab
    @app.callback(
        [Output('chemical-site-dropdown', 'children'),
        Output('chemical-site-dropdown', 'style')],
        [Input('chemical-site-search-input', 'value')],
        [State('chemical-available-sites', 'data'),
        State('chemical-selected-site-data', 'data')]  # Add this State
    )
    def update_chemical_site_dropdown(search_value, data_type, selected_site_data):  # Add parameter
        """Update the chemical site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type, selected_site_data)  # Pass all 3 parameters

    # Site selection callback for chemical tab
    @app.callback(
        [Output('chemical-selected-site-data', 'data'),
        Output('chemical-site-search-input', 'value'),
        Output('chemical-site-clear-button', 'style'),
        Output('chemical-no-site-message', 'style'),
        Output('chemical-controls-content', 'style')],
        [Input({'type': 'site-option', 'index': ALL, 'tab': 'chemical'}, 'n_clicks'),
        Input('chemical-site-clear-button', 'n_clicks')],
        [State('chemical-selected-site-data', 'data')]
    )
    def handle_chemical_site_selection(site_clicks, clear_clicks, current_site):
        """Handle site selection for chemical tab."""
        return handle_site_selection(site_clicks, clear_clicks, current_site, 'chemical')

    # Main chemical display callback
    @app.callback(
        [Output('chemical-graph-container', 'children'),
        Output('chemical-explanation-container', 'children'),
        Output('chemical-diagram-container', 'children'),
        Output('chemical-data-cache', 'data')],  
        [Input('chemical-parameter-dropdown', 'value'),
        Input('year-range-slider', 'value'),
        Input('month-checklist', 'value'),
        Input('highlight-thresholds-switch', 'value'),
        Input('chemical-selected-site-data', 'data')],
        [State('chemical-data-cache', 'data')]
    )
    def update_chemical_display(selected_parameter, year_range, selected_months, highlight_thresholds, selected_site, cache_data):
        """
        Update chemical parameter graph and explanations based on user selections.
        Now includes site filtering and caching for improved performance.
        """
        try:
            # If no site selected, return empty
            if not selected_site:
               return html.Div(), html.Div(), html.Div(), cache_data or {}

            print(f"DEBUG CACHE: Received cache_data keys: {list(cache_data.keys()) if cache_data else 'None'}")
            # Clean expired cache entries periodically
            cache_data = clear_expired_cache(cache_data)
            
            # Generate cache key for this specific request (include site)
            cache_key = get_cache_key("chemical", f"{selected_site}_{selected_parameter or 'all_parameters'}")
            
            # Check if we have valid cached data for this parameter and site
            cached_result = get_cached_data(cache_data, cache_key)
            if cached_result is not None:
                # Cache hit! Return cached components
                graph_component = cached_result.get('graph')
                explanation_component = cached_result.get('explanation') 
                diagram_component = cached_result.get('diagram')
                
                if all([graph_component, explanation_component, diagram_component]):
                    return graph_component, explanation_component, diagram_component, cache_data
            
            # Cache miss - need to fetch fresh data
            from data_processing.chemical_processing import process_chemical_data
            
            # Get and filter chemical data by site
            df_clean, key_parameters, reference_values = process_chemical_data(site_name=selected_site)
            
            # Filter by year range 
            year_min, year_max = year_range
            df_filtered = df_clean[(df_clean['Year'] >= year_min) & (df_clean['Year'] <= year_max)]
            
            # Filter by selected months 
            if selected_months and len(selected_months) < 12:
                df_filtered = df_filtered[df_filtered['Month'].isin(selected_months)]
            
            # Check if we have data after filtering 
            if len(df_filtered) == 0:
                no_data_message = html.Div(
                    "No data available for the selected time range.", 
                    className="alert alert-warning"
                )
                return no_data_message, html.Div(), html.Div(), cache_data
            
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
            
            # Cache the results for future use
            cache_result = {
                'graph': graph_component,
                'explanation': explanation_component,
                'diagram': diagram_component
            }
            cache_data = set_cache_data(cache_data, cache_key, cache_result)
            
            return graph_component, explanation_component, diagram_component, cache_data
            
        except Exception as e:
            print(f"Error updating chemical display: {e}")
            error_message = html.Div([
                html.Div("Error updating chemical display", className="alert alert-danger"),
                html.Pre(str(e), style={"fontSize": "12px"})
            ])
            return error_message, html.Div(), html.Div(), cache_data or {}

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