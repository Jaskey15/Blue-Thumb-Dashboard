"""
visualization_utils.py - Shared utilities for data visualizations

This module contains helper functions and constants shared between different 
visualization modules (fish, macroinvertebrate, habitat) to ensure consistent 
styling and reduce code duplication.

Key Functions:
- create_line_plot(): Generic line plot creation
- add_reference_lines(): Add threshold reference lines to plots
- format_metrics_table(): Format metrics data into table structure
- create_table_styles(): Consistent table styling
- Helper functions for error handling and data processing
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash import dash_table, html
from utils import setup_logging

logger = setup_logging("visualization_utils", category="visualization")

# Shared styling constants
DEFAULT_COLORS = {
    'Winter': 'blue',
    'Summer': 'red',
    'excellent': 'green',
    'good': 'lightgreen',
    'fair': 'orange',
    'poor': 'red',
    'default': 'blue'
}

FONT_SIZES = {
    'title': 16,
    'axis_title': 14,
    'header': 12,
    'cell': 11
}

def create_line_plot(df, title, y_column='comparison_to_reference', 
                    has_seasons=False, color_map=None):
    """
    Create a generic line plot for data visualizations.
    
    Args:
        df: DataFrame containing the data
        title: Plot title
        y_column: Column name for y-axis data
        has_seasons: Whether to differentiate by season
        color_map: Dictionary mapping colors to categories
    
    Returns:
        Plotly figure object
    """
    try:
        if has_seasons:
            # Create multi-line plot with seasons
            fig = px.line(
                df,
                x='year',
                y=y_column,
                color='season',
                markers=True,
                title=title,
                labels={
                    'year': 'Year',
                    'season': 'Season'
                },
                color_discrete_map=color_map or DEFAULT_COLORS
            )
        else:
            # Create single line plot
            fig = px.line(
                df,
                x='year',
                y=y_column,
                markers=True,
                title=title,
                labels={
                    'year': 'Year',
                    y_column: 'IBI Score (Compared to Reference)' if 'comparison' in y_column else y_column
                }
            )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error creating line plot: {e}")
        return create_error_figure(str(e))

def calculate_dynamic_y_range(df, column='comparison_to_reference'):
    """
    Calculate dynamic y-axis range based on data.
    For biological data (comparison_to_reference): minimum range 0-1.1, expands if needed
    For habitat data (total_score): minimum range 0-100, expands if needed
    
    Args:
        df: DataFrame containing the data
        column: Column name to calculate range for
    
    Returns:
        Tuple of (y_min, y_max)
    """
    try:
        if df.empty or column not in df.columns:
            # Return appropriate default based on column type
            if column == 'total_score':
                return 0, 110  # Habitat default
            else:
                return 0, 1.1  # Biological default
        
        max_value = df[column].max()
        
        # Use different minimum ranges based on data type
        if column == 'total_score':
            # Habitat data: minimum range 0-100, expand if data exceeds ~90
            y_upper_limit = max(110, max_value * 1.1)
        else:
            # Biological data: minimum range 0-1.1, expand if data exceeds ~1.0
            y_upper_limit = max(1.1, max_value * 1.1)
        
        return 0, y_upper_limit
    
    except Exception as e:
        logger.warning(f"Error calculating y-range: {e}")
        if column == 'total_score':
            return 0, 110
        else:
            return 0, 1.1


def update_figure_layout(fig, df, title, y_label=None, y_column='comparison_to_reference', tick_format='.2f'):
    """
    Apply common layout settings to figures.
    
    Args:
        fig: Plotly figure to update
        df: DataFrame containing the data
        title: Plot title
        y_label: Custom y-axis label
        y_column: Column name to use for y-range calculation
        tick_format: Format string for y-axis ticks (default: '.2f')
    
    Returns:
        Updated figure
    """
    try:
        if df.empty:
            return fig
        
        # Calculate y-range using the specified column
        y_min, y_max = calculate_dynamic_y_range(df, column=y_column)
        
        # Get unique years for x-axis
        years = sorted(df['year'].unique()) if 'year' in df.columns else []
        
        # Update layout
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=years,
                title_font=dict(size=FONT_SIZES['axis_title'])
            ),
            yaxis=dict(
                range=[y_min, y_max],
                tickformat=tick_format,
                title_font=dict(size=FONT_SIZES['axis_title']),
                title=y_label
            ),
            title_x=0.5,
            title_font=dict(size=FONT_SIZES['title']),
            hovermode='closest'
        )
        
        # Add legend title if seasons exist
        if any('season' in trace.name.lower() for trace in fig.data if hasattr(trace, 'name') and trace.name):
            fig.update_layout(legend_title_text='Season')
        
        return fig
    
    except Exception as e:
        logger.error(f"Error updating figure layout: {e}")
        return fig

def add_reference_lines(fig, df, thresholds, line_colors=None):
    """
    Add reference lines for threshold values to the figure.
    
    Args:
        fig: Plotly figure to add reference lines to
        df: DataFrame containing the data with year values
        thresholds: Dictionary of {label: threshold_value}
        line_colors: Dictionary of {label: color} for line colors
    
    Returns:
        Updated figure with reference lines
    """
    try:
        if df.empty or not thresholds:
            return fig
        
        # Get min and max year for reference lines
        x_min = df['year'].min() - 1 if 'year' in df.columns else 0
        x_max = df['year'].max() + 1 if 'year' in df.columns else 10
        
        # Add reference lines for each threshold
        for label, threshold in thresholds.items():
            color = 'gray'
            if line_colors and label in line_colors:
                color = line_colors[label]
            elif label.lower() in DEFAULT_COLORS:
                color = DEFAULT_COLORS[label.lower()]
            
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
                x=x_min - 0.5,
                y=threshold,
                text=label,
                showarrow=False,
                yshift=10
            )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error adding reference lines: {e}")
        return fig

def format_metrics_table(metrics_df, summary_df, metric_order, 
                        summary_labels=None, season=None):
    """
    Format metrics data into a table structure.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
        metric_order: List of metrics in display order
        summary_labels: List of summary row labels
        season: Optional season to filter data for
    
    Returns:
        Tuple of (metrics_table, summary_rows) DataFrames
    """
    try:
        if metrics_df.empty or summary_df.empty:
            return pd.DataFrame({'Metric': metric_order}), pd.DataFrame({'Metric': ['No Data']})
        
        # Filter by season if specified
        if season:
            if 'season' in metrics_df.columns:
                metrics_df = metrics_df[metrics_df['season'] == season]
            if 'season' in summary_df.columns:
                summary_df = summary_df[summary_df['season'] == season]
        
        # Get unique years
        years = sorted(metrics_df['year'].unique()) if not metrics_df.empty else []
        
        # Create table data dictionary
        table_data = {'Metric': metric_order}
        
        # Add columns for each year
        for year in years:
            year_metrics = metrics_df[metrics_df['year'] == year]
            
            # Add scores for this year
            scores = []
            for metric in metric_order:
                metric_row = year_metrics[year_metrics['metric_name'] == metric]
                if not metric_row.empty:
                    try:
                        # Handle different column names for score values
                        if 'metric_score' in metric_row.columns:
                            score_value = metric_row['metric_score'].values[0]
                        elif 'score' in metric_row.columns:
                            score_value = metric_row['score'].values[0]
                        else:
                            logger.warning(f"No score column found for metric {metric}")
                            scores.append('-')
                            continue
                        
                        # Round to 1 decimal place for habitat scores, int for others
                        if isinstance(score_value, float) and score_value != int(score_value):
                            scores.append(round(score_value, 1))
                        else:
                            scores.append(int(score_value))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert metric score to number: {score_value}, error: {e}")
                        scores.append('-')
                else:
                    scores.append('-')
            
            table_data[str(year)] = scores
        
        # Create metrics table
        metrics_table = pd.DataFrame(table_data)
        
        # Create summary rows
        default_summary_labels = ['Total Score', 'Comparison to Reference', 'Condition']
        summary_labels = summary_labels or default_summary_labels
        summary_rows = pd.DataFrame({'Metric': summary_labels})
        
        # Add summary data for each year
        for year in years:
            year_summary = summary_df[summary_df['year'] == year]
            if not year_summary.empty:
                try:
                    total_score = int(year_summary['total_score'].values[0])
                    
                    # Create summary row data based on available columns
                    summary_data = [total_score]
                    
                    # Add comparison to reference if available (fish/macro data)
                    if 'comparison_to_reference' in year_summary.columns:
                        comparison = f"{year_summary['comparison_to_reference'].values[0]:.2f}"
                        summary_data.append(comparison)
                        
                        # Get condition/integrity class
                        condition = 'Unknown'
                        if 'biological_condition' in year_summary.columns:
                            condition = year_summary['biological_condition'].values[0]
                        elif 'integrity_class' in year_summary.columns:
                            condition = year_summary['integrity_class'].values[0]
                        summary_data.append(condition)
                    
                    # Handle habitat data (has habitat_grade instead of comparison)
                    elif 'habitat_grade' in year_summary.columns:
                        habitat_grade = year_summary['habitat_grade'].values[0]
                        summary_data.append(habitat_grade)
                    
                    # Fill remaining positions if summary_labels has more items
                    while len(summary_data) < len(summary_labels):
                        summary_data.append('-')
                    
                    summary_rows[str(year)] = summary_data
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing summary data for year {year}: {e}")
                    summary_rows[str(year)] = ['-'] * len(summary_labels)
            else:
                summary_rows[str(year)] = ['-'] * len(summary_labels)
        
        return metrics_table, summary_rows
    
    except Exception as e:
        logger.error(f"Error formatting metrics table: {e}")
        return pd.DataFrame({'Metric': metric_order}), pd.DataFrame({'Metric': ['Error']})

def create_table_styles(metrics_table):
    """
    Create consistent styling for metrics tables.
    
    Args:
        metrics_table: DataFrame with the metrics rows (used for row indexing)
    
    Returns:
        Dictionary of style configurations for the table
    """
    return {
        'style_table': {
            'maxWidth': '100%',
            'overflowX': 'auto'
        },
        'style_header': {
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'fontSize': FONT_SIZES['header']
        },
        'style_cell': {
            'textAlign': 'center',
            'padding': '5px',
            'fontFamily': 'Arial',
            'fontSize': FONT_SIZES['cell'],
            'minWidth': '50px',
            'maxWidth': '150px'
        },
        'style_cell_conditional': [
            {
                'if': {'column_id': 'Metric'},
                'textAlign': 'left',
                'fontWeight': 'bold'
            }
        ],
        'style_data_conditional': [
            {
                'if': {'row_index': len(metrics_table)},
                'borderTop': '2px solid black',
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': len(metrics_table) + 1},
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': len(metrics_table) + 2},
                'fontWeight': 'bold'
            }
        ]
    }

def create_data_table(full_table, table_id, styles):
    """
    Create a standardized DataTable component for data.
    
    Args:
        full_table: DataFrame containing the table data
        table_id: Unique ID for the table
        styles: Style dictionary from create_table_styles()
    
    Returns:
        Dash DataTable component
    """
    try:
        return dash_table.DataTable(
            id=table_id,
            columns=[{"name": col, "id": col} for col in full_table.columns],
            data=full_table.to_dict('records'),
            **styles
        )
    except Exception as e:
        logger.error(f"Error creating data table: {e}")
        return html.Div(f"Error creating table: {str(e)}")

def create_hover_text(df, has_seasons=False, condition_column='biological_condition'):
    """
    Generate hover text for plots.
    
    Args:
        df: DataFrame containing the data
        has_seasons: Whether data includes seasons
        condition_column: Column name containing condition/integrity class
    
    Returns:
        List of hover text strings
    """
    try:
        hover_text = []
        for _, row in df.iterrows():
            condition = row.get(condition_column, 'Unknown')
            
            if has_seasons:
                text = f"<b>Year</b>: {row['year']}<br><b>Season</b>: {row['season']}<br><b>Score</b>: {row['comparison_to_reference']}<br><b>Condition</b>: {condition}"
            else:
                text = f"<b>Year</b>: {row['year']}<br><b>Score</b>: {row['comparison_to_reference']}<br><b>Condition</b>: {condition}"
            
            hover_text.append(text)
        
        return hover_text
    
    except Exception as e:
        logger.error(f"Error creating hover text: {e}")
        return []

def update_hover_data(fig, hover_text):
    """
    Update figure traces with hover data.
    
    Args:
        fig: Plotly figure to update
        hover_text: List of hover text strings or dict for multi-trace
    
    Returns:
        Updated figure
    """
    try:
        if isinstance(hover_text, list):
            # Single trace
            fig.update_traces(
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
                hoverinfo='text'
            )
        elif isinstance(hover_text, dict):
            # Multiple traces (seasons)
            for i, trace in enumerate(fig.data):
                if trace.name in hover_text:
                    trace.update(
                        text=hover_text[trace.name],
                        hovertemplate='%{text}<extra></extra>',
                        hoverinfo='text'
                    )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error updating hover data: {e}")
        return fig

def create_empty_figure(site_name=None, data_type="data"):
    """
    Create an empty figure with appropriate message.
    
    Args:
        site_name: Optional site name
        data_type: Type of data
    
    Returns:
        Empty Plotly figure with message
    """
    fig = go.Figure()
    site_msg = f" for {site_name}" if site_name else ""
    fig.update_layout(
        title=f"No {data_type} data available{site_msg}",
        annotations=[dict(
            text="No data available",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5
        )]
    )
    return fig

def create_error_figure(error_message):
    """
    Create an error figure with error message.
    
    Args:
        error_message: Error message to display
    
    Returns:
        Plotly figure with error message
    """
    fig = go.Figure()
    fig.update_layout(
        title="Error creating visualization",
        annotations=[dict(
            text=f"Error: {error_message}",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5
        )]
    )
    return fig 