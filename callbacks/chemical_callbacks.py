"""
Chemical callbacks for the Tenmile Creek Water Quality Dashboard.
"""

import dash
from dash import html, Input, Output, State, dcc
import pandas as pd
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
    # 1. STATE MANAGEMENT
    # ===========================
    
    @app.callback(
        Output('chemical-tab-state', 'data'),
        [Input('chemical-site-dropdown', 'value'),
         Input('chemical-parameter-dropdown', 'value'),
         Input('year-range-slider', 'value'),
         Input('month-checklist', 'value'),
         Input('highlight-thresholds-switch', 'value')],
        [State('chemical-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_chemical_state(selected_site, selected_parameter, year_range, selected_months, 
                           highlight_thresholds, current_state):
        """Save chemical tab state when selections change."""
        # Only save valid selections, don't overwrite with None
        if any(val is not None for val in [selected_site, selected_parameter, year_range, selected_months, highlight_thresholds]):
            # Preserve existing values when only some change
            new_state = current_state.copy() if current_state else {
                'selected_site': None,
                'selected_parameter': None,
                'year_range': None,
                'selected_months': None,
                'highlight_thresholds': None
            }
            
            if selected_site is not None:
                new_state['selected_site'] = selected_site
                logger.info(f"Saving chemical site state: {selected_site}")
            
            if selected_parameter is not None:
                new_state['selected_parameter'] = selected_parameter
                logger.info(f"Saving chemical parameter state: {selected_parameter}")
            
            if year_range is not None:
                new_state['year_range'] = year_range
                logger.info(f"Saving chemical year range state: {year_range}")
            
            if selected_months is not None:
                new_state['selected_months'] = selected_months
                logger.info(f"Saving chemical months state: {len(selected_months) if selected_months else 0} months")
            
            if highlight_thresholds is not None:
                new_state['highlight_thresholds'] = highlight_thresholds
                logger.info(f"Saving chemical highlight thresholds state: {highlight_thresholds}")
            
            return new_state
        else:
            # Keep existing state when all controls are cleared
            return current_state or {
                'selected_site': None,
                'selected_parameter': None,
                'year_range': None,
                'selected_months': None,
                'highlight_thresholds': None
            }
    
    # ===========================
    # 2. NAVIGATION AND DROPDOWN POPULATION
    # ===========================
    
    @app.callback(
        [Output('chemical-site-dropdown', 'options'),
         Output('chemical-site-dropdown', 'value', allow_duplicate=True),
         Output('chemical-parameter-dropdown', 'value', allow_duplicate=True),
         Output('year-range-slider', 'value', allow_duplicate=True),
         Output('month-checklist', 'value', allow_duplicate=True),
         Output('highlight-thresholds-switch', 'value', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        [State('chemical-tab-state', 'data')],
        prevent_initial_call=True
    )
    def handle_chemical_navigation_and_state_restoration(active_tab, nav_data, chemical_state):
        """Handle navigation from map, initial tab loading, and state restoration for all chemical controls."""
        if active_tab != 'chemical-tab':
            return [], dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Get the trigger to understand what caused this callback
        ctx = dash.callback_context
        if not ctx.triggered:
            return [], dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            # Get all sites with chemical data
            sites = get_sites_with_data('chemical')
            
            if not sites:
                logger.warning("No sites with chemical data found")
                return [], dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated chemical dropdown with {len(options)} sites")
            
            # Priority 1: Handle navigation from map (highest priority)
            if (nav_data and nav_data.get('target_tab') == 'chemical-tab' and 
                nav_data.get('target_site')):
                
                target_site = nav_data.get('target_site')
                target_parameter = nav_data.get('target_parameter')
                
                if target_site in sites:
                    # For map navigation, set site + parameter from nav, preserve other filters from state or use defaults
                    restored_year_range = (chemical_state.get('year_range') 
                                         if chemical_state and chemical_state.get('year_range') 
                                         else dash.no_update)
                    restored_months = (chemical_state.get('selected_months') 
                                     if chemical_state and chemical_state.get('selected_months') 
                                     else dash.no_update)
                    restored_thresholds = (chemical_state.get('highlight_thresholds') 
                                         if chemical_state and chemical_state.get('highlight_thresholds') is not None 
                                         else dash.no_update)
                    
                    return (
                        options,  # Site options
                        target_site,  # Set target site
                        target_parameter or 'do_percent',  # Set target parameter
                        restored_year_range,  # Preserve year range from state
                        restored_months,  # Preserve months from state
                        restored_thresholds  # Preserve thresholds from state
                    )
                else:
                    logger.warning(f"Navigation target site '{target_site}' not found in available sites")
            
            # Priority 2: Restore from saved state if tab was just activated AND no active navigation
            if (trigger_id == 'main-tabs' and chemical_state and 
                chemical_state.get('selected_site') and
                (not nav_data or not nav_data.get('target_tab'))):
                
                saved_site = chemical_state.get('selected_site')
                saved_parameter = chemical_state.get('selected_parameter')
                saved_year_range = chemical_state.get('year_range')
                saved_months = chemical_state.get('selected_months')
                saved_thresholds = chemical_state.get('highlight_thresholds')
                
                # Verify saved site is still available
                if saved_site in sites:
                    return (
                        options,  # Site options
                        saved_site,  # Restore site
                        saved_parameter,  # Restore parameter
                        saved_year_range,  # Restore year range
                        saved_months,  # Restore months
                        saved_thresholds  # Restore thresholds
                    )
                else:
                    logger.warning(f"Saved site '{saved_site}' no longer available")
            
            # Ignore navigation-store clearing events (when nav_data is empty/None)
            if trigger_id == 'navigation-store' and (not nav_data or not nav_data.get('target_tab')):
                return options, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            # Default behavior - just populate options
            return options, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        except Exception as e:
            logger.error(f"Error in chemical navigation/state restoration: {e}")
            return [], dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # ===========================
    # 3. SITE SELECTION & CONTROLS
    # ===========================
    
    @app.callback(
        [Output('chemical-controls-content', 'style'),
         Output('chemical-download-btn', 'style'),
         Output('chemical-download-site-btn', 'style')],
        [Input('chemical-site-dropdown', 'value'),
         Input('chemical-parameter-dropdown', 'value')]
    )
    def show_chemical_controls(selected_site, selected_parameter):
        """Show parameter controls and download buttons when a site and parameter are selected."""
        if selected_site and selected_parameter:
            logger.info(f"Chemical site selected: {selected_site}, parameter: {selected_parameter}")
            return {'display': 'block'}, {'display': 'block'}, {'display': 'block', 'marginRight': '10px'}
        elif selected_site:
            logger.info(f"Chemical site selected: {selected_site}")
            return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
    
    # ================================
    # 4. DATA VISUALIZATION & FILTERS
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
        
        # Validate year_range - if None, get default range
        if year_range is None:
            from data_processing.data_queries import get_chemical_date_range
            min_year, max_year = get_chemical_date_range()
            year_range = [min_year, max_year]
            logger.info(f"Using default year range: {year_range}")
        
        # Validate selected_months - if None, use all months
        if selected_months is None:
            selected_months = list(range(1, 13))
            logger.info(f"Using default months: all months")
        
        # Validate highlight_thresholds - if None, use default True
        if highlight_thresholds is None:
            highlight_thresholds = True
            logger.info(f"Using default highlight thresholds: {highlight_thresholds}")
        
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

    # ===========================
    # 5. DATA DOWNLOAD
    # ===========================
    
    @app.callback(
        Output('chemical-download-component', 'data'),
        [Input('chemical-download-btn', 'n_clicks'),
         Input('chemical-download-site-btn', 'n_clicks')],
        [State('chemical-site-dropdown', 'value')],
        prevent_initial_call=True
    )
    def download_chemical_data(all_clicks, site_clicks, selected_site):
        """Download chemical data CSV file with timestamp - all data or site-specific."""
        if not all_clicks and not site_clicks:
            return dash.no_update
        
        # Determine which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            # Read the processed chemical data CSV
            processed_chemical_path = 'data/processed/processed_chemical_data.csv'
            chemical_df = pd.read_csv(processed_chemical_path)
            
            if chemical_df.empty:
                logger.warning("No chemical data found in processed CSV")
                return dash.no_update
            
            # Handle site-specific download
            if button_id == 'chemical-download-site-btn':
                if not selected_site:
                    logger.warning("No site selected for site-specific download")
                    return dash.no_update
                
                # Filter data for selected site
                site_df = chemical_df[chemical_df['Site_Name'] == selected_site]
                
                if site_df.empty:
                    logger.warning(f"No chemical data found for site: {selected_site}")
                    return dash.no_update
                
                # Generate site-specific filename
                # Sanitize site name for filename (replace spaces and special chars with underscores)
                site_name = selected_site.replace(' ', '_').replace(':', '').replace('(', '').replace(')', '').replace(',', '')
                filename = f"{site_name}_chemical_data.csv"
                
                logger.info(f"Successfully prepared chemical data export for {selected_site} with {len(site_df)} records")
                
                return dcc.send_data_frame(
                    site_df.to_csv,
                    filename,
                    index=False
                )
            
            # Handle all data download
            elif button_id == 'chemical-download-btn':
                logger.info("Downloading all chemical data CSV")
                
                filename = f"blue_thumb_chemical_data.csv"
                
                logger.info(f"Successfully prepared chemical data export with {len(chemical_df)} records")
                
                return dcc.send_data_frame(
                    chemical_df.to_csv,
                    filename,
                    index=False
                )
                
        except Exception as e:
            logger.error(f"Error downloading chemical data: {e}")
            return dash.no_update


