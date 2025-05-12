import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
import dash_bootstrap_components as dbc  
from data_processing.macro_processing import get_macroinvertebrate_dataframe, get_macro_metrics_data_for_table
from utils import create_metrics_accordion

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

# Reference scores configuration
REFERENCE_SCORES = {
    'Summer': {
        'Taxa Richness': 6,
        'EPT Taxa Richness': 6,
        'EPT Abundance': 6,
        'HBI Score': 6,
        '% Contribution Dominants': 6,
        'Shannon-Weaver': 4
    },
    'Winter': {
        'Taxa Richness': 6,
        'EPT Taxa Richness': 6,
        'EPT Abundance': 6,
        'HBI Score': 6,
        '% Contribution Dominants': 6,
        'Shannon-Weaver': 2
    }
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

def create_macro_viz():
    """
    Create macroinvertebrate visualization for the app.
    
    Returns:
        Plotly figure: Line plot showing bioassessment scores over time for both seasons.
    """
    try:
        # Get macroinvertebrate data from the database
        macro_df = get_macroinvertebrate_dataframe()
        
        if macro_df.empty:
            # Return an empty figure with a message if no data
            fig = go.Figure()
            fig.update_layout(
                title="No macroinvertebrate data available",
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
        fig_macro = px.line(
            macro_df, 
            x='year', 
            y='comparison_to_reference',
            color='season',  
            markers=True,
            title='Bioassessment Scores Over Time',
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
        print(f"Error creating macroinvertebrate visualization: {e}")
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
        # Filter data for the selected season
        season_metrics = metrics_df[metrics_df['season'] == season]
        season_summary = summary_df[summary_df['season'] == season]
        
        # Get unique years for this season
        years = sorted(season_metrics['year'].unique())
        
        # Get reference scores for this season
        reference_scores = REFERENCE_SCORES[season]

        # Create a dictionary to hold the table data
        table_data = {'Metric': METRIC_ORDER}
        
        # Add reference scores column
        ref_scores = [str(reference_scores.get(metric, '-')) for metric in METRIC_ORDER]
        
        # Add columns for each year
        for year in years:
            year_metrics = season_metrics[season_metrics['year'] == year]
            
            # Add a column for this year's scores
            scores = []
            for metric in METRIC_ORDER:
                metric_row = year_metrics[year_metrics['metric_name'] == metric]
                if not metric_row.empty:
                    scores.append(int(metric_row['metric_score'].values[0]))
                else:
                    scores.append('-')
            
            table_data[str(year)] = scores
        
        # Add the reference column at the end
        table_data['Reference'] = ref_scores
        
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
                summary_rows[str(year)] = [
                    int(year_summary['total_score'].values[0]),
                    f"{year_summary['comparison_to_reference'].values[0]:.2f}",
                    year_summary['biological_condition'].values[0]
                ]
            else:
                summary_rows[str(year)] = ['-', '-', '-']

        # Add the reference column (dynamically calculated)
        reference_total = sum(reference_scores.values())
        summary_rows['Reference'] = [reference_total, '1.00', '']
        
        return metrics_table, summary_rows
    
    except Exception as e:
        print(f"Error formatting {season} metrics table: {e}")
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
        print(f"Error creating {season} metrics table: {e}")
        # Return a simple error message if table creation fails
        return html.Div(f"Error creating {season} metrics table")

def create_macro_metrics_accordion():
    """
    Create an accordion layout for macroinvertebrate metrics tables.
    
    Returns:
        HTML Div containing accordion components for each season's metrics
    """
    try:
        # Get the data
        metrics_df, summary_df = get_macro_metrics_data_for_table()
        
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
        print(f"Error creating metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")

def create_macro_metrics_table():
    """
    Create tables showing macroinvertebrate metrics scores for both seasons (legacy function).
    
    Returns:
        HTML Div containing side-by-side tables for Summer and Winter metrics
    """
    try:
        # Get the data
        metrics_df, summary_df = get_macro_metrics_data_for_table()
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No data available")
        
        # Create tables for each season
        winter_table = create_macro_metrics_table_for_season(metrics_df, summary_df, 'Winter')
        summer_table = create_macro_metrics_table_for_season(metrics_df, summary_df, 'Summer')
        
        # Create a side-by-side layout 
        macro_tables = html.Div([
            dbc.Row([
                dbc.Col([
                    html.H5("Macroinvertebrate Metrics Scores", className="text-center mb-3")
                ], width=12) 
            ]),
            dbc.Row([
                dbc.Col([
                    html.H6("Winter Collections", className="text-center"),
                    winter_table
                ], width=6),  
                dbc.Col([
                    html.H6("Summer Collections", className="text-center"),
                    summer_table
                ], width=6) 
            ])
        ])
        
        return macro_tables
    
    except Exception as e:
        print(f"Error creating metrics tables: {e}")
        return html.Div(f"Error creating metrics tables: {str(e)}")

def create_macro_viz_with_table():
    """
    Create macroinvertebrate community visualization with metrics tables for the app.
    
    Returns:
        Tuple of (figure, metrics_tables) for inclusion in the app layout
    """
    try:
        # Get the line chart
        fig_macro = create_macro_viz()
        
        # Get the metrics tables
        metrics_tables = create_macro_metrics_table()
        
        # Return both components for inclusion in the app layout
        return fig_macro, metrics_tables
    
    except Exception as e:
        print(f"Error creating macroinvertebrate visualization with tables: {e}")
        # Return simple placeholders if error occurs
        fig = go.Figure()
        fig.update_layout(title="Error creating visualization")
        return fig, html.Div("Error loading metrics data")

# Test visualization if run directly
if __name__ == "__main__":
    fig = create_macro_viz()
    fig.show()