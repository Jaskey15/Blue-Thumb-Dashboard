import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
from data_processing.data_queries import get_macroinvertebrate_dataframe, get_macro_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging

logger = setup_logging("macro_viz", category="visualization")

# Styling constants
COLORS = {
    'Winter': 'blue',
    'Summer': 'red',
    'reference_lines': {
        'Non-impaired': 'green',
        'Slightly Impaired': 'orange',
        'Moderately Impaired': 'red'
    }
}

FONT_SIZES = {
    'title': 16,
    'axis_title': 14,
    'header': 12,
    'cell': 11
}

# Reference thresholds
CONDITION_THRESHOLDS = {
    'Non-impaired': 0.83,
    'Slightly Impaired': 0.54,
    'Moderately Impaired': 0.17
}

# Metrics display order
METRIC_ORDER = [
    'Taxa Richness',
    'EPT Taxa Richness',
    'EPT Abundance',
    'HBI Score',
    '% Contribution Dominants',
    'Shannon-Weaver'
]

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
            # Return an empty figure with a message if no data
            fig = go.Figure()
            site_msg = f" for {site_name}" if site_name else ""
            fig.update_layout(
                title=f"No macroinvertebrate data available{site_msg}",
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

        # Create a line plot for macroinvertebrate data
        title = f"Bioassessment Scores Over Time - {site_name}" if site_name else "Bioassessment Scores Over Time"
        fig_macro = px.line(
            macro_df, 
            x='year', 
            y='comparison_to_reference',
            color='season',  
            markers=True,
            title=title,
            labels={
                'year': 'Year',
                'season': 'Season'
            },
            color_discrete_map=COLORS
        )

        # Update y-axis title to be multiline
        fig_macro.update_layout(
            yaxis_title='Bioassessment Score<br>(Compared to Reference)'
        )

        # Add reference lines for biological condition classes
        add_condition_reference_lines(fig_macro, macro_df)

        # Improve the layout
        fig_macro.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=sorted(macro_df['year'].unique()),
                title_font=dict(size=FONT_SIZES['axis_title']),
            ),
            yaxis=dict(
                range=[0, 1.1],
                tickformat='.2f',
                title_font=dict(size=FONT_SIZES['axis_title']),
            ),
            hovermode='x unified',
            legend_title_text='Season',
            title_x=0.5,
            title_font=dict(size=FONT_SIZES['title'])
        )

        # Add hover data
        fig_macro.update_traces(
            hovertemplate='<b>Year:</b> %{x}<br><b>Season:</b> %{fullData.name}<br><b>Score:</b> %{y:.2f}<extra></extra>'
        )

        return fig_macro
    
    except Exception as e:
        logger.error(f"Error creating macroinvertebrate visualization for {site_name}: {e}")
        # Return empty figure with error message
        fig = go.Figure()
        fig.update_layout(
            title="Error creating visualization",
            annotations=[dict(
                text=f"Error: {str(e)}",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5
            )]
        )
        return fig

def add_condition_reference_lines(fig, df):
    """
    Add reference lines for biological condition classes to the figure.
    
    Args:
        fig: Plotly figure to add reference lines to
        df: DataFrame containing the data with year values
    
    Returns:
        Updated figure with reference lines
    """
    if df.empty:
        return fig
        
    # Get min and max year for reference lines
    x_min = df['year'].min() - 1
    x_max = df['year'].max() + 1
    
    # Add reference lines for each condition threshold
    for condition, threshold in CONDITION_THRESHOLDS.items():
        color = COLORS['reference_lines'][condition]
        
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
            text=condition,
            showarrow=False,
            yshift=10
        )
    
    return fig

