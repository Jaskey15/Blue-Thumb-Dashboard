"""
Biological callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the biological data tab.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL
from utils import setup_logging, load_markdown_content, create_image_with_caption
from config.data_definitions import FISH_DATA, MACRO_DATA
from .helper_functions import (
    should_perform_search, is_item_clicked, extract_selected_item,
    create_empty_state, create_error_state, create_search_results
)

# Configure logging
logger = setup_logging("biological_callbacks", category="callbacks")

def register_biological_callbacks(app):
    """Register all biological-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. COMMUNITY SELECTION
    # ===========================
    
    @app.callback(
        [Output('biological-site-search-section', 'style'),
         Output('biological-search-input', 'disabled'),
         Output('biological-search-button', 'disabled'),
         Output('biological-clear-button', 'disabled'),  
         Output('biological-search-input', 'value'),
         Output('biological-selected-site', 'data'),
         Output('biological-search-results', 'style'),
         Output('biological-search-results', 'children')],
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_search_visibility(selected_community):
        """Show/hide search section and reset state when community is selected."""
        if selected_community:
            # Show search section and enable inputs
            return (
                {'display': 'block', 'position': 'relative', 'marginBottom': '20px'},  # search_section_style
                False,  # input_disabled
                False,  # button_disabled
                False,  # clear_disabled
                "",     # search_value (clear)
                None,   # selected_item (clear)
                {'display': 'none'},  # results_style
                []      # results_children (clear)
            )
        else:
            # Hide search section and disable inputs
            return (
                {'display': 'none'},  # search_section_style
                True,   # input_disabled
                True,   # button_disabled
                True,   # clear_disabled
                "",     # search_value (clear)
                None,   # selected_item (clear)
                {'display': 'none'},  # results_style
                []      # results_children (clear)
            )
    
    # ===========================
    # 2. SITE SEARCH & SELECTION
    # ===========================
    
    @app.callback(
        [Output('biological-search-results', 'children', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input('biological-search-button', 'n_clicks'),
         Input('biological-search-input', 'n_submit')],
        [State('biological-search-input', 'value'),
         State('biological-community-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_biological_search_results(button_clicks, enter_presses, search_value, selected_community):
        """Filter and display sites based on search input."""
        if not should_perform_search(button_clicks, enter_presses, search_value, selected_community):
            return [], {'display': 'none'}
        
        try:
            # Get sites for the selected community type
            from utils import get_sites_with_data
            available_sites = get_sites_with_data(selected_community)
            
            if not available_sites:
                return [html.Div("No sites found for this community type.", 
                            className="p-2 text-muted")], {'display': 'block'}
            
            # Filter sites based on search
            search_term = search_value.lower().strip()
            matching_sites = [
                site for site in available_sites 
                if search_term in site.lower()
            ]
            
            # Use shared function to create consistent search results
            return create_search_results(matching_sites, 'biological', search_value)
            
        except Exception as e:
            logger.error(f"Error in biological search: {e}")
            return [html.Div("Error performing search.", 
                        className="p-2 text-danger")], {'display': 'block'}
    
    @app.callback(
        [Output('biological-selected-site', 'data', allow_duplicate=True),
         Output('biological-search-input', 'value', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input({'type': 'biological-site-option', 'site': ALL}, 'n_clicks')],
        [State('biological-selected-site', 'data')],
        prevent_initial_call=True
    )
    def select_biological_site(site_clicks, current_site):
        """Handle site selection from search results."""
        if not is_item_clicked(site_clicks):
            return current_site, dash.no_update, dash.no_update
        
        try:
            selected_site = extract_selected_item('site')
            logger.info(f"Biological site selected: {selected_site}")
            
            return (
                selected_site,           # Store selected site
                selected_site,           # Update search input
                {'display': 'none'}      # Hide search results
            )
        except Exception as e:
            logger.error(f"Error in biological site selection: {e}")
            return current_site, dash.no_update, dash.no_update
    
    @app.callback(
        [Output('biological-search-input', 'value', allow_duplicate=True),
         Output('biological-selected-site', 'data', allow_duplicate=True),
         Output('biological-search-results', 'style', allow_duplicate=True)],
        [Input('biological-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_biological_search(n_clicks):
        """Clear search input and reset selections."""
        if n_clicks:
            logger.info("Biological search cleared")
            return "", None, {'display': 'none'}
        return dash.no_update, dash.no_update, dash.no_update
    
    # ===========================
    # 3. MAIN CONTENT DISPLAY
    # ===========================
    
    @app.callback(
        Output('biological-content-container', 'children'),
        [Input('biological-community-dropdown', 'value'),
         Input('biological-selected-site', 'data')]
    )
    def update_biological_display(selected_community, selected_site):
        """Update biological display based on selected community and site."""
        if not selected_community or not selected_site:
            return create_empty_state("Please select a community type and site to view biological data.")
        
        try:
            return create_biological_community_display(selected_community, selected_site)
        except Exception as e:
            logger.error(f"Error creating biological display: {e}")
            return create_error_state(
                f"Error Loading {selected_community.title()} Data",
                f"Could not load {selected_community} data for {selected_site}. Please try again.",
                str(e)
            )

    # ===========================
    # 4. GALLERY NAVIGATION
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


# ===========================================================================================
# BIOLOGICAL-SPECIFIC DISPLAY FUNCTIONS
# ===========================================================================================

def create_species_display(item):
    """
    Create HTML layout for displaying a species.
    
    Args:
        item: Dictionary with species information (name, image, description)
        
    Returns:
        Dash HTML component for displaying the species
    """
    return html.Div([
        # Image container with fixed height
        html.Div(
            html.Img(
                src=item['image'],
                style={'max-height': '300px', 'object-fit': 'contain', 'max-width': '100%'}
            ),
            style={
                'height': '300px',  
                'display': 'flex',
                'align-items': 'center',
                'justify-content': 'center'
            }
        ),
        # Text container with fixed height
        html.Div([
            html.H5(item['name'], className="mt-3"),
            html.P(item['description'], className="mt-2")
        ], style={'min-height': '80px'})
    ], style={'min-height': '400px'})

def create_gallery_navigation_callback(gallery_type):
    """
    Create a callback function for species gallery navigation.
    
    Args:
        gallery_type: Gallery type ('fish' or 'macro')
        
    Returns:
        Function that handles gallery navigation for the specified type
    """
    # Get the appropriate data based on gallery type
    data = FISH_DATA if gallery_type == 'fish' else MACRO_DATA
    
    def update_gallery(prev_clicks, next_clicks, current_index):
        """
        Update gallery based on previous/next button clicks.
        
        Args:
            prev_clicks: Number of clicks on previous button
            next_clicks: Number of clicks on next button
            current_index: Current index in the gallery
            
        Returns:
            Tuple of (gallery_display, new_index)
        """
        ctx = dash.callback_context
        
        # If no buttons clicked yet, show the first item
        if not ctx.triggered:
            return create_species_display(data[0]), 0
        
        # Determine which button was clicked
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Calculate new index based on which button was clicked
        if f'prev-{gallery_type}-button' in button_id:
            new_index = (current_index - 1) % len(data)
        else:  # next button
            new_index = (current_index + 1) % len(data)
        
        # Get the data for the new index
        item = data[new_index]
        
        # Create the display for the current item
        return create_species_display(item), new_index
    
    return update_gallery

def create_biological_community_display(selected_community, selected_site):
    """
    Create a complete display for biological community data with visualizations.
    
    Args:
        selected_community: Community type ('fish' or 'macro')
        selected_site: Selected site name
        
    Returns:
        Dash HTML component with the complete community display
    """
    try:
        # Import required functions for visualization
        if selected_community == 'fish':
            from visualizations.fish_viz import create_fish_viz, create_fish_metrics_accordion
            from data_processing.fish_processing import get_fish_dataframe
            
            # Get site-specific data to check if it exists
            site_data = get_fish_dataframe(selected_site)
            
            if site_data.empty:
                return create_empty_state(f"No fish data available for {selected_site}")
            
            # Create site-specific visualizations
            viz_figure = create_fish_viz(selected_site)
            metrics_accordion = create_fish_metrics_accordion(selected_site)
            
        elif selected_community == 'macro':
            from visualizations.macro_viz import create_macro_viz, create_macro_metrics_accordion
            from data_processing.macro_processing import get_macroinvertebrate_dataframe
            
            # Get all macro data first
            all_macro_data = get_macroinvertebrate_dataframe()
            
            if all_macro_data.empty:
                return create_empty_state("No macroinvertebrate data available in database")
            
            # Filter for the selected site
            site_data = all_macro_data[all_macro_data['site_name'] == selected_site]
            
            if site_data.empty:
                return create_empty_state(f"No macroinvertebrate data available for {selected_site}")
            
            # Create site-specific visualizations
            viz_figure = create_macro_viz(selected_site)
            metrics_accordion = create_macro_metrics_accordion(selected_site)
            
        else:
            return create_error_state(
                "Invalid Community Type",
                f"'{selected_community}' is not a valid community type."
            )

        # Import gallery creation function
        from layouts import create_species_gallery
            
        # Create unified layout for the community
        content = html.Div([
            # First row: Description on left, gallery on right
            dbc.Row([
                # Left column: Description
                dbc.Col([
                    load_markdown_content(f"biological/{selected_community}_description.md")
                ], width=6),
                
                # Right column: Species gallery
                dbc.Col([
                    create_species_gallery(selected_community)
                ], width=6, className="d-flex align-items-center"),
            ], className="mb-4"),
            
            # Second row: Graph (full width)
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=viz_figure)
                ], width=12)
            ], className="mb-4"),
            
            # Third row: Accordion section for metrics tables
            dbc.Row([
                dbc.Col([
                    metrics_accordion
                ], width=12)
            ], className="mb-4"),
            
            # Fourth row: Analysis section
            dbc.Row([
                dbc.Col([
                    load_markdown_content(f"biological/{selected_community}_analysis.md")
                ], width=12)
            ], className="mb-4"),
        ])
        
        return content
        
    except Exception as e:
        logger.error(f"Error creating biological display for {selected_community} at {selected_site}: {e}")
        return create_error_state(
            f"Error Loading {selected_community.title()} Data",
            f"Could not load {selected_community} data for {selected_site}. Please try again.",
            str(e)
        )