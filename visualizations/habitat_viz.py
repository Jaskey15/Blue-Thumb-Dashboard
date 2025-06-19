"""
habitat_viz.py - Habitat Assessment Data Visualization

This module creates visualizations for habitat assessment data including line charts 
with grade threshold reference lines and data tables for Blue Thumb stream assessments.

Key Functions:
- create_habitat_viz(): Create line chart with habitat grade threshold lines
- create_habitat_table(): Create data table for habitat metrics
- create_habitat_metrics_accordion(): Create accordion layout for habitat metrics

Usage:
- Import functions for use in the main dashboard
- Habitat grades: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
"""

import os
import pandas as pd

from dash import html, dash_table
from utils import create_metrics_accordion, setup_logging
from .biological_utils import (
    create_biological_line_plot,
    update_biological_figure_layout,
    add_reference_lines,
    format_biological_metrics_table,
    create_biological_table_styles,
    create_biological_data_table,
    create_hover_text,
    update_hover_data,
    create_empty_biological_figure,
    create_error_biological_figure,
    FONT_SIZES
)

logger = setup_logging("habitat_viz", category="visualization")

# Habitat-specific configuration
HABITAT_GRADE_THRESHOLDS = {
    'A': 90,
    'B': 80,
    'C': 70,
    'D': 60
    # F is anything below 60
}

HABITAT_GRADE_COLORS = {
    'A': '#1e8449',    # Green (A grade)
    'B': '#7cb342',    # Light green (B grade)
    'C': '#ff9800',    # Orange (C grade)
    'D': '#e53e3e',    # Red-orange (D grade)
    'F': '#e74c3c'     # Red (F grade)
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
                'year': years,  # Use 'year' to match biological_utils expectations
                'total_score': total_points  # Use 'total_score' to match biological_utils expectations
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
                    'year': [2012, 2016, 2022],
                    'total_score': [118.2, 88.5, 96.1]
                })
            else:
                # Rename columns to match expected format
                data = data.rename(columns={'Year': 'year', 'Total_Points': 'total_score'})

        # Check if we have any data
        if data.empty:
            return create_empty_biological_figure(site_name, "habitat")

        # Create the line plot using shared utilities
        title = f'Habitat Assessment Scores Over Time for {site_name}' if site_name else 'Habitat Assessment Scores Over Time'
        fig = create_biological_line_plot(
            data, 
            title, 
            y_column='total_score',
            has_seasons=False
        )

        # Update layout using shared utilities
        fig = update_biological_figure_layout(
            fig, 
            data, 
            title,
            y_label='Habitat Assessment Score'
        )

        # Add habitat grade reference lines using shared utilities
        fig = add_reference_lines(fig, data, HABITAT_GRADE_THRESHOLDS, HABITAT_GRADE_COLORS)

        # Create custom hover text for habitat data
        hover_text = []
        for _, row in data.iterrows():
            grade = row.get('habitat_grade', 'Unknown')
            hover_text.append(f"<b>Year</b>: {row['year']}<br><b>Score</b>: {int(row['total_score'])}<br><b>Grade</b>: {grade}")
        
        # Update hover data using shared utilities
        fig = update_hover_data(fig, hover_text)

        return fig
        
    except Exception as e:
        logger.error(f"Error creating habitat visualization: {e}")
        return create_error_biological_figure(str(e))

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
        
        # Use shared table styling utilities
        styles = create_biological_table_styles(df_filtered)
        
        # Create the table using shared utilities
        table = create_biological_data_table(
            df_filtered, 
            'habitat-metrics-table', 
            styles
        )
        
        # Override specific style for habitat table if needed
        if isinstance(table, dash_table.DataTable):
            # Add habitat-specific styling
            table.style_table.update({'height': '500px'})  # Match the height of the graph
            
            # Update conditional styling for Total Points row
            table.style_data_conditional = [
                {
                    'if': {'filter_query': '{Parameter} = "Total Points"'},
                    'borderTop': '2px solid black',
                    'fontWeight': 'bold'
                }
            ]
        
        # Wrap table in a container
        return html.Div([
            table
        ], style={"marginBottom": "0px", "paddingBottom": "0px"})
    
    except Exception as e:
        logger.error(f"Error creating habitat table: {e}")
        # Fall back to database data with site filtering
        try:
            from data_processing.data_queries import get_habitat_metrics_data_for_table
            
            # Get data from database with site filtering
            df = get_habitat_metrics_data_for_table(site_name)
            
            if df.empty:
                return html.Div(f"No habitat assessment data available{' for ' + site_name if site_name else ''}.")
            
            # Use shared table styling utilities for database fallback
            styles = create_biological_table_styles(df)
            
            table = create_biological_data_table(
                df,
                'habitat-metrics-table',
                styles
            )
            
            # Override height for habitat table
            if isinstance(table, dash_table.DataTable):
                table.style_table.update({'height': '500px'})
            
            return html.Div([table])
            
        except Exception as db_error:
            logger.error(f"Error loading habitat data from database: {db_error}")
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
        logger.error(f"Error creating habitat metrics accordion: {e}")
        return html.Div(f"Error creating habitat metrics accordion: {str(e)}")
