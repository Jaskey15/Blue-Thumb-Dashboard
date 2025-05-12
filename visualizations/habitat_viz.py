import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dash import html, dash_table
from utils import create_metrics_accordion

# Styling constants
COLORS = {
    'line': '#3366CC',
    'marker': '#3366CC',
    'background': 'rgba(240, 248, 255, 0.8)',
    'grid': 'white'
}

FONT_SIZES = {
    'title': 14,
    'axis_title': 14,
    'header': 12,
    'cell': 11
}

# Habitat metrics to include in the table
HABITAT_METRICS = [
    'Instream Cover', 'Pool Bottom Substrate', 'Pool Variability',
    'Canopy Cover Shading', 'Presence of Rocky Runs or Riffles',
    'Flow', 'Channel Alteration', 'Channel Sinuosity',
    'Bank Stability', 'Bank Vegetation Stability', 'Streamside Cover',
    'Total Points'
]

def get_habitat_data_path():
    """
    Get the path to the habitat assessment data file.
    
    Returns:
        str: Full path to the habitat assessment data CSV file
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, 'data', 'processed', 'habitat_assessment_data.csv')

def create_habitat_viz():
    """
    Create habitat assessment visualization for the app.
    
    Returns:
        Plotly figure: Line plot showing habitat scores over time.
    """
    try:
        # Try to read from the same CSV file used in create_habitat_table
        try:
            file_path = get_habitat_data_path()
            df = pd.read_csv(file_path)
            
            # Extract years and total points
            total_points_row = df[df['Parameter'] == 'Total Points']
            years = [int(col) for col in total_points_row.columns if col.isdigit()]
            total_points = [float(total_points_row[str(year)].values[0]) for year in years]
            
            # Create a DataFrame in the format needed for the chart
            data = pd.DataFrame({
                'Year': years,
                'Total_Points': total_points
            })
            
        except Exception as e:
            print(f"Error reading habitat data from file: {e}")
            # Fall back to hardcoded data if file read fails
            data = pd.DataFrame({
                'Year': [2012, 2016, 2022],
                'Total_Points': [118.2, 88.5, 96.1]
            })

        # Create the line chart
        fig = px.line(
            data, 
            x='Year', 
            y='Total_Points',
            markers=True,
            title='Habitat Assessment Scores Over Time',
            labels={'Total_Points': 'Habitat Assessment Score', 'Year': 'Year'}
        )

        # Customize styling
        fig.update_traces(
            line=dict(color=COLORS['line'], width=2.5),
            marker=dict(size=6, color=COLORS['marker'], line=dict(width=1, color=COLORS['marker']))
        )

        # Update layout
        fig.update_layout(
            plot_bgcolor=COLORS['background'],
            font=dict(family='Arial', size=12),
            yaxis=dict(
                gridcolor=COLORS['grid'],
                gridwidth=1,
                zeroline=False,
                range=[0, 130],
                title_font=dict(size=FONT_SIZES['axis_title'])
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=data['Year'].tolist(),
                title_font=dict(size=FONT_SIZES['axis_title']),
                gridcolor=COLORS['grid']
            ),
            hovermode='x unified',
            title_x=0.5,
            title_font=dict(size=FONT_SIZES['title']),
            height=500,
            margin=dict(l=50, r=30, t=50, b=10)
        )

        # Add hover data
        fig.update_traces(
            hovertemplate='<b>Year:</b> %{x}<br><b>Score:</b> %{y}<extra></extra>'
        )

        return fig
        
    except Exception as e:
        print(f"Error creating habitat visualization: {e}")
        # Return empty figure with error message
        fig = go.Figure()
        fig.update_layout(
            title="Error creating habitat visualization",
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

def create_habitat_table():
    """
    Create a table showing habitat assessment scores from CSV file.
    
    Returns:
        HTML Div containing the habitat metrics table
    """
    try:
        # Determine the file path
        file_path = get_habitat_data_path()
        
        # Load data from CSV file
        df = pd.read_csv(file_path)
        
        # Select only the rows that are habitat metrics
        df_filtered = df[df['Parameter'].isin(HABITAT_METRICS)]
        
        # Create the table component
        table = dash_table.DataTable(
            id='habitat-metrics-table',
            columns=[{"name": col, "id": col} for col in df_filtered.columns],
            data=df_filtered.to_dict('records'),
            style_table={
                'maxWidth': '100%',
                'overflowX': 'auto',
                'height': '500px'  # Match the height of the graph
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'fontSize': FONT_SIZES['header']
            },
            style_cell={
                'textAlign': 'center',
                'padding': '5px',
                'fontFamily': 'Arial',
                'fontSize': FONT_SIZES['cell'],
                'minWidth': '50px',
                'maxWidth': '150px'
            },
            style_cell_conditional=[
                {
                    'if': {'column_id': 'Parameter'},
                    'textAlign': 'left',
                    'fontWeight': 'bold'
                }
            ],
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Parameter} contains "Total Points"'},
                    'borderTop': '2px solid black',
                    'fontWeight': 'bold'
                }
            ]
        )
        
        # Wrap table in a container
        return html.Div([
            table
        ], style={"marginBottom": "0px", "paddingBottom": "0px"})
    
    except Exception as e:
        print(f"Error creating habitat table: {e}")
        return html.Div(f"Error loading habitat assessment data: {str(e)}")
    
def create_habitat_metrics_accordion():
    """
    Create an accordion layout for habitat metrics table.
    
    Returns:
        HTML Div containing accordion component with habitat metrics table
    """
    try:
        table = create_habitat_table()
        return create_metrics_accordion(table, "Habitat Assessment Scores", "habitat-accordion")
    except Exception as e:
        print(f"Error creating habitat metrics accordion: {e}")
        return html.Div(f"Error creating habitat metrics accordion: {str(e)}")