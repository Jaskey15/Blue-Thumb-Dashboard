"""
Macroinvertebrate bioassessment visualization with seasonal analysis and condition thresholds.

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
    Generate seasonal macroinvertebrate visualization with condition thresholds.
    """
    try:
        macro_df = get_macroinvertebrate_dataframe(site_name)
        
        if macro_df.empty:
            return create_empty_figure(site_name, "macroinvertebrate")

        macro_df['habitat'] = macro_df['habitat'].fillna('Unknown')
        macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
        
        fig = go.Figure()
        
        seasons = sorted(macro_df['season'].unique())
        
        # Create separate traces for summer and winter data
        for season in seasons:
            season_data = macro_df[macro_df['season'] == season].copy()
            season_data = season_data.sort_values('collection_date')
            
            color = DEFAULT_COLORS.get(season, DEFAULT_COLORS.get('default', 'blue'))
            
            hover_fields = {
                'Collection Date': 'collection_date',
                'Season': 'season',
                'Habitat Type': 'habitat',
                'Bioassessment Score': 'comparison_to_reference',
                'Biological Condition': 'biological_condition'
            }
            
            hover_text = generate_hover_text(season_data, hover_fields)
            
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
        
        title = f"Bioassessment Scores Over Time for {site_name}" if site_name else "Bioassessment Scores Over Time"
        
        fig = update_layout(
            fig,
            macro_df,
            title,
            y_label='Bioassessment Score<br>(Compared to Reference)',
            y_column='comparison_to_reference',
            tick_format='.2f',
            has_legend=True  # Show legend for seasonal differentiation
        )
        
        fig = add_reference_lines(fig, macro_df, CONDITION_THRESHOLDS, CONDITION_COLORS)

        return fig
    
    except Exception as e:
        logger.error(f"Error creating macroinvertebrate visualization for {site_name}: {e}")
        return create_error_figure(str(e))

def create_macro_metrics_table_for_season(metrics_df, summary_df, season):
    """
    Create metrics table for a specific season with habitat type handling.
    """
    try:
        season_metrics, habitat_row, season_summary = format_macro_metrics_table(
            metrics_df, 
            summary_df, 
            season=season
        )
        
        season_full_table = pd.concat([habitat_row, season_metrics, season_summary], ignore_index=True)
        
        styles = create_macro_table_styles(season_metrics, habitat_row)
        
        table = create_data_table(
            season_full_table, 
            f'{season.lower()}-macro-metrics-table', 
            styles
        )
        
        # Add explanatory footnotes for data interpretation
        footnote1 = html.P(
            "*(REP) indicates a replicate sample collected in the same year/season/habitat",
            style={'font-style': 'italic', 'margin-top': '8px', 'margin-bottom': '2px', 'font-size': '12px'}
        )
        footnote2 = html.P(
            "*Year-R/V/W suffixes indicate different habitat types: R=Riffle, V=Vegetation, W=Woody",
            style={'font-style': 'italic', 'margin-top': '2px', 'margin-bottom': '2px', 'font-size': '12px'}
        )
        footnote3 = html.P(
            "*Comparison to Reference values are capped at 1.0 even when calculated values exceed 1.0",
            style={'font-style': 'italic', 'margin-top': '2px', 'margin-bottom': '5px', 'font-size': '12px'}
        )
        
        return html.Div([table, footnote1, footnote2, footnote3])
    
    except Exception as e:
        logger.error(f"Error creating {season} metrics table: {e}")
        return html.Div(f"Error creating {season} metrics table")

