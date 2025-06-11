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
        Output('chemical-site-dropdown', 'options'),
        Input('main-tabs', 'active_tab')
    )
    def populate_chemical_sites(active_tab):
        """Populate site dropdown options when chemical tab is opened."""
        if active_tab != 'chemical-tab':
            return []
        
        try:
            # Get all sites with chemical data
            sites = get_sites_with_data('chemical')
            
            if not sites:
                logger.warning("No sites with chemical data found")
                return []
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated chemical dropdown with {len(options)} sites")
            
            return options
            
        except Exception as e:
            logger.error(f"Error populating chemical sites: {e}")
            return []
    
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


