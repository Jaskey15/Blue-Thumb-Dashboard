"""
Callback functions for the Tenmile Creek Water Quality Dashboard.
This file contains all the callbacks that handle user interactions.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from dash import html, dcc
from dash.dependencies import Input, Output, State
from utils import load_markdown_content, create_image_with_caption, setup_logging

# Import data definitions
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
                {"color": "#e74c3c", "label": "Poor (<50% or >150%)"},
                {"color": "gray", "label": "No data"}
            ]
        elif param_name == 'pH':
            return [
                {"color": "#1e8449", "label": "Normal (6.5-9.0)"},
                {"color": "#ff9800", "label": "Outside Normal Range"},
                {"color": "gray", "label": "No data"}
            ]
        elif param_name == 'soluble_nitrogen':
            return [
                {"color": "#1e8449", "label": "Normal (<0.8 mg/L)"},
                {"color": "#ff9800", "label": "Caution (0.8-1.5 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>1.5 mg/L)"},
                {"color": "gray", "label": "No data"}
            ]
        elif param_name == 'Phosphorus':
            return [
                {"color": "#1e8449", "label": "Normal (<0.05 mg/L)"},
                {"color": "#ff9800", "label": "Caution (0.05-0.1 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>0.1 mg/L)"},
                {"color": "gray", "label": "No data"}
            ]
        elif param_name == 'Chloride':
            return [
                {"color": "#1e8449", "label": "Normal (<250 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>250 mg/L)"},
                {"color": "gray", "label": "No data"}
            ]
    
    # Biological parameter legends
    elif param_type == 'bio':
        if param_name == 'Fish_IBI':
            return [
                {"color": "#1e8449", "label": "Excellent (>0.97)"},
                {"color": "#7cb342", "label": "Good (0.80-0.97)"},
                {"color": "#ff9800", "label": "Fair (0.67-0.80)"},
                {"color": "#e74c3c", "label": "Poor (<0.67)"},
                {"color": "gray", "label": "No data"}
            ]
        elif param_name.startswith('Macro'):
            return [
                {"color": "#1e8449", "label": "Non-impaired (>0.83)"},
                {"color": "#ff9800", "label": "Slightly Impaired (0.54-0.83)"},
                {"color": "#f57c00", "label": "Moderately Impaired (0.17-0.54)"},
                {"color": "#e74c3c", "label": "Severely Impaired (<0.17)"},
                {"color": "gray", "label": "No data"}
            ]
    
    # Habitat parameter legends
    elif param_type == 'habitat':
        return [
            {"color": "#1e8449", "label": "Grade A (> 90)"},
            {"color": "#7cb342", "label": "Grade B (80-89)"},
            {"color": "#ff9800", "label": "Grade C (70-79)"},
            {"color": "#e53e3e", "label": "Grade D (60-69)"},
            {"color": "#e74c3c", "label": "Grade F (<60)"},
            {"color": "gray", "label": "No data"}
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

def create_biological_community_display(selected_community):
    """
    Create a display for biological community data with description, gallery, and metrics.
    
    Args:
        selected_community: Community type ('fish' or 'macro')
        
    Returns:
        Dash HTML component with the complete community display
    """
    try:
        # Import required functions for visualization
        if selected_community == 'fish':
            from visualizations.fish_viz import create_fish_viz, create_fish_metrics_accordion
            viz_function = create_fish_viz
            metrics_function = create_fish_metrics_accordion
        elif selected_community == 'macro':
            from visualizations.macro_viz import create_macro_viz, create_macro_metrics_accordion
            viz_function = create_macro_viz
            metrics_function = create_macro_metrics_accordion
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

# --------------------------------------------------------------------------------------
# CALLBACK REGISTRATION FUNCTION
# --------------------------------------------------------------------------------------

def register_callbacks(app):
    """Register all callbacks for the dashboard."""

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
            
            # Add parameter-specific colors
            updated_map = add_parameter_colors_to_map(fig, param_type, param_name)
            
            # Create appropriate legend based on parameter type and name
            legend_items = get_parameter_legend(param_type, param_name)
            
            # Build the legend HTML
            legend_html = html.Div([
                html.Div([
                    html.Span("● ", style={"color": item["color"], "font-size": "20px"}),
                    html.Span(item["label"], className="mr-3")
                ], style={"display": "inline-block", "margin-right": "15px"})
                for item in legend_items
            ], className="text-center mt-2 mb-4")
            
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
         Output('chemical-diagram-container', 'children')],
        [Input('chemical-parameter-dropdown', 'value'),
         Input('year-range-slider', 'value'),
         Input('month-checklist', 'value'),
         Input('highlight-thresholds-switch', 'value')]
    )
    def update_chemical_display(selected_parameter, year_range, selected_months, highlight_thresholds):
        """
        Update chemical parameter graph and explanations based on user selections.
        
        Args:
            selected_parameter: Selected chemical parameter
            year_range: Selected year range [min, max]
            selected_months: List of selected months
            highlight_thresholds: Boolean indicating whether to highlight threshold violations
            
        Returns:
            Tuple of (graph, explanation, diagram) components
        """
        try:
            # Import functions for data processing
            from data_processing.chemical_processing import process_chemical_data
            
            # Get and filter chemical data
            df_clean, key_parameters, reference_values = process_chemical_data()
            
            # Filter by year range
            year_min, year_max = year_range
            df_filtered = df_clean[(df_clean['Year'] >= year_min) & (df_clean['Year'] <= year_max)]
            
            # Filter by selected months (if not all months selected)
            if selected_months and len(selected_months) < 12:
                df_filtered = df_filtered[df_filtered['Month'].isin(selected_months)]
            
            # Check if we have data after filtering
            if len(df_filtered) == 0:
                no_data_message = html.Div(
                    "No data available for the selected time range.", 
                    className="alert alert-warning"
                )
                return no_data_message, html.Div(), html.Div()
            
            # Handle "all parameters" view differently
            if selected_parameter == 'all_parameters':
                graph = create_all_parameters_view(
                    df_filtered, 
                    key_parameters, 
                    reference_values, 
                    highlight_thresholds
                )
                return graph, html.Div(), html.Div()
            else:
                # Create components for single parameter view
                return create_single_parameter_view(
                    df_filtered, 
                    selected_parameter, 
                    reference_values, 
                    highlight_thresholds
                )
                
        except Exception as e:
            print(f"Error updating chemical display: {e}")
            error_message = html.Div([
                html.Div("Error updating chemical display", className="alert alert-danger"),
                html.Pre(str(e), style={"fontSize": "12px"})
            ])
            return error_message, html.Div(), html.Div()

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
        [Input('biological-community-dropdown', 'value')]
    )
    def update_biological_display_callback(selected_community):
        """
        Update biological display based on selected community.
        
        Args:
            selected_community: Selected biological community ('fish' or 'macro')
            
        Returns:
            Dash HTML component with the biological display
        """
        if not selected_community:
            return html.Div("Please select a biological community from the dropdown.")
        
        return create_biological_community_display(selected_community)

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