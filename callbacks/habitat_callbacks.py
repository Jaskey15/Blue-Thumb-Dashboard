"""
Habitat callbacks for the Blue Thumb Stream Health Dashboard.
This file contains callbacks specific to the habitat data tab.
"""

import dash
import pandas as pd
from datetime import datetime
from dash import html, Input, Output, State, dcc
from utils import setup_logging, get_sites_with_data
from .tab_utilities import create_habitat_display
from .helper_functions import create_empty_state, create_error_state

# Configure logging
logger = setup_logging("habitat_callbacks", category="callbacks")

def register_habitat_callbacks(app):
    """Register all habitat-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. STATE MANAGEMENT
    # ===========================
    
    @app.callback(
        Output('habitat-tab-state', 'data'),
        Input('habitat-site-dropdown', 'value'),
        [State('habitat-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_habitat_state(selected_site, current_state):
        """Save habitat tab state when selections change."""
        # Only save valid selections, don't overwrite with None
        if selected_site is not None:
            logger.info(f"Saving habitat state: {selected_site}")
            return {'selected_site': selected_site}
        else:
            # Keep existing state when dropdown is cleared
            return current_state or {'selected_site': None}
    
    # ===========================
    # 2. DROPDOWN POPULATION
    # ===========================
    
    @app.callback(
        [Output('habitat-site-dropdown', 'options'),
         Output('habitat-site-dropdown', 'value', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        [State('habitat-tab-state', 'data')],
        prevent_initial_call=True
    )
    def populate_habitat_sites_and_handle_navigation(active_tab, nav_data, habitat_state):
        """Populate site dropdown options and handle navigation from map or restore from state."""
        if active_tab != 'habitat-tab':
            return [], dash.no_update
        
        # Get the trigger to understand what caused this callback
        ctx = dash.callback_context
        if not ctx.triggered:
            return [], dash.no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            # Get all sites with habitat data
            sites = get_sites_with_data('habitat')
            
            if not sites:
                logger.warning("No sites with habitat data found")
                return [], dash.no_update
            
            # Create dropdown options
            options = [{'label': site, 'value': site} for site in sorted(sites)]
            logger.info(f"Populated habitat dropdown with {len(options)} sites")
            
            # Priority 1: Check if we need to set a specific site from navigation (map clicks)
            # Handle navigation data regardless of trigger source
            if (nav_data and nav_data.get('target_tab') == 'habitat-tab' and nav_data.get('target_site')):
                target_site = nav_data.get('target_site')
                if target_site in sites:
                    return options, target_site
                else:
                    logger.warning(f"Navigation target site '{target_site}' not found in available sites")
            
            # Priority 2: Restore from saved state if tab was just activated AND no active navigation
            if (trigger_id == 'main-tabs' and habitat_state and habitat_state.get('selected_site') and
                (not nav_data or not nav_data.get('target_tab'))):
                saved_site = habitat_state.get('selected_site')
                if saved_site in sites:
                    return options, saved_site
                else:
                    logger.warning(f"Saved site '{saved_site}' no longer available in habitat data")
            
            # Ignore navigation-store clearing events (when nav_data is empty/None)
            if trigger_id == 'navigation-store' and (not nav_data or not nav_data.get('target_tab')):
                return options, dash.no_update
            
            return options, dash.no_update
            
        except Exception as e:
            logger.error(f"Error populating habitat sites: {e}")
            return [], dash.no_update
    
    # ===========================
    # 3. DATA VISUALIZATION
    # ===========================
    
    @app.callback(
        Output('habitat-controls-content', 'style'),
        Input('habitat-site-dropdown', 'value')
    )
    def show_habitat_controls(selected_site):
        """Show habitat content when a site is selected."""
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
        """Update habitat content based on selected site."""        
        # Handle site selection
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
        
        # Default case - no site selected
        empty_content = create_empty_state("Select a site above to view habitat assessment data.")
        return empty_content

    # ===========================
    # 4. DATA DOWNLOAD
    # ===========================
    
    @app.callback(
        Output('habitat-download-component', 'data'),
        Input('habitat-download-btn', 'n_clicks'),
        State('habitat-site-dropdown', 'value'),
        prevent_initial_call=True
    )
    def download_habitat_data(n_clicks, selected_site):
        """Download habitat metrics data for the selected site."""
        if not n_clicks or not selected_site:
            return dash.no_update
        
        try:
            logger.info(f"Downloading habitat data for {selected_site}")
            
            # Import the data query function
            from data_processing.data_queries import get_habitat_metrics_data_for_table
            
            # Get the habitat metrics data
            metrics_df, summary_df = get_habitat_metrics_data_for_table(selected_site)
            
            if metrics_df.empty and summary_df.empty:
                logger.warning(f"No habitat data found for {selected_site}")
                return dash.no_update
            
            # Combine metrics and summary data into a comprehensive export
            export_data = []
            
            # Add metrics data if available
            if not metrics_df.empty:
                # Pivot metrics data to have years as columns and metrics as rows
                metrics_pivot = metrics_df.pivot_table(
                    index='metric_name',
                    columns='year',
                    values='score',
                    aggfunc='first'
                ).reset_index()
                
                # Add a section header
                header_row = pd.DataFrame({
                    'metric_name': ['HABITAT METRICS'],
                    **{str(year): [''] for year in metrics_pivot.columns if year != 'metric_name'}
                })
                
                export_data.append(header_row)
                export_data.append(metrics_pivot)
            
            # Add summary data if available
            if not summary_df.empty:
                # Add spacing and summary header
                spacing_row = pd.DataFrame({
                    'metric_name': [''],
                    **{str(year): [''] for year in summary_df['year'].unique()}
                })
                
                summary_header = pd.DataFrame({
                    'metric_name': ['SUMMARY SCORES'],
                    **{str(year): [''] for year in summary_df['year'].unique()}
                })
                
                # Pivot summary data
                summary_pivot = summary_df.pivot_table(
                    index=['total_score', 'habitat_grade'],
                    columns='year',
                    values='assessment_id',
                    aggfunc='count',
                    fill_value=0
                ).reset_index()
                
                # Rename index columns for clarity
                summary_pivot['metric_name'] = summary_pivot.apply(
                    lambda row: f"Total Score: {row['total_score']} ({row['habitat_grade']})", 
                    axis=1
                )
                summary_pivot = summary_pivot.drop(['total_score', 'habitat_grade'], axis=1)
                
                export_data.extend([spacing_row, summary_header, summary_pivot])
            
            # Combine all data
            if export_data:
                final_df = pd.concat(export_data, ignore_index=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{selected_site.replace(' ', '_')}_habitat_data_{timestamp}.csv"
                
                logger.info(f"Successfully prepared habitat data export for {selected_site}")
                
                return dcc.send_data_frame(
                    final_df.to_csv,
                    filename,
                    index=False
                )
            else:
                logger.warning(f"No data to export for {selected_site}")
                return dash.no_update
                
        except Exception as e:
            logger.error(f"Error downloading habitat data for {selected_site}: {e}")
            return dash.no_update

