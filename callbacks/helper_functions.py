"""
Helper functions for the Tenmile Creek Water Quality Dashboard callbacks.
This file contains reusable helper functions used across different callback modules.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json

from dash import html, dcc
from utils import load_markdown_content, create_image_with_caption, setup_logging, get_sites_with_data

from config.data_definitions import (
    FISH_DATA, MACRO_DATA, CHEMICAL_DIAGRAMS, CHEMICAL_DIAGRAM_CAPTIONS,
    PARAMETER_DISPLAY_NAMES, PARAMETER_AXIS_LABELS
)

# Configure logging
logger = setup_logging("helper_callbacks", category="callbacks")

# --------------------------------------------------------------------------------------
# SEARCH AND SELECTION UTILITIES
# --------------------------------------------------------------------------------------

def should_perform_search(button_clicks, enter_presses, search_value, selection_value):
    """
    Check if search should be performed based on user inputs.
    
    Args:
        button_clicks: Number of clicks on search button
        enter_presses: Number of enter key presses in search input
        search_value: Current value in search input
        selection_value: Current dropdown/selection value
        
    Returns:
        bool: True if search should proceed, False otherwise
    """
    return (button_clicks or enter_presses) and search_value and selection_value

def get_search_results(search_value, data_type, max_results=10):
    """
    Get and format search results for any data type.
    
    Args:
        search_value: String to search for
        data_type: Type of data to search ('fish', 'macro', 'chemical', 'habitat', etc.)
        max_results: Maximum number of results to return
        
    Returns:
        tuple: (list of HTML components, dict with display style)
    """
    try:
        # Get available items based on data type
        available_items = get_sites_with_data(data_type)
        
        if not available_items:
            return [html.Div(f"No sites found for {data_type} data.", 
                        className="p-2 text-muted")], {'display': 'block'}
        
        # Filter items based on search
        filtered_items = [
            item for item in available_items 
            if search_value.lower() in item.lower()
        ]
        
        if not filtered_items:
            return [html.Div("No sites match your search.", 
                        className="p-2 text-muted")], {'display': 'block'}
        
        # Create clickable buttons for results
        result_buttons = [
            html.Button(
                item,
                id={'type': f'{data_type}-site-button', 'site': item},
                className="list-group-item list-group-item-action",
                style={'border': 'none', 'textAlign': 'left', 'width': '100%'}
            )
            for item in filtered_items[:max_results]
        ]
        
        return result_buttons, {'display': 'block'}
        
    except Exception as e:
        logger.error(f"Error in search for {data_type}: {e}")
        return [html.Div("Error performing search.", 
                    className="p-2 text-danger")], {'display': 'block'}

def is_item_clicked(click_list):
    """
    Check if any item in a list of click counts was clicked.
    
    Args:
        click_list: List of click counts from Dash ALL pattern matching
        
    Returns:
        bool: True if any item was clicked, False otherwise
    """
    return any(click_list) and any(click for click in click_list if click)

def extract_selected_item(item_key='site'):
    """
    Extract the selected item from Dash callback context.
    
    Args:
        item_key: Key name to extract from the triggered component ID (default: 'site')
        
    Returns:
        str: The selected item value
        
    Raises:
        ValueError: If no callback was triggered or item key not found
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise ValueError("No callback triggered")
    
    triggered_id = ctx.triggered[0]['prop_id']
    item_info = json.loads(triggered_id.split('.')[0])
    
    if item_key not in item_info:
        raise ValueError(f"Key '{item_key}' not found in triggered component")
    
    return item_info[item_key]

def create_search_visibility_response(has_selection, reset_values=None):
    """
    Create a standardized response for search visibility callbacks.
    
    Args:
        has_selection: Boolean indicating if a selection has been made
        reset_values: Dictionary of default values to use when resetting
        
    Returns:
        tuple: Standard response tuple for search visibility callbacks
    """
    if reset_values is None:
        reset_values = {
            'search_value': '',
            'selected_item': None,
            'results_style': {'display': 'none'},
            'results_children': []
        }
    
    if has_selection:
        # Show search section and enable inputs
        return (
            {'display': 'block', 'position': 'relative', 'marginBottom': '20px'},  # search_section_style
            False,  # input_disabled
            False,  # button_disabled
            False,  # clear_disabled
            reset_values['search_value'],
            reset_values['selected_item'],
            reset_values['results_style'],
            reset_values['results_children']
        )
    else:
        # Hide search section and disable inputs
        return (
            {'display': 'none'},  # search_section_style
            True,   # input_disabled
            True,   # button_disabled
            True,   # clear_disabled
            reset_values['search_value'],
            reset_values['selected_item'],
            reset_values['results_style'],
            reset_values['results_children']
        )

