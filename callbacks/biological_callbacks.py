"""
Callbacks for biological data visualization and interaction.
"""

import dash
from dash import html, Input, Output, State, dcc
import pandas as pd
from utils import setup_logging, get_sites_with_data
from .tab_utilities import create_biological_community_info, create_biological_site_display, create_gallery_navigation_callback
from .helper_functions import create_empty_state, create_error_state

# Initialize callback logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register callbacks for biological data exploration and visualization."""
    
    # State persistence
    @app.callback(
        Output('biological-tab-state', 'data'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-site-dropdown', 'value')],
        [State('biological-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_biological_state(selected_community, selected_site, current_state):
        """Preserve user selections between tab switches."""
        if selected_community is not None or selected_site is not None:
            # Keep existing values when only one selection changes
            new_state = current_state.copy() if current_state else {'selected_community': None, 'selected_site': None}
            
            if selected_community is not None:
                new_state['selected_community'] = selected_community
                logger.info(f"Saving biological community state: {selected_community}")
            
            if selected_site is not None:
                new_state['selected_site'] = selected_site
                logger.info(f"Saving biological site state: {selected_site}")
            
            return new_state
        else:
            # Maintain state when dropdowns cleared
            return current_state or {'selected_community': None, 'selected_site': None}
    
    # Navigation handling
    @app.callback(
        [Output('biological-community-dropdown', 'value', allow_duplicate=True),
         Output('biological-site-dropdown', 'options', allow_duplicate=True),
         Output('biological-site-dropdown', 'value', allow_duplicate=True),
         Output('biological-site-search-section', 'style', allow_duplicate=True),
         Output('biological-site-dropdown', 'disabled', allow_duplicate=True)],
        [Input('main-tabs', 'active_tab'),
         Input('navigation-store', 'data')],
        [State('biological-tab-state', 'data')],
        prevent_initial_call=True
    )
    def handle_biological_navigation_and_initial_load(active_tab, nav_data, biological_state):
        """
        Handle navigation from map clicks and restore saved state.
        
        Priority order:
        1. Map click navigation
        2. Saved state restoration
        3. Default state
        """
        if active_tab != 'biological-tab':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Handle map navigation
        if (nav_data and nav_data.get('target_tab') == 'biological-tab' and 
            nav_data.get('target_community') and nav_data.get('target_site')):
            
            target_community = nav_data.get('target_community')
            target_site = nav_data.get('target_site')
            
            try:
                # Validate available sites
                available_sites = get_sites_with_data(target_community)
                
                if not available_sites:
                    logger.warning(f"No sites found for community type: {target_community}")
                    return (
                        target_community,
                        [],
                        None,
                        {'display': 'block', 'marginBottom': '20px'},
                        False
                    )
                
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                
                # Verify target site exists
                if target_site in available_sites:
                    return (
                        target_community,
                        options,
                        target_site,
                        {'display': 'block', 'marginBottom': '20px'},
                        False
                    )
                else:
                    logger.warning(f"Target site '{target_site}' not found in available sites for {target_community}")
                    return (
                        target_community,
                        options,
                        None,
                        {'display': 'block', 'marginBottom': '20px'},
                        False
                    )
                    
            except Exception as e:
                logger.error(f"Error handling navigation for {target_community}: {e}")
                return (
                    target_community,
                    [],
                    None,
                    {'display': 'none'},
                    True
                )
        
        # Restore previous state
        if (trigger_id == 'main-tabs' and biological_state and 
            biological_state.get('selected_community') and
            (not nav_data or not nav_data.get('target_tab'))):
            
            saved_community = biological_state.get('selected_community')
            saved_site = biological_state.get('selected_site')
            
            try:
                # Validate saved selections
                available_sites = get_sites_with_data(saved_community)
                
                if not available_sites:
                    logger.warning(f"Saved community '{saved_community}' no longer has available sites")
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                
                # Restore site if still valid
                site_value_to_restore = None
                if saved_site and saved_site in available_sites:
                    site_value_to_restore = saved_site
                
                return (
                    saved_community,
                    options,
                    site_value_to_restore,
                    {'display': 'block', 'marginBottom': '20px'},
                    False
                )
                
            except Exception as e:
                logger.error(f"Error restoring state for {saved_community}: {e}")
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Ignore navigation store clearing
        if trigger_id == 'navigation-store' and (not nav_data or not nav_data.get('target_tab')):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Site selection
    @app.callback(
        [Output('biological-site-search-section', 'style'),
         Output('biological-site-dropdown', 'disabled'),
         Output('biological-site-dropdown', 'options'),
         Output('biological-site-dropdown', 'value')],
        [Input('biological-community-dropdown', 'value')],
        [State('biological-site-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_biological_site_dropdown(selected_community, current_site_value):
        """Update available sites when community type changes."""
        if selected_community:
            try:
                available_sites = get_sites_with_data(selected_community)
                
                if not available_sites:
                    logger.warning(f"No sites found for community type: {selected_community}")
                    return (
                        {'display': 'block', 'marginBottom': '20px'},
                        False,
                        [],
                        None
                    )
                
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                logger.info(f"Populated {selected_community} dropdown with {len(options)} sites")
                
                # Keep current site if valid
                site_value_to_set = None
                if current_site_value and current_site_value in available_sites:
                    site_value_to_set = current_site_value
                    logger.info(f"Preserving existing site selection: {current_site_value}")
                
                return (
                    {'display': 'block', 'marginBottom': '20px'},
                    False,
                    options,
                    site_value_to_set
                )
                
            except Exception as e:
                logger.error(f"Error populating {selected_community} sites: {e}")
                return (
                    {'display': 'block', 'marginBottom': '20px'},
                    False,
                    [],
                    None
                )
        else:
            # Hide site selection until community chosen
            return (
                {'display': 'none'},
                True,
                [],
                None
            )
    
    # Content display
    @app.callback(
        Output('biological-community-content', 'children'),
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_community_content(selected_community):
        """Display community information and species gallery."""
        if not selected_community:
            return html.Div()
        
        try:
            logger.info(f"Creating biological community content for {selected_community}")
            return create_biological_community_info(selected_community)
        except Exception as e:
            logger.error(f"Error creating biological community content: {e}")
            return create_error_state(
                f"Error Loading {selected_community.title()} Information",
                f"Could not load {selected_community} community information. Please try again.",
                str(e)
            )
    
    @app.callback(
        Output('biological-site-content', 'children'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-site-dropdown', 'value')]
    )
    def update_biological_site_content(selected_community, selected_site):
        """Display site-specific biological metrics and visualizations."""
        if not selected_community or not selected_site:
            return create_empty_state("Please select a community type and site to view biological data.")
        
        try:
            logger.info(f"Creating biological site display for {selected_community} at {selected_site}")
            return create_biological_site_display(selected_community, selected_site)
        except Exception as e:
            logger.error(f"Error creating biological site display: {e}")
            return create_error_state(
                f"Error Loading {selected_community.title()} Data",
                f"Could not load {selected_community} data for {selected_site}. Please try again.",
                str(e)
            )

    # Gallery navigation
    @app.callback(
        [Output('fish-gallery-container', 'children'),
         Output('current-fish-index', 'data')],
        [Input('prev-fish-button', 'n_clicks'),
         Input('next-fish-button', 'n_clicks')],
        [State('current-fish-index', 'data')]
    )
    def update_fish_gallery(prev_clicks, next_clicks, current_index):
        """Navigate through fish species gallery."""
        update_gallery = create_gallery_navigation_callback('fish')
        return update_gallery(prev_clicks, next_clicks, current_index)
    
    @app.callback(
        [Output('macro-gallery-container', 'children'),
         Output('current-macro-index', 'data')],
        [Input('prev-macro-button', 'n_clicks'),
         Input('next-macro-button', 'n_clicks')],
        [State('current-macro-index', 'data')]
    )
    def update_macro_gallery(prev_clicks, next_clicks, current_index):
        """Navigate through macroinvertebrate species gallery."""
        update_gallery = create_gallery_navigation_callback('macro')
        return update_gallery(prev_clicks, next_clicks, current_index)

    # Data export
    @app.callback(
        Output('biological-download-component', 'data'),
        Input('biological-download-btn', 'n_clicks'),
        [State('biological-community-dropdown', 'value')],
        prevent_initial_call=True
    )
    def download_biological_data(n_clicks, selected_community):
        """Export biological data as CSV based on selected community."""
        if not n_clicks or not selected_community:
            return dash.no_update
        
        try:
            if selected_community == 'fish':
                logger.info("Downloading fish data CSV")
                processed_data_path = 'data/processed/processed_fish_data.csv'
                data_df = pd.read_csv(processed_data_path)
                
                if data_df.empty:
                    logger.warning("No fish data found in processed CSV")
                    return dash.no_update
                
                filename = f"blue_thumb_fish_data.csv"
                logger.info(f"Successfully prepared fish data export with {len(data_df)} records")
                
            elif selected_community == 'macro':
                logger.info("Downloading macro data CSV")
                processed_data_path = 'data/processed/processed_macro_data.csv'
                data_df = pd.read_csv(processed_data_path)
                
                if data_df.empty:
                    logger.warning("No macro data found in processed CSV")
                    return dash.no_update
                
                filename = f"blue_thumb_macro_data.csv"
                logger.info(f"Successfully prepared macro data export with {len(data_df)} records")
                
            else:
                logger.warning(f"Unknown community type for download: {selected_community}")
                return dash.no_update
            
            return dcc.send_data_frame(
                data_df.to_csv,
                filename,
                index=False
            )
                
        except Exception as e:
            logger.error(f"Error downloading {selected_community} data: {e}")
            return dash.no_update


