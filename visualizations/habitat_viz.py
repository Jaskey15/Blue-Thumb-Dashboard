"""
Habitat assessment visualization with grade-based thresholds and metrics display.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import html

from data_processing.data_queries import (
    get_habitat_dataframe,
    get_habitat_metrics_data_for_table,
)
from utils import create_metrics_accordion, setup_logging

from .visualization_utils import (
    DEFAULT_COLORS,
    add_reference_lines,
    create_data_table,
    create_empty_figure,
    create_error_figure,
    create_table_styles,
    create_trace,
    format_metrics_table,
    update_layout,
)

logger = setup_logging("habitat_viz", category="visualization")

HABITAT_GRADE_THRESHOLDS = {
    'A': 90,
    'B': 80,
    'C': 70,
    'D': 60
}

HABITAT_GRADE_COLORS = {
    'A': '#1e8449',    # Dark green for excellent
    'B': '#7cb342',    # Light green for good
    'C': '#ff9800',    # Orange for fair
    'D': '#e53e3e',    # Red-orange for poor
    'F': '#e74c3c'     # Red for failing
}

# Preserve metric order for consistent table display
HABITAT_METRIC_ORDER = [
    'Instream Cover',
    'Pool Bottom Substrate',
    'Pool Variability',
    'Canopy Cover',
    'Rocky Runs Riffles',
    'Flow',
    'Channel Alteration',
    'Channel Sinuosity',
    'Bank Stability',
    'Bank Vegetation Stability',
    'Streamside Cover'
]

HABITAT_SUMMARY_LABELS = ['Total Points', 'Habitat Grade']

def create_habitat_viz(site_name=None):
    """
    Generate habitat assessment visualization with grade thresholds.
    """
    try:
        habitat_df = get_habitat_dataframe(site_name)
        
        if habitat_df.empty:
            return create_empty_figure(site_name, "habitat")

        fig = go.Figure()
        
        hover_fields = {
            'Assessment Date': 'assessment_date',
            'Habitat Score': 'total_score',
            'Grade': 'habitat_grade'
        }

        trace = create_trace(
            habitat_df,
            date_column='assessment_date',
            y_column='total_score',
            name='Habitat Score',
            color=DEFAULT_COLORS['default'],
            hover_fields=hover_fields
        )
        
        fig.add_trace(trace)
        
        title = f"Habitat Scores Over Time for {site_name}" if site_name else "Habitat Scores Over Time"
        
        fig = update_layout(
            fig,
            habitat_df,
            title,
            y_label='Habitat Score',
            y_column='total_score',
            tick_format='d',
            has_legend=False
        )
        
        fig = add_reference_lines(fig, habitat_df, HABITAT_GRADE_THRESHOLDS, HABITAT_GRADE_COLORS)

        return fig
        
    except Exception as e:
        logger.error(f"Error creating habitat visualization for {site_name}: {e}")
        return create_error_figure(str(e))

def create_habitat_metrics_table(metrics_df, summary_df):
    """
    Create metrics table showing habitat assessment details.
    """
    try:
        metrics_table, summary_rows = format_metrics_table(
            metrics_df, 
            summary_df, 
            HABITAT_METRIC_ORDER,
            HABITAT_SUMMARY_LABELS
        )
        
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
    
        styles = create_table_styles(metrics_table)
        
        table = create_data_table(full_table, 'habitat-metrics-table', styles)
        
        return table
    
    except Exception as e:
        logger.error(f"Error creating habitat metrics table: {e}")
        return html.Div(f"Error creating habitat metrics table: {str(e)}")

def create_habitat_metrics_accordion(site_name=None):
    """
    Create collapsible view of habitat metrics.
    """
    try:
        metrics_df, summary_df = get_habitat_metrics_data_for_table(site_name)
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No habitat assessment data available")

        table = create_habitat_metrics_table(metrics_df, summary_df)

        return create_metrics_accordion(table, "Habitat Assessment Metrics", "habitat-accordion")
    
    except Exception as e:
        logger.error(f"Error creating habitat metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")
