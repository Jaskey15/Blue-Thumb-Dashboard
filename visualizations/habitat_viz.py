"""
habitat_viz.py - Habitat Assessment Data Visualization

This module creates visualizations for habitat assessment data including line charts 
with grade threshold reference lines and data tables for Blue Thumb stream assessments.

Key Functions:
- create_habitat_viz(): Create line chart with habitat grade threshold lines
- create_habitat_table(): Create data table for habitat metrics
- create_habitat_metrics_accordion(): Create accordion layout for habitat metrics

Usage:
- Import functions for use in the main dashboard
- Habitat grades: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
"""

import os
import pandas as pd

from dash import html, dash_table
from data_processing.data_queries import get_habitat_dataframe, get_habitat_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging
from .visualization_utils import (
    create_line_plot,
    update_figure_layout,
    add_reference_lines,
    format_metrics_table,
    create_table_styles,
    create_data_table,
    update_hover_data,
    create_empty_figure,
    create_error_figure,
)

logger = setup_logging("habitat_viz", category="visualization")

# Habitat-specific configuration
HABITAT_GRADE_THRESHOLDS = {
    'A': 90,
    'B': 80,
    'C': 70,
    'D': 60
    # F is anything below 60
}

HABITAT_GRADE_COLORS = {
    'A': '#1e8449',    # Green (A grade)
    'B': '#7cb342',    # Light green (B grade)
    'C': '#ff9800',    # Orange (C grade)
    'D': '#e53e3e',    # Red-orange (D grade)
    'F': '#e74c3c'     # Red (F grade)
}

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
    Create habitat assessment visualization for the app.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing habitat scores over time with grade threshold lines.
    """
    try:
        # Get habitat data from the database
        habitat_df = get_habitat_dataframe(site_name)
        
        if habitat_df.empty:
            return create_empty_figure(site_name, "habitat")

        # Create the line plot using shared utilities
        title = f'Habitat Assessment Scores Over Time for {site_name}' if site_name else 'Habitat Assessment Scores Over Time'
        fig = create_line_plot(
            habitat_df, 
            title, 
            y_column='total_score',
            has_seasons=False
        )

        # Update layout using shared utilities
        fig = update_figure_layout(
            fig, 
            habitat_df, 
            title,
            y_label='Habitat Assessment Score',
            y_column='total_score'
        )

        # Add habitat grade reference lines using shared utilities
        fig = add_reference_lines(fig, habitat_df, HABITAT_GRADE_THRESHOLDS, HABITAT_GRADE_COLORS)

        # Create custom hover text for habitat data
        hover_text = []
        for _, row in habitat_df.iterrows():
            grade = row.get('habitat_grade', 'Unknown')
            hover_text.append(f"<b>Year</b>: {row['year']}<br><b>Score</b>: {int(row['total_score'])}<br><b>Grade</b>: {grade}")
        
        # Update hover data using shared utilities
        fig = update_hover_data(fig, hover_text)

        return fig
        
    except Exception as e:
        logger.error(f"Error creating habitat visualization: {e}")
        return create_error_figure(str(e))

def create_habitat_metrics_table(metrics_df, summary_df):
    """
    Create a metrics table for habitat data.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
    
    Returns:
        Dash DataTable component
    """
    try:
        # Format the data using shared utilities
        metrics_table, summary_rows = format_metrics_table(
            metrics_df, 
            summary_df, 
            HABITAT_METRIC_ORDER,
            HABITAT_SUMMARY_LABELS
        )
        
        # Combine metrics and summary rows
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
    
        styles = create_table_styles(metrics_table)
        
        table = create_data_table(full_table, 'habitat-metrics-table', styles)
        
        # Override specific style for habitat table if needed
        if isinstance(table, dash_table.DataTable):
            table.style_table.update({'height': '500px'})  # Match the height of the graph
        
        return table
    
    except Exception as e:
        logger.error(f"Error creating habitat metrics table: {e}")
        return html.Div(f"Error creating habitat metrics table: {str(e)}")

def create_habitat_metrics_accordion(site_name=None):
    """
    Create an accordion layout for habitat metrics table.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        HTML Div containing accordion component with metrics table
    """
    try:
        # Get the data with site filtering from database
        metrics_df, summary_df = get_habitat_metrics_data_for_table(site_name)
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No habitat assessment data available")
        
        # Get the table component
        table = create_habitat_metrics_table(metrics_df, summary_df)
        
        # Use the reusable accordion function
        return create_metrics_accordion(table, "Habitat Assessment Metrics", "habitat-accordion")
    
    except Exception as e:
        logger.error(f"Error creating habitat metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")