# --------------------------------------------------------------------------------------
# LEGEND AND PARAMETER FUNCTIONS
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
                {"color": "#ff9800", "label": "Elevated (0.8-2.0 mg/L)"},
                {"color": "#e74c3c", "label": "High (>2.0 mg/L)"}
            ]
        elif param_name == 'Phosphorus':
            return [
                {"color": "#1e8449", "label": "Normal (<0.1 mg/L)"},
                {"color": "#ff9800", "label": "Elevated (0.1-0.3 mg/L)"},
                {"color": "#e74c3c", "label": "High (>0.3 mg/L)"}
            ]
        elif param_name == 'Chloride':
            return [
                {"color": "#1e8449", "label": "Normal (<250 mg/L)"},
                {"color": "#ff9800", "label": "Elevated (250-500 mg/L)"},
                {"color": "#e74c3c", "label": "High (>500 mg/L)"}
            ]
    
    # Biological parameter legends
    elif param_type == 'bio':
        return [
            {"color": "#1e8449", "label": "Non-impaired (>0.79)"},
            {"color": "#ff9800", "label": "Slightly Impaired (0.60-0.79)"},
            {"color": "#e74c3c", "label": "Moderately Impaired (0.40-0.59)"},
            {"color": "#8b0000", "label": "Severely Impaired (<0.40)"}
        ]
    
    # Habitat parameter legends
    elif param_type == 'habitat':
        return [
            {"color": "#1e8449", "label": "Excellent (16-20)"},
            {"color": "#ff9800", "label": "Good (11-15)"},
            {"color": "#e74c3c", "label": "Fair (6-10)"},
            {"color": "#8b0000", "label": "Poor (0-5)"}
        ]
    
    # Default legend if parameter not found
    return [{"color": "#666", "label": "No data available"}]

def get_parameter_label(param_type, param_name):
    """
    Get the appropriate y-axis label for a parameter.
    
    Args:
        param_type: Type of parameter ('chem', 'bio', or 'habitat')
        param_name: Specific parameter name
        
    Returns:
        str: Y-axis label for the parameter
    """
    return PARAMETER_AXIS_LABELS.get(param_name, param_name.replace('_', ' ').title())

