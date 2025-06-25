"""
fish_viz.py - Fish Community Assessment Data Visualization

This module creates visualizations for fish community Index of Biotic Integrity (IBI) 
data including line charts with integrity class reference lines and data tables for 
Blue Thumb bioassessment monitoring.

Key Functions:
- create_fish_viz(): Create IBI score line chart with integrity thresholds
- create_fish_metrics_table(): Create data table for fish community metrics
- create_fish_metrics_accordion(): Create accordion layout for fish metrics

Integrity Classes:
- Excellent (0.97+), Good (0.76+), Fair (0.60+), Poor (0.47+)
"""

import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
from data_processing.data_queries import get_fish_dataframe, get_fish_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging
from .visualization_utils import (
    DEFAULT_COLORS, 
    create_table_styles,
    create_data_table,
    create_empty_figure,
    create_error_figure,
    add_date_aware_reference_lines,
    update_date_aware_layout,
    create_date_based_trace,
    FONT_SIZES
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
    'Excellent': DEFAULT_COLORS['excellent'],
    'Good': DEFAULT_COLORS['good'],
    'Fair': DEFAULT_COLORS['fair'],
    'Poor': DEFAULT_COLORS['poor']
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

def format_fish_metrics_table(metrics_df, summary_df):
    """
    Format fish metrics data into a table structure that shows ALL collections
    including replicates with (REP) notation.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
    
    Returns:
        Tuple of (metrics_table, summary_rows) DataFrames
    """
    try:
        if metrics_df.empty or summary_df.empty:
            return (pd.DataFrame({'Metric': FISH_METRIC_ORDER}), 
                   pd.DataFrame({'Metric': ['No Data']}))
        
        # Get unique collections
        unique_collections = summary_df.drop_duplicates(subset=['event_id']).copy()
        unique_collections['collection_date'] = pd.to_datetime(unique_collections['collection_date'])
        
        # Group by year and process each year separately
        collections = []
        
        for year, year_group in unique_collections.groupby('year'):
            # Sort within each year by collection date
            year_group = year_group.sort_values('collection_date')
            
            # Assign REP notation within each year
            for idx, (_, row) in enumerate(year_group.iterrows()):
                event_id = row.get('event_id', None)
                
                # Create column name with REP notation for second+ samples in same year
                if idx == 0:
                    column_name = str(year)
                else:
                    column_name = f"{year} (REP)"
                
                collections.append({
                    'event_id': event_id,
                    'year': year,
                    'column_name': column_name,
                    'collection_date': row['collection_date']
                })
        
        # Sort collections by year, then by whether it's REP (original first, then REP)
        collections.sort(key=lambda x: (x['year'], '(REP)' in x['column_name']))
        
        if not collections:
            return (pd.DataFrame({'Metric': FISH_METRIC_ORDER}), 
                   pd.DataFrame({'Metric': ['No Data']}))
        
        # Create table data dictionary starting with metrics
        table_data = {'Metric': FISH_METRIC_ORDER}
        
        # Add columns for each collection in proper order
        for collection in collections:
            column_name = collection['column_name']
            event_id = collection['event_id']
            
            # Get metrics for this specific collection using event_id
            collection_metrics = metrics_df[metrics_df['event_id'] == event_id]
            
            # Add scores for this collection
            scores = []
            for metric in FISH_METRIC_ORDER:
                metric_row = collection_metrics[collection_metrics['metric_name'] == metric]
                if not metric_row.empty:
                    try:
                        score_value = metric_row['metric_score'].values[0]
                        scores.append(int(score_value))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert metric score to number: {score_value}, error: {e}")
                        scores.append('-')
                else:
                    scores.append('-')
            
            table_data[column_name] = scores
        
        # Create metrics table
        metrics_table = pd.DataFrame(table_data)
        
        # Create summary rows
        summary_rows = pd.DataFrame({'Metric': FISH_SUMMARY_LABELS})
        
        # Add summary data for each collection in proper order
        for collection in collections:
            column_name = collection['column_name']
            event_id = collection['event_id']
            
            collection_summary = summary_df[summary_df['event_id'] == event_id]
            if not collection_summary.empty:
                try:
                    row = collection_summary.iloc[0]
                    total_score = int(row['total_score'])
                    comparison = f"{row['comparison_to_reference']:.2f}"
                    integrity_class = row['integrity_class']
                    
                    summary_data = [total_score, comparison, integrity_class]
                    summary_rows[column_name] = summary_data
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing summary data for event {event_id}: {e}")
                    summary_rows[column_name] = ['-', '-', '-']
            else:
                summary_rows[column_name] = ['-', '-', '-']
        
        return metrics_table, summary_rows
    
    except Exception as e:
        logger.error(f"Error formatting fish metrics table: {e}")
        return (pd.DataFrame({'Metric': FISH_METRIC_ORDER}), 
               pd.DataFrame({'Metric': ['Error']}))

def create_fish_viz(site_name=None):
    """
    Create fish community visualization with date-based plotting and year labels.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing IBI scores over time with actual collection dates.
    """
    try:
        # Get fish data from the database
        fish_df = get_fish_dataframe(site_name)
        
        if fish_df.empty:
            return create_empty_figure(site_name, "fish")

        # Create figure
        fig = go.Figure()
        
        # Define hover fields for fish data
        hover_fields = {
            'Collection Date': 'collection_date',
            'IBI Score': 'comparison_to_reference',
            'Integrity Class': 'integrity_class'
        }
        
        # Create date-based trace using shared utility
        trace = create_date_based_trace(
            fish_df,
            date_column='collection_date',
            y_column='comparison_to_reference',
            name='IBI Score',
            color=DEFAULT_COLORS['default'],
            hover_fields=hover_fields
        )
        
        # Add trace to figure
        fig.add_trace(trace)
        
        # Set up title
        title = f"IBI Scores Over Time for {site_name}" if site_name else "IBI Scores Over Time"
        
        # Update layout using shared utility
        fig = update_date_aware_layout(
            fig,
            fish_df,
            title,
            y_label='IBI Score (Compared to Reference)',
            y_column='comparison_to_reference',
            tick_format='.2f',
            has_legend=False
        )
        
        # Add integrity reference lines using shared utility
        fig = add_date_aware_reference_lines(fig, fish_df, INTEGRITY_THRESHOLDS, INTEGRITY_COLORS)

        return fig
    
    except Exception as e:
        logger.error(f"Error creating fish visualization for {site_name}: {e}")
        return create_error_figure(str(e))

def create_fish_metrics_table(metrics_df, summary_df):
    """
    Create a metrics table for fish data that shows ALL samples including replicates.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
    
    Returns:
        Dash DataTable component with footnote
    """
    try:
        # Format the data using fish-specific logic
        metrics_table, summary_rows = format_fish_metrics_table(
            metrics_df, 
            summary_df
        )
        
        # Combine metrics and summary rows
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
    
        styles = create_table_styles(metrics_table)
        
        table = create_data_table(full_table, 'fish-metrics-table', styles)
        
        # Add footnote for REP notation
        footnote = html.P(
            "*(REP) indicates a replicate sample collected in the same year",
            style={'font-style': 'italic', 'margin-top': '10px', 'font-size': '12px'}
        )
        
        return html.Div([table, footnote])
    
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

