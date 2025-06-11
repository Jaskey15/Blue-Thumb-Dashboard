import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dash import dash_table, html
from data_processing.data_queries import get_fish_dataframe, get_fish_metrics_data_for_table
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
    'Good': 0.76,
    'Fair': 0.60,
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

def create_fish_viz(site_name=None):
    """
    Create fish community visualization for the app.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing IBI scores over time.
    """
    try:
        # Get fish data from the database - now with site filtering
        fish_df = get_fish_dataframe(site_name)
        
        if fish_df.empty:
            # Return an empty figure with a message if no data
            fig = go.Figure()
            site_msg = f" for {site_name}" if site_name else ""
            fig.update_layout(
                title=f"No fish data available{site_msg}",
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
        title = f"IBI Scores Over Time - {site_name}" if site_name else "IBI Scores Over Time"
        fig_fish = px.line(
            fish_df, 
            x='year', 
            y='comparison_to_reference',
            markers=True,
            title=title,
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
        logger.error(f"Error creating fish visualization for {site_name}: {e}")
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
    if df.empty:
        return fig
        
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
        if metrics_df.empty or summary_df.empty:
            return pd.DataFrame({'Metric': METRIC_ORDER}), pd.DataFrame({'Metric': ['No Data']})
            
        # Get unique years
        years = sorted(metrics_df['year'].unique())
        
        # Create a dictionary to hold the table data
        table_data = {'Metric': METRIC_ORDER}
                
        # Add columns for each year
        for year in years:
            year_metrics = metrics_df[metrics_df['year'] == year]
            
            # Add a column for this year's scores
            scores = []
            for metric in METRIC_ORDER:
                metric_row = year_metrics[year_metrics['metric_name'] == metric]
                if not metric_row.empty:
                    # Convert to int safely
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
            'Metric': ['Total Score', 'Comparison to Reference', 'Integrity Class'],
        })
        
        # Add the summary data for each year
        for year in years:
            year_summary = summary_df[summary_df['year'] == year]
            if not year_summary.empty:
                try:
                    total_score = int(year_summary['total_score'].values[0])
                    comparison = f"{year_summary['comparison_to_reference'].values[0]:.2f}"
                    integrity = year_summary['integrity_class'].values[0]
                    summary_rows[str(year)] = [total_score, comparison, integrity]
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing summary data for year {year}: {e}")
                    summary_rows[str(year)] = ['-', '-', '-']
            else:
                summary_rows[str(year)] = ['-', '-', '-']
        
        return metrics_table, summary_rows
    
    except Exception as e:
        logger.error(f"Error formatting fish metrics table: {e}")
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

def create_fish_metrics_table_for_accordion(site_name=None):
    """
    Create a metrics table for fish data to display in accordion.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Dash DataTable component
    """
    try:
        # Get the data with site filtering
        metrics_df, summary_df = get_fish_metrics_data_for_table(site_name)
        
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
        logger.error(f"Error creating fish metrics table for accordion: {e}")
        # Return a simple error message if table creation fails
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
        # Get the table component with site filtering
        table = create_fish_metrics_table_for_accordion(site_name)
        
        # Use the reusable accordion function
        return create_metrics_accordion(table, "Fish Collection Metrics", "fish-accordion")
    
    except Exception as e:
        logger.error(f"Error creating fish metrics accordion: {e}")
        return html.Div(f"Error creating metrics accordion: {str(e)}")

# Legacy functions maintained for compatibility
def create_fish_metrics_table(site_name=None):
    """Create a table showing fish metrics scores (legacy function)."""
    return create_fish_metrics_table_for_accordion(site_name)

def create_fish_viz_with_table(site_name=None):
    """Create fish community visualization with metrics table for the app."""
    try:
        fig_fish = create_fish_viz(site_name)
        metrics_table = create_fish_metrics_table(site_name)
        return fig_fish, metrics_table
    except Exception as e:
        logger.error(f"Error creating fish visualization with table: {e}")
        fig = go.Figure()
        fig.update_layout(title="Error creating visualization")
        return fig, html.Div("Error loading fish metrics data")

# Test visualization if run directly
if __name__ == "__main__":
    fig = create_fish_viz()
    fig.show()