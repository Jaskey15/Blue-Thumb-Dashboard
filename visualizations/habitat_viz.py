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
import plotly.graph_objects as go

from dash import html, dash_table
from data_processing.data_queries import get_habitat_dataframe, get_habitat_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging
from .visualization_utils import (
    DEFAULT_COLORS,
    format_metrics_table,
    create_table_styles,
    create_data_table,
    create_empty_figure,
    create_error_figure,
    calculate_dynamic_y_range,
    FONT_SIZES
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
    Create habitat assessment visualization with date-based plotting and year labels.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing habitat scores over time with actual assessment dates.
    """
    try:
        # Get habitat data from the database
        habitat_df = get_habitat_dataframe(site_name)
        
        if habitat_df.empty:
            return create_empty_figure(site_name, "habitat")

        # Parse assessment dates
        habitat_df['assessment_date'] = pd.to_datetime(habitat_df['assessment_date'])
        habitat_df = habitat_df.sort_values('assessment_date')
        
        # Create figure
        fig = go.Figure()
        
        # Create hover text
        hover_text = []
        for _, row in habitat_df.iterrows():
            text = (f"<b>Assessment Date</b>: {row['assessment_date'].strftime('%Y-%m-%d')}<br>"
                   f"<b>Habitat Score</b>: {int(row['total_score'])}<br>"
                   f"<b>Grade</b>: {row['habitat_grade']}")
            hover_text.append(text)
        
        # Add trace
        fig.add_trace(go.Scatter(
            x=habitat_df['assessment_date'],
            y=habitat_df['total_score'],
            mode='lines+markers',
            name='Habitat Score',
            line=dict(color=DEFAULT_COLORS['default']),
            marker=dict(
                color=DEFAULT_COLORS['default'],
                symbol='circle',
                size=8
            ),
            text=hover_text,
            hovertemplate='%{text}<extra></extra>',
            hoverinfo='text'
        ))
        
        # Set up title
        title = f"Habitat Scores Over Time for {site_name}" if site_name else "Habitat Scores Over Time"
        
        # Calculate y-range using shared utility
        y_min, y_max = calculate_dynamic_y_range(habitat_df, column='total_score')
        
        # Get year range for x-axis ticks
        years = sorted(habitat_df['year'].unique()) if 'year' in habitat_df.columns else []
        
        # Update layout using shared styling constants
        fig.update_layout(
            title=title,
            title_x=0.5,
            title_font=dict(size=FONT_SIZES['title']),
            xaxis=dict(
                title='Year',
                title_font=dict(size=FONT_SIZES['axis_title']),
                tickmode='array',
                tickvals=[pd.Timestamp(f'{year}-01-01') for year in years],
                ticktext=[str(year) for year in years]
            ),
            yaxis=dict(
                title='Habitat Score',
                title_font=dict(size=FONT_SIZES['axis_title']),
                range=[y_min, y_max],
                tickformat='d'
            ),
            hovermode='closest'
        )
        
        # Add habitat grade reference lines (date-aware version)
        if years:
            x_min = pd.Timestamp(f'{min(years)}-01-01')
            x_max = pd.Timestamp(f'{max(years)}-12-31')
            
            for label, threshold in HABITAT_GRADE_THRESHOLDS.items():
                color = HABITAT_GRADE_COLORS.get(label, 'gray')
                
                # Add line
                fig.add_shape(
                    type="line",
                    x0=x_min,
                    y0=threshold,
                    x1=x_max,
                    y1=threshold,
                    line=dict(color=color, width=1, dash="dash"),
                )
                
                # Add annotation
                fig.add_annotation(
                    x=x_min,
                    y=threshold,
                    text=label,
                    showarrow=False,
                    yshift=10,
                    xshift=-20
                )

        return fig
        
    except Exception as e:
        logger.error(f"Error creating habitat visualization for {site_name}: {e}")
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