def create_macro_metrics_accordion(site_name=None):
    """
    Create collapsible view of seasonal macroinvertebrate metrics.
    """
    try:
        metrics_df, summary_df = get_macro_metrics_data_for_table()
        
        if site_name:
            metrics_df = metrics_df[metrics_df['site_name'] == site_name] if 'site_name' in metrics_df.columns else metrics_df
            summary_df = summary_df[summary_df['site_name'] == site_name] if 'site_name' in summary_df.columns else summary_df
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No data available")
        
        # Create separate tables for summer and winter assessments
        summer_table = create_macro_metrics_table_for_season(metrics_df, summary_df, 'Summer')
        winter_table = create_macro_metrics_table_for_season(metrics_df, summary_df, 'Winter')
        
        summer_accordion = create_metrics_accordion(summer_table, "Summer Collection Metrics", "summer-accordion")
        winter_accordion = create_metrics_accordion(winter_table, "Winter Collection Metrics", "winter-accordion")
        
        return html.Div([summer_accordion, winter_accordion])
    
    except Exception as e:
        logger.error(f"Error creating metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")

def format_macro_metrics_table(metrics_df, summary_df, season=None):
    """
    Format metrics data with habitat type differentiation and replicate handling.
    
    Organizes data by year, season, and habitat type while preserving replicate samples.
    """
    try:
        if metrics_df.empty or summary_df.empty:
            return (pd.DataFrame({'Metric': MACRO_METRIC_ORDER}), 
                   pd.DataFrame({'Metric': ['Habitat Type']}),
                   pd.DataFrame({'Metric': ['No Data']}))
        
        if season:
            if 'season' in metrics_df.columns:
                metrics_df = metrics_df[metrics_df['season'] == season]
            if 'season' in summary_df.columns:
                summary_df = summary_df[summary_df['season'] == season]
        
        collections = []
        unique_collections = metrics_df.drop_duplicates(subset=['event_id']).copy()
        unique_collections['collection_date'] = pd.to_datetime(unique_collections['collection_date'])
        
        # Process collections by year and habitat
        for year, year_group in unique_collections.groupby('year'):
            year_group = year_group.sort_values('collection_date')
            habitat_counts = {}
            
            for _, row in year_group.iterrows():
                habitat = row.get('habitat', 'Unknown')
                event_id = row.get('event_id', None)
                
                if habitat not in habitat_counts:
                    habitat_counts[habitat] = 0
                habitat_counts[habitat] += 1
                
                # Determine column name based on habitat and replicate status
                column_name = str(year) if habitat_counts[habitat] == 1 else f"{year} (REP)"
                
                unique_habitats_this_year = year_group['habitat'].nunique()
                
                if unique_habitats_this_year > 1:
                    habitat_abbrev = habitat[0] if habitat else 'U'
                    column_name = f"{year}-{habitat_abbrev}" if habitat_counts[habitat] == 1 else f"{year}-{habitat_abbrev} (REP)"
                
                collections.append({
                    'event_id': event_id,
                    'year': year,
                    'habitat': habitat,
                    'column_name': column_name,
                    'collection_date': row['collection_date']
                })
        
        collections.sort(key=lambda x: (x['year'], '(REP)' in x['column_name']))
        
        if not collections:
            return (pd.DataFrame({'Metric': MACRO_METRIC_ORDER}), 
                   pd.DataFrame({'Metric': ['Habitat Type']}),
                   pd.DataFrame({'Metric': ['No Data']}))
        
        table_data = {'Metric': MACRO_METRIC_ORDER}
        habitat_data = {'Metric': ['Habitat Type']}
        
        # Build metrics and habitat data
        for collection in collections:
            column_name = collection['column_name']
            event_id = collection['event_id']
            habitat = collection['habitat']
            
            collection_metrics = metrics_df[metrics_df['event_id'] == event_id]
            
            habitat_data[column_name] = habitat
            
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
        
        metrics_table = pd.DataFrame(table_data)
        habitat_row = pd.DataFrame(habitat_data)
        
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
    Create consistent styling for macro metrics tables with habitat emphasis.
    """
    from .visualization_utils import create_table_styles
    styles = create_table_styles(metrics_table)
    
    habitat_row_index = 0
    metrics_start_index = len(habitat_row)
    summary_start_index = len(habitat_row) + len(metrics_table)
    
    styles['style_data_conditional'] = [
        {
            'if': {'row_index': habitat_row_index},
            'backgroundColor': 'rgb(245, 245, 245)',
            'fontWeight': 'bold'
        },
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

