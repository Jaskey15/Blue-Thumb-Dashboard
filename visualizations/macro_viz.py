import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
from data_processing.data_queries import get_macroinvertebrate_dataframe, get_macro_metrics_data_for_table
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
    Create macroinvertebrate visualization for the app.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing bioassessment scores over time for both seasons.
    """
    try:
        # Get macroinvertebrate data from the database
        macro_df = get_macroinvertebrate_dataframe()
        
        # Filter by site if specified
        if site_name:
            macro_df = macro_df[macro_df['site_name'] == site_name]
        
        if macro_df.empty:
            return create_empty_biological_figure(site_name, "macroinvertebrate")

        # Create the line plot using shared utilities
        title = f"Bioassessment Scores Over Time for {site_name}" if site_name else "Bioassessment Scores Over Time"
        fig_macro = create_biological_line_plot(
            macro_df,
            title,
            y_column='comparison_to_reference',
            has_seasons=True,
            color_map=BIOLOGICAL_COLORS
        )

        # Update layout using shared utilities
        fig_macro = update_biological_figure_layout(
            fig_macro,
            macro_df,
            title,
            y_label='Bioassessment Score<br>(Compared to Reference)'
        )

        # Add condition reference lines
        fig_macro = add_reference_lines(fig_macro, macro_df, CONDITION_THRESHOLDS, CONDITION_COLORS)

        # Add hover data using shared utilities - need to handle multiple seasons
        hover_text_dict = {}
        for season in macro_df['season'].unique():
            season_data = macro_df[macro_df['season'] == season]
            season_hover = create_hover_text(season_data, has_seasons=True, condition_column='biological_condition')
            hover_text_dict[season] = season_hover

        fig_macro = update_hover_data(fig_macro, hover_text_dict)

        return fig_macro
    
    except Exception as e:
        logger.error(f"Error creating macroinvertebrate visualization for {site_name}: {e}")
        return create_error_biological_figure(str(e))

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
        season_metrics, season_summary = format_biological_metrics_table(
            metrics_df, 
            summary_df, 
            MACRO_METRIC_ORDER,
            MACRO_SUMMARY_LABELS,
            season=season
        )
        season_full_table = pd.concat([season_metrics, season_summary], ignore_index=True)
        
        # Get styling using shared utilities
        styles = create_biological_table_styles(season_metrics)
        
        # Create the table component using shared utilities
        table = create_biological_data_table(
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

