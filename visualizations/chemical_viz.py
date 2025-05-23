import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from plotly.subplots import make_subplots
from data_processing.chemical_processing import process_chemical_data
from utils import setup_logging

logger = setup_logging("chemical_viz", category="visualization")

# Styling constants
COLORS = {
    'Normal': '#1e8449',      # Darker green
    'Caution': '#ff9800',     # Orange
    'Above Normal': '#ff9800',# Orange
    'Below Normal': '#ff9800',# Orange
    'Outside Normal': '#ff9800', # Orange
    'Poor': '#e74c3c',        # Softer red
    'Unknown': '#95a5a6'      # Gray
}

MARKER_SIZES = {
    'individual': 6,
    'dashboard': 4
}

LINE_STYLES = {
    'normal': dict(width=1.5, dash='dash'),
    'caution': dict(width=1.5, dash='dash'),
    'poor': dict(width=1.5, dash='dash')
}

# Parameter configuration
PARAMETER_THRESHOLDS = {
    'do_percent': {
        'ranges': [
            {'min': -float('inf'), 'max': 50, 'status': 'Poor'},
            {'min': 50, 'max': 80, 'status': 'Caution'},
            {'min': 80, 'max': 130, 'status': 'Normal'},
            {'min': 130, 'max': 150, 'status': 'Caution'},
            {'min': 150, 'max': float('inf'), 'status': 'Poor'}
        ]
    },
    'pH': {
        'ranges': [
            {'min': 6.5, 'max': 9.0, 'status': 'Normal'},
            {'min': -float('inf'), 'max': 6.5, 'status': 'Outside Normal'},
            {'min': 9.0, 'max': float('inf'), 'status': 'Outside Normal'}
        ]
    },
    'soluble_nitrogen': {
        'ranges': [
            {'min': -float('inf'), 'max': 0.8, 'status': 'Normal'},
            {'min': 0.8, 'max': 1.5, 'status': 'Caution'},
            {'min': 1.5, 'max': float('inf'), 'status': 'Poor'}
        ]
    },
    'Phosphorus': {
        'ranges': [
            {'min': -float('inf'), 'max': 0.05, 'status': 'Normal'},
            {'min': 0.05, 'max': 0.1, 'status': 'Caution'},
            {'min': 0.1, 'max': float('inf'), 'status': 'Poor'}
        ]
    },
    'Chloride': {
        'ranges': [
            {'min': -float('inf'), 'max': 250, 'status': 'Normal'},
            {'min': 250, 'max': float('inf'), 'status': 'Poor'}
        ]
    }
}

# Reference line configuration
REFERENCE_LINES = {
    'do_percent': [
        {'value': 80, 'color': 'orange', 'label': 'Normal Min', 'style': LINE_STYLES['normal']},
        {'value': 130, 'color': 'orange', 'label': 'Normal Max', 'style': LINE_STYLES['normal']},
        {'value': 50, 'color': 'red', 'label': 'Caution Min', 'style': LINE_STYLES['caution']},
        {'value': 150, 'color': 'red', 'label': 'Caution Max', 'style': LINE_STYLES['caution']}
    ],
    'pH': [
        {'value': 6.5, 'color': 'orange', 'label': 'Normal Min', 'style': LINE_STYLES['normal']},
        {'value': 9.0, 'color': 'orange', 'label': 'Normal Max', 'style': LINE_STYLES['normal']}
    ],
    'soluble_nitrogen': [
        {'value': 0.8, 'color': 'orange', 'label': 'Caution', 'style': LINE_STYLES['normal']},
        {'value': 1.5, 'color': 'red', 'label': 'Poor', 'style': LINE_STYLES['caution']}
    ],
    'Phosphorus': [
        {'value': 0.05, 'color': 'orange', 'label': 'Caution', 'style': LINE_STYLES['normal']},
        {'value': 0.1, 'color': 'red', 'label': 'Poor', 'style': LINE_STYLES['caution']}
    ],
    'Chloride': [
        {'value': 250, 'color': 'red', 'label': 'Poor', 'style': LINE_STYLES['poor']}
    ]
}

