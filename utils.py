"""
Utility functions for the Tenmile Creek Water Quality Dashboard.
This module contains reusable helper functions used across the dashboard.
"""

import os
import traceback
import logging
from dash import html, dcc
import dash_bootstrap_components as dbc

# Configure logger
logger = logging.getLogger(__name__)

# Common style configurations
CAPTION_STYLE = {
    'font-style': 'italic',
    'color': '#666',
    'font-size': '0.9rem',
    'margin-top': '0.5rem',
    'text-align': 'center'
}

DEFAULT_IMAGE_STYLE = {
    'width': '100%',
    'max-width': '100%',
    'height': 'auto'
}

def load_markdown_content(filename, fallback_message=None):
    """
    Load content from a markdown file and convert it to Dash components.
    
    Args:
        filename: Path to the markdown file relative to the text directory
        fallback_message: Optional custom message to display if loading fails
        
    Returns:
        Dash component with the markdown content
    """
    try:
        base_dir = os.path.dirname(__file__) 
        file_path = os.path.join(base_dir, 'text', filename)  

        # Check if file exists before attempting to open it
        if not os.path.exists(file_path):
            error_msg = f"Markdown file not found: {file_path}"
            logger.error(error_msg)
            return html.Div(
                fallback_message or f"Content not available: {filename}",
                className="alert alert-warning"
            )

        # Read and convert the markdown content
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        return html.Div([
            dcc.Markdown(content)
        ], className="markdown-content")
    
    except Exception as e:
        error_msg = f"Error loading content from {filename}: {e}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        
        return html.Div(
            fallback_message or f"Error loading content: {str(e)}",
            className="alert alert-danger"
        )
    
def create_metrics_accordion(table_component, title, accordion_id):
    """
    Create an accordion layout for a metrics table.
    
    Args:
        table_component: The table to display inside the accordion
        title: The title to display for the accordion item
        accordion_id: A unique ID for the accordion component
        
    Returns:
        A Dash accordion component
    """
    try:
        accordion = html.Div([
            dbc.Accordion([
                dbc.AccordionItem(
                    # Content - metrics table
                    table_component,
                    title=title,
                ),
            ], start_collapsed=True, id=accordion_id)
        ])
        
        return accordion
    except Exception as e:
        logger.error(f"Error creating accordion {accordion_id}: {e}")
        return html.Div(
            f"Could not create metrics table: {str(e)}",
            className="alert alert-warning"
        )

def create_image_with_caption(src, caption, className="img-fluid", style=None, alt_text=None):
    """
    Create an image with a caption below it.
    
    Args:
        src: Image source URL or path
        caption: Caption text to display below the image
        className: CSS class for the image (default: "img-fluid")
        style: Optional custom style for the image
        alt_text: Alternative text for the image for accessibility
        
    Returns:
        A Div containing the image and caption
    """
    try:
        # Use default style if none provided
        if style is None:
            style = DEFAULT_IMAGE_STYLE.copy()
            
        # Use caption as alt text if none provided
        if alt_text is None:
            alt_text = caption
        
        return html.Div([
            # Image component
            html.Img(
                src=src,
                className=className,
                style=style,
                alt=alt_text
            ),
            # Caption below the image
            html.Figcaption(
                caption,
                style=CAPTION_STYLE
            )
        ], style={'width': '100%', 'margin-bottom': '1rem'})
    
    except Exception as e:
        logger.error(f"Error creating image with caption: {e}")
        return html.Div(
            f"Image could not be loaded: {str(e)}",
            className="alert alert-warning"
        )

def safe_div(a, b, default=0):
    """
    Safely divide two numbers, returning a default value if division by zero.
    
    Args:
        a: Numerator
        b: Denominator
        default: Default value to return if b is zero (default: 0)
        
    Returns:
        Result of a/b or default if b is zero
    """
    try:
        return a / b if b != 0 else default
    except:
        return default

def format_value(value, precision=2, unit=None):
    """
    Format a numerical value with specified precision and optional unit.
    
    Args:
        value: Numerical value to format
        precision: Number of decimal places (default: 2)
        unit: Optional unit to append (e.g., "mg/L")
        
    Returns:
        Formatted string representation of the value
    """
    try:
        if value is None:
            return "N/A"
        
        formatted = f"{float(value):.{precision}f}"
        if unit:
            formatted += f" {unit}"
        
        return formatted
    except:
        return "N/A"