"""
habitat_viz.py - Habitat Assessment Data Visualization

This module creates visualizations for habitat assessment data including line charts 
with grade threshold reference lines and data tables for Blue Thumb stream assessments.

Key Functions:
- create_habitat_viz(): Create line chart with habitat grade threshold lines
- add_habitat_grade_reference_lines(): Add reference lines for grades A, B, C, D, F
- create_habitat_table(): Create data table for habitat metrics
- create_habitat_metrics_accordion(): Create accordion layout for habitat metrics

Usage:
- Import functions for use in the main dashboard
- Habitat grades: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
"""

import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dash import html, dash_table
from utils import create_metrics_accordion, setup_logging

logger = setup_logging("habitat_viz", category="visualization")

# Styling constants
COLORS = {
    'line': '#3366CC',
    'marker': '#3366CC',
    'background': 'rgba(240, 248, 255, 0.8)',
    'grid': 'white',
    'habitat_grades': {
        'A': '#1e8449',    # Green (A grade)
        'B': '#7cb342',    # Light green (B grade)
        'C': '#ff9800',    # Orange (C grade)
        'D': '#e53e3e',    # Red-orange (D grade)
        'F': '#e74c3c'     # Red (F grade)
    },
    'default': '#666666'
}

FONT_SIZES = {
    'title': 16,
    'axis_title': 14,
    'header': 12,
    'cell': 11
}

# Habitat grade thresholds
HABITAT_GRADE_THRESHOLDS = {
    'A': 90,
    'B': 80,
    'C': 70,
    'D': 60
    # F is anything below 60
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
    return os.path.join(base_dir, 'data', 'processed', 'processed_habitat_data.csv')

def add_habitat_grade_reference_lines(fig, df):
    """
    Add reference lines for habitat grade thresholds to the figure.
    
    Args:
        fig: Plotly figure to add reference lines to
        df: DataFrame containing the data with year values
    
    Returns:
        Updated figure with reference lines
    """
    if df.empty:
        return fig
        
    # Get min and max year for reference lines
    x_min = df['Year'].min() - 1
    x_max = df['Year'].max() + 1
    
    # Add reference lines for each habitat grade threshold
    for grade, threshold in HABITAT_GRADE_THRESHOLDS.items():
        color = COLORS['habitat_grades'].get(grade, COLORS['default'])
        
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
            text=f"{grade}",
            showarrow=False,
            yshift=10
        )
    
    return fig