def format_macro_metrics_table(metrics_df, summary_df, season):
    """
    Format the macroinvertebrate metrics data for a specific season into a table structure.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
        season: Season to filter data for ('Summer' or 'Winter')
    
    Returns:
        Tuple of (metrics_table, summary_rows) DataFrames
    """
    try:
        if metrics_df.empty or summary_df.empty:
            return pd.DataFrame({'Metric': METRIC_ORDER}), pd.DataFrame({'Metric': ['No Data']})
            
        # Filter data for the selected season
        season_metrics = metrics_df[metrics_df['season'] == season]
        season_summary = summary_df[summary_df['season'] == season]
        
        # Get unique years for this season
        years = sorted(season_metrics['year'].unique()) if not season_metrics.empty else []
        
        # Create a dictionary to hold the table data
        table_data = {'Metric': METRIC_ORDER}
        
        # Add columns for each year
        for year in years:
            year_metrics = season_metrics[season_metrics['year'] == year]
            
            # Add a column for this year's scores
            scores = []
            for metric in METRIC_ORDER:
                metric_row = year_metrics[year_metrics['metric_name'] == metric]
                if not metric_row.empty:
                    try:
                        score_value = metric_row['metric_score'].values[0]
                        scores.append(int(score_value))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert metric score to int: {score_value}, error: {e}")
                        scores.append('-')
                else:
                    scores.append('-')
            
            table_data[str(year)] = scores
        
        # Create a DataFrame for the metrics
        metrics_table = pd.DataFrame(table_data)
        
        # Create a separate DataFrame for the summary rows
        summary_rows = pd.DataFrame({
            'Metric': ['Total Score', 'Comparison to Reference', 'Biological Condition'],
        })
        
        # Add the summary data for each year
        for year in years:
            year_summary = season_summary[season_summary['year'] == year]
            if not year_summary.empty:
                try:
                    total_score = int(year_summary['total_score'].values[0])
                    comparison = f"{year_summary['comparison_to_reference'].values[0]:.2f}"
                    condition = year_summary['biological_condition'].values[0]
                    summary_rows[str(year)] = [total_score, comparison, condition]
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing summary data for {season} year {year}: {e}")
                    summary_rows[str(year)] = ['-', '-', '-']
            else:
                summary_rows[str(year)] = ['-', '-', '-']

        return metrics_table, summary_rows
    
    except Exception as e:
        logger.error(f"Error formatting {season} metrics table: {e}")
        # Return empty DataFrames
        return pd.DataFrame({'Metric': METRIC_ORDER}), pd.DataFrame({'Metric': ['Error']})

def create_metrics_table_styles(season_metrics):
    """
    Create consistent styling for metrics tables.
    
    Args:
        season_metrics: DataFrame with the metrics rows (used for row indexing)
    
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
                'if': {'row_index': len(season_metrics)},
                'borderTop': '2px solid black',
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': len(season_metrics) + 1},
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': len(season_metrics) + 2},
                'fontWeight': 'bold'
            }
        ]
    }

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
        # Format data for the selected season
        season_metrics, season_summary = format_macro_metrics_table(metrics_df, summary_df, season)
        season_full_table = pd.concat([season_metrics, season_summary], ignore_index=True)
        
        # Get styling for the table
        styles = create_metrics_table_styles(season_metrics)
        
        # Create the table component
        table = dash_table.DataTable(
            id=f'{season.lower()}-macro-metrics-table',
            columns=[{"name": col, "id": col} for col in season_full_table.columns],
            data=season_full_table.to_dict('records'),
            **styles
        )
        
        return table
    
    except Exception as e:
        logger.error(f"Error creating {season} metrics table: {e}")
        # Return a simple error message if table creation fails
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

# Legacy functions maintained for compatibility
def create_macro_metrics_table(site_name=None):
    """Create tables showing macroinvertebrate metrics scores for both seasons (legacy function)."""
    return create_macro_metrics_accordion(site_name)

def create_macro_viz_with_table(site_name=None):
    """Create macroinvertebrate community visualization with metrics tables for the app."""
    try:
        fig_macro = create_macro_viz(site_name)
        metrics_tables = create_macro_metrics_table(site_name)
        return fig_macro, metrics_tables
    except Exception as e:
        logger.error(f"Error creating macroinvertebrate visualization with tables: {e}")
        fig = go.Figure()
        fig.update_layout(title="Error creating visualization")
        return fig, html.Div("Error loading metrics data")

# Test visualization if run directly
if __name__ == "__main__":
    fig = create_macro_viz()
    fig.show()