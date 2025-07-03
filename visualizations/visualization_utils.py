"""
Shared visualization utilities for consistent styling and data presentation.

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
    Add threshold reference lines with dynamic date ranges.
    
    Priority order:
    1. Use provided colors if specified
    2. Match threshold label to DEFAULT_COLORS
    3. Fall back to gray for unmatched labels
    """
    try:
        if df.empty or not thresholds:
            return fig
        
        years = sorted(df['year'].unique()) if 'year' in df.columns else []
        
        if not years:
            logger.warning("No year data found for reference lines")
            return fig
        
        # Create bounds for full year range
        x_min = pd.Timestamp(f'{min(years)}-01-01')
        x_max = pd.Timestamp(f'{max(years)}-12-31')
        
        # Add reference lines for each threshold
        for label, threshold in thresholds.items():
            # Select line color based on priority order
            color = 'gray'
            if colors and label in colors:
                color = colors[label]
            elif label.lower() in DEFAULT_COLORS:
                color = DEFAULT_COLORS[label.lower()]
            
            fig.add_shape(
                type="line",
                x0=x_min,
                y0=threshold,
                x1=x_max,
                y1=threshold,
                line=dict(color=color, width=1, dash="dash"),
            )
            
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
    Apply consistent layout settings across all visualizations.
    
    Priority order:
    1. Set dynamic y-range based on data type
    2. Configure x-axis with year ticks
    3. Add legend if multi-trace plot
    """
    try:
        if df.empty:
            return fig
        
        y_min, y_max = calculate_dynamic_y_range(df, column=y_column)
        years = sorted(df['year'].unique()) if 'year' in df.columns else []
        
        # Standardize layout across all plots
        layout_updates = {
            'title': title,
            'title_x': 0.5,
            'title_y': 0.95, 
            'margin': dict(t=70),  
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
            'template': 'seaborn'  
        }
        
        # Add horizontal legend for multi-trace plots
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
    Create standardized scatter trace with consistent styling and hover text.
    
    Priority order:
    1. Sort data chronologically
    2. Apply consistent marker styling
    3. Generate hover text if fields provided
    """
    try:
        if df.empty:
            return go.Scatter()
        
        df_copy = df.copy()
        df_copy[date_column] = pd.to_datetime(df_copy[date_column])
        df_copy = df_copy.sort_values(date_column)
        
        trace_color = color if color else DEFAULT_COLORS['default']
        
        hover_text = []
        if hover_fields:
            hover_text = generate_hover_text(df_copy, hover_fields)
        
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
    Generate hover text with consistent formatting across all visualizations.
    
    Format rules:
    1. Dates: MM-DD-YYYY
    2. Total scores: Integer
    3. Other scores: 2 decimal places
    4. Missing values: 'Unknown'
    """
    try:
        hover_text = []
        
        for _, row in df.iterrows():
            text_parts = []
            
            for display_name, column_name in hover_fields.items():
                if column_name in row and pd.notna(row[column_name]):
                    value = row[column_name]
                    
                    if 'date' in column_name.lower() and hasattr(value, 'strftime'):
                        formatted_value = value.strftime('%m-%d-%Y')
                    
                    elif 'score' in display_name.lower() and isinstance(value, (int, float)):
                        if column_name == 'total_score':  # Integer for habitat
                            formatted_value = int(value)
                        else:  # 2 decimals for biological
                            formatted_value = f"{value:.2f}"
                    
                    else:
                        formatted_value = value
                    
                    text_parts.append(f"<b>{display_name}</b>: {formatted_value}")
                
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
    Calculate y-axis range with appropriate padding for data type.
    
    Rules:
    - Habitat (total_score): 0-110 minimum, expand if > ~90
    - Biological: 0-1.1 minimum, expand if > ~1.0
    """
    try:
        if df.empty or column not in df.columns:
            if column == 'total_score':
                return 0, 110  # Default habitat range
            else:
                return 0, 1.1  # Default biological range
        
        max_value = df[column].max()
        
        if column == 'total_score':
            y_upper_limit = max(110, max_value * 1.1)  # Ensure habitat scores visible
        else:
            y_upper_limit = max(1.1, max_value * 1.1)  # Ensure biological scores visible
        
        return 0, y_upper_limit
    
    except Exception as e:
        logger.warning(f"Error calculating y-range: {e}")
        if column == 'total_score':
            return 0, 110
        else:
            return 0, 1.1

def format_metrics_table(metrics_df, summary_df, metric_order, summary_labels=None, season=None):
    """
    Format metrics into standardized table with summary statistics.
    
    Priority order:
    1. Filter by season if specified
    2. Format metrics by year
    3. Add summary rows with appropriate precision
    """
    try:
        if metrics_df.empty or summary_df.empty:
            return pd.DataFrame({'Metric': metric_order}), pd.DataFrame({'Metric': ['No Data']})
        
        if season:
            if 'season' in metrics_df.columns:
                metrics_df = metrics_df[metrics_df['season'] == season]
            if 'season' in summary_df.columns:
                summary_df = summary_df[summary_df['season'] == season]
        
        years = sorted(metrics_df['year'].unique()) if not metrics_df.empty else []
        
        # Build metrics table
        table_data = {'Metric': metric_order}
        
        for year in years:
            year_metrics = metrics_df[metrics_df['year'] == year]
            scores = []
            
            for metric in metric_order:
                metric_row = year_metrics[year_metrics['metric_name'] == metric]
                if not metric_row.empty:
                    try:
                        if 'metric_score' in metric_row.columns:
                            score_value = metric_row['metric_score'].values[0]
                        elif 'score' in metric_row.columns:
                            score_value = metric_row['score'].values[0]
                        else:
                            logger.warning(f"No score column found for metric {metric}")
                            scores.append('-')
                            continue
                        
                        # Format with appropriate precision
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
        
        metrics_table = pd.DataFrame(table_data)
        
        # Build summary rows
        default_summary_labels = ['Total Score', 'Comparison to Reference', 'Condition']
        summary_labels = summary_labels or default_summary_labels
        summary_rows = pd.DataFrame({'Metric': summary_labels})
        
        for year in years:
            year_summary = summary_df[summary_df['year'] == year]
            if not year_summary.empty:
                try:
                    total_score = int(year_summary['total_score'].values[0])
                    summary_data = [total_score]
                    
                    if 'comparison_to_reference' in year_summary.columns:
                        comparison = f"{year_summary['comparison_to_reference'].values[0]:.2f}"
                        summary_data.append(comparison)
                        
                        condition = 'Unknown'
                        if 'biological_condition' in year_summary.columns:
                            condition = year_summary['biological_condition'].values[0]
                        elif 'integrity_class' in year_summary.columns:
                            condition = year_summary['integrity_class'].values[0]
                        summary_data.append(condition)
                    
                    elif 'habitat_grade' in year_summary.columns:
                        habitat_grade = year_summary['habitat_grade'].values[0]
                        summary_data.append(habitat_grade)
                    
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
    Create consistent table styling across all data views.
    
    Style rules:
    1. Bold headers and first column
    2. Center-align numeric data
    3. Bold summary rows with top border
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
    """Create standardized data table with consistent styling."""
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
    """Create empty figure with informative message when no data available."""
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
    """Create error figure with clear error message for troubleshooting."""
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