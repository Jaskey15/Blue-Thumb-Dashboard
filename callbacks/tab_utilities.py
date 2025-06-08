"""
Tab-specific utility functions for the Blue Thumb Stream Health Dashboard.

This module contains utility functions that are specific to individual tabs
but not shared across the entire application. Each section is clearly marked
for its corresponding tab.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from config.data_definitions import PARAMETER_DISPLAY_NAMES, PARAMETER_AXIS_LABELS, FISH_DATA, MACRO_DATA
from utils import setup_logging, load_markdown_content, create_image_with_caption
from .helper_functions import create_empty_state, create_error_state

logger = setup_logging("tab_utilities")

# ===========================================================================================
# OVERVIEW TAB UTILITIES
# ===========================================================================================

def get_parameter_legend(param_type, param_name):
    """
    Return legend items specific to the selected parameter type and name.
    Used primarily by the overview tab for map legends.
    
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
    Used by visualization functions across tabs.
    
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
    Used across tabs for display purposes.
    
    Args:
        parameter: Parameter code
        
    Returns:
        str: Human-readable name for the parameter
    """
    return PARAMETER_DISPLAY_NAMES.get(parameter, parameter)

def get_site_count_message(param_type, param_name, sites_with_data, total_sites):
    """
    Create custom site count message based on parameter type.
    Used by overview tab for map status messages.
    
    Args:
        param_type: Type of parameter ('chem', 'bio', 'habitat')
        param_name: Specific parameter name
        sites_with_data: Number of sites with data
        total_sites: Total number of sites
        
    Returns:
        str: Formatted site count message
    """
    if param_type == 'chem':
        return f"Showing {sites_with_data} of {total_sites} sites with chemical data"
    elif param_type == 'bio':
        if param_name == 'Fish_IBI':
            return f"Showing {sites_with_data} of {total_sites} sites with fish community data"
        elif param_name == 'Macro_Combined':
            return f"Showing {sites_with_data} of {total_sites} sites with macroinvertebrate data"
    elif param_type == 'habitat':
        return f"Showing {sites_with_data} of {total_sites} sites with habitat data"
    
    return f"Showing {sites_with_data} of {total_sites} sites"

# ===========================================================================================
# BIOLOGICAL TAB UTILITIES
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

# ===========================================================================================
# CHEMICAL TAB UTILITIES
# ===========================================================================================
def create_single_parameter_visualization(df_filtered, parameter, reference_values, highlight_thresholds):
    """Create visualization for a single chemical parameter."""
    try:
        if df_filtered.empty or parameter not in df_filtered.columns:
            empty_state = create_empty_state(f"No {parameter} data available for the selected time period.")
            return empty_state, html.Div(), html.Div()
        
        # Import required functions
        from visualizations.chemical_viz import create_time_series_plot
        from config.data_definitions import CHEMICAL_DIAGRAMS, CHEMICAL_DIAGRAM_CAPTIONS
        from utils import load_markdown_content, create_image_with_caption
        
        # Get parameter name for display
        parameter_name = get_parameter_name(parameter)
        
        # Create the time series plot
        fig = create_time_series_plot(
            df_filtered, 
            parameter, 
            reference_values,
            title=f"{parameter_name} Over Time",
            y_label=get_parameter_label('chem', parameter),
            highlight_thresholds=highlight_thresholds
        )
        
        # Create graph component
        graph = dcc.Graph(
            figure=fig,
            style={'height': '450px'}
        )
        
        # Load explanation from markdown file
        file_path = f"chemical/{parameter_name.lower().replace(' ', '_')}.md"
        explanation = load_markdown_content(file_path)
        
        # Create diagram component if available
        if parameter in CHEMICAL_DIAGRAMS:
            diagram = html.Div([
                create_image_with_caption(
                    src=CHEMICAL_DIAGRAMS[parameter],
                    caption=CHEMICAL_DIAGRAM_CAPTIONS.get(parameter, "")
                )
            ], className="d-flex h-100 align-items-center justify-content-center", 
            style={'height': '100%'})
        else:
            diagram = html.Div(
                "No diagram available for this parameter.", 
                className="d-flex h-100 align-items-center justify-content-center"
            )
        
        return graph, explanation, diagram
        
    except Exception as e:
        logger.error(f"Error creating single parameter view for {parameter}: {e}")
        error_state = create_error_state(
            "Visualization Error", 
            f"Could not create {parameter} visualization.", 
            str(e)
        )
        return error_state, html.Div(), html.Div()

def create_all_parameters_visualization(df_filtered, key_parameters, reference_values, highlight_thresholds):
    """Create visualization for all chemical parameters."""
    try:
        if df_filtered.empty:
            empty_state = create_empty_state("No data available for the selected time period.")
            return empty_state, html.Div(), html.Div()
        
        # Import the visualization function
        from visualizations.chemical_viz import create_parameter_dashboard
        
        # Create the comprehensive figure
        fig = create_parameter_dashboard(df_filtered, key_parameters, reference_values, highlight_thresholds)
        
        # Create the graph component
        graph = dcc.Graph(
            figure=fig,
            style={'height': '800px'},  
            config={'displayModeBar': True, 'toImageButtonOptions': {'width': 1200, 'height': 800}}
        )
        
        return graph, html.Div(), html.Div()  
        
    except Exception as e:
        logger.error(f"Error creating all parameters view: {e}")
        error_state = create_error_state(
            "Visualization Error", 
            "Could not create all parameters visualization.", 
            str(e)
        )
        return error_state, html.Div(), html.Div()

# ===========================================================================================
# HABITAT TAB UTILITIES
# ===========================================================================================

def create_habitat_display(site_name):
    """
    Create the complete habitat display for a selected site.
    
    Args:
        site_name (str): Name of the selected monitoring site
        
    Returns:
        dash.html.Div: Complete habitat display layout
    """
    try:
        # Import required functions
        from visualizations.habitat_viz import create_habitat_viz, create_habitat_metrics_accordion
        
        # Create habitat visualization chart
        habitat_fig = create_habitat_viz(site_name)
        
        # Create habitat metrics table in accordion
        habitat_accordion = create_habitat_metrics_accordion(site_name)
        
        # Combine into layout - single column, stacked vertically
        display = html.Div([
            # Chart section - full width
            dcc.Graph(
                figure=habitat_fig,
                config={'displayModeBar': False},
                style={'height': '500px'}
            ),
            
            # Metrics accordion section - full width
            html.Div([
                habitat_accordion
            ], className="mb-4"),
        ])   
        return display
        
    except Exception as e:
        logger.error(f"Error creating habitat display for {site_name}: {e}")
        return create_error_state(
            "Error Creating Habitat Display",
            f"Could not create habitat visualization for {site_name}.",
            str(e)
        )