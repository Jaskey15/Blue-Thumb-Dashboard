"""
Callback functions for the Tenmile Creek Water Quality Dashboard.
This file contains all the callbacks that handle user interactions.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json

from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
from utils import load_markdown_content, create_image_with_caption, setup_logging, get_sites_with_data

from cache_utils import (
    get_cache_key, is_cache_valid, get_cached_data, 
    set_cache_data, clear_expired_cache
)

from data_definitions import (
    FISH_DATA, MACRO_DATA, CHEMICAL_DIAGRAMS, CHEMICAL_DIAGRAM_CAPTIONS,
    PARAMETER_DISPLAY_NAMES, PARAMETER_AXIS_LABELS, SEASON_MONTHS
)

# Configure logging
logger = setup_logging("callbacks", category="app")

# --------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------------------

def get_parameter_legend(param_type, param_name):
    """
    Return legend items specific to the selected parameter type and name.
    
    Args:
        param_type: Type of parameter ('chem', 'bio', or 'habitat')
        param_name: Specific parameter name
        
    Returns:
        List of dictionaries with color and label for each legend item
    """
    # Chemical parameter legends
    if param_type == 'chem':
        if param_name == 'do_percent':
            return [
                {"color": "#1e8449", "label": "Normal (80-130%)"},
                {"color": "#ff9800", "label": "Caution (50-80% or 130-150%)"},
                {"color": "#e74c3c", "label": "Poor (<50% or >150%)"}
            ]
        elif param_name == 'pH':
            return [
                {"color": "#1e8449", "label": "Normal (6.5-9.0)"},
                {"color": "#f57c00", "label": "Below Normal (<6.5: Acidic)"},
                {"color": "#5e35b1", "label": "Above Normal (>9.0: Basic/Alkaline)"}
            ]
        elif param_name == 'soluble_nitrogen':
            return [
                {"color": "#1e8449", "label": "Normal (<0.8 mg/L)"},
                {"color": "#ff9800", "label": "Caution (0.8-1.5 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>1.5 mg/L)"}
            ]
        elif param_name == 'Phosphorus':
            return [
                {"color": "#1e8449", "label": "Normal (<0.05 mg/L)"},
                {"color": "#ff9800", "label": "Caution (0.05-0.1 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>0.1 mg/L)"}
            ]
        elif param_name == 'Chloride':
            return [
                {"color": "#1e8449", "label": "Normal (<250 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>250 mg/L)"}
            ]
    
    # Biological parameter legends
    elif param_type == 'bio':
        if param_name == 'Fish_IBI':
            return [
                {"color": "#1e8449", "label": "Excellent (>0.97)"},
                {"color": "#7cb342", "label": "Good (0.80-0.97)"},
                {"color": "#ff9800", "label": "Fair (0.67-0.80)"},
                {"color": "#e74c3c", "label": "Poor (<0.67)"}
            ]
        elif param_name.startswith('Macro'):
            return [
                {"color": "#1e8449", "label": "Non-impaired (>0.83)"},
                {"color": "#ff9800", "label": "Slightly Impaired (0.54-0.83)"},
                {"color": "#f57c00", "label": "Moderately Impaired (0.17-0.54)"},
                {"color": "#e74c3c", "label": "Severely Impaired (<0.17)"}
            ]
    
    # Habitat parameter legends
    elif param_type == 'habitat':
        return [
            {"color": "#1e8449", "label": "Grade A (>0.90)"},
            {"color": "#7cb342", "label": "Grade B (0.80-0.89)"},
            {"color": "#ff9800", "label": "Grade C (0.70-0.79)"},
            {"color": "#e53e3e", "label": "Grade D (0.60-0.69)"},
            {"color": "#e74c3c", "label": "Grade F (<0.60)"}
        ]
    
    # Default legend if parameter type/name not recognized
    return [{"color": "red", "label": "Monitoring Site"}]

def get_parameter_label(parameter):
    """
    Return appropriate Y-axis label for a given parameter.
    
    Args:
        parameter: Parameter code
        
    Returns:
        String with formatted label for the y-axis
    """
    return PARAMETER_AXIS_LABELS.get(parameter, parameter)

def get_parameter_name(parameter):
    """
    Convert parameter code to human-readable name for explanations lookup.
    
    Args:
        parameter: Parameter code
        
    Returns:
        Human-readable name for the parameter
    """
    return PARAMETER_DISPLAY_NAMES.get(parameter, parameter)

def get_site_count_message(param_type, param_name, sites_with_data, total_sites):
    """Create custom site count message based on parameter type."""
    if param_type == 'chem':
        return f"Showing {sites_with_data} of {total_sites} sites with chemical data"
    elif param_type == 'bio':
        if param_name == 'Fish_IBI':
            return f"Showing {sites_with_data} of {total_sites} sites with fish community data"
        elif param_name == 'Macro_Summer':
            return f"Showing {sites_with_data} of {total_sites} sites with macroinvertebrate summer data"
        elif param_name == 'Macro_Winter':
            return f"Showing {sites_with_data} of {total_sites} sites with macroinvertebrate winter data"
    elif param_type == 'habitat':
        return f"Showing {sites_with_data} of {total_sites} sites with habitat data"

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

def create_all_parameters_view(df_filtered, key_parameters, reference_values, highlight_thresholds):
    """
    Create a dashboard view showing all chemical parameters.
    
    Args:
        df_filtered: Filtered dataframe with chemical data
        key_parameters: List of key parameters to display
        reference_values: Dictionary of reference values for parameters
        highlight_thresholds: Boolean indicating whether to highlight threshold violations
        
    Returns:
        Dash HTML component with the dashboard graph
    """
    from visualizations.chemical_viz import create_parameter_dashboard
    
    try:
        fig = create_parameter_dashboard(
            df_filtered, 
            key_parameters, 
            reference_values, 
            highlight_thresholds, 
            get_parameter_name
        )
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'width': '100%', 'height': '100%'}
            )
        ], className="mb-4")
        
    except Exception as e:
        print(f"Error creating parameter dashboard: {e}")
        return html.Div([
            html.Div("Error creating parameter dashboard", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])

def create_single_parameter_view(df_filtered, parameter, reference_values, highlight_thresholds):
    """
    Create a view for a single chemical parameter with graph, explanation, and diagram.
    
    Args:
        df_filtered: Filtered dataframe with chemical data
        parameter: Parameter code to display
        reference_values: Dictionary of reference values for parameters
        highlight_thresholds: Boolean indicating whether to highlight threshold violations
        
    Returns:
        Tuple of (graph, explanation, diagram) components
    """
    from visualizations.chemical_viz import create_time_series_plot
    
    try:
        # Get parameter name and prepare components
        parameter_name = get_parameter_name(parameter)
        
        # Create graph component
        graph = html.Div([
            dcc.Graph(
                figure=create_time_series_plot(
                    df_filtered, 
                    parameter, 
                    reference_values,
                    title=f"{parameter_name} Over Time",
                    y_label=get_parameter_label(parameter),
                    highlight_thresholds=highlight_thresholds
                ),
                style={'height': '450px'}
            )
        ])
        
        # Get description and analysis text from markdown file
        file_path = f"chemical/{parameter_name.lower().replace(' ', '_')}.md"
        explanation_component = load_markdown_content(file_path)
        
        # Create diagram component if available
        if parameter in CHEMICAL_DIAGRAMS:
            diagram_component = html.Div([
                create_image_with_caption(
                    src=CHEMICAL_DIAGRAMS[parameter],
                    caption=CHEMICAL_DIAGRAM_CAPTIONS.get(parameter, "")
                )
            ], className="d-flex h-100 align-items-center justify-content-center")
        else:
            diagram_component = html.Div(
                "No diagram available for this parameter.", 
                className="d-flex h-100 align-items-center justify-content-center"
            )
        
        return graph, explanation_component, diagram_component
        
    except Exception as e:
        print(f"Error creating single parameter view for {parameter}: {e}")
        error_component = html.Div([
            html.Div(f"Error creating view for {parameter}", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])
        return error_component, html.Div(), html.Div()

def create_biological_community_display(selected_community, selected_site):
    """
    Create a display for biological community data with description, gallery, and metrics.
    
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
            viz_function = lambda: create_fish_viz()  # You'll need to modify these to accept site parameter
            metrics_function = lambda: create_fish_metrics_accordion()
        elif selected_community == 'macro':
            from visualizations.macro_viz import create_macro_viz, create_macro_metrics_accordion
            viz_function = lambda: create_macro_viz()
            metrics_function = lambda: create_macro_metrics_accordion()
        else:
            return html.Div("Please select a valid biological community from the dropdown.")
        
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
            ]),
            
            # Second row: Graph (full width)
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=viz_function())
                ], width=12)
            ], className="mt-4"),
            
            # Third row: Accordion section for metrics tables
            dbc.Row([
                dbc.Col([
                    metrics_function()
                ], width=12)
            ], className="mt-4"),
            
            # Fourth row: Analysis section
            dbc.Row([
                dbc.Col([
                    load_markdown_content(f"biological/{selected_community}_analysis.md")
                ], width=12)
            ], className="mt-4"),
        ])
        
        return content
        
    except Exception as e:
        print(f"Error creating biological display for {selected_community}: {e}")
        return html.Div([
            html.Div(f"Error creating biological display", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])

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

def update_site_dropdown(search_value, data_type):
    """
    Helper function to update site dropdown for any tab.
    
    Args:
        search_value: Current search input value
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat')
    
    Returns:
        Tuple of (dropdown_children, dropdown_style)
    """
    # If search is empty or too short, hide dropdown
    if not search_value or len(search_value) < 1:  # Changed from 3 to 1
        return [], {'display': 'none', 'position': 'absolute', 'top': '100%', 'left': '0', 'right': '0', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'borderTop': 'none', 'maxHeight': '200px', 'overflowY': 'auto', 'zIndex': '1000', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}
    
    # Get available sites for this data type
    available_sites = get_sites_with_data(data_type)
    
    # Filter sites based on search (case-insensitive contains)
    search_lower = search_value.lower()
    matching_sites = [
        site for site in available_sites 
        if search_lower in site.lower()
    ]
    
    # Sort by relevance: sites that start with the search term first
    def sort_key(site):
        site_lower = site.lower()
        if site_lower.startswith(search_lower):
            return (0, site)  # Starts with - highest priority
        else:
            return (1, site)  # Contains - lower priority
    
    matching_sites.sort(key=sort_key)
    
    # Limit to 10 results
    matching_sites = matching_sites[:10]
    
    # If no matches, show "no results"
    if not matching_sites:
        return [
            html.Div(
                "No sites found",
                className="dropdown-item disabled",
                style={'padding': '8px 12px', 'color': '#6c757d'}
            )
        ], {'display': 'block', 'position': 'absolute', 'top': '100%', 'left': '0', 'right': '0', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'borderTop': 'none', 'maxHeight': '200px', 'overflowY': 'auto', 'zIndex': '1000', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}
    
    # Create dropdown items
    dropdown_items = []
    for site in matching_sites:
        dropdown_items.append(
            html.Div(
                site,
                className="dropdown-item",
                id={'type': 'site-option', 'index': site, 'tab': data_type},
                style={
                    'padding': '8px 12px',
                    'cursor': 'pointer',
                    'borderBottom': '1px solid #eee'
                },
                n_clicks=0
            )
        )
    
    return dropdown_items, {'display': 'block', 'position': 'absolute', 'top': '100%', 'left': '0', 'right': '0', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'borderTop': 'none', 'maxHeight': '200px', 'overflowY': 'auto', 'zIndex': '1000', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}
    
    # Create dropdown items
    dropdown_items = []
    for site in matching_sites:
        dropdown_items.append(
            html.Div(
                site,
                className="dropdown-item",
                id={'type': 'site-option', 'index': site, 'tab': data_type},
                style={
                    'padding': '8px 12px',
                    'cursor': 'pointer',
                    'borderBottom': '1px solid #eee'
                },
                n_clicks=0
            )
        )
    
    return dropdown_items, {'display': 'block', 'position': 'absolute', 'top': '100%', 'left': '0', 'right': '0', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'borderTop': 'none', 'maxHeight': '200px', 'overflowY': 'auto', 'zIndex': '1000', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}

def handle_site_selection(site_clicks, clear_clicks, current_site, tab_prefix):
    """
    Helper function to handle site selection for any tab.
    """
    ctx = dash.callback_context
    
    # If clear button was clicked
    if ctx.triggered and f'{tab_prefix}-site-clear-button' in ctx.triggered[0]['prop_id']:
        return (
            None,  # selected-site-data
            "",    # search input value (clear it)
            {'display': 'none'},  # clear button style (hide it)
            {'display': 'block', 'textAlign': 'center', 'marginTop': '20px'}, # no-site-message style
            {'display': 'none'}   # controls-content style
        )
    
    # If a site option was clicked
    if ctx.triggered and 'site-option' in str(ctx.triggered[0]['prop_id']):
        # Find which site was clicked
        triggered_id = ctx.triggered[0]['prop_id']
        site_id = json.loads(triggered_id.split('.')[0])
        selected_site = site_id['index']
        
        return (
            selected_site,  # selected-site-data
            selected_site,  # search input value (show site name in search box)
            {'display': 'block', 'position': 'absolute', 'right': '5px', 'top': '50%', 'transform': 'translateY(-50%)', 'border': 'none', 'background': 'transparent', 'fontSize': '20px'},  # clear button style (show it)
            {'display': 'none'},   # no-site-message style (hide it)
            {'display': 'block'}   # controls-content style (show controls)
        )
    
    # No change
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# --------------------------------------------------------------------------------------
# CALLBACK REGISTRATION FUNCTION
# --------------------------------------------------------------------------------------

def register_callbacks(app):
    """Register all callbacks for the dashboard."""

    # --------------------------------------------------------------------------------------
    # SITE SELECTOR CALLBACKS
    # --------------------------------------------------------------------------------------

    @app.callback(
        [Output('chemical-site-dropdown', 'children'),
         Output('chemical-site-dropdown', 'style')],
        [Input('chemical-site-search-input', 'value')],
        [State('chemical-available-sites', 'data')]
    )
    def update_chemical_site_dropdown(search_value, data_type):
        """Update the chemical site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type)

    @app.callback(
        [Output('biological-site-dropdown', 'children'),
         Output('biological-site-dropdown', 'style')],
        [Input('biological-site-search-input', 'value')],
        [State('biological-available-sites', 'data')]
    )
    def update_biological_site_dropdown(search_value, data_type):
        """Update the biological site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type)

    @app.callback(
        [Output('habitat-site-dropdown', 'children'),
         Output('habitat-site-dropdown', 'style')],
        [Input('habitat-site-search-input', 'value')],
        [State('habitat-available-sites', 'data')]
    )
    def update_habitat_site_dropdown(search_value, data_type):
        """Update the habitat site dropdown based on search input."""
        return update_site_dropdown(search_value, data_type)

    # Site selection callbacks for each tab
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
         Output('biological-selected-site-display', 'children'),
         Output('biological-selected-site-display', 'style'),
         Output('biological-site-clear-button', 'style'),
         Output('biological-no-site-message', 'style'),
         Output('biological-controls-content', 'style')],
        [Input({'type': 'site-option', 'index': ALL, 'tab': 'fish'}, 'n_clicks'),
         Input('biological-site-clear-button', 'n_clicks')],
        [State('biological-selected-site-data', 'data')]
    )
    def handle_biological_site_selection(site_clicks, clear_clicks, current_site):
        """Handle site selection for biological tab."""
        return handle_site_selection(site_clicks, clear_clicks, current_site, 'biological')

    @app.callback(
        [Output('habitat-selected-site-data', 'data'),
         Output('habitat-site-search-input', 'value'),
         Output('habitat-selected-site-display', 'children'),
         Output('habitat-selected-site-display', 'style'),
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
    # OVERVIEW TAB CALLBACKS
    # --------------------------------------------------------------------------------------

    @app.callback(
        [Output('site-map-graph', 'figure'),
        Output('parameter-dropdown', 'disabled'),
        Output('map-legend-container', 'children')],
        [Input('main-tabs', 'active_tab')]
    )
    def load_basic_map_on_tab_open(active_tab):
        """
        Load the basic map when the Overview tab is opened.
        This shows blue dots immediately without parameter-specific data.
        """
        # Only load map when Overview tab is active
        if active_tab != 'overview-tab':
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            from visualizations.map_viz import create_basic_site_map
            
            # Create basic map with blue markers
            basic_map = create_basic_site_map()
            
            # Enable the parameter dropdown now that map is loaded
            dropdown_disabled = False
            
            # No legend needed for basic map
            legend_html = html.Div()
            
            return basic_map, dropdown_disabled, legend_html
            
        except Exception as e:
            print(f"Error loading basic map: {e}")
            
            # Return error map and keep dropdown disabled
            from visualizations.map_viz import create_error_map
            error_map = create_error_map(f"Error loading monitoring sites: {str(e)}")
            
            return error_map, True, html.Div()
        
    @app.callback(
        [Output('site-map-graph', 'figure', allow_duplicate=True),
        Output('map-legend-container', 'children', allow_duplicate=True)],
        [Input('parameter-dropdown', 'value')],
        [State('site-map-graph', 'figure')],
        prevent_initial_call=True
    )
    def update_map_with_parameter_selection(parameter_value, current_figure):
        """
        Update the map with parameter-specific color coding when user selects a parameter.
        """
        try:
            from visualizations.map_viz import create_basic_site_map, add_parameter_colors_to_map
            
            # If no parameter selected, show basic map
            if not parameter_value:
                basic_map = create_basic_site_map()
                return basic_map, html.Div()
            
            # Split the parameter value to get type and parameter
            param_type, param_name = parameter_value.split(':')
            
            # Start with current figure or create basic map
            if current_figure and current_figure.get('data'):
                # Use plotly's graph_objects to recreate the figure
                fig = go.Figure(current_figure)
            else:
                fig = create_basic_site_map()
            
            # Add parameter-specific colors and get site counts
            updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(fig, param_type, param_name)
            
            # Create appropriate legend based on parameter type and name (excluding "No data")
            legend_items = get_parameter_legend(param_type, param_name)
            # Remove "No data" entries from legend
            legend_items = [item for item in legend_items if "No data" not in item["label"]]
            
            # Build the legend HTML with site count
            legend_content = [
                # Site count display
                html.Div(
                    get_site_count_message(param_type, param_name, sites_with_data, total_sites),
                    className="text-center mb-2",
                    style={"font-weight": "bold", "color": "#666"}
                ),
                # Legend items wrapper
                html.Div([
                    html.Div([
                        html.Span("● ", style={"color": item["color"], "font-size": "20px"}),
                        html.Span(item["label"], className="mr-3")
                    ], style={"display": "inline-block", "margin-right": "15px"})
                    for item in legend_items
                ])
            ]

            legend_html = html.Div(legend_content, className="text-center mt-2 mb-4")

            return updated_map, legend_html
            
        except Exception as e:
            print(f"Error updating map with parameter selection: {e}")
            return dash.no_update, html.Div(
                html.Div("Error updating map. Please try again.", className="text-danger"),
                className="text-center mt-2 mb-4"
            )

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