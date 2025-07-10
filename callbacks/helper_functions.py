"""
Shared UI components and utilities for consistent user experience across tabs.
"""

from dash import html

from utils import setup_logging

# Initialize callback logging
logger = setup_logging("helper_callbacks", category="callbacks")

# SHARED UI STATE FUNCTIONS

def create_empty_state(message, min_height='300px'):
    """Provide consistent feedback when no data is available to display."""
    return html.Div(
        html.P(message, className="text-center text-muted mt-5"),
        style={
            'minHeight': min_height, 
            'display': 'flex', 
            'alignItems': 'center',
            'justifyContent': 'center'
        }
    )

def create_error_state(title, message, error_details=None):
    """Display user-friendly errors with optional technical details for debugging."""
    error_components = [
        html.H4(title, className="text-danger"),
        html.P(message, className="mb-3")
    ]
    
    if error_details:
        error_components.append(
            html.Details([
                html.Summary("Error Details", className="text-muted"),
                html.Pre(
                    str(error_details), 
                    style={
                        "fontSize": "12px", 
                        "color": "red",
                        "backgroundColor": "#f8f9fa",
                        "padding": "10px",
                        "borderRadius": "4px",
                        "marginTop": "10px"
                    }
                )
            ])
        )
    
    return html.Div(error_components, className="mt-3")

def create_loading_state(message="Loading data..."):
    """Show loading feedback during data fetching and processing."""
    return html.Div([
        html.Div([
            html.I(className="fas fa-spinner fa-spin fa-2x text-primary mb-3"),
            html.P(message, className="text-muted")
        ], className="text-center")
    ], style={
        'minHeight': '300px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center'
    })

def create_info_state(title, message, icon_class="fas fa-info-circle"):
    """Display informational messages and help text to guide users."""
    return html.Div([
        html.Div([
            html.I(className=f"{icon_class} fa-2x text-info mb-3"),
            html.H5(title, className="text-info"),
            html.P(message, className="text-muted")
        ], className="text-center")
    ], style={
        'minHeight': '200px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center'
    })

# PARAMETER AND LEGEND UTILITIES (USED BY OVERVIEW TAB)

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
                {"color": "#e74c3c", "label": "High (>1.5 mg/L)"}
            ]
        elif param_name == 'Phosphorus':
            return [
                {"color": "#1e8449", "label": "Normal (<0.05 mg/L)"},
                {"color": "#ff9800", "label": "Caution (0.05-0.1 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>0.1 mg/L)"}
            ]
        elif param_name == 'Chloride':
            return [
                {"color": "#1e8449", "label": "Normal (<200 mg/L)"},
                {"color": "#ff9800", "label": "Caution (200-400 mg/L)"},
                {"color": "#e74c3c", "label": "Poor (>400 mg/L)"}
            ]
    
    elif param_type == 'bio':
        return [
            {"color": "#1e8449", "label": "Non-impaired (>0.79)"},
            {"color": "#ff9800", "label": "Slightly Impaired (0.60-0.79)"},
            {"color": "#e74c3c", "label": "Moderately Impaired (0.40-0.59)"},
            {"color": "#8b0000", "label": "Severely Impaired (<0.40)"}
        ]
    
    elif param_type == 'habitat':
        return [
            {"color": "#1e8449", "label": "Excellent (16-20)"},
            {"color": "#ff9800", "label": "Good (11-15)"},
            {"color": "#e74c3c", "label": "Fair (6-10)"},
            {"color": "#8b0000", "label": "Poor (0-5)"}
        ]
    
    # Default legend if parameter not found
    return [{"color": "#666", "label": "No data available"}]

