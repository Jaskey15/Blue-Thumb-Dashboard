import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
from data_processing.fish_processing import get_fish_dataframe, get_fish_metrics_data_for_table
from utils import create_metrics_accordion, setup_logging

logger = setup_logging("fish_viz", category="visualization")

# Styling constants
COLORS = {
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

# Integrity class thresholds
INTEGRITY_THRESHOLDS = {
    'Excellent': 0.97,
    'Good': 0.8,
    'Fair': 0.67,
    'Poor': 0.47
}

# Reference metrics configuration
METRIC_ORDER = [
    'Total No. of species',
    'No. of sensitive benthic species', 
    'No. of sunfish species',
    'No. of intolerant species',
    'Proportion tolerant individuals',
    'Proportion insectivorous cyprinid',
    'Proportion lithophilic spawners'
]

REFERENCE_SCORES = {
    'Total No. of species': 5,
    'No. of sensitive benthic species': 5, 
    'No. of sunfish species': 5,
    'No. of intolerant species': 5,
    'Proportion tolerant individuals': 1,
    'Proportion insectivorous cyprinid': 1,
    'Proportion lithophilic spawners': 3
}

REFERENCE_TOTAL_SCORE = 25  # Ouachita Mountains reference score

def create_fish_viz():
    """
    Create fish community visualization for the app.
    
    Returns:
        Plotly figure: Line plot showing IBI scores over time.
    """
    try:
        # Get fish data from the database
        fish_df = get_fish_dataframe()
        
        if fish_df.empty:
            # Return an empty figure with a message if no data
            fig = go.Figure()
            fig.update_layout(
                title="No fish data available",
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

        # Create a line plot for fish data
        fig_fish = px.line(
            fish_df, 
            x='year', 
            y='comparison_to_reference',
            markers=True,
            title='IBI Scores Over Time',
            labels={
                'year': 'Year',
                'comparison_to_reference': 'IBI Score (Compared to Reference)'
            }
        )

        # Add reference lines for integrity classes
        add_integrity_reference_lines(fig_fish, fish_df)

        # Improve the layout
        fig_fish.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=fish_df['year'].tolist(),
                title_font=dict(size=FONT_SIZES['axis_title'])
            ),
            yaxis=dict(
                range=[0, 1.1],
                tickformat='.2f',
                title_font=dict(size=FONT_SIZES['axis_title'])
            ),
            title_x=0.5,
            title_font=dict(size=FONT_SIZES['title']),
            hovermode='x unified'
        )

        # Add hover data
        fig_fish.update_traces(
            hovertemplate='<b>Year:</b> %{x}<br><b>Score:</b> %{y:.2f}<extra></extra>'
        )

        return fig_fish
    
    except Exception as e:
        print(f"Error creating fish visualization: {e}")
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

def add_integrity_reference_lines(fig, df):
    """
    Add reference lines for integrity class thresholds to the figure.
    
    Args:
        fig: Plotly figure to add reference lines to
        df: DataFrame containing the data with year values
    
    Returns:
        Updated figure with reference lines
    """
    # Get min and max year for reference lines
    x_min = df['year'].min() - 1
    x_max = df['year'].max() + 1
    
    # Add reference lines for each integrity threshold
    for integrity_class, threshold in INTEGRITY_THRESHOLDS.items():
        color = COLORS.get(integrity_class.lower(), COLORS['default'])
        
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
            text=integrity_class,
            showarrow=False,
            yshift=10
        )
    
    return fig

