"""
Tab-specific visualization and UI components for data exploration.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from layouts.ui_data import FISH_DATA, MACRO_DATA
from utils import setup_logging, load_markdown_content
from .helper_functions import create_empty_state, create_error_state, get_parameter_name, get_parameter_label
from visualizations.map_viz import COLORS

logger = setup_logging("tab_utilities", category="callbacks")

# ===========================================================================================
# OVERVIEW TAB UTILITIES
# ===========================================================================================

def get_parameter_legend(param_type, param_name):
    """
    Define color-coded ranges for parameter visualization.
    
    Maps parameter values to meaningful color ranges based on:
    - Chemical: Normal, Caution, Poor ranges
    - Biological: Impairment levels
    - Habitat: Quality assessment scores
    """
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
    """Generate status message showing data coverage for selected parameter."""
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
    """Create consistent map legend with site counts and parameter ranges."""
    if legend_items is None and total_count is not None:
        if active_only and total_sites_count is not None:
            count_text = f"Showing {total_count} of {total_sites_count} monitoring sites (active only)"
        else:
            active_text = " (active only)" if active_only else ""
            count_text = f"Showing {total_count} monitoring sites{active_text}"
        
        legend_content = [
            html.Div(
                count_text,
                className="text-center mb-2",
                style={"font-weight": "bold", "color": "#666"}
            ),
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
    else:
        legend_content = [
            html.Div(
                count_message,
                className="text-center mb-2",
                style={"font-weight": "bold", "color": "#666"}
            ),
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
    """Create standardized species card with image and description."""
    return html.Div([
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
        html.Div([
            html.H5(item['name'], className="mt-2"),
            html.P(item['description'], className="mt-1")
        ], style={'min-height': '80px'})
    ], style={'min-height': '400px'})

def create_macro_dual_display(item):
    """Create side-by-side comparison of larval and adult stages."""
    return html.Div([
        html.Div([
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
        
        html.Div([
            html.H5(item['name'], className="mt-2 text-center"),
            html.P(item['description'], className="mt-1 text-center")
        ], style={'min-height': '80px'})
    ], style={'min-height': '400px'})

def create_gallery_navigation_callback(gallery_type):
    """Enable circular navigation through species galleries."""
    data = FISH_DATA if gallery_type == 'fish' else MACRO_DATA
    
    def update_gallery(prev_clicks, next_clicks, current_index):
        """Update gallery display based on navigation button clicks."""
        ctx = dash.callback_context
        
        if not ctx.triggered:
            if gallery_type == 'macro':
                return create_macro_dual_display(data[0]), 0
            else:
                return create_species_display(data[0]), 0
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if f'prev-{gallery_type}-button' in button_id:
            new_index = (current_index - 1) % len(data)
        else:
            new_index = (current_index + 1) % len(data)
        
        item = data[new_index]
        
        if gallery_type == 'macro':
            return create_macro_dual_display(item), new_index
        else:
            return create_species_display(item), new_index
    
    return update_gallery

def create_biological_community_info(selected_community):
    """Display community overview with species gallery and interpretation."""
    try:
        if not selected_community or selected_community not in ['fish', 'macro']:
            return html.Div()
        
        from layouts.helpers import create_species_gallery
        
        content = html.Div([
            dbc.Row([
                dbc.Col([
                    load_markdown_content(f'biological/{selected_community}_description.md', link_target="_blank")
                ], width=6),
                
                dbc.Col([
                    create_species_gallery(selected_community)
                ], width=6, className="d-flex align-items-center"),
            ], className="mb-4"),
            
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
    """Generate site-specific biological metrics and visualizations."""
    try:
        if selected_community == 'fish':
            from visualizations.fish_viz import create_fish_viz, create_fish_metrics_accordion
            from data_processing.data_queries import get_fish_dataframe
            
            site_data = get_fish_dataframe(selected_site)
            
            if site_data.empty:
                return create_empty_state(f"No fish data available for {selected_site}")
            
            viz_figure = create_fish_viz(selected_site)
            metrics_accordion = create_fish_metrics_accordion(selected_site)
            
            download_text = [html.I(className="fas fa-download me-2"), "Download Fish Data"]
            
        elif selected_community == 'macro':
            from visualizations.macro_viz import create_macro_viz, create_macro_metrics_accordion
            from data_processing.data_queries import get_macroinvertebrate_dataframe
            
            all_macro_data = get_macroinvertebrate_dataframe()
            
            if all_macro_data.empty:
                return create_empty_state("No macroinvertebrate data available in database")
            
            site_data = all_macro_data[all_macro_data['site_name'] == selected_site]
            
            if site_data.empty:
                return create_empty_state(f"No macroinvertebrate data available for {selected_site}")
            
            viz_figure = create_macro_viz(selected_site)
            metrics_accordion = create_macro_metrics_accordion(selected_site)
            
            download_text = [html.I(className="fas fa-download me-2"), "Download Macroinvertebrate Data"]
            
        else:
            return create_error_state(
                "Invalid Community Type",
                f"'{selected_community}' is not a valid community type."
            )
            
        content = html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        download_text,
                        id="biological-download-btn",
                        color="success",
                        size="sm",
                        style={'display': 'block'}
                    )
                ], width=12, className="d-flex justify-content-end")
            ]),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=viz_figure)
                ], width=12)
            ], className="mb-2"),
            
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
    """Create focused view of a single chemical parameter's trends."""
    try:
        if df_filtered.empty or parameter not in df_filtered.columns:
            empty_state = create_empty_state(f"No {parameter} data available for the selected time period.")
            return empty_state, html.Div(), html.Div()
        
        from visualizations.chemical_viz import create_time_series_plot
        from layouts.ui_data import CHEMICAL_DIAGRAMS, CHEMICAL_DIAGRAM_CAPTIONS
        from utils import load_markdown_content, create_image_with_caption
        
        parameter_name = get_parameter_name(parameter)
        
        fig = create_time_series_plot(
            df_filtered, 
            parameter, 
            reference_values,
            y_label=get_parameter_label('chem', parameter),
            highlight_thresholds=highlight_thresholds,
            site_name=site_name
        )
        
        graph = dcc.Graph(
            figure=fig,
            style={'height': '450px'}
        )
        
        file_path = f"chemical/{parameter_name.lower().replace(' ', '_')}.md"
        explanation = load_markdown_content(file_path)
        
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
    """Create comprehensive view of all chemical parameters."""
    try:
        if df_filtered.empty:
            empty_state = create_empty_state("No data available for the selected time period.")
            return empty_state, html.Div(), html.Div()
        
        from visualizations.chemical_viz import create_all_parameters_view
        
        fig = create_all_parameters_view(df_filtered, key_parameters, reference_values, highlight_thresholds, site_name=site_name)
        
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
    """Generate habitat assessment visualization and metrics."""
    try:
        from visualizations.habitat_viz import create_habitat_viz, create_habitat_metrics_accordion
        import dash_bootstrap_components as dbc
        
        habitat_fig = create_habitat_viz(site_name)
        habitat_accordion = create_habitat_metrics_accordion(site_name)
        
        display = html.Div([
            dcc.Graph(
                figure=habitat_fig,
                config={'displayModeBar': False},
                style={'height': '500px'}
            ),
            
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