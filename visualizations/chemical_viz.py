"""
chemical_viz.py - Water Quality Chemical Data Visualization

This module creates visualizations for water quality chemical parameters including 
time series plots with threshold-based color coding and reference lines for 
Blue Thumb stream monitoring data.

Key Functions:
- create_time_series_plot(): Individual parameter time series with threshold highlighting
- create_all_parameters_view(): Multi-parameter subplot dashboard view
- Helper functions for threshold plotting, reference lines, and status color mapping

Parameters Supported:
- Dissolved Oxygen, pH, Soluble Nitrogen, Phosphorus, Chloride
- Status categories: Normal, Caution, Poor, Above/Below Normal for pH
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from plotly.subplots import make_subplots
from data_processing.data_queries import get_chemical_data_from_db
from data_processing.chemical_utils import KEY_PARAMETERS, get_reference_values
from callbacks.helper_functions import get_parameter_label, get_parameter_name
from visualizations.visualization_utils import create_empty_figure, create_error_figure, FONT_SIZES
from utils import setup_logging

logger = setup_logging("chemical_viz", category="visualization")

# Styling constants
COLORS = {
    'Normal': '#1e8449',      # Darker green
    'Caution': '#ff9800',     # Orange
    'Above Normal (Basic/Alkaline)': '#5e35b1', # Purple-blue 
    'Below Normal (Acidic)': '#f57c00', # Dark orange-red 
    'Poor': '#e74c3c',        # Softer red
    'Unknown': '#95a5a6'      # Gray
}

MARKER_SIZES = {
    'individual': 6,
    'dashboard': 4
}

# Helper functions
def _add_threshold_plot(fig, df, parameter, reference_values, marker_size, y_label, row=None, col=None):
    """Add threshold-based colored scatter plot with connecting lines and reference lines"""
    plot_df = df.copy()
    status_col = f'{parameter}_status'
    
    if status_col in df.columns:
        plot_df['status'] = df[status_col].fillna('Unknown')
    else:
        plot_df['status'] = 'Normal'
    
    # Add points colored by status
    for status_type, color in COLORS.items():
        if status_type == 'Unknown':
            continue
        mask = plot_df['status'] == status_type
        if mask.any():
            fig.add_trace(
                go.Scatter(
                    x=plot_df.loc[mask, 'Date'],
                    y=plot_df.loc[mask, parameter],
                    mode='markers',
                    marker=dict(size=marker_size, color=color),
                    name=status_type if row is None else f"{parameter} - {status_type}",
                    showlegend=(row is None),  # Only show legend for individual plots
                    legendgroup=parameter if row is not None else None,
                    hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br>' +
                                '<b>' + y_label + '</b>: %{y}<br>' +
                                '<b>Status</b>: ' + status_type +
                                '<extra></extra>'
                ),
                row=row, col=col
            )
    
    # Add connecting line
    fig.add_trace(
        go.Scatter(
            x=df['Date'],
            y=df[parameter],
            mode='lines',
            line=dict(color='gray', width=1),
            opacity=0.2,
            showlegend=False,
            hoverinfo='skip',
            legendgroup=parameter if row is not None else None
        ),
        row=row, col=col
    )
    
    # Add reference lines
    return _add_parameter_reference_lines(fig, parameter, df, reference_values, row, col)

def _add_standard_plot(fig, df, parameter, marker_size, y_label, row=None, col=None):
    """Add standard blue scatter plot with lines"""
    fig.add_trace(
        go.Scatter(
            x=df['Date'],
            y=df[parameter],
            mode='markers+lines',
            marker=dict(size=marker_size, color='blue'),
            line=dict(color='blue', width=1),
            name=parameter,
            opacity=0.7 if row is not None else 1.0,
            hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>' + y_label + '</b>: %{y}<extra></extra>'
        ),
        row=row, col=col
    )
    return fig

def _format_date_axes(fig, nticks=10):
    """Format x-axes to display years properly"""
    fig.update_xaxes(
        tickformat='%Y',
        tickmode='auto',
        nticks=nticks
    )
    return fig

def _add_parameter_reference_lines(fig, parameter, df, reference_values, row=None, col=None):
    """
    Add reference lines to the plot based on parameter thresholds.
    Can be used for both individual plots and subplots.
    """
    # Get date range for the lines
    x0 = df['Date'].min()
    x1 = df['Date'].max()
    
    # Helper function to add a reference line
    def add_reference_line(y_value, color, label=None, line_style=None):
        """Add a reference line to the figure."""
        if line_style is None:
            line_style = dict(width=1.5, dash='dash')
            
        # For subplot or main plot
        if row is not None and col is not None:
            fig.add_shape(
                type='line',
                x0=x0, x1=x1,
                y0=y_value, y1=y_value,
                line=dict(color=color, **line_style),
                opacity=0.7,
                row=row, col=col
            )
        else:
            # Add the line
            fig.add_shape(
                type='line',
                x0=x0, x1=x1,
                y0=y_value, y1=y_value,
                line=dict(color=color, **line_style),
                opacity=0.7,
                name=label
            )
            
            # Add annotation if requested and not in subplot
            if label:
                fig.add_annotation(
                    x=x0, y=y_value,
                    text=label,
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=FONT_SIZES['cell'], color=color),
                    opacity=0.7,
                    xshift=-5
                )
    
    # Add reference lines from the reference values dictionary
    if parameter in reference_values:
        try:
            ref = reference_values[parameter]
            
            if parameter == 'do_percent':
                if 'normal min' in ref:
                    add_reference_line(ref['normal min'], 'orange', "Normal Min")
                if 'normal max' in ref:
                    add_reference_line(ref['normal max'], 'orange', "Normal Max")
                if 'caution min' in ref:
                    add_reference_line(ref['caution min'], 'red', "Caution Min")
                if 'caution max' in ref:
                    add_reference_line(ref['caution max'], 'red', "Caution Max")
            
            elif parameter == 'pH':
                if 'normal min' in ref:
                    add_reference_line(ref['normal min'], 'orange', "Normal Min")
                if 'normal max' in ref:
                    add_reference_line(ref['normal max'], 'orange', "Normal Max")
            
            elif parameter in ['soluble_nitrogen', 'Phosphorus', 'Chloride']:
                if 'normal' in ref:
                    add_reference_line(ref['normal'], 'orange', "Caution")
                if 'caution' in ref:
                    add_reference_line(ref['caution'], 'red', "Poor")
                    
        except Exception as e:
            print(f"Error adding reference lines for {parameter}: {e}")
    
    return fig

def create_time_series_plot(df, parameter, reference_values, title=None, y_label=None, highlight_thresholds=True, site_name=None):
    """Generate time series plot for parameter with optional threshold highlighting"""
    # Check if we have data
    if len(df) == 0:
        return create_empty_figure(site_name, "chemical")
    
    # Use defaults if no custom values provided
    if title is None:
        parameter_name = get_parameter_name(parameter)
        title = f'{parameter_name} Over Time for {site_name}'
    if y_label is None:
        y_label = get_parameter_label('chem', parameter)
    
    # Create the base figure
    fig = go.Figure()
    
    # Add alternating year shading for individual parameter graphs
    years = df['Year'].unique()
    years.sort()
    x0 = df['Date'].min()
    x1 = df['Date'].max()
    
    for i, year in enumerate(years):
        if i % 2 == 0:  # Only shade alternate years
            year_start = pd.Timestamp(f"{year}-01-01")
            year_end = pd.Timestamp(f"{year}-12-31")
            # Ensure within data range
            if year_start < x0:
                year_start = x0
            if year_end > x1:
                year_end = x1
            
            fig.add_shape(
                type="rect",
                x0=year_start,
                x1=year_end,
                y0=0,
                y1=1,
                yref="paper",
                fillcolor="lightgray",
                opacity=0.1,
                layer="below",
                line_width=0,
            )
    
    # Set up color mapping for different threshold categories
    if highlight_thresholds and parameter in reference_values:
        try:
            fig = _add_threshold_plot(fig, df, parameter, reference_values, 
                                    MARKER_SIZES['individual'], y_label)
        except Exception as e:
            print(f"Error creating highlighted plot for {parameter}: {e}")
            fig = _add_standard_plot(fig, df, parameter, MARKER_SIZES['individual'], y_label)
    else:
        fig = _add_standard_plot(fig, df, parameter, MARKER_SIZES['individual'], y_label)
    
    # Calculate a small amount of padding (e.g., 2% of the date range)
    date_range = df['Date'].max() - df['Date'].min()
    padding = pd.Timedelta(days=int(date_range.days * 0.02))  # 2% padding
    
    # Update layout for better appearance
    fig.update_layout(
        title=title,
        xaxis_title='Year',
        yaxis_title=y_label,
        hovermode='closest',
        template='plotly_white',
        title_x=0.5,
        xaxis=dict(
            range=[df['Date'].min() - padding, df['Date'].max() + padding],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Format date axis better
    fig = _format_date_axes(fig, nticks=10)
    
    return fig

def create_all_parameters_view(df=None, parameters=None, reference_values=None, highlight_thresholds=True, get_param_name=None, site_name=None):
    """Create a subplot figure for all parameters with optional threshold highlighting"""
    # If no data is provided, get it from database
    if df is None or parameters is None or reference_values is None:
        try:
            df = get_chemical_data_from_db()
            parameters = KEY_PARAMETERS
            reference_values = get_reference_values()
        except Exception as e:
            print(f"Error loading chemical data: {e}")
            return create_error_figure(str(e))

    # If no parameter name function provided, use the standard function
    if get_param_name is None:
        get_param_name = get_parameter_name

    # Check if there is data
    if len(df) == 0:
        return create_empty_figure(site_name, "chemical")
    
    # Calculate rows and columns needed
    n_params = len(parameters)
    n_cols = 2  
    n_rows = (n_params + 1) // 2  
    
    # Create subplot structure with more spacing
    fig = make_subplots(
        rows=n_rows, 
        cols=n_cols,
        subplot_titles=[get_param_name(p) for p in parameters],
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )
    
    # Add each parameter plot to the appropriate subplot
    for i, param in enumerate(parameters):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        # Get the proper parameter label for hover text
        param_label = get_parameter_label('chem', param)
        
        try:
            # Set up color mapping if highlighting is enabled
            if highlight_thresholds and param in reference_values:
                fig = _add_threshold_plot(fig, df, param, reference_values, 
                                        MARKER_SIZES['dashboard'], param_label, row, col)
            else:
                fig = _add_standard_plot(fig, df, param, MARKER_SIZES['dashboard'], 
                                       param_label, row, col)
        except Exception as e:
            print(f"Error creating subplot for {param}: {e}")
            fig.add_annotation(
                text=f"Error displaying {param}",
                xref=f"x{i+1}",
                yref=f"y{i+1}",
                x=0.5,
                y=0.5,
                showarrow=False,
                row=row,
                col=col
            )
    
    # Update layout for better appearance
    fig.update_layout(
        height=350 * n_rows,
        title_text=f"Water Quality Parameters Over Time for {site_name}",
        title_x=0.5,              
        showlegend=False,
        template='plotly_white',
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    # Format all x-axes to show years nicely
    fig = _format_date_axes(fig, nticks=5)
    
    # Add y-axis titles and improve formatting
    for i, param in enumerate(parameters):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        # Get appropriate y-axis label
        y_label = get_parameter_label('chem', param)
        
        # Update y-axis title
        fig.update_yaxes(
            title_text=y_label,
            title_font=dict(size=FONT_SIZES['header']),
            tickfont=dict(size=FONT_SIZES['cell']),
            row=row, col=col
        )
    
    return fig

