"""
Utility functions for the Tenmile Creek Water Quality Dashboard.
This module contains reusable helper functions used across the dashboard.
"""

import dash_bootstrap_components as dbc
import os
import traceback
from dash import html, dcc

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

# Cache configuration constants
CACHE_EXPIRATION_HOURS = 1

def setup_logging(module_name, category="general"):
    """
    Configure logging to use the logs directory with component-specific log file.
    
    Args:
        module_name: Name of the module (used for log file name)
        category: Category subfolder for organizing logs (default: "general")
    """
    import os
    import logging
    
    # Find project root by looking for app.py
    def find_project_root():
        current_dir = os.getcwd()
        max_levels = 5
        
        for _ in range(max_levels):
            if os.path.exists(os.path.join(current_dir, 'app.py')):
                return current_dir
            
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # Reached system root
                break
            current_dir = parent_dir
        
        raise FileNotFoundError(
            f"Could not find project root (app.py) within {max_levels} parent directories. "
            f"Make sure app.py exists in your project root."
        )
    
    # Get project root and create logs directory structure
    project_root = find_project_root()
    logs_dir = os.path.join(project_root, 'logs', category)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log file path
    log_file = os.path.join(logs_dir, f"{module_name}.log")
    
    # Get or create logger for this module
    logger = logging.getLogger(module_name)
    
    # Clear any existing handlers for this specific logger
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    
    # Prevent propagation to root logger to avoid conflicts
    logger.propagate = False
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler  
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

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
    
def get_sites_with_data(data_type):
    """
    Get a list of site names that have data for the specified data type.
    
    Args:
        data_type: 'chemical', 'fish', 'macro', or 'habitat'
    
    Returns:
        List of site names that have data for the specified type
    """
    from database.database import get_connection, close_connection
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Define queries for each data type
        queries = {
            'chemical': """
                SELECT DISTINCT s.site_name 
                FROM sites s
                JOIN chemical_collection_events c ON s.site_id = c.site_id
                JOIN chemical_measurements m ON c.event_id = m.event_id
                ORDER BY s.site_name
            """,
            'fish': """
                SELECT DISTINCT s.site_name 
                FROM sites s
                JOIN fish_collection_events f ON s.site_id = f.site_id
                JOIN fish_summary_scores fs ON f.event_id = fs.event_id
                ORDER BY s.site_name
            """,
            'macro': """
                SELECT DISTINCT s.site_name 
                FROM sites s
                JOIN macro_collection_events m ON s.site_id = m.site_id
                JOIN macro_summary_scores ms ON m.event_id = ms.event_id
                ORDER BY s.site_name
            """,
            'habitat': """
                SELECT DISTINCT s.site_name 
                FROM sites s
                JOIN habitat_assessments h ON s.site_id = h.site_id
                JOIN habitat_summary_scores hs ON h.assessment_id = hs.assessment_id
                ORDER BY s.site_name
            """
        }
        
        if data_type not in queries:
            logger.error(f"Unknown data type: {data_type}")
            return []
        
        cursor.execute(queries[data_type])
        sites = [row[0] for row in cursor.fetchall()]
        
        logger.debug(f"Found {len(sites)} sites with {data_type} data")
        return sites
        
    except Exception as e:
        logger.error(f"Error getting sites with {data_type} data: {e}")
        return []
        
    finally:
        if conn:
            close_connection(conn)
    
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