def format_fish_metrics_table(metrics_df, summary_df):
    """
    Format the fish metrics data into a table structure with reference values.
    
    Args:
        metrics_df: DataFrame containing metrics data
        summary_df: DataFrame containing summary scores
    
    Returns:
        Tuple of (metrics_table, summary_rows) DataFrames
    """
    try:
        # Get unique years
        years = sorted(metrics_df['year'].unique())
        
        # Create a dictionary to hold the table data
        table_data = {'Metric': METRIC_ORDER}
        
        # Add reference scores column
        ref_scores = [str(REFERENCE_SCORES.get(metric, '-')) for metric in METRIC_ORDER]
        
        # Add columns for each year
        for year in years:
            year_metrics = metrics_df[metrics_df['year'] == year]
            
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
            'Metric': ['Total Score', 'Comparison to Reference', 'Integrity Class'],
        })
        
        # Add the summary data for each year
        for year in years:
            year_summary = summary_df[summary_df['year'] == year]
            if not year_summary.empty:
                summary_rows[str(year)] = [
                    int(year_summary['total_score'].values[0]),
                    f"{year_summary['comparison_to_reference'].values[0]:.2f}",
                    year_summary['integrity_class'].values[0]
                ]
            else:
                summary_rows[str(year)] = ['-', '-', '-']
        
        # Add reference values for summary rows
        summary_rows['Reference'] = [REFERENCE_TOTAL_SCORE, '1.00', '']
        
        return metrics_table, summary_rows
    
    except Exception as e:
        print(f"Error formatting fish metrics table: {e}")
        # Return empty DataFrames
        return pd.DataFrame({'Metric': METRIC_ORDER}), pd.DataFrame({'Metric': ['Error']})

def create_metrics_table_styles(metrics_table):
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
            'maxWidth': '120px'
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

def create_fish_metrics_table_for_accordion():
    """
    Create a metrics table for fish data to display in accordion.
    
    Returns:
        Dash DataTable component
    """
    try:
        # Get the data
        metrics_df, summary_df = get_fish_metrics_data_for_table()
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No data available")
        
        # Format the data into table structure with reference values added
        metrics_table, summary_rows = format_fish_metrics_table(metrics_df, summary_df)
        
        # Combine metrics and summary rows
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
        
        # Get styling for the table
        styles = create_metrics_table_styles(metrics_table)
        
        # Create the table component
        table = dash_table.DataTable(
            id='fish-metrics-table',
            columns=[{"name": col, "id": col} for col in full_table.columns],
            data=full_table.to_dict('records'),
            **styles
        )
        
        return table
    
    except Exception as e:
        print(f"Error creating fish metrics table for accordion: {e}")
        # Return a simple error message if table creation fails
        return html.Div(f"Error creating fish metrics table: {str(e)}")

def create_fish_metrics_accordion():
    """
    Create an accordion layout for fish metrics table.
    
    Returns:
        HTML Div containing accordion component with metrics table
    """
    try:
        # Get the table component
        table = create_fish_metrics_table_for_accordion()
        
        # Use the reusable accordion function
        return create_metrics_accordion(table, "Fish Collection Metrics", "fish-accordion")
    
    except Exception as e:
        print(f"Error creating fish metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")

def create_fish_metrics_table():
    """
    Create a table showing fish metrics scores (legacy function).
    
    Returns:
        Dash DataTable component
    """
    try:
        # Get the data
        metrics_df, summary_df = get_fish_metrics_data_for_table()
        
        if metrics_df.empty or summary_df.empty:
            return html.Div("No data available")
        
        # Format the data into table structure with reference values added
        metrics_table, summary_rows = format_fish_metrics_table(metrics_df, summary_df)
        
        # Combine metrics and summary rows
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
        
        # Get styling for the table
        styles = create_metrics_table_styles(metrics_table)
        
        # Create the table component
        table = dash_table.DataTable(
            id='fish-metrics-table',
            columns=[{"name": col, "id": col} for col in full_table.columns],
            data=full_table.to_dict('records'),
            **styles
        )
        
        return table
    
    except Exception as e:
        print(f"Error creating fish metrics table: {e}")
        return html.Div(f"Error creating fish metrics table: {str(e)}")

def create_fish_viz_with_table():
    """
    Create fish community visualization with metrics table for the app.
    
    Returns:
        Tuple of (figure, metrics_table) for inclusion in the app layout
    """
    try:
        # Get the line chart
        fig_fish = create_fish_viz()
        
        # Get the metrics table
        metrics_table = create_fish_metrics_table()
        
        # Return both components for inclusion in the app layout
        return fig_fish, metrics_table
    
    except Exception as e:
        print(f"Error creating fish visualization with table: {e}")
        # Return simple placeholders if error occurs
        fig = go.Figure()
        fig.update_layout(title="Error creating visualization")
        return fig, html.Div("Error loading fish metrics data")

# Test visualization if run directly
if __name__ == "__main__":
    fig = create_fish_viz()
    fig.show()