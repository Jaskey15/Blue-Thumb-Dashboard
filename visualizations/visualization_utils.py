"""
visualization_utils.py - Shared utilities for data visualizations

This module contains helper functions and constants shared between different 
visualization modules (fish, macroinvertebrate, habitat) to ensure consistent 
styling and reduce code duplication.

Functions organized by purpose:
- Core Visualization Functions: Primary chart creation utilities
- Data Processing & Formatting: Data manipulation for visualization
- Table & UI Components: Metrics table creation and styling
- Error Handling & Fallbacks: Graceful error handling
- Constants & Configuration: Shared styling and configuration
"""

import plotly.graph_objects as go
import pandas as pd
from dash import dash_table, html
from utils import setup_logging

logger = setup_logging("visualization_utils", category="visualization")

# =============================================================================
# Constants & Configuration
# =============================================================================

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

# =============================================================================
# Core Visualization Functions
# =============================================================================

def add_reference_lines(fig, df, thresholds, colors=None):
    """
    Add reference lines for threshold values to visualizations.
    
    Args:
        fig: Plotly figure to add reference lines to
        df: DataFrame containing the data with year values
        thresholds: Dictionary of {label: threshold_value}
        colors: Dictionary of {label: color} for line colors
    
    Returns:
        Updated figure with reference lines
    """
    try:
        if df.empty or not thresholds:
            return fig
        
        # Get min and max year for reference lines
        years = sorted(df['year'].unique()) if 'year' in df.columns else []
        
        if not years:
            logger.warning("No year data found for reference lines")
            return fig
        
        # Create date bounds
        x_min = pd.Timestamp(f'{min(years)}-01-01')
        x_max = pd.Timestamp(f'{max(years)}-12-31')
        
        # Add reference lines for each threshold
        for label, threshold in thresholds.items():
            color = 'gray'
            if colors and label in colors:
                color = colors[label]
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
                x=x_min,
                y=threshold,
                text=label,
                showarrow=False,
                yshift=10,
                xshift=-20
            )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error adding reference lines: {e}")
        return fig

def update_layout(fig, df, title, y_label, y_column='comparison_to_reference', tick_format='.2f', has_legend=False):
    """
    Apply standardized layout settings to visualization figures.

    Args:
        fig: Plotly figure to update
        df: DataFrame containing the data
        title: Plot title
        y_label: Y-axis label
        y_column: Column name to use for y-range calculation
        tick_format: Format string for y-axis ticks (default: '.2f')
        has_legend: Whether to add legend title (for multi-trace plots like macro viz)
    
    Returns:
        Updated figure with consistent layout
    """
    try:
        if df.empty:
            return fig
        
        # Calculate y-range using the specified column
        y_min, y_max = calculate_dynamic_y_range(df, column=y_column)
        
        # Get unique years for x-axis
        years = sorted(df['year'].unique()) if 'year' in df.columns else []
        
        # Update layout with x-axis
        layout_updates = {
            'title': title,
            'title_x': 0.5,
            'title_y': 0.95,  # Adjust this value (0.95 to 0.99) to move title closer to plot
            'margin': dict(t=70),  # Reduce top margin (default is usually 80-100)
            'xaxis': dict(
                title='Year',
                tickmode='array',
                tickvals=[pd.Timestamp(f'{year}-01-01') for year in years],
                ticktext=[str(year) for year in years]
            ),
            'yaxis': dict(
                title=y_label,
                range=[y_min, y_max],
                tickformat=tick_format
            ),
            'hovermode': 'closest',
            'template': 'seaborn'  # Add white template to match chemical viz
        }
        
        # Add legend configuration if needed (matching chemical viz style)
        if has_legend:
            layout_updates['legend'] = dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title_text='Season'
            )
        
        fig.update_layout(**layout_updates)
        
        return fig
        
    except Exception as e:
        logger.error(f"Error updating layout: {e}")
        return fig

