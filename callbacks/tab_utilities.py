"""
Tab-specific utility functions for the Blue Thumb Stream Health Dashboard.

This module contains utility functions that are specific to individual tabs
but not shared across the entire application. Each section is clearly marked
for its corresponding tab.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from layouts.ui_data import FISH_DATA, MACRO_DATA
from utils import setup_logging, load_markdown_content
from .helper_functions import create_empty_state, create_error_state, get_parameter_name, get_parameter_label
from visualizations.map_viz import COLORS

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
                {"color": COLORS['normal'], "label": "Normal (80-130%)"},
                {"color": COLORS['caution'], "label": "Caution (50-80% or 130-150%)"},
                {"color": COLORS['poor'], "label": "Poor (<50% or >150%)"}
            ]
        elif param_name == 'pH':
            return [
                {"color": COLORS['normal'], "label": "Normal (6.5-9.0)"},
                {"color": COLORS['below_normal'], "label": "Below Normal (<6.5: Acidic)"},
                {"color": COLORS['above_normal'], "label": "Above Normal (>9.0: Basic/Alkaline)"}
            ]
        elif param_name == 'soluble_nitrogen':
            return [
                {"color": COLORS['normal'], "label": "Normal (<0.8 mg/L)"},
                {"color": COLORS['caution'], "label": "Caution (0.8-1.5 mg/L)"},
                {"color": COLORS['poor'], "label": "Poor (>1.5 mg/L)"}
            ]
        elif param_name == 'Phosphorus':
            return [
                {"color": COLORS['normal'], "label": "Normal (<0.05 mg/L)"},
                {"color": COLORS['caution'], "label": "Caution (0.05-0.1 mg/L)"},
                {"color": COLORS['poor'], "label": "Poor (>0.1 mg/L)"}
            ]
        elif param_name == 'Chloride':
            return [
                {"color": COLORS['normal'], "label": "Normal (<200 mg/L)"},
                {"color": COLORS['caution'], "label": "Caution (200-400 mg/L)"},
                {"color": COLORS['poor'], "label": "Poor (>400 mg/L)"}
            ]
    
    # Biological parameter legends
    elif param_type == 'bio':
        if param_name == 'Fish_IBI':
            return [
                {"color": COLORS['fish']['excellent'], "label": "Excellent (>0.97)"},
                {"color": COLORS['fish']['good'], "label": "Good (0.76-0.97)"},
                {"color": COLORS['fish']['fair'], "label": "Fair (0.60-0.79)"},
                {"color": COLORS['fish']['poor'], "label": "Poor (0.47-0.60)"},
                {"color": COLORS['fish']['very poor'], "label": "Very Poor (<0.47)"}
            ]
        elif param_name == 'Macro_Combined':
            return [
                {"color": COLORS['macro']['non-impaired'], "label": "Non-impaired (>0.83)"},
                {"color": COLORS['macro']['slightly_impaired'], "label": "Slightly Impaired (0.54-0.83)"},
                {"color": COLORS['macro']['moderately_impaired'], "label": "Moderately Impaired (0.17-0.54)"},
                {"color": COLORS['macro']['severely_impaired'], "label": "Severely Impaired (<0.17)"}
            ]
    
    # Habitat parameter legends
    elif param_type == 'habitat':
        return [
            {"color": COLORS['habitat']['a'], "label": "A (>=90)"},
            {"color": COLORS['habitat']['b'], "label": "B (80-89)"},
            {"color": COLORS['habitat']['c'], "label": "C (70-79)"},
            {"color": COLORS['habitat']['d'], "label": "D (60-69)"},
            {"color": COLORS['habitat']['f'], "label": "F (<60)"}
        ]
    
    # Default legend if parameter not found
    return [{"color": "#666", "label": "No data available"}]

def get_site_count_message(param_type, param_name, sites_with_data, total_sites, active_only=False):
    """
    Create custom site count message based on parameter type.
    Used by overview tab for parameter-specific map status messages.
    
    Args:
        param_type: Type of parameter ('chem', 'bio', 'habitat')
        param_name: Specific parameter name
        sites_with_data: Number of sites with data
        total_sites: Total number of sites
        active_only: Whether to include "(active only)" in the message
        
    Returns:
        str: Formatted site count message
    """
    active_text = " (active only)" if active_only else ""
    
    if param_type == 'chem':
        chemical_parameter_labels = {
            'do_percent': 'dissolved oxygen',
            'pH': 'pH',
            'soluble_nitrogen': 'soluble nitrogen',
            'Phosphorus': 'phosphorus',
            'Chloride': 'chloride'
        }
        parameter_label = chemical_parameter_labels.get(param_name, 'chemical')
        return f"Showing {sites_with_data} of {total_sites} monitoring sites{active_text} with {parameter_label} data"
    elif param_type == 'bio':
        if param_name == 'Fish_IBI':
            return f"Showing {sites_with_data} of {total_sites} monitoring sites{active_text} with fish data"
        elif param_name == 'Macro_Combined':
            return f"Showing {sites_with_data} of {total_sites} monitoring sites{active_text} with macroinvertebrate data"
    elif param_type == 'habitat':
        return f"Showing {sites_with_data} of {total_sites} monitoring sites{active_text} with habitat data"
    
    return f"Showing {sites_with_data} of {total_sites} monitoring sites{active_text}"

def create_map_legend_html(legend_items=None, count_message=None, total_count=None, active_only=False, total_sites_count=None):
    """
    Create standardized HTML for map legends in the overview tab.
    Handles both basic maps (no parameter) and parameter-specific maps.
    
    Args:
        legend_items: List of dictionaries with 'color' and 'label' keys (for parameter maps)
        count_message: String message about site counts (for parameter maps)
        total_count: Total number of sites being displayed (for basic maps)
        active_only: Whether showing active sites only (for basic maps)
        total_sites_count: Total number of all sites (for showing "X of Y" format when active_only=True)
        
    Returns:
        Dash HTML component for the legend
    """
    # Basic map case (no parameter selected)
    if legend_items is None and total_count is not None:
        if active_only and total_sites_count is not None:
            count_text = f"Showing {total_count} of {total_sites_count} monitoring sites (active only)"
        else:
            active_text = " (active only)" if active_only else ""
            count_text = f"Showing {total_count} monitoring sites{active_text}"
        
        legend_content = [
            # Site count display
            html.Div(
                count_text,
                className="text-center mb-2",
                style={"font-weight": "bold", "color": "#666"}
            ),
            # Legend items for basic map
            html.Div([
                html.Div([
                    html.Span("●", style={"color": "#3366CC", "font-size": "12px"}),
                    html.Span(" Active Sites", className="mr-3")
                ], style={"display": "inline-block", "margin-right": "15px"}),
                html.Div([
                    html.Span("●", style={"color": "#9370DB", "font-size": "8px"}),
                    html.Span(" Historic Sites", className="mr-3")
                ], style={"display": "inline-block", "margin-right": "15px"})
            ])
        ]
    
    # Parameter-specific map case
    else:
        legend_content = [
            # Site count display
            html.Div(
                count_message,
                className="text-center mb-2",
                style={"font-weight": "bold", "color": "#666"}
            ),
            # Legend items for parameter map
            html.Div([
                html.Div([
                    html.Span("● ", style={"color": item["color"], "font-size": "12px"}),
                    html.Span(item["label"], className="mr-3")
                ], style={"display": "inline-block", "margin-right": "15px"})
                for item in legend_items
            ])
        ]
    
    return html.Div(legend_content, className="text-center mt-2 mb-4")

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
            html.H5(item['name'], className="mt-2"),
            html.P(item['description'], className="mt-1")
        ], style={'min-height': '80px'})
    ], style={'min-height': '400px'})

def create_macro_dual_display(item):
    """
    Create HTML layout for displaying macroinvertebrate larval and adult stages side-by-side.
    
    Args:
        item: Dictionary with species information including larval and adult images/descriptions
        
    Returns:
        Dash HTML component for displaying both life stages
    """
    return html.Div([
        # Image container with side-by-side layout
        html.Div([
            # Larval stage (left side)
            html.Div([
                html.H6("Larval Stage", className="text-center mb-2", style={'fontSize': '14px', 'fontWeight': 'bold'}),
                html.Img(
                    src=item['larval_image'],
                    style={'max-height': '250px', 'object-fit': 'contain', 'max-width': '100%'}
                ),
            ], style={
                'width': '48%', 
                'display': 'inline-block', 
                'vertical-align': 'top',
                'text-align': 'center'
            }),
            
            # Adult stage (right side)  
            html.Div([
                html.H6("Adult Stage", className="text-center mb-2", style={'fontSize': '14px', 'fontWeight': 'bold'}),
                html.Img(
                    src=item['adult_image'],
                    style={'max-height': '250px', 'object-fit': 'contain', 'max-width': '100%'}
                ),
            ], style={
                'width': '48%', 
                'display': 'inline-block', 
                'vertical-align': 'top', 
                'margin-left': '4%',
                'text-align': 'center'
            })
        ], className="create-macro-dual-display", style={
            'height': '300px', 
            'display': 'flex', 
            'align-items': 'center', 
            'justify-content': 'center'
        }),
        
        # Text container with unified description
        html.Div([
            html.H5(item['name'], className="mt-2 text-center"),
            html.P(item['description'], className="mt-1 text-center")
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
            if gallery_type == 'macro':
                return create_macro_dual_display(data[0]), 0
            else:
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
        
        # Create the display for the current item based on gallery type
        if gallery_type == 'macro':
            return create_macro_dual_display(item), new_index
        else:
            return create_species_display(item), new_index
    
    return update_gallery

def create_biological_community_info(selected_community):
    """
    Create community-specific content (description, gallery, interpretation).
    This content only depends on the community type, not the specific site.
    
    Args:
        selected_community: Community type ('fish' or 'macro')
        
    Returns:
        Dash HTML component with community-specific content
    """
    try:
        if not selected_community or selected_community not in ['fish', 'macro']:
            return html.Div()
        
        # Import gallery creation function
        from layouts.helpers import create_species_gallery
        
        # Create community-specific layout
        content = html.Div([
            # Description and gallery row
            dbc.Row([
                # Left column: Description
                dbc.Col([
                    load_markdown_content(f'biological/{selected_community}_description.md', link_target="_blank")
                ], width=6),
                
                # Right column: Species gallery
                dbc.Col([
                    create_species_gallery(selected_community)
                ], width=6, className="d-flex align-items-center"),
            ], className="mb-4"),
            
            # Analysis section
            dbc.Row([
                dbc.Col([
                    load_markdown_content(f"biological/{selected_community}_interpretation.md")
                ], width=12)
            ], className="mb-4"),
        ])
        
        return content
        
    except Exception as e:
        logger.error(f"Error creating biological community info for {selected_community}: {e}")
        return create_error_state(
            f"Error Loading {selected_community.title()} Information",
            f"Could not load {selected_community} community information. Please try again.",
            str(e)
        )

def create_biological_site_display(selected_community, selected_site):
    """
    Create site-specific content (charts and metrics).
    This content depends on both the community type and the specific site.
    
    Args:
        selected_community: Community type ('fish' or 'macro')
        selected_site: Selected site name
        
    Returns:
        Dash HTML component with site-specific visualizations
    """
    try:
        # Import required functions for visualization
        if selected_community == 'fish':
            from visualizations.fish_viz import create_fish_viz, create_fish_metrics_accordion
            from data_processing.data_queries import get_fish_dataframe
            
            # Get site-specific data to check if it exists
            site_data = get_fish_dataframe(selected_site)
            
            if site_data.empty:
                return create_empty_state(f"No fish data available for {selected_site}")
            
            # Create site-specific visualizations
            viz_figure = create_fish_viz(selected_site)
            metrics_accordion = create_fish_metrics_accordion(selected_site)
            
            # Set download button text for fish
            download_text = [html.I(className="fas fa-download me-2"), "Download Fish Data"]
            
        elif selected_community == 'macro':
            from visualizations.macro_viz import create_macro_viz, create_macro_metrics_accordion
            from data_processing.data_queries import get_macroinvertebrate_dataframe
            
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
            
            # Set download button text for macro
            download_text = [html.I(className="fas fa-download me-2"), "Download Macroinvertebrate Data"]
            
        else:
            return create_error_state(
                "Invalid Community Type",
                f"'{selected_community}' is not a valid community type."
            )
            
        # Create site-specific layout (charts and metrics only)
        content = html.Div([
            # Download button row
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        download_text,
                        id="biological-download-btn",
                        color="success",
                        size="sm",
                        style={'display': 'block'}  # Make button visible
                    )
                ], width=12, className="d-flex justify-content-end")
            ]),
            
            # Graph row
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=viz_figure)
                ], width=12)
            ], className="mb-2"),
            
            # Metrics accordion row
            dbc.Row([
                dbc.Col([
                    metrics_accordion
                ], width=12)
            ], className="mb-4"),
        ])
        
        return content
        
    except Exception as e:
        logger.error(f"Error creating biological site display for {selected_community} at {selected_site}: {e}")
        return create_error_state(
            f"Error Loading {selected_community.title()} Data",
            f"Could not load {selected_community} data for {selected_site}. Please try again.",
            str(e)
        )

# ===========================================================================================
# CHEMICAL TAB UTILITIES
# ===========================================================================================
def create_single_parameter_visualization(df_filtered, parameter, reference_values, highlight_thresholds, site_name=None):
    """Create visualization for a single chemical parameter."""
    try:
        if df_filtered.empty or parameter not in df_filtered.columns:
            empty_state = create_empty_state(f"No {parameter} data available for the selected time period.")
            return empty_state, html.Div(), html.Div()
        
        # Import required functions
        from visualizations.chemical_viz import create_time_series_plot
        from layouts.ui_data import CHEMICAL_DIAGRAMS, CHEMICAL_DIAGRAM_CAPTIONS
        from utils import load_markdown_content, create_image_with_caption
        
        # Get parameter name for display
        parameter_name = get_parameter_name(parameter)
        
        # Create the time series plot
        fig = create_time_series_plot(
            df_filtered, 
            parameter, 
            reference_values,
            y_label=get_parameter_label('chem', parameter),
            highlight_thresholds=highlight_thresholds,
            site_name=site_name
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

def create_all_parameters_visualization(df_filtered, key_parameters, reference_values, highlight_thresholds, site_name=None):
    """Create visualization for all chemical parameters."""
    try:
        if df_filtered.empty:
            empty_state = create_empty_state("No data available for the selected time period.")
            return empty_state, html.Div(), html.Div()
        
        # Import the visualization function
        from visualizations.chemical_viz import create_all_parameters_view
        
        # Create the comprehensive figure
        fig = create_all_parameters_view(df_filtered, key_parameters, reference_values, highlight_thresholds, site_name=site_name)
        
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
        import dash_bootstrap_components as dbc
        
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
            ], className="mb-2"),
        ])   
        return display
        
    except Exception as e:
        logger.error(f"Error creating habitat display for {site_name}: {e}")
        return create_error_state(
            "Error Creating Habitat Display",
            f"Could not create habitat visualization for {site_name}.",
            str(e)
        )