def get_parameter_label(parameter):
    """Return appropriate Y-axis label for a given parameter."""
    labels = {
        'do_percent': 'DO Saturation (%)',
        'pH': 'pH',
        'soluble_nitrogen': 'Soluble Nitrogen (mg/L)',
        'Phosphorus': 'Phosphorus (mg/L)',
        'Chloride': 'Chloride (mg/L)',
    }
    return labels.get(parameter, parameter)

def get_parameter_name(parameter):
    """Convert parameter code to human-readable name."""
    names = {
        'do_percent': 'Dissolved Oxygen',
        'pH': 'pH',
        'soluble_nitrogen': 'Nitrogen',
        'Phosphorus': 'Phosphorus',
        'Chloride': 'Chloride',
    }
    return names.get(parameter, parameter)

def categorize_data_points(df, parameter, reference_values):
    """
    Categorize data points based on parameter thresholds.
    Returns a DataFrame with a 'status' column and a color map for plotting.
    """
    # Create a new DataFrame with status
    plot_df = df.copy()
    
    # Default status for NaN values
    plot_df['status'] = 'Unknown'
    
    # Use parameter-specific logic from configuration if available
    if parameter in PARAMETER_THRESHOLDS:
        ranges = PARAMETER_THRESHOLDS[parameter]['ranges']
        values = plot_df[parameter]
        
        # Create a mask of non-null values
        valid_mask = ~pd.isna(values)
        
        for range_dict in ranges:
            # Create a mask for this range
            min_val = range_dict['min']
            max_val = range_dict['max']
            status = range_dict['status']
            
            # Apply range conditions and set status
            if min_val == -float('inf'):
                if max_val == float('inf'):
                    # All values match
                    range_mask = valid_mask
                else:
                    # Less than max
                    range_mask = valid_mask & (values < max_val)
            elif max_val == float('inf'):
                # Greater than or equal to min
                range_mask = valid_mask & (values >= min_val)
            else:
                # Between min (inclusive) and max (exclusive)
                range_mask = valid_mask & (values >= min_val) & (values < max_val)
            
            # Set status for matching values
            plot_df.loc[range_mask, 'status'] = status
    
    # Fallback to generic logic using reference values if no specific config
    else:
        try:
            ref = reference_values[parameter]
            values = plot_df[parameter]
            valid_mask = ~pd.isna(values)
            
            if 'normal min' in ref and 'normal max' in ref:
                plot_df.loc[valid_mask & (values < ref['normal min']), 'status'] = 'Below Normal'
                plot_df.loc[valid_mask & (values >= ref['normal min']) & (values <= ref['normal max']), 'status'] = 'Normal'
                plot_df.loc[valid_mask & (values > ref['normal max']), 'status'] = 'Above Normal'
            
            elif 'normal' in ref and 'caution' in ref and 'poor' in ref:
                plot_df.loc[valid_mask & (values > ref['poor']), 'status'] = 'Poor'
                plot_df.loc[valid_mask & (values > ref['caution']) & (values <= ref['poor']), 'status'] = 'Caution'
                plot_df.loc[valid_mask & (values <= ref['normal']), 'status'] = 'Normal'
                plot_df.loc[valid_mask & (values > ref['normal']) & (values <= ref['caution']), 'status'] = 'Above Normal'
            
            elif 'normal' in ref and 'caution' in ref:
                plot_df.loc[valid_mask & (values > ref['caution']), 'status'] = 'Caution'
                plot_df.loc[valid_mask & (values <= ref['normal']), 'status'] = 'Normal'
                plot_df.loc[valid_mask & (values > ref['normal']) & (values <= ref['caution']), 'status'] = 'Above Normal'
            
            else:
                # If no thresholds match, set all to Normal
                plot_df.loc[valid_mask, 'status'] = 'Normal'
        
        except Exception as e:
            print(f"Error categorizing {parameter}: {e}")
            # Default to normal if any error occurs
            plot_df.loc[~pd.isna(plot_df[parameter]), 'status'] = 'Normal'
    
    return plot_df, COLORS

def add_parameter_reference_lines(fig, parameter, df, reference_values, row=None, col=None):
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
                    font=dict(size=10, color=color),
                    opacity=0.7,
                    xshift=-5
                )
    
    # Add parameter-specific reference lines from configuration
    if parameter in REFERENCE_LINES:
        for line_config in REFERENCE_LINES[parameter]:
            add_reference_line(
                line_config['value'], 
                line_config['color'], 
                line_config.get('label'), 
                line_config.get('style')
            )
    
    # Add generic reference lines from the reference values dictionary
    elif parameter in reference_values:
        try:
            ref = reference_values[parameter]
            
            if 'normal min' in ref:
                add_reference_line(ref['normal min'], 'green', "Normal Min")
                    
            if 'normal max' in ref:
                add_reference_line(ref['normal max'], 'green', "Normal Max")
                    
            if 'normal' in ref:
                add_reference_line(ref['normal'], 'green', "Normal")
                    
            if 'caution' in ref:
                add_reference_line(ref['caution'], 'orange', "Caution")
                    
            if 'poor' in ref:
                add_reference_line(ref['poor'], 'red', "Poor")
        except Exception as e:
            print(f"Error adding reference lines for {parameter}: {e}")
    
    return fig

def create_time_series_plot(df, parameter, reference_values, title=None, y_label=None, highlight_thresholds=True):
    """Generate time series plot for parameter with optional threshold highlighting"""
    # Check if we have data
    if len(df) == 0:
        # Return an empty figure with a message
        fig = px.scatter(title="No data available for selected time range")
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title=y_label,
            annotations=[
                dict(
                    text="No data available for the selected time range",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )
            ]
        )
        return fig
    
    # Use defaults if no custom values provided
    if title is None:
        title = f'{parameter} Over Time'
    if y_label is None:
        y_label = get_parameter_label(parameter)
    
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
            # Get categorized data using our helper function
            plot_df, color_map = categorize_data_points(df, parameter, reference_values)
            
            # Add points colored by status
            for status_type, color in color_map.items():
                mask = plot_df['status'] == status_type
                if mask.any():
                    fig.add_trace(
                        go.Scatter(
                            x=plot_df.loc[mask, 'Date'],
                            y=plot_df.loc[mask, parameter],
                            mode='markers',
                            marker=dict(size=MARKER_SIZES['individual'], color=color),
                            name=status_type,
                            hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br>' +
                                        '<b>' + y_label + '</b>: %{y:.2f}<br>' +
                                        '<b>Status</b>: ' + status_type +
                                        '<extra></extra>'
                        )
                    )
            
            # Add connecting line (in light gray and underneath points)
            fig.add_trace(
                go.Scatter(
                    x=df['Date'],
                    y=df[parameter],
                    mode='lines',
                    line=dict(color='gray', width=1, dash='solid'),
                    opacity=0.2,
                    showlegend=False,
                    hoverinfo='skip'
                )
            )
            
            # Add reference lines using our helper function
            fig = add_parameter_reference_lines(fig, parameter, df, reference_values)
        except Exception as e:
            print(f"Error creating highlighted plot for {parameter}: {e}")
            # Fall back to standard plot if error occurs
            highlight_thresholds = False
    
    # Create standard plot if highlighting is disabled or an error occurred
    if not highlight_thresholds or parameter not in reference_values:
        fig.add_trace(
            go.Scatter(
                x=df['Date'],
                y=df[parameter],
                mode='markers+lines',
                marker=dict(size=MARKER_SIZES['individual'], color='blue'),
                line=dict(color='blue', width=1),
                name=parameter,
                hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>Value</b>: %{y:.2f}<extra></extra>'
            )
        )
    
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
    fig.update_xaxes(
        tickformat='%Y',
        tickmode='auto',
        nticks=10
    )
    
    return fig