def create_trace(df, date_column, y_column, name, color=None, hover_fields=None):
    """
    Create a standardized scatter trace for visualizations.
    
    Args:
        df: DataFrame containing the data
        date_column: Name of the date column (e.g., 'collection_date', 'assessment_date')
        y_column: Name of the y-axis data column
        name: Name for the trace
        color: Color for the trace (uses default if None)
        hover_fields: Dictionary mapping display names to column names for hover text
                     e.g., {'Collection Date': 'collection_date', 'Score': 'comparison_to_reference'}
    
    Returns:
        Plotly Scatter trace object
    """
    try:
        if df.empty:
            return go.Scatter()
        
        # Parse and sort by date
        df_copy = df.copy()
        df_copy[date_column] = pd.to_datetime(df_copy[date_column])
        df_copy = df_copy.sort_values(date_column)
        
        # Set color
        trace_color = color if color else DEFAULT_COLORS['default']
        
        # Create hover text if fields provided
        hover_text = []
        if hover_fields:
            hover_text = generate_hover_text(df_copy, hover_fields)
        
        # Create trace
        trace = go.Scatter(
            x=df_copy[date_column],
            y=df_copy[y_column],
            mode='lines+markers',
            name=name,
            line=dict(color=trace_color),
            marker=dict(
                color=trace_color,
                symbol='circle',
                size=8
            ),
            text=hover_text,
            hovertemplate='%{text}<extra></extra>' if hover_text else None,
            hoverinfo='text' if hover_text else 'y'
        )
        
        return trace
    
    except Exception as e:
        logger.error(f"Error creating trace: {e}")
        return go.Scatter()

def generate_hover_text(df, hover_fields):
    """
    Generate hover text for visualizations with flexible field mapping.
    
    Args:
        df: DataFrame containing the data
        hover_fields: Dictionary mapping display names to column names
                     e.g., {'Collection Date': 'collection_date', 'Score': 'comparison_to_reference'}
                     
    Special field handling:
        - Date fields (containing 'date'): Formatted as YYYY-MM-DD
        - Score fields (containing 'score'): Formatted based on column name
          - 'total_score': Integer (habitat data)
          - Other scores: 2 decimal places (biological data)
        - All other fields: Display as-is
    
    Returns:
        List of hover text strings
    """
    try:
        hover_text = []
        
        for _, row in df.iterrows():
            text_parts = []
            
            for display_name, column_name in hover_fields.items():
                if column_name in row and pd.notna(row[column_name]):
                    value = row[column_name]
                    
                    # Format dates
                    if 'date' in column_name.lower() and hasattr(value, 'strftime'):
                        formatted_value = value.strftime('%m-%d-%Y')
                    
                    # Format numeric scores
                    elif 'score' in display_name.lower() and isinstance(value, (int, float)):
                        if column_name == 'total_score':  # Habitat scores are integers
                            formatted_value = int(value)
                        else:  # Biological scores are decimals
                            formatted_value = f"{value:.2f}"
                    
                    # Display other fields as-is
                    else:
                        formatted_value = value
                    
                    text_parts.append(f"<b>{display_name}</b>: {formatted_value}")
                
                # Handle missing values gracefully
                elif column_name in hover_fields.values():
                    text_parts.append(f"<b>{display_name}</b>: Unknown")
            
            hover_text.append("<br>".join(text_parts))
        
        return hover_text
    
    except Exception as e:
        logger.error(f"Error generating hover text: {e}")
        return []

# =============================================================================
# Data Processing & Formatting
# =============================================================================

def calculate_dynamic_y_range(df, column='comparison_to_reference'):
    """
    Calculate dynamic y-axis range based on data type and values.
    
    Args:
        df: DataFrame containing the data
        column: Column name to calculate range for
    
    Returns:
        Tuple of (y_min, y_max)
        - For biological data (comparison_to_reference): minimum range 0-1.1, expands if needed
        - For habitat data (total_score): minimum range 0-110, expands if needed
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
            # Habitat data: minimum range 0-110, expand if data exceeds ~90
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

def format_metrics_table(metrics_df, summary_df, metric_order, 
                        summary_labels=None, season=None):
    """
    Format metrics data into a standardized table structure.
    
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

# =============================================================================
# Table & UI Components
# =============================================================================

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

# =============================================================================
# Error Handling & Fallbacks
# =============================================================================

def create_empty_figure(site_name=None, data_type="data"):
    """
    Create an empty figure with appropriate "no data" message.
    
    Args:
        site_name: Optional site name
        data_type: Type of data (e.g., "habitat", "fish", "macroinvertebrate")
    
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