"""
Callback functions for the Tenmile Creek Water Quality Dashboard.
This file contains all the callbacks that handle user interactions.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
from utils import setup_logging, get_sites_with_data

from cache_utils import (
    get_cache_key, is_cache_valid, get_cached_data, 
    set_cache_data, clear_expired_cache
)

from data_definitions import SEASON_MONTHS

# Import helper functions
from .helper_functions import (
    get_parameter_legend, get_parameter_label, get_parameter_name,
    get_site_count_message, create_species_display, create_all_parameters_view,
    create_single_parameter_view, create_biological_community_display,
    create_gallery_navigation_callback, update_site_dropdown,
    update_site_dropdown_with_sites, handle_site_selection
)

# Configure logging
logger = setup_logging("callbacks", category="app")

# --------------------------------------------------------------------------------------
# CALLBACK REGISTRATION FUNCTION
# --------------------------------------------------------------------------------------

def register_callbacks(app):
    """Register all callbacks for the dashboard."""
    
    # --------------------------------------------------------------------------------------
    # SITE SELECTOR CALLBACKS - SIMPLIFIED VERSION
    # --------------------------------------------------------------------------------------

    @app.callback(
        [Output('chemical-site-dropdown', 'children'),
         Output('chemical-site-dropdown', 'style')],
        [Input('chemical-site-search-input', 'value')],
        [State('chemical-available-sites', 'data'),
         State('chemical-selected-site-data', 'data')]
    )
    def update_chemical_site_dropdown(search_value, data_type, selected_site_data):
        """Update the chemical site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type, selected_site_data)

    @app.callback(
        [Output('biological-site-dropdown', 'children'),
         Output('biological-site-dropdown', 'style')],
        [Input('biological-site-search-input', 'value')],
        [State('biological-available-sites', 'data'),
         State('biological-selected-site-data', 'data')]
    )
    def update_biological_site_dropdown(search_value, data_type, selected_site_data):
        """Update the biological site dropdown based on search input."""
        # For biological data, we need to get sites that have either fish OR macro data
        fish_sites = get_sites_with_data('fish')
        macro_sites = get_sites_with_data('macro')
        biological_sites = list(set(fish_sites + macro_sites))  # Combine and remove duplicates
        
        return update_site_dropdown_with_sites(search_value, biological_sites, selected_site_data)

    @app.callback(
        [Output('habitat-site-dropdown', 'children'),
         Output('habitat-site-dropdown', 'style')],
        [Input('habitat-site-search-input', 'value')],
        [State('habitat-available-sites', 'data'),
         State('habitat-selected-site-data', 'data')]
    )
    def update_habitat_site_dropdown(search_value, data_type, selected_site_data):
        """Update the habitat site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type, selected_site_data)

    # Site selection callbacks for each tab - SIMPLIFIED VERSION
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

    @app.callback(
        [Output('biological-selected-site-data', 'data'),
         Output('biological-site-search-input', 'value'),
         Output('biological-site-clear-button', 'style'),
         Output('biological-no-site-message', 'style'),
         Output('biological-controls-content', 'style')],
        [Input({'type': 'site-option', 'index': ALL, 'tab': 'biological'}, 'n_clicks'),
         Input('biological-site-clear-button', 'n_clicks')],
        [State('biological-selected-site-data', 'data')]
    )
    def handle_biological_site_selection(site_clicks, clear_clicks, current_site):
        """Handle site selection for biological tab."""
        return handle_site_selection(site_clicks, clear_clicks, current_site, 'biological')

    @app.callback(
        [Output('habitat-selected-site-data', 'data'),
         Output('habitat-site-search-input', 'value'),
         Output('habitat-site-clear-button', 'style'),
         Output('habitat-no-site-message', 'style'),
         Output('habitat-controls-content', 'style')],
        [Input({'type': 'site-option', 'index': ALL, 'tab': 'habitat'}, 'n_clicks'),
         Input('habitat-site-clear-button', 'n_clicks')],
        [State('habitat-selected-site-data', 'data')]
    )
    def handle_habitat_site_selection(site_clicks, clear_clicks, current_site):
        """Handle site selection for habitat tab."""
        return handle_site_selection(site_clicks, clear_clicks, current_site, 'habitat')

    # --------------------------------------------------------------------------------------
    # CHEMICAL TAB CALLBACKS
    # --------------------------------------------------------------------------------------

    @app.callback(
        [Output('chemical-graph-container', 'children'),
        Output('chemical-explanation-container', 'children'),
        Output('chemical-diagram-container', 'children'),
        Output('chemical-data-cache', 'data')],  
        [Input('chemical-parameter-dropdown', 'value'),
        Input('year-range-slider', 'value'),
        Input('month-checklist', 'value'),
        Input('highlight-thresholds-switch', 'value'),
        Input('chemical-selected-site-data', 'data')],  # Add this input
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

   # --------------------------------------------------------------------------------------
   # BIOLOGICAL TAB CALLBACKS
   # --------------------------------------------------------------------------------------

    @app.callback(
        Output('biological-content-container', 'children'),
        [Input('biological-community-dropdown', 'value'),
        Input('biological-selected-site-data', 'data')]
    )
    def update_biological_display_callback(selected_community, selected_site):
        """
        Update biological display based on selected community and site.
        
        Args:
            selected_community: Selected biological community ('fish' or 'macro')
            selected_site: Selected site name
            
        Returns:
            Dash HTML component with the biological display
        """
        if not selected_community or not selected_site:
            return html.Div("Please select a biological community from the dropdown.")
        
        return create_biological_community_display(selected_community, selected_site)

    @app.callback(
        [Output('fish-gallery-container', 'children'),
        Output('current-fish-index', 'data')],
        [Input('prev-fish-button', 'n_clicks'),
        Input('next-fish-button', 'n_clicks')],
        [State('current-fish-index', 'data')]
    )
    def update_fish_gallery_callback(prev_clicks, next_clicks, current_index):
        """
        Update fish gallery based on navigation buttons.
        
        Args:
            prev_clicks: Number of clicks on previous button
            next_clicks: Number of clicks on next button
            current_index: Current index in the gallery
            
        Returns:
            Tuple of (gallery_display, new_index)
        """
        return create_gallery_navigation_callback('fish')(prev_clicks, next_clicks, current_index)

    @app.callback(
        [Output('macro-gallery-container', 'children'),
        Output('current-macro-index', 'data')],
        [Input('prev-macro-button', 'n_clicks'),
        Input('next-macro-button', 'n_clicks')],
        [State('current-macro-index', 'data')]
    )
    def update_macro_gallery_callback(prev_clicks, next_clicks, current_index):
        """
        Update macroinvertebrate gallery based on navigation buttons.
        
        Args:
            prev_clicks: Number of clicks on previous button
            next_clicks: Number of clicks on next button
            current_index: Current index in the gallery
            
        Returns:
            Tuple of (gallery_display, new_index)
        """
        return create_gallery_navigation_callback('macro')(prev_clicks, next_clicks, current_index)

   # --------------------------------------------------------------------------------------
   # HABITAT TAB CALLBACKS  
   # --------------------------------------------------------------------------------------

    @app.callback(
        [Output('habitat-graph-container', 'children'),
        Output('habitat-table-container', 'children')],
        [Input('habitat-selected-site-data', 'data')]
    )
    def update_habitat_display_callback(selected_site):
        """
        Update habitat display based on selected site.
        
        Args:
            selected_site: Selected site name
            
        Returns:
            Tuple of (graph_component, table_component)
        """
        if not selected_site:
            return html.Div(), html.Div()
        
        try:
            # Import habitat visualization functions
            from visualizations.habitat_viz import create_habitat_viz, create_habitat_metrics_accordion
            
            # Create graph (you'll need to modify this to accept site parameter)
            graph_component = dcc.Graph(figure=create_habitat_viz())
            
            # Create metrics table
            table_component = create_habitat_metrics_accordion()
            
            return graph_component, table_component
            
        except Exception as e:
            print(f"Error creating habitat display: {e}")
            error_component = html.Div([
                html.Div("Error creating habitat display", className="alert alert-danger"),
                html.Pre(str(e), style={"fontSize": "12px"})
            ])
            return error_component, html.Div()
   
   # --------------------------------------------------------------------------------------
   # ATTRIBUTION MODAL CALLBACKS
   # --------------------------------------------------------------------------------------
   
    @app.callback(
        Output("attribution-modal", "is_open"),
        [Input("attribution-link", "n_clicks"), 
        Input("close-attribution", "n_clicks")],
        [State("attribution-modal", "is_open")]
    )
    def toggle_attribution_modal(n1, n2, is_open):
        """
        Toggle the attribution modal open/closed.
        
        Args:
            n1: Number of clicks on the attribution link
            n2: Number of clicks on the close button
            is_open: Current state of the modal
            
        Returns:
            Boolean indicating whether the modal should be open
        """
        if n1 or n2:
            return not is_open
        return is_open

    @app.callback(
        Output("image-credits-modal", "is_open"),
        [Input("image-credits-link", "n_clicks"), 
        Input("close-image-credits", "n_clicks")],
        [State("image-credits-modal", "is_open")]
    )
    def toggle_image_credits_modal(n1, n2, is_open):
        """
        Toggle the image credits modal open/closed.
        
        Args:
            n1: Number of clicks on the image credits link
            n2: Number of clicks on the close button
            is_open: Current state of the modal
            
        Returns:
            Boolean indicating whether the modal should be open
        """
        if n1 or n2:
            return not is_open
        return is_open