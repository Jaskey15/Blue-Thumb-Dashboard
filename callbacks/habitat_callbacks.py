"""
Callbacks for habitat assessment visualization and interaction.
"""

import dash
import pandas as pd
from dash import Input, Output, State, dcc

from utils import get_sites_with_data, setup_logging

from .helper_functions import create_empty_state, create_error_state
from .tab_utilities import create_habitat_display

logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register callbacks for habitat data exploration and visualization."""
    
    # State persistence
    @app.callback(
        Output('habitat-tab-state', 'data'),
        Input('habitat-site-dropdown', 'value'),
        [State('habitat-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_habitat_state(selected_site, current_state):
        """Preserve site selection between tab switches."""
        if selected_site is not None:
            logger.info(f"Saving habitat state: {selected_site}")
            return {'selected_site': selected_site}
        else:
            # Maintain state when dropdown cleared
            return current_state or {'selected_site': None}
    
    # Site selection
    @app.callback(
        [Output('habitat-site-dropdown', 'options'),
         Output('habitat-site-dropdown', 'value', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        [State('habitat-tab-state', 'data')],
        prevent_initial_call=True
    )
    def populate_habitat_sites_and_handle_navigation(active_tab, nav_data, habitat_state):
        """
        Handle site selection from map clicks and restore saved state.
        
        Priority order:
        1. Map click navigation
        2. Saved state restoration
        3. Default state
        """
        if active_tab != 'habitat-tab':
            return [], dash.no_update
        
        ctx = dash.callback_context
        if not ctx.triggered:
            return [], dash.no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            sites = get_sites_with_data('habitat')
            
            if not sites:
                logger.warning("No sites with habitat data found")
                return [], dash.no_update
            
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated habitat dropdown with {len(options)} sites")
            
            # Handle map navigation
            if (nav_data and nav_data.get('target_tab') == 'habitat-tab' and nav_data.get('target_site')):
                target_site = nav_data.get('target_site')
                if target_site in sites:
                    return options, target_site
                else:
                    logger.warning(f"Navigation target site '{target_site}' not found in available sites")
            
            # Restore previous state
            if (trigger_id == 'main-tabs' and habitat_state and habitat_state.get('selected_site') and
                (not nav_data or not nav_data.get('target_tab'))):
                saved_site = habitat_state.get('selected_site')
                if saved_site in sites:
                    return options, saved_site
                else:
                    logger.warning(f"Saved site '{saved_site}' no longer available in habitat data")
            
            # Ignore navigation store clearing
            if trigger_id == 'navigation-store' and (not nav_data or not nav_data.get('target_tab')):
                return options, dash.no_update
            
            return options, dash.no_update
            
        except Exception as e:
            logger.error(f"Error populating habitat sites: {e}")
            return [], dash.no_update
    
    # Content display
    @app.callback(
        Output('habitat-controls-content', 'style'),
        Input('habitat-site-dropdown', 'value')
    )
    def show_habitat_controls(selected_site):
        """Show habitat assessment controls when site is selected."""
        if selected_site:
            logger.info(f"Habitat site selected: {selected_site}")
            return {'display': 'block'}
        return {'display': 'none'}
    
    @app.callback(
        Output('habitat-content-container', 'children'),
        Input('habitat-site-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_habitat_content(selected_site):
        """Display habitat assessment metrics and visualizations."""        
        if selected_site:
            try:
                logger.info(f"Creating habitat display for {selected_site}")
                content = create_habitat_display(selected_site)
                return content
            except Exception as e:
                logger.error(f"Error creating habitat display for {selected_site}: {e}")
                error_content = create_error_state(
                    "Error Loading Habitat Data",
                    f"Could not load habitat data for {selected_site}. Please try again.",
                    str(e)
                )
                return error_content
        
        return create_empty_state("Select a site above to view habitat assessment data.")

    # Data export
    @app.callback(
        Output('habitat-download-component', 'data'),
        Input('habitat-download-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_habitat_data(n_clicks):
        """Export habitat assessment data as CSV."""
        if not n_clicks:
            return dash.no_update
        
        try:
            logger.info("Downloading habitat data CSV")
            processed_habitat_path = 'data/processed/processed_habitat_data.csv'
            habitat_df = pd.read_csv(processed_habitat_path)
            
            if habitat_df.empty:
                logger.warning("No habitat data found in processed CSV")
                return dash.no_update
            
            filename = f"blue_thumb_habitat_data.csv"
            logger.info(f"Successfully prepared habitat data export with {len(habitat_df)} records")
            
            return dcc.send_data_frame(
                habitat_df.to_csv,
                filename,
                index=False
            )
                
        except Exception as e:
            logger.error(f"Error downloading habitat data: {e}")
            return dash.no_update