def get_parameter_name(parameter):
    """
    Get the human-readable name for a parameter code.
    
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
        elif param_name == 'Macro_Combined':
            return f"Showing {sites_with_data} of {total_sites} sites with macroinvertebrate data"
    elif param_type == 'habitat':
        return f"Showing {sites_with_data} of {total_sites} sites with habitat data"

# --------------------------------------------------------------------------------------
# CONTENT DISPLAY FUNCTIONS
# --------------------------------------------------------------------------------------

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
                return html.Div([
                    html.Div(f"No fish data available for {selected_site}", 
                            className="alert alert-warning mt-3")
                ])
            
            # Create site-specific visualizations
            viz_figure = create_fish_viz(selected_site)  # Pass site parameter
            metrics_accordion = create_fish_metrics_accordion(selected_site)  # Pass site parameter
            
        elif selected_community == 'macro':
            from visualizations.macro_viz import create_macro_viz, create_macro_metrics_accordion
            from data_processing.macro_processing import get_macroinvertebrate_dataframe
            
            # Get all macro data first
            all_macro_data = get_macroinvertebrate_dataframe()
            
            if all_macro_data.empty:
                return html.Div([
                    html.Div("No macroinvertebrate data available in database", 
                            className="alert alert-warning mt-3")
                ])
            
            # Filter for the selected site
            site_data = all_macro_data[all_macro_data['site_name'] == selected_site]
            
            if site_data.empty:
                return html.Div([
                    html.H4(f"Macroinvertebrate Community Data for {selected_site}", className="mb-4"),
                    html.Div(f"No macroinvertebrate data available for {selected_site}", 
                            className="alert alert-warning mt-3")
                ])
            
            # Create site-specific visualizations
            viz_figure = create_macro_viz(selected_site)  # Pass site parameter
            metrics_accordion = create_macro_metrics_accordion(selected_site)  # Pass site parameter
            
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
        return html.Div([
            html.H4(f"Error Loading {selected_community.title()} Data", className="mb-4"),
            html.Div(f"Error loading {selected_community} data for {selected_site}", 
                    className="alert alert-danger mt-3"),
            html.P("Please try selecting a different site or refresh the page."),
            html.Details([
                html.Summary("Error Details"),
                html.Pre(str(e), style={"fontSize": "12px", "color": "#666"})
            ])
        ])

def create_habitat_display(selected_site):
    """
    Create a display for habitat assessment data with visualization and metrics.
    
    Args:
        selected_site: Selected site name
        
    Returns:
        Dash HTML component with habitat data display
    """
    try:
        # Import required functions for visualization
        from visualizations.habitat_viz import create_habitat_viz, create_habitat_metrics_accordion
        from data_processing.habitat_processing import get_habitat_dataframe
        
        # Get site-specific data to check if it exists
        site_data = get_habitat_dataframe(selected_site)
        
        if site_data.empty:
            return html.Div([
                html.Div(f"No habitat data available for {selected_site}", 
                        className="alert alert-warning mt-3")
            ])
        
        # Create site-specific visualizations
        viz_figure = create_habitat_viz(selected_site)
        metrics_accordion = create_habitat_metrics_accordion(selected_site)
        
        # Create unified layout for habitat data
        content = html.Div([
            # First row: Description on left, image on right
            dbc.Row([
                # Left column: Description
                dbc.Col([
                    load_markdown_content("habitat/habitat_description.md")
                ], width=6),
                
                # Right column: Habitat image
                dbc.Col([
                    create_image_with_caption(
                        src='/assets/images/stream_habitat_diagram.jpg',
                        caption="Physical features evaluated during habitat assessment"
                    )
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
                    load_markdown_content("habitat/habitat_analysis.md")
                ], width=12)
            ], className="mb-4"),
        ])
        
        return content
        
    except Exception as e:
        logger.error(f"Error creating habitat display for {selected_site}: {e}")
        return html.Div([
            html.H4(f"Error Loading Habitat Data", className="mb-4"),
            html.Div(f"Error loading habitat data for {selected_site}", 
                    className="alert alert-danger mt-3"),
            html.P("Please try selecting a different site or refresh the page."),
            html.Details([
                html.Summary("Error Details"),
                html.Pre(str(e), style={"fontSize": "12px", "color": "#666"})
            ])
        ])

def create_all_parameters_view(df_filtered, key_parameters, reference_values, highlight_thresholds):
    """
    Create a dashboard view showing all chemical parameters.
    
    Args:
        df_filtered: Filtered dataframe with chemical data
        key_parameters: List of parameters to display
        reference_values: Dictionary of reference values for parameters
        highlight_thresholds: Dictionary of threshold values for highlighting
        
    Returns:
        Dash HTML component with all parameters view
    """
    try:
        from visualizations.chemical_viz import create_all_parameters_figure
        
        # Create the comprehensive figure
        fig = create_all_parameters_figure(df_filtered, key_parameters, reference_values, highlight_thresholds)
        
        # Return the figure wrapped in a graph component
        return dcc.Graph(
            figure=fig,
            style={'height': '800px'},  # Make it taller for better readability
            config={'displayModeBar': True, 'toImageButtonOptions': {'width': 1200, 'height': 800}}
        )
        
    except Exception as e:
        logger.error(f"Error creating all parameters view: {e}")
        return html.Div([
            html.H4("Error Loading All Parameters View", className="mb-4"),
            html.Div("Error loading the comprehensive parameters view.", 
                    className="alert alert-danger mt-3"),
            html.Details([
                html.Summary("Error Details"),
                html.Pre(str(e), style={"fontSize": "12px", "color": "#666"})
            ])
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
                    y_label=get_parameter_label('chem', parameter),
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
            ], className="d-flex h-100 align-items-center justify-content-center", 
            style={'height': '100%'})
        else:
            diagram_component = html.Div(
                "No diagram available for this parameter.", 
                className="d-flex h-100 align-items-center justify-content-center"
            )
        
        return graph, explanation_component, diagram_component
        
    except Exception as e:
        logger.error(f"Error creating single parameter view for {parameter}: {e}")
        error_component = html.Div([
            html.Div(f"Error creating view for {parameter}", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])
        return error_component, html.Div(), html.Div()