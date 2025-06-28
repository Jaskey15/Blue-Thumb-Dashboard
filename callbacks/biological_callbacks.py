"""
Biological callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the biological data tab.
"""

import dash
from dash import html, Input, Output, State, dcc
from datetime import datetime
import pandas as pd
from utils import setup_logging
from .tab_utilities import create_biological_community_info, create_biological_site_display, create_gallery_navigation_callback
from .helper_functions import create_empty_state, create_error_state

# Configure logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register all biological-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. STATE MANAGEMENT
    # ===========================
    
    @app.callback(
        Output('biological-tab-state', 'data'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-site-dropdown', 'value')],
        [State('biological-tab-state', 'data')],
        prevent_initial_call=True
    )
    def save_biological_state(selected_community, selected_site, current_state):
        """Save biological tab state when selections change."""
        # Only save valid selections, don't overwrite with None
        if selected_community is not None or selected_site is not None:
            # Preserve existing values when only one changes
            new_state = current_state.copy() if current_state else {'selected_community': None, 'selected_site': None}
            
            if selected_community is not None:
                new_state['selected_community'] = selected_community
                logger.info(f"Saving biological community state: {selected_community}")
            
            if selected_site is not None:
                new_state['selected_site'] = selected_site
                logger.info(f"Saving biological site state: {selected_site}")
            
            return new_state
        else:
            # Keep existing state when both dropdowns are cleared
            return current_state or {'selected_community': None, 'selected_site': None}
    
    # ==================================================
    # 2. NAVIGATION AND DROPDOWN POPULATION  
    # ==================================================
    
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
        """Handle navigation from map, initial tab loading, and state restoration."""
        if active_tab != 'biological-tab':
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Get the trigger to understand what caused this callback
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Priority 1: Handle navigation from map (highest priority)
        if (nav_data and nav_data.get('target_tab') == 'biological-tab' and 
            nav_data.get('target_community') and nav_data.get('target_site')):
            
            target_community = nav_data.get('target_community')
            target_site = nav_data.get('target_site')
            
            try:
                # Get sites for the target community type
                from utils import get_sites_with_data
                available_sites = get_sites_with_data(target_community)
                
                if not available_sites:
                    logger.warning(f"No sites found for community type: {target_community}")
                    return (
                        target_community,  # Set community
                        [],  # No site options
                        None,  # No site value
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False  # Enable dropdown
                    )
                
                # Create dropdown options
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                
                # Verify target site is available for this community
                if target_site in available_sites:
                    return (
                        target_community,  # Set community
                        options,  # Site options
                        target_site,  # Set target site
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False  # Enable dropdown
                    )
                else:
                    logger.warning(f"Target site '{target_site}' not found in available sites for {target_community}")
                    return (
                        target_community,  # Set community
                        options,  # Site options
                        None,  # No site value
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False  # Enable dropdown
                    )
                    
            except Exception as e:
                logger.error(f"Error handling navigation for {target_community}: {e}")
                return (
                    target_community,  # Set community
                    [],  # No options
                    None,  # No site value
                    {'display': 'none'},  # Hide section
                    True  # Disable dropdown
                )
        
        # Priority 2: Restore from saved state if tab was just activated AND no active navigation
        if (trigger_id == 'main-tabs' and biological_state and 
            biological_state.get('selected_community') and
            (not nav_data or not nav_data.get('target_tab'))):
            
            saved_community = biological_state.get('selected_community')
            saved_site = biological_state.get('selected_site')
            
            try:
                # Get sites for the saved community type
                from utils import get_sites_with_data
                available_sites = get_sites_with_data(saved_community)
                
                if not available_sites:
                    logger.warning(f"Saved community '{saved_community}' no longer has available sites")
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                # Create dropdown options
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                
                # Check if saved site is still valid for this community
                site_value_to_restore = None
                if saved_site and saved_site in available_sites:
                    site_value_to_restore = saved_site
                
                return (
                    saved_community,  # Restore community
                    options,  # Site options
                    site_value_to_restore,  # Restore site if available
                    {'display': 'block', 'marginBottom': '20px'},  # Show section
                    False  # Enable dropdown
                )
                
            except Exception as e:
                logger.error(f"Error restoring state for {saved_community}: {e}")
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Ignore navigation-store clearing events (when nav_data is empty/None)
        if trigger_id == 'navigation-store' and (not nav_data or not nav_data.get('target_tab')):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # ==================================================
    # 3. COMMUNITY SELECTION & SITE DROPDOWN POPULATION
    # ==================================================
    
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
        """Show site dropdown and populate options when community is selected."""
        if selected_community:
            try:
                # Get sites for the selected community type
                from utils import get_sites_with_data
                available_sites = get_sites_with_data(selected_community)
                
                if not available_sites:
                    logger.warning(f"No sites found for community type: {selected_community}")
                    return (
                        {'display': 'block', 'marginBottom': '20px'},  # Show section
                        False,  # Enable dropdown
                        [],     # No options
                        None    # Clear value
                    )
                
                # Create dropdown options
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                logger.info(f"Populated {selected_community} dropdown with {len(options)} sites")
                
                # Preserve existing site value if it's valid for this community (from navigation)
                site_value_to_set = None
                if current_site_value and current_site_value in available_sites:
                    site_value_to_set = current_site_value
                    logger.info(f"Preserving existing site selection: {current_site_value}")
                
                return (
                    {'display': 'block', 'marginBottom': '20px'},  # Show section
                    False,  # Enable dropdown
                    options,  # Site options
                    site_value_to_set    # Preserve existing selection or clear
                )
                
            except Exception as e:
                logger.error(f"Error populating {selected_community} sites: {e}")
                return (
                    {'display': 'block', 'marginBottom': '20px'},  # Show section
                    False,  # Enable dropdown
                    [],     # No options
                    None    # Clear value
                )
        else:
            # Hide section and disable dropdown when no community selected
            return (
                {'display': 'none'},  # Hide section
                True,   # Disable dropdown
                [],     # Clear options
                None    # Clear value
            )
    
    # ===========================
    # 4. SEPARATED CONTENT DISPLAY
    # ===========================
    
    @app.callback(
        Output('biological-community-content', 'children'),
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_community_content(selected_community):
        """Update community-specific content (description, gallery, interpretation)."""
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
        """Update site-specific content (charts, metrics)."""
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

    # ===========================
    # 5. GALLERY NAVIGATION
    # ===========================
    
    @app.callback(
        [Output('fish-gallery-container', 'children'),
         Output('current-fish-index', 'data')],
        [Input('prev-fish-button', 'n_clicks'),
         Input('next-fish-button', 'n_clicks')],
        [State('current-fish-index', 'data')]
    )
    def update_fish_gallery(prev_clicks, next_clicks, current_index):
        """Handle fish gallery navigation."""
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
        """Handle macroinvertebrate gallery navigation."""
        update_gallery = create_gallery_navigation_callback('macro')
        return update_gallery(prev_clicks, next_clicks, current_index)

    # ===========================
    # 6. DATA DOWNLOAD
    # ===========================
    
    @app.callback(
        Output('biological-download-component', 'data'),
        Input('biological-download-btn', 'n_clicks'),
        [State('biological-community-dropdown', 'value')],
        prevent_initial_call=True
    )
    def download_biological_data(n_clicks, selected_community):
        """Download biological data CSV file with timestamp based on selected community type."""
        if not n_clicks or not selected_community:
            return dash.no_update
        
        try:
            if selected_community == 'fish':
                logger.info("Downloading fish data CSV")
                
                # Read the processed fish data CSV
                processed_data_path = 'data/processed/processed_fish_data.csv'
                data_df = pd.read_csv(processed_data_path)
                
                if data_df.empty:
                    logger.warning("No fish data found in processed CSV")
                    return dash.no_update
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%d-%m-%Y")
                filename = f"blue_thumb_fish_data_{timestamp}.csv"
                
                logger.info(f"Successfully prepared fish data export with {len(data_df)} records")
                
            elif selected_community == 'macro':
                logger.info("Downloading macro data CSV")
                
                # Read the processed macro data CSV
                processed_data_path = 'data/processed/processed_macro_data.csv'
                data_df = pd.read_csv(processed_data_path)
                
                if data_df.empty:
                    logger.warning("No macro data found in processed CSV")
                    return dash.no_update
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%m-%d-%Y")
                filename = f"blue_thumb_macro_data_{timestamp}.csv"
                
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


