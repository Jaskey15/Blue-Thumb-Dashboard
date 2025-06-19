import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
from data_processing.data_queries import get_fish_dataframe, get_fish_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging
from .biological_utils import (
    BIOLOGICAL_COLORS, 
    create_biological_line_plot,
    update_biological_figure_layout,
    add_reference_lines,
    format_biological_metrics_table,
    create_biological_table_styles,
    create_biological_data_table,
    create_hover_text,
    update_hover_data,
    create_empty_biological_figure,
    create_error_biological_figure
)

logger = setup_logging("fish_viz", category="visualization")

# Fish-specific configuration
INTEGRITY_THRESHOLDS = {
    'Excellent': 0.97,
    'Good': 0.76,
    'Fair': 0.60,
    'Poor': 0.47
}

INTEGRITY_COLORS = {
    'Excellent': BIOLOGICAL_COLORS['excellent'],
    'Good': BIOLOGICAL_COLORS['good'],
    'Fair': BIOLOGICAL_COLORS['fair'],
    'Poor': BIOLOGICAL_COLORS['poor']
}

FISH_METRIC_ORDER = [
    'Total No. of species',
    'No. of sensitive benthic species', 
    'No. of sunfish species',
    'No. of intolerant species',
    'Proportion tolerant individuals',
    'Proportion insectivorous cyprinid',
    'Proportion lithophilic spawners'
]

FISH_SUMMARY_LABELS = ['Total Score', 'Comparison to Reference', 'Integrity Class']

def create_fish_viz(site_name=None):
    """
    Create fish community visualization for the app.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing IBI scores over time.
    """
    try:
        # Get fish data from the database
        fish_df = get_fish_dataframe(site_name)
        
        if fish_df.empty:
            return create_empty_biological_figure(site_name, "fish")

        # Create the line plot using shared utilities
        title = f"IBI Scores Over Time for {site_name}" if site_name else "IBI Scores Over Time"
        fig_fish = create_biological_line_plot(
            fish_df, 
            title, 
            y_column='comparison_to_reference',
            has_seasons=False
        )

        # Update layout using shared utilities
        fig_fish = update_biological_figure_layout(
            fig_fish, 
            fish_df, 
            title,
            y_label='IBI Score (Compared to Reference)'
        )

        # Add integrity reference lines
        fig_fish = add_reference_lines(fig_fish, fish_df, INTEGRITY_THRESHOLDS, INTEGRITY_COLORS)

        # Add hover data using shared utilities
        hover_text = create_hover_text(fish_df, has_seasons=False, condition_column='integrity_class')
        fig_fish = update_hover_data(fig_fish, hover_text)

        return fig_fish
    
    except Exception as e:
        logger.error(f"Error creating fish visualization for {site_name}: {e}")
        return create_error_biological_figure(str(e))

def create_fish_metrics_table(metrics_df, summary_df):
    """
    Create a metrics table for fish data.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
    
    Returns:
        Dash DataTable component
    """
    try:
        # Format the data using shared utilities
        metrics_table, summary_rows = format_biological_metrics_table(
            metrics_df, 
            summary_df, 
            FISH_METRIC_ORDER,
            FISH_SUMMARY_LABELS
        )
        
        # Combine metrics and summary rows
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
    
        styles = create_biological_table_styles(metrics_table)
        
        table = create_biological_data_table(full_table, 'fish-metrics-table', styles)
        
        return table
    
    except Exception as e:
        logger.error(f"Error creating fish metrics table: {e}")
        return html.Div(f"Error creating fish metrics table: {str(e)}")

def create_fish_metrics_accordion(site_name=None):
    """
    Create an accordion layout for fish metrics table.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        HTML Div containing accordion component with metrics table
    """
    try:
        # Get the data with site filtering
        metrics_df, summary_df = get_fish_metrics_data_for_table(site_name)
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No data available")
        
        # Get the table component
        table = create_fish_metrics_table(metrics_df, summary_df)
        
        # Use the reusable accordion function
        return create_metrics_accordion(table, "Fish Collection Metrics", "fish-accordion")
    
    except Exception as e:
        logger.error(f"Error creating fish metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")

