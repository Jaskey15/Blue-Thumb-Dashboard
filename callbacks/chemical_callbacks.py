"""
Chemical callbacks for the Tenmile Creek Water Quality Dashboard.
"""

import dash
from dash import html, Input, Output, State
from utils import setup_logging, get_sites_with_data
from data_processing.data_queries import get_chemical_data_from_db
from data_processing.chemical_utils import KEY_PARAMETERS, get_reference_values
from .tab_utilities import create_all_parameters_visualization, create_single_parameter_visualization
from .helper_functions import create_empty_state, create_error_state

# Configure logging
logger = setup_logging("chemical_callbacks", category="callbacks")

def register_chemical_callbacks(app):
    """Register all chemical-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. DROPDOWN POPULATION
    # ===========================
    
    @app.callback(
        [Output('chemical-site-dropdown', 'options'),
         Output('chemical-site-dropdown', 'value', allow_duplicate=True),
         Output('chemical-parameter-dropdown', 'value', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        prevent_initial_call=True
    )
    def populate_chemical_sites_and_handle_navigation(active_tab, nav_data):
        """Populate site dropdown options and handle navigation from map."""
        if active_tab != 'chemical-tab':
            return [], dash.no_update, dash.no_update
        
        try:
            # Get all sites with chemical data
            sites = get_sites_with_data('chemical')
            
            if not sites:
                logger.warning("No sites with chemical data found")
                return [], dash.no_update, dash.no_update
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated chemical dropdown with {len(options)} sites")
            
            # Check if we need to set a specific site and parameter from navigation
            if nav_data and nav_data.get('target_tab') == 'chemical-tab' and active_tab == 'chemical-tab':
                target_site = nav_data.get('target_site')
                target_parameter = nav_data.get('target_parameter')
                
                if target_site and target_site in sites:
                    logger.info(f"Setting dropdown values from navigation - site: {target_site}, parameter: {target_parameter}")
                    return options, target_site, target_parameter or 'do_percent'
                elif target_site:
                    logger.warning(f"Navigation target site '{target_site}' not found in available sites")
            
            return options, dash.no_update, dash.no_update
            
        except Exception as e:
            logger.error(f"Error populating chemical sites: {e}")
            return [], dash.no_update, dash.no_update
    
    # ===========================
    # 2. SITE SELECTION & CONTROLS
    # ===========================
    
    @app.callback(
        Output('chemical-controls-content', 'style'),
        Input('chemical-site-dropdown', 'value')
    )
    def show_chemical_controls(selected_site):
        """Show parameter controls when a site is selected."""
        if selected_site:
            logger.info(f"Chemical site selected: {selected_site}")
            return {'display': 'block'}
        return {'display': 'none'}
    
    # ================================
    # 3. DATA VISUALIZATION & FILTERS
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
         Input('chemical-site-dropdown', 'value')]
    )
    def update_chemical_display(selected_parameter, year_range, selected_months, 
                              highlight_thresholds, selected_site):
        """Update chemical parameter visualization based on user selections."""
        
        # Validate inputs
        if not selected_site:
            return create_empty_state("Please select a site to view data."), html.Div(), html.Div()
        
        if not selected_parameter:
            return create_empty_state("Please select a parameter to visualize."), html.Div(), html.Div()
        
        try:
            logger.info(f"Creating chemical visualization for {selected_site}, parameter: {selected_parameter}")
            
            # Get processed data
            df_filtered = get_chemical_data_from_db(selected_site)
            key_parameters = KEY_PARAMETERS
            reference_values = get_reference_values()
            
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
                    df_filtered, key_parameters, reference_values, highlight_thresholds, selected_site
                )
            else:
                graph, explanation, diagram = create_single_parameter_visualization(
                    df_filtered, selected_parameter, reference_values, highlight_thresholds, selected_site
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