def create_habitat_viz(site_name=None):
    """
    Create habitat assessment visualization for the app.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Plotly figure: Line plot showing habitat scores over time with grade threshold lines.
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
            # Fall back to database data with site filtering
            from data_processing.data_queries import get_habitat_dataframe
            
            if site_name:
                data = get_habitat_dataframe(site_name)
            else:
                data = get_habitat_dataframe()
            
            if data.empty:
                # Fall back to hardcoded data if database is also empty
                data = pd.DataFrame({
                    'Year': [2012, 2016, 2022],
                    'Total_Points': [118.2, 88.5, 96.1]
                })
            else:
                # Rename columns to match expected format and include habitat_grade
                data = data.rename(columns={'year': 'Year', 'total_score': 'Total_Points'})

        # Create the line chart
        title = f'Habitat Assessment Scores Over Time for{site_name}' if site_name else 'Habitat Assessment Scores Over Time'
        fig = px.line(
            data, 
            x='Year', 
            y='Total_Points',
            markers=True,
            title=title,
            labels={'Total_Points': 'Habitat Assessment Score', 'Year': 'Year'}
        )

        # Add reference lines for habitat grades
        add_habitat_grade_reference_lines(fig, data)

        # Calculate dynamic y-axis range based on data
        max_value = data['Total_Points'].max()
        y_upper_limit = max(130, max_value * 1.1)  # Use at least 130 or 110% of max value

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
                range=[0, y_upper_limit],
                title_font=dict(size=FONT_SIZES['axis_title'])
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=data['Year'].tolist(),
                title_font=dict(size=FONT_SIZES['axis_title']),
                gridcolor=COLORS['grid']
            ),
            hovermode='closest',
            title_x=0.5,
            title_font=dict(size=FONT_SIZES['title']),
            height=500,
            margin=dict(l=50, r=30, t=50, b=10)
        )

        # Add hover data
        hover_text = []
        for _, row in data.iterrows():
            grade = row.get('habitat_grade', 'Unknown')
            hover_text.append(f"<b>Year</b>: {row['Year']}<br><b>Score</b>: {int(row['Total_Points'])}<br><b>Grade</b>: {grade}")
        
        fig.update_traces(
            text=hover_text,
            hovertemplate='%{text}<extra></extra>',
            hoverinfo='text'
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

def create_habitat_table(site_name=None):
    """
    Create a table showing habitat assessment scores from CSV file.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        HTML Div containing the habitat metrics table
    """
    try:
        # First try to find the correctly formatted file (as shown in screenshots)
        try:
            file_path = get_habitat_data_path()
            df = pd.read_csv(file_path)
            
            # Check if this is the raw processed data (needs restructuring)
            if 'instream_cover' in df.columns:
                # Restructure the data to match the format needed for the table
                if site_name:
                    # Filter by site name if provided
                    df = df[df['site_name'] == site_name]
                
                # Group by year and aggregate the habitat metrics
                yearly_data = {}
                for _, row in df.iterrows():
                    year = str(row['year'])
                    if year not in yearly_data:
                        yearly_data[year] = {}
                    
                    # Map column names to parameter names
                    parameter_mapping = {
                        'instream_cover': 'Instream Cover',
                        'pool_bottom_substrate': 'Pool Bottom Substrate', 
                        'pool_variability': 'Pool Variability',
                        'canopy_cover': 'Canopy Cover Shading',
                        'rocky_runs_riffles': 'Presence of Rocky Runs or Riffles',
                        'flow': 'Flow',
                        'channel_alteration': 'Channel Alteration',
                        'channel_sinuosity': 'Channel Sinuosity',
                        'bank_stability': 'Bank Stability',
                        'bank_vegetation_stability': 'Bank Vegetation Stability',
                        'streamside_cover': 'Streamside Cover',
                        'total_score': 'Total Points'
                    }
                    
                    for col, param in parameter_mapping.items():
                        if col in row and pd.notna(row[col]):
                            yearly_data[year][param] = round(float(row[col]), 1)
                
                # Convert to DataFrame format expected by the table
                table_data = []
                for param in HABITAT_METRICS:
                    row_data = {'Parameter': param}
                    for year in sorted(yearly_data.keys()):
                        if param in yearly_data[year]:
                            row_data[year] = yearly_data[year][param]
                        else:
                            row_data[year] = ''
                    table_data.append(row_data)
                
                df_filtered = pd.DataFrame(table_data)
            else:
                # Assume this is already the correct format
                df_filtered = df[df['Parameter'].isin(HABITAT_METRICS)]
        except Exception as e:
            # If file doesn't exist or has issues, return error message
            return html.Div(f"Error: Cannot access habitat data from processed_habitat_data.csv. Details: {str(e)}")
        
        # Check if we have any data after processing
        if df_filtered.empty:
            site_msg = f" for site '{site_name}'" if site_name else ""
            return html.Div(f"No habitat assessment data available{site_msg} in processed_habitat_data.csv.")
        
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
                    'if': {'filter_query': '{Parameter} = "Total Points"'},
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
        # Fall back to database data with site filtering
        try:
            from data_processing.data_queries import get_habitat_metrics_data_for_table
            
            # Get data from database with site filtering
            df = get_habitat_metrics_data_for_table(site_name)
            
            if df.empty:
                return html.Div(f"No habitat assessment data available{' for ' + site_name if site_name else ''}.")
            
            # Create table from database data
            table = dash_table.DataTable(
                id='habitat-metrics-table',
                columns=[{"name": col, "id": col} for col in df.columns],
                data=df.to_dict('records'),
                style_table={
                    'maxWidth': '100%',
                    'overflowX': 'auto',
                    'height': '500px'
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
                        'if': {'filter_query': '{Parameter} = "Total Points"'},
                        'borderTop': '2px solid black',
                        'fontWeight': 'bold'
                    }
                ]
            )
            
            return html.Div([table])
            
        except Exception as db_error:
            print(f"Error loading habitat data from database: {db_error}")
            return html.Div(f"Error loading habitat assessment data: {str(e)}")


def create_habitat_metrics_accordion(site_name=None):
    """
    Create an accordion layout for habitat metrics table.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        HTML Div containing accordion component with habitat metrics table
    """
    try:
        table = create_habitat_table(site_name)
        return create_metrics_accordion(table, "Habitat Assessment Scores", "habitat-accordion")
    except Exception as e:
        print(f"Error creating habitat metrics accordion: {e}")
        return html.Div(f"Error creating habitat metrics accordion: {str(e)}")