def create_parameter_dashboard(df=None, parameters=None, reference_values=None, highlight_thresholds=True, get_param_name=None):
    """Create a subplot figure for all parameters with optional threshold highlighting"""
    # If no data is provided, process it
    if df is None or parameters is None or reference_values is None:
        try:
            df, parameters, reference_values = process_chemical_data()
        except Exception as e:
            print(f"Error loading chemical data: {e}")
            # Return empty figure with error message
            fig = go.Figure()
            fig.update_layout(
                title="Error loading data",
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

    # If no parameter name function provided, use the standard function
    if get_param_name is None:
        get_param_name = get_parameter_name

    # Check if there is data
    if len(df) == 0:
        # Return an empty figure with a message
        fig = go.Figure()
        fig.update_layout(
            title="No data available for selected time range",
            annotations=[
                dict(
                    text="No data available for the selected time range",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5
                )
            ]
        )
        return fig
    
    # Calculate rows and columns needed
    n_params = len(parameters)
    n_cols = 2  
    n_rows = (n_params + 1) // 2  
    
    # Create subplot structure with more spacing
    fig = make_subplots(
        rows=n_rows, 
        cols=n_cols,
        subplot_titles=[get_param_name(p) + " Over Time" for p in parameters],
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )
    
    # Add each parameter plot to the appropriate subplot
    for i, param in enumerate(parameters):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        try:
            # Set up color mapping if highlighting is enabled
            if highlight_thresholds and param in reference_values:
                # Get categorized data using our helper function
                plot_df, color_map = categorize_data_points(df, param, reference_values)
                
                # Add points colored by status
                for status_type, color in color_map.items():
                    mask = plot_df['status'] == status_type
                    if mask.any():
                        fig.add_trace(
                            go.Scatter(
                                x=plot_df.loc[mask, 'Date'],
                                y=plot_df.loc[mask, param],
                                mode='markers',
                                marker=dict(size=MARKER_SIZES['dashboard'], color=color),
                                name=f"{param} - {status_type}",
                                legendgroup=param,
                                showlegend=False,
                                hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br>' +
                                            '<b>' + param + '</b>: %{y:.2f}<br>' +
                                            '<b>Status</b>: ' + status_type +
                                            '<extra></extra>'
                            ),
                            row=row, col=col
                        )
                
                # Add connecting line (underneath points)
                fig.add_trace(
                    go.Scatter(
                        x=df['Date'],
                        y=df[param],
                        mode='lines',
                        line=dict(color='gray', width=1),
                        opacity=0.2,
                        showlegend=False,
                        hoverinfo='skip',
                        legendgroup=param
                    ),
                    row=row, col=col
                )
                
                # Add reference lines using our helper function
                fig = add_parameter_reference_lines(fig, param, df, reference_values, row, col)
                
            else:
                # Standard plot without highlighting
                fig.add_trace(
                    go.Scatter(
                        x=df['Date'],
                        y=df[param],
                        mode='markers+lines',
                        name=param,
                        marker=dict(size=MARKER_SIZES['dashboard'], color='blue'),
                        line=dict(width=1, color='blue', dash='solid'),
                        opacity=0.7,
                        hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>Value</b>: %{y:.2f}<extra></extra>'
                    ),
                    row=row, col=col
                )
        except Exception as e:
            print(f"Error creating subplot for {param}: {e}")
            # Add an error message to the subplot
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
        title_text="Water Quality Parameters Over Time",
        title_x=0.5,              
        showlegend=False,
        template='plotly_white',
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    # Format all x-axes to show years nicely
    fig.update_xaxes(
        tickformat='%Y',
        tickmode='auto',
        nticks=5
    )
    
    # Add y-axis titles and improve formatting
    for i, param in enumerate(parameters):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        # Get appropriate y-axis label
        y_label = get_parameter_label(param)
        
        # Update y-axis title
        fig.update_yaxes(
            title_text=y_label,
            title_font=dict(size=12),
            tickfont=dict(size=10),
            row=row, col=col
        )
    
    return fig

def create_chemical_viz(highlight_thresholds=True):
    """Create chemical dashboard for the app"""
    try:
        df_clean, key_parameters, reference_values = process_chemical_data()
        return create_parameter_dashboard(df_clean, key_parameters, reference_values, highlight_thresholds)
    except Exception as e:
        print(f"Error creating chemical visualization: {e}")
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

# Test visualization if run directly
if __name__ == "__main__":
    fig = create_chemical_viz()
    fig.show()