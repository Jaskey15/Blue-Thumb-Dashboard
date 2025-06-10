"""
Helper functions for the Tenmile Creek Water Quality Dashboard callbacks.
This file contains reusable helper functions used across different callback modules.
Only shared functionality that is used by multiple tabs is included here.
"""

import dash
import json
from dash import html
from utils import setup_logging
from config.shared_constants import PARAMETER_DISPLAY_NAMES, PARAMETER_AXIS_LABELS

# Configure logging
logger = setup_logging("helper_callbacks", category="callbacks")

# ===========================================================================================
# SEARCH AND SELECTION UTILITIES
# ===========================================================================================

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

def create_search_results(matching_sites, tab_prefix, search_value, max_results=10):
    """
    Create standardized search results with consistent styling across all tabs.
    
    Args:
        matching_sites: List of site names that match the search
        tab_prefix: Prefix for the tab (e.g., 'chemical', 'biological', 'habitat')
        search_value: The search term used (for logging)
        max_results: Maximum number of results to display
        
    Returns:
        tuple: (list of HTML components, dict with display style)
    """
    try:
        if not matching_sites:
            return [html.Div("No sites match your search.", 
                        className="p-2 text-muted")], {'display': 'block'}
        
        # Create clickable list items with consistent styling
        result_items = []
        for site in matching_sites[:max_results]:
            result_items.append(
                html.Div(
                    site,
                    id={'type': f'{tab_prefix}-site-option', 'site': site},
                    style={
                        'padding': '8px 12px',
                        'cursor': 'pointer',
                        'borderBottom': '1px solid #eee'
                    },
                    className="site-option",
                    n_clicks=0
                )
            )
        
        logger.info(f"{tab_prefix.title()} search for '{search_value}' found {len(matching_sites)} sites")
        
        # Consistent dropdown-style results container
        results_style = {
            'display': 'block',
            'position': 'absolute',
            'top': '100%',
            'left': '0',
            'right': '0',
            'backgroundColor': 'white',
            'border': '1px solid #ccc',
            'borderTop': 'none',
            'maxHeight': '200px',
            'overflowY': 'auto',
            'zIndex': '1000',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
        }
        
        return result_items, results_style
        
    except Exception as e:
        logger.error(f"Error creating {tab_prefix} search results: {e}")
        return [html.Div("Error creating search results.", 
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

# ===========================================================================================
# SHARED UI STATE FUNCTIONS
# ===========================================================================================

def create_empty_state(message, min_height='300px'):
    """
    Create a consistent empty state display across all tabs.
    
    Args:
        message: Message to display to the user
        min_height: Minimum height for the container (default: '300px')
        
    Returns:
        Dash HTML component with consistent empty state styling
    """
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
    """
    Create a consistent error state display across all tabs.
    
    Args:
        title: Error title/heading
        message: User-friendly error message
        error_details: Optional technical error details for debugging
        
    Returns:
        Dash HTML component with consistent error state styling
    """
    error_components = [
        html.H4(title, className="text-danger"),
        html.P(message, className="mb-3")
    ]
    
    # Add expandable error details if provided
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
    """
    Create a consistent loading state display across all tabs.
    
    Args:
        message: Loading message to display
        
    Returns:
        Dash HTML component with consistent loading state styling
    """
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
    """
    Create a consistent info state display across all tabs.
    
    Args:
        title: Info title/heading
        message: Informational message
        icon_class: CSS class for the icon (default: info circle)
        
    Returns:
        Dash HTML component with consistent info state styling
    """
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

# ===========================================================================================
# PARAMETER AND LEGEND UTILITIES (USED BY OVERVIEW TAB)
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