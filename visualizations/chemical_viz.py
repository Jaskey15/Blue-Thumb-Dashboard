"""
Chemical parameter visualization with status-based coloring and threshold analysis.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_processing.chemical_utils import KEY_PARAMETERS, get_reference_values
from data_processing.data_queries import get_chemical_data_from_db
from utils import get_parameter_label, get_parameter_name, setup_logging
from visualizations.visualization_utils import (
    FONT_SIZES,
    create_empty_figure,
    create_error_figure,
)

logger = setup_logging("chemical_viz", category="visualization")

# Status-based color scheme
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

# Detection limit handling notes
BDL_FOOTNOTES = {
    'Phosphorus': '*Phosphorus values below detection limit (BDL) have been converted to 0.005 mg/L for analysis purposes.',
    'soluble_nitrogen': '*Soluble nitrogen component values below detection limit (BDL) have been converted (nitrate: 0.3, nitrite: 0.03, ammonia: 0.03) for analysis purposes.'
}

# Helper functions
def _add_threshold_plot(fig, df, parameter, reference_values, marker_size, y_label, row=None, col=None):
    """
    Add scatter plot with status-based coloring and threshold reference lines.
    """
    plot_df = df.copy()
    status_col = f'{parameter}_status'
    
    if status_col in df.columns:
        plot_df['status'] = df[status_col].fillna('Unknown')
    else:
        plot_df['status'] = 'Normal'
    
    # Status-based marker coloring
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
                    hovertemplate='<b>Date</b>: %{x|%m-%d-%Y}<br>' +
                                '<b>' + y_label + '</b>: %{y}<br>' +
                                '<b>Status</b>: ' + status_type +
                                '<extra></extra>'
                ),
                row=row, col=col
            )
    
    # Connecting line for trend visualization
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
    
    return _add_parameter_reference_lines(fig, parameter, df, reference_values, row, col)

def _add_standard_plot(fig, df, parameter, marker_size, y_label, row=None, col=None):
    """
    Adds basic scatter plot with connecting lines.
    
    Args:
        fig: Plotly figure to add traces to
        df: DataFrame with chemical data
        parameter: Chemical parameter name
        marker_size: Point size for scatter plot
        y_label: Y-axis label text
        row: Optional subplot row index
        col: Optional subplot column index
    """
    fig.add_trace(
        go.Scatter(
            x=df['Date'],
            y=df[parameter],
            mode='markers+lines',
            marker=dict(size=marker_size, color='blue'),
            line=dict(color='blue', width=1),
            name=parameter,
            opacity=0.7 if row is not None else 1.0,
            hovertemplate='<b>Date</b>: %{x|%m-%d-%Y}<br><b>' + y_label + '</b>: %{y}<extra></extra>'
        ),
        row=row, col=col
    )
    return fig

def _format_date_axes(fig, nticks=10):
    """
    Formats x-axes to display years consistently.
    
    Args:
        fig: Plotly figure to format
        nticks: Number of year ticks to display
    """
    fig.update_xaxes(
        tickformat='%Y',
        tickmode='auto',
        nticks=nticks
    )
    return fig

def _add_parameter_reference_lines(fig, parameter, df, reference_values, row=None, col=None):
    """
    Adds threshold reference lines with labels.
    
    Args:
        fig: Plotly figure to add lines to
        parameter: Chemical parameter name
        df: DataFrame with chemical data
        reference_values: Dictionary of threshold values
        row: Optional subplot row index
        col: Optional subplot column index
    """
    # Get date range for lines
    x0 = df['Date'].min()
    x1 = df['Date'].max()
    
    def add_reference_line(y_value, color, label=None, line_style=None):
        """Add a single threshold line with optional labeling."""
        if line_style is None:
            line_style = dict(width=1.5, dash='dash')
            
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
            fig.add_shape(
                type='line',
                x0=x0, x1=x1,
                y0=y_value, y1=y_value,
                line=dict(color=color, **line_style),
                opacity=0.7,
                name=label
            )
            
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
    
    # Parameter-specific threshold handling
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
    """
    Creates time series plot for a single chemical parameter.
    
    Args:
        df: DataFrame with chemical data
        parameter: Chemical parameter to plot
        reference_values: Dictionary of threshold values
        title: Optional custom title
        y_label: Optional custom y-axis label
        highlight_thresholds: If True, color points by status
        site_name: Optional site name for empty plot
    
    Returns:
        Plotly figure with time series plot
    """
    if len(df) == 0:
        return create_empty_figure(site_name, "chemical")
    
    if title is None:
        parameter_name = get_parameter_name(parameter)
        title = f'{parameter_name} Over Time for {site_name}'
    if y_label is None:
        y_label = get_parameter_label('chem', parameter)
    
    fig = go.Figure()
    
    # Alternating year background shading for trend clarity
    years = df['Year'].unique()
    years.sort()
    x0 = df['Date'].min()
    x1 = df['Date'].max()
    
    for i, year in enumerate(years):
        if i % 2 == 0:  # Shade alternate years
            year_start = pd.Timestamp(f"{year}-01-01")
            year_end = pd.Timestamp(f"{year}-12-31")
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
    
    # Data visualization with threshold highlighting
    if highlight_thresholds and parameter in reference_values:
        try:
            fig = _add_threshold_plot(fig, df, parameter, reference_values, 
                                    MARKER_SIZES['individual'], y_label)
        except Exception as e:
            print(f"Error creating highlighted plot for {parameter}: {e}")
            fig = _add_standard_plot(fig, df, parameter, MARKER_SIZES['individual'], y_label)
    else:
        fig = _add_standard_plot(fig, df, parameter, MARKER_SIZES['individual'], y_label)
    
    # Date range padding for visual clarity
    date_range = df['Date'].max() - df['Date'].min()
    padding = pd.Timedelta(days=int(date_range.days * 0.02))
    
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
    
    # Detection limit disclosure when applicable
    if parameter in BDL_FOOTNOTES:
        fig.add_annotation(
            text=BDL_FOOTNOTES[parameter],
            xref="paper", yref="paper",
            x=0, y=-0.20,
            xanchor='left', yanchor='top',
            showarrow=False,
            font=dict(size=10, color="gray", style="italic")
        )
    
    fig = _format_date_axes(fig, nticks=10)
    
    return fig

def create_all_parameters_view(df=None, parameters=None, reference_values=None, highlight_thresholds=True, get_param_name=None, site_name=None):
    """
    Creates dashboard view with subplots for all chemical parameters.
    
    Args:
        df: Optional DataFrame with chemical data
        parameters: Optional list of parameters to display
        reference_values: Optional dictionary of threshold values
        highlight_thresholds: If True, color points by status
        get_param_name: Optional function to get parameter display names
        site_name: Optional site name for empty plot
    
    Returns:
        Plotly figure with parameter subplots
    """
    # Load data if not provided
    if df is None or parameters is None or reference_values is None:
        try:
            df = get_chemical_data_from_db()
            parameters = KEY_PARAMETERS
            reference_values = get_reference_values()
        except Exception as e:
            print(f"Error loading chemical data: {e}")
            return create_error_figure(str(e))

    if get_param_name is None:
        get_param_name = get_parameter_name

    if len(df) == 0:
        return create_empty_figure(site_name, "chemical")
    
    # Subplot grid calculation
    n_params = len(parameters)
    n_cols = 2  
    n_rows = (n_params + 1) // 2  
    
    fig = make_subplots(
        rows=n_rows, 
        cols=n_cols,
        subplot_titles=[get_param_name(p) for p in parameters],
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )
    
    # Parameter plot generation
    for i, param in enumerate(parameters):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        param_label = get_parameter_label('chem', param)
        
        try:
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
    
    fig.update_layout(
        height=350 * n_rows,
        title_text=f"Water Quality Parameters Over Time for {site_name}",
        title_x=0.5,              
        showlegend=False,
        template='plotly_white',
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    fig = _format_date_axes(fig, nticks=5)
    
    # Y-axis labeling for each subplot
    for i, param in enumerate(parameters):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        y_label = get_parameter_label('chem', param)
        
        fig.update_yaxes(
            title_text=y_label,
            title_font=dict(size=FONT_SIZES['header']),
            tickfont=dict(size=FONT_SIZES['cell']),
            row=row, col=col
        )

    return fig

