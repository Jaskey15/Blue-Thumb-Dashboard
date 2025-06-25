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
import pandas as pd

from dash import html
from data_processing.data_queries import get_macroinvertebrate_dataframe, get_macro_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging
from .visualization_utils import (
    DEFAULT_COLORS,
    create_data_table,
    create_empty_figure,
    create_error_figure,
    add_reference_lines,
    update_layout,
    generate_hover_text
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
        
        # Parse collection dates
        macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
        
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
            
            # Define hover fields for macro seasonal data
            hover_fields = {
                'Collection Date': 'collection_date',
                'Season': 'season',
                'Habitat Type': 'habitat',
                'Bioassessment Score': 'comparison_to_reference',
                'Biological Condition': 'biological_condition'
            }
            
            # Create hover text for this season using shared utility
            hover_text = generate_hover_text(season_data, hover_fields)
            
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
        
        # Update layout using shared utility (with legend for seasons)
        fig = update_layout(
            fig,
            macro_df,
            title,
            y_label='Bioassessment Score<br>(Compared to Reference)',
            y_column='comparison_to_reference',
            tick_format='.2f',
            has_legend=True  # Macro viz has seasons so needs legend
        )
        
        # Add condition reference lines using shared utility
        fig = add_reference_lines(fig, macro_df, CONDITION_THRESHOLDS, CONDITION_COLORS)

        return fig
    
    except Exception as e:
        logger.error(f"Error creating macroinvertebrate visualization for {site_name}: {e}")
        return create_error_figure(str(e))

def create_macro_metrics_table_for_season(metrics_df, summary_df, season):
    """
    Create a metrics table for a specific season that shows ALL collections 
    including multiple habitat types per year.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
        season: Season to filter data for ('Summer' or 'Winter')
    
    Returns:
        HTML Div containing Dash DataTable component with footnote
    """
    try:
        # Format data for the selected season using macro-specific utilities
        season_metrics, habitat_row, season_summary = format_macro_metrics_table(
            metrics_df, 
            summary_df, 
            season=season
        )
        
        # Combine all parts: habitat row + metrics + summary
        season_full_table = pd.concat([habitat_row, season_metrics, season_summary], ignore_index=True)
        
        # Get styling using macro-specific utilities
        styles = create_macro_table_styles(season_metrics, habitat_row)
        
        # Create the table component using shared utilities
        table = create_data_table(
            season_full_table, 
            f'{season.lower()}-macro-metrics-table', 
            styles
        )
        
        # Add footnote for comparison to reference values
        footnote = html.P(
            "*Comparison to Reference values are capped at 1.0 even when calculated values exceed 1.0",
            style={'font-style': 'italic', 'margin-top': '10px', 'font-size': '12px'}
        )
        
        return html.Div([table, footnote])
    
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

def format_macro_metrics_table(metrics_df, summary_df, season=None):
    """
    Format macroinvertebrate metrics data into a table structure that shows ALL collections
    including multiple habitat types per year/season.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
        season: Optional season to filter data for ('Summer' or 'Winter')
    
    Returns:
        Tuple of (metrics_table, habitat_row, summary_rows) DataFrames
    """
    try:
        if metrics_df.empty or summary_df.empty:
            return (pd.DataFrame({'Metric': MACRO_METRIC_ORDER}), 
                   pd.DataFrame({'Metric': ['Habitat Type']}),
                   pd.DataFrame({'Metric': ['No Data']}))
        
        # Filter by season if specified
        if season:
            if 'season' in metrics_df.columns:
                metrics_df = metrics_df[metrics_df['season'] == season]
            if 'season' in summary_df.columns:
                summary_df = summary_df[summary_df['season'] == season]
        
        # Get unique collections (event_id represents unique year-season-habitat combinations)
        collections = []
        # Get unique collections from metrics data with all necessary info
        unique_collections = metrics_df.drop_duplicates(subset=['event_id']).copy()
        
        for _, row in unique_collections.iterrows():
            year = row.get('year', 'Unknown')
            habitat = row.get('habitat', 'Unknown')
            event_id = row.get('event_id', None)
            
            collections.append({
                'event_id': event_id,
                'year': year,
                'habitat': habitat,
                'column_name': str(year)  # Just use year as column name
            })
        
        # Sort collections by year and habitat for consistent ordering
        collections = sorted(collections, key=lambda x: (x['year'], x['habitat']))
        
        if not collections:
            return (pd.DataFrame({'Metric': MACRO_METRIC_ORDER}), 
                   pd.DataFrame({'Metric': ['Habitat Type']}),
                   pd.DataFrame({'Metric': ['No Data']}))
        
        # Create table data dictionary starting with metrics
        table_data = {'Metric': MACRO_METRIC_ORDER}
        habitat_data = {'Metric': ['Habitat Type']}
        
        # Add columns for each collection (year-habitat combination)
        for collection in collections:
            column_name = collection['column_name']
            event_id = collection['event_id']
            habitat = collection['habitat']
            
            # Get metrics for this specific collection using event_id
            collection_metrics = metrics_df[metrics_df['event_id'] == event_id]
            
            # Add habitat to habitat row
            habitat_data[column_name] = habitat
            
            # Add scores for this collection
            scores = []
            for metric in MACRO_METRIC_ORDER:
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
        
        # Create metrics and habitat tables
        metrics_table = pd.DataFrame(table_data)
        habitat_row = pd.DataFrame(habitat_data)
        
        # Create summary rows
        summary_rows = pd.DataFrame({'Metric': MACRO_SUMMARY_LABELS})
        
        # Add summary data for each collection
        for collection in collections:
            column_name = collection['column_name']
            event_id = collection['event_id']
            
            collection_summary = summary_df[summary_df['event_id'] == event_id]
            if not collection_summary.empty:
                try:
                    row = collection_summary.iloc[0]
                    total_score = int(row['total_score'])
                    comparison = f"{row['comparison_to_reference']:.2f}"
                    condition = row['biological_condition']
                    
                    summary_data = [total_score, comparison, condition]
                    summary_rows[column_name] = summary_data
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing summary data for event {event_id}: {e}")
                    summary_rows[column_name] = ['-', '-', '-']
            else:
                summary_rows[column_name] = ['-', '-', '-']
        
        return metrics_table, habitat_row, summary_rows
    
    except Exception as e:
        logger.error(f"Error formatting macro metrics table: {e}")
        return (pd.DataFrame({'Metric': MACRO_METRIC_ORDER}), 
               pd.DataFrame({'Metric': ['Habitat Type']}),
               pd.DataFrame({'Metric': ['Error']}))

def create_macro_table_styles(metrics_table, habitat_row):
    """
    Create styling for macro metrics tables that includes the habitat type row.
    Uses the shared styling but adds special handling for the habitat row.
    
    Args:
        metrics_table: DataFrame with the metrics rows
        habitat_row: DataFrame with the habitat type row
    
    Returns:
        Dictionary of style configurations for the table
    """
    # Start with the standard table styles from shared utilities
    from .visualization_utils import create_table_styles
    styles = create_table_styles(metrics_table)
    
    # Calculate row indices (habitat row is now first, then metrics, then summary)
    habitat_row_index = 0  # Habitat row is now the first row
    metrics_start_index = len(habitat_row)  # Metrics start after habitat row
    summary_start_index = len(habitat_row) + len(metrics_table)  # Summary starts after habitat + metrics
    
    # Update the conditional styling to account for the habitat row
    styles['style_data_conditional'] = [
        {
            'if': {'row_index': habitat_row_index},
            'backgroundColor': 'rgb(245, 245, 245)',
            'fontWeight': 'bold'
        },
        # Summary rows styling - bold with border (adjusted indices)
        {
            'if': {'row_index': summary_start_index},
            'borderTop': '2px solid black',
            'fontWeight': 'bold'
        },
        {
            'if': {'row_index': summary_start_index + 1},
            'fontWeight': 'bold'
        },
        {
            'if': {'row_index': summary_start_index + 2},
            'fontWeight': 'bold'
        }
    ]
    
    return styles

