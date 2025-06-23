"""
macro_viz.py - Macroinvertebrate Community Assessment Data Visualization

This module creates visualizations for macroinvertebrate bioassessment data including 
seasonal line charts with biological condition reference lines and data tables for 
Blue Thumb stream monitoring.

Key Functions:
- create_macro_viz(): Create bioassessment score line chart with condition thresholds
- create_macro_metrics_table_for_season(): Create season-specific metrics tables
- create_macro_metrics_accordion(): Create accordion layout for summer/winter metrics

Biological Conditions:
- Non-impaired (0.83+), Slightly Impaired (0.54+), Moderately Impaired (0.17+)
- Supports both Summer and Winter seasonal data
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from dash import dash_table, html
from data_processing.data_queries import get_macroinvertebrate_dataframe, get_macro_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging
from .visualization_utils import (
    DEFAULT_COLORS,
    create_line_plot,
    update_figure_layout,
    add_reference_lines,
    format_metrics_table,
    create_table_styles,
    create_data_table,
    create_hover_text,
    update_hover_data,
    create_empty_figure,
    create_error_figure,
    calculate_dynamic_y_range,
    FONT_SIZES
)

logger = setup_logging("macro_viz", category="visualization")

# Macroinvertebrate-specific configuration
CONDITION_THRESHOLDS = {
    'Non-impaired': 0.83,
    'Slightly Impaired': 0.54,
    'Moderately Impaired': 0.17
}

CONDITION_COLORS = {
    'Non-impaired': 'green',
    'Slightly Impaired': 'orange',
    'Moderately Impaired': 'red'
}

MACRO_METRIC_ORDER = [
    'Taxa Richness',
    'EPT Taxa Richness',
    'EPT Abundance',
    'HBI Score',
    '% Contribution Dominants',
    'Shannon-Weaver'
]

MACRO_SUMMARY_LABELS = ['Total Score', 'Comparison to Reference', 'Biological Condition']

def create_macro_viz(site_name=None):
    """
    Create macroinvertebrate visualization with date-based plotting and seasonal grouping.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing bioassessment scores over time by season.
    """
    try:
        # Get macroinvertebrate data from the database
        macro_df = get_macroinvertebrate_dataframe(site_name)
        
        if macro_df.empty:
            return create_empty_figure(site_name, "macroinvertebrate")

        # Handle missing habitat types
        macro_df['habitat'] = macro_df['habitat'].fillna('Unknown')
        
        # Create figure
        fig = go.Figure()
        
        # Get unique seasons and sort them
        seasons = sorted(macro_df['season'].unique())
        
        # Plot each season as separate trace
        for season in seasons:
            season_data = macro_df[macro_df['season'] == season].copy()
            season_data = season_data.sort_values('collection_date')
            
            # Get color for this season using shared constants
            color = DEFAULT_COLORS.get(season, DEFAULT_COLORS.get('default', 'blue'))
            
            # Create hover text for this season
            hover_text = []
            for _, row in season_data.iterrows():
                text = (f"<b>Collection Date</b>: {row['collection_date'].strftime('%Y-%m-%d')}<br>"
                       f"<b>Season</b>: {row['season']}<br>"
                       f"<b>Habitat Type</b>: {row['habitat']}<br>"
                       f"<b>Bioassessment Score</b>: {row['comparison_to_reference']:.2f}<br>"
                       f"<b>Biological Condition</b>: {row['biological_condition']}")
                hover_text.append(text)
            
            # Add trace for this season
            fig.add_trace(go.Scatter(
                x=season_data['collection_date'],
                y=season_data['comparison_to_reference'],
                mode='lines+markers',
                name=season,
                line=dict(color=color),
                marker=dict(
                    color=color,
                    symbol='circle',
                    size=8
                ),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                hoverinfo='text'
            ))
        
        # Set up title
        title = f"Bioassessment Scores Over Time for {site_name}" if site_name else "Bioassessment Scores Over Time"
        
        # Calculate y-range using shared utility
        y_min, y_max = calculate_dynamic_y_range(macro_df, column='comparison_to_reference')
        
        # Get year range for x-axis ticks
        years = sorted(macro_df['year'].unique()) if 'year' in macro_df.columns else []
        
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
                title='Bioassessment Score<br>(Compared to Reference)',
                title_font=dict(size=FONT_SIZES['axis_title']),
                range=[y_min, y_max],
                tickformat='.2f'
            ),
            hovermode='closest',
            legend_title_text='Season'
        )
        
        # Add condition reference lines (date-aware version for macro plots)
        if years:
            x_min = pd.Timestamp(f'{min(years)}-01-01')
            x_max = pd.Timestamp(f'{max(years)}-12-31')
            
            for label, threshold in CONDITION_THRESHOLDS.items():
                color = CONDITION_COLORS.get(label, 'gray')
                
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
        logger.error(f"Error creating macroinvertebrate visualization for {site_name}: {e}")
        return create_error_figure(str(e))

def create_macro_metrics_table_for_season(metrics_df, summary_df, season):
    """
    Create a metrics table for a specific season.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
        season: Season to filter data for ('Summer' or 'Winter')
    
    Returns:
        Dash DataTable component
    """
    try:
        # Format data for the selected season using shared utilities
        season_metrics, season_summary = format_metrics_table(
            metrics_df, 
            summary_df, 
            MACRO_METRIC_ORDER,
            MACRO_SUMMARY_LABELS,
            season=season
        )
        season_full_table = pd.concat([season_metrics, season_summary], ignore_index=True)
        
        # Get styling using shared utilities
        styles = create_table_styles(season_metrics)
        
        # Create the table component using shared utilities
        table = create_data_table(
            season_full_table, 
            f'{season.lower()}-macro-metrics-table', 
            styles
        )
        
        return table
    
    except Exception as e:
        logger.error(f"Error creating {season} metrics table: {e}")
        return html.Div(f"Error creating {season} metrics table")

def create_macro_metrics_accordion(site_name=None):
    """
    Create an accordion layout for macroinvertebrate metrics tables.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        HTML Div containing accordion components for each season's metrics
    """
    try:
        # Get the data with site filtering
        metrics_df, summary_df = get_macro_metrics_data_for_table()
        
        # Filter by site if specified
        if site_name:
            metrics_df = metrics_df[metrics_df['site_name'] == site_name] if 'site_name' in metrics_df.columns else metrics_df
            summary_df = summary_df[summary_df['site_name'] == site_name] if 'site_name' in summary_df.columns else summary_df
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No data available")
        
        # Create the tables for each season
        summer_table = create_macro_metrics_table_for_season(metrics_df, summary_df, 'Summer')
        winter_table = create_macro_metrics_table_for_season(metrics_df, summary_df, 'Winter')
        
        # Create the accordion layout using the reusable function
        summer_accordion = create_metrics_accordion(summer_table, "Summer Collection Metrics", "summer-accordion")
        winter_accordion = create_metrics_accordion(winter_table, "Winter Collection Metrics", "winter-accordion")
        
        # Return both accordions in a div
        return html.Div([summer_accordion, winter_accordion])
    
    except Exception as e:
        logger.error(f"Error creating metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")

