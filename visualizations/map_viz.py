import plotly.graph_objects as go
import pandas as pd

# Styling constants
COLORS = {
    'normal': '#1e8449',      # Green
    'caution': '#ff9800',     # Orange
    'poor': '#e74c3c',        # Red
    'unknown': 'gray',        # Gray
    'outline': '#777777',     # Medium-light gray
    'fish': {
        'excellent': '#1e8449',  # Green
        'good': '#7cb342',       # Light green
        'fair': '#ff9800',       # Orange
        'poor': '#e74c3c',       # Red
    },
    'macro': {
        'non-impaired': '#1e8449',        # Green
        'slightly_impaired': '#ff9800',   # Orange
        'moderately_impaired': '#f57c00', # Dark orange
        'severely_impaired': '#e74c3c',   # Red
    }
}

MARKER_SIZES = {
    'outline': 12,
    'inner': 9
}

# Parameter thresholds configuration
PARAMETER_THRESHOLDS = {
    'DO_Percent': [
        {'min': -float('inf'), 'max': 50, 'status': 'Poor', 'color': COLORS['poor']},
        {'min': 50, 'max': 80, 'status': 'Caution', 'color': COLORS['caution']},
        {'min': 80, 'max': 130, 'status': 'Normal', 'color': COLORS['normal']},
        {'min': 130, 'max': 150, 'status': 'Caution', 'color': COLORS['caution']},
        {'min': 150, 'max': float('inf'), 'status': 'Poor', 'color': COLORS['poor']}
    ],
    'pH': [
        {'min': 6.5, 'max': 9.0, 'status': 'Normal', 'color': COLORS['normal']},
        {'min': -float('inf'), 'max': 6.5, 'status': 'Outside Normal', 'color': COLORS['caution']},
        {'min': 9.0, 'max': float('inf'), 'status': 'Outside Normal', 'color': COLORS['caution']}
    ],
    'Soluble_Nitrogen': [
        {'min': -float('inf'), 'max': 0.8, 'status': 'Normal', 'color': COLORS['normal']},
        {'min': 0.8, 'max': 1.5, 'status': 'Caution', 'color': COLORS['caution']},
        {'min': 1.5, 'max': float('inf'), 'status': 'Poor', 'color': COLORS['poor']}
    ],
    'Phosphorus': [
        {'min': -float('inf'), 'max': 0.05, 'status': 'Normal', 'color': COLORS['normal']},
        {'min': 0.05, 'max': 0.1, 'status': 'Caution', 'color': COLORS['caution']},
        {'min': 0.1, 'max': float('inf'), 'status': 'Poor', 'color': COLORS['poor']}
    ],
    'Chloride': [
        {'min': -float('inf'), 'max': 250, 'status': 'Normal', 'color': COLORS['normal']},
        {'min': 250, 'max': float('inf'), 'status': 'Poor', 'color': COLORS['poor']}
    ]
}

# Fish IBI thresholds
FISH_IBI_THRESHOLDS = [
    {'min': 0.97, 'max': float('inf'), 'status': 'Excellent', 'color': COLORS['fish']['excellent']},
    {'min': 0.8, 'max': 0.97, 'status': 'Good', 'color': COLORS['fish']['good']},
    {'min': 0.67, 'max': 0.8, 'status': 'Fair', 'color': COLORS['fish']['fair']},
    {'min': -float('inf'), 'max': 0.67, 'status': 'Poor', 'color': COLORS['fish']['poor']}
]

# Macroinvertebrate bioassessment thresholds
MACRO_THRESHOLDS = [
    {'min': 0.83, 'max': float('inf'), 'status': 'Non-impaired', 'color': COLORS['macro']['non-impaired']},
    {'min': 0.54, 'max': 0.83, 'status': 'Slightly Impaired', 'color': COLORS['macro']['slightly_impaired']},
    {'min': 0.17, 'max': 0.54, 'status': 'Moderately Impaired', 'color': COLORS['macro']['moderately_impaired']},
    {'min': -float('inf'), 'max': 0.17, 'status': 'Severely Impaired', 'color': COLORS['macro']['severely_impaired']}
]

# Parameter display names
PARAMETER_LABELS = {
    'DO_Percent': 'Dissolved Oxygen',
    'pH': 'pH',
    'Soluble_Nitrogen': 'Soluble Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride',
    'Fish_IBI': 'Fish Community Health',
    'Macro_Summer': 'Macroinvertebrate Community (Summer)',
    'Macro_Winter': 'Macroinvertebrate Community (Winter)'
}

# Monitoring sites
MONITORING_SITES = [
    {"name": "Tenmile Creek: Davis", "lat": 34.298889, "lon": -95.737222}
]

def get_latest_chemical_data():
    """
    Get the most recent reading for each chemical parameter at each monitoring site.
    
    Returns:
        Tuple of (latest_data, key_parameters, reference_values)
    """
    try:
        # Import necessary data processing functions
        from data_processing.chemical_processing import process_chemical_data
        
        # Get the chemical data
        df_clean, key_parameters, reference_values = process_chemical_data()
        
        # Group by site and get the most recent date for each site
        latest_data = df_clean.sort_values('Date').groupby('Site_Name').last().reset_index()
        
        return latest_data, key_parameters, reference_values
    
    except Exception as e:
        print(f"Error getting latest chemical data: {e}")
        return pd.DataFrame(), [], {}

def get_latest_fish_data():
    """
    Get the latest fish IBI scores.
    
    Returns:
        DataFrame containing fish IBI data
    """
    try:
        from data_processing.fish_processing import get_fish_dataframe
        
        # Get fish data
        fish_df = get_fish_dataframe()
        
        # Sort by year to ensure we get the latest data
        if not fish_df.empty:
            fish_df = fish_df.sort_values('year')
        
        return fish_df
    
    except Exception as e:
        print(f"Error getting latest fish data: {e}")
        return pd.DataFrame()

def get_latest_macro_data():
    """
    Get the latest macroinvertebrate bioassessment scores.
    
    Returns:
        DataFrame containing macroinvertebrate data
    """
    try:
        from data_processing.macro_processing import get_macroinvertebrate_dataframe
        
        # Get macroinvertebrate data
        macro_df = get_macroinvertebrate_dataframe()
        
        # Sort by year to ensure we get the latest data
        if not macro_df.empty:
            macro_df = macro_df.sort_values(['season', 'year'])
        
        return macro_df
    
    except Exception as e:
        print(f"Error getting latest macroinvertebrate data: {e}")
        return pd.DataFrame()

def determine_status(parameter, value, reference_values):
    """
    Determine the status and corresponding color for a parameter value.
    
    Args:
        parameter: Parameter name to check
        value: Parameter value to evaluate
        reference_values: Dictionary of reference values
    
    Returns:
        Tuple of (status_text, color_code)
    """
    # Default status
    status = "Unknown"
    color = COLORS['unknown']
    
    # Check for NaN values
    if pd.isna(value):
        return status, color
    
    # Use parameter thresholds configuration
    if parameter in PARAMETER_THRESHOLDS:
        thresholds = PARAMETER_THRESHOLDS[parameter]
        
        for threshold in thresholds:
            if threshold['min'] <= value < threshold['max']:
                return threshold['status'], threshold['color']
    
    return status, color

def determine_fish_status(ibi_score):
    """
    Determine the status and color for a fish IBI score.
    
    Args:
        ibi_score: Fish IBI score to evaluate
    
    Returns:
        Tuple of (status_text, color_code)
    """
    for threshold in FISH_IBI_THRESHOLDS:
        if threshold['min'] <= ibi_score < threshold['max']:
            return threshold['status'], threshold['color']
    
    return "Unknown", COLORS['unknown']

def determine_macro_status(bio_score):
    """
    Determine the status and color for a macroinvertebrate bioassessment score.
    
    Args:
        bio_score: Bioassessment score to evaluate
    
    Returns:
        Tuple of (status_text, color_code)
    """
    for threshold in MACRO_THRESHOLDS:
        if threshold['min'] <= bio_score < threshold['max']:
            return threshold['status'], threshold['color']
    
    return "Unknown", COLORS['unknown']

def format_parameter_value(parameter, value):
    """
    Format parameter values for display in hover text.
    
    Args:
        parameter: Parameter name
        value: Parameter value to format
    
    Returns:
        Formatted string representation of the value
    """
    if pd.isna(value):
        return "No data"
        
    if parameter == 'DO_Percent':
        return f"{value:.1f}%"
    elif parameter == 'pH':
        return f"{value:.1f}"
    elif parameter in ['Soluble_Nitrogen', 'Phosphorus', 'Chloride']:
        return f"{value:.3f} mg/L"
    else:
        return f"{value}"

def add_site_marker(fig, lat, lon, color, site_name, hover_text=None):
    """
    Add a site marker with outline to the map.
    
    Args:
        fig: The plotly figure to add the marker to
        lat: Latitude of the marker
        lon: Longitude of the marker
        color: Color of the inner marker
        site_name: Name of the site
        hover_text: Text to display on hover (defaults to site_name if None)
    
    Returns:
        The updated figure
    """
    # TODO: Update from scattermapbox to scattermap in a future iteration
    # Currently using scattermapbox despite deprecation warnings because it correctly handles map centering
    # See: https://plotly.com/python/mapbox-to-maplibre/ for future migration
    
    # Add outline marker first
    fig.add_trace(go.Scattermapbox(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(
            size=MARKER_SIZES['outline'],
            color=COLORS['outline'],
            opacity=1.0
        ),
        hoverinfo='none',
        showlegend=False
    ))
    
    # Add colored marker on top
    fig.add_trace(go.Scattermapbox(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(
            size=MARKER_SIZES['inner'],
            color=color,
            opacity=1.0
        ),
        text=[hover_text if hover_text else site_name],
        name=site_name,
        hoverinfo='text'
    ))
    
    return fig

def add_chemical_markers(fig, sites, param_name):
    """
    Add chemical parameter markers to the map.
    
    Args:
        fig: The plotly figure to add markers to
        sites: List of site dictionaries with coordinates
        param_name: Chemical parameter name
    
    Returns:
        The updated figure
    """
    # Get the latest chemical readings and reference values
    latest_data, key_parameters, reference_values = get_latest_chemical_data()
    
    # Check if the selected parameter is valid
    if param_name in key_parameters:
        for site in sites:
            site_name = site["name"]
            site_data = latest_data[latest_data['Site_Name'] == site_name]
            
            if not site_data.empty and param_name in site_data.columns:
                # Get value and determine status for chemical parameter
                value = site_data[param_name].values[0]
                status, color = determine_status(param_name, value, reference_values)
                formatted_value = format_parameter_value(param_name, value)
                
                # Format the date for display
                date_str = pd.to_datetime(site_data['Date'].values[0]).strftime('%B %d, %Y')
                
                # Add marker with color based on status
                hover_text = f"{site_name}<br>{param_name}: {formatted_value}<br>Status: {status}<br>Last reading: {date_str}"
                fig = add_site_marker(
                    fig=fig,
                    lat=site["lat"],
                    lon=site["lon"],
                    color=color,
                    site_name=site_name,
                    hover_text=hover_text
                )
            else:
                # Add default marker if no data available
                hover_text = f"{site_name}<br>No data available for {param_name}"
                fig = add_site_marker(
                    fig=fig,
                    lat=site["lat"],
                    lon=site["lon"],
                    color=COLORS['unknown'],
                    site_name=site_name,
                    hover_text=hover_text
                )
    
    return fig

def add_fish_markers(fig, sites):
    """
    Add fish IBI markers to the map.
    
    Args:
        fig: The plotly figure to add markers to
        sites: List of site dictionaries with coordinates
    
    Returns:
        The updated figure
    """
    # Get fish IBI scores
    fish_data = get_latest_fish_data()
    
    for site in sites:
        site_name = site["name"]
        
        if not fish_data.empty:
            # Get the latest IBI score
            ibi_score = fish_data['comparison_to_reference'].iloc[-1]
            integrity_class = fish_data['integrity_class'].iloc[-1]
            
            # Get the date of the latest reading
            year = fish_data['year'].iloc[-1]
            date_str = str(year)  # Use year as the date string
            
            # Determine status and color based on IBI score
            status, color = determine_fish_status(ibi_score)
            
            # Add marker
            hover_text = f"{site_name}<br>IBI Score: {ibi_score:.2f}<br>Status: {status}<br>Last survey: {date_str}"
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color=color,
                site_name=site_name,
                hover_text=hover_text
            )
        else:
            # No fish data
            hover_text = f"{site_name}<br>No fish data available"
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color=COLORS['unknown'],
                site_name=site_name,
                hover_text=hover_text
            )
    
    return fig

def add_macro_markers(fig, sites, season):
    """
    Add macroinvertebrate markers to the map.
    
    Args:
        fig: The plotly figure to add markers to
        sites: List of site dictionaries with coordinates
        season: Season to display ('Summer' or 'Winter')
    
    Returns:
        The updated figure
    """
    # Get macroinvertebrate bioassessment scores
    macro_data = get_latest_macro_data()
    
    for site in sites:
        site_name = site["name"]
        
        if not macro_data.empty:
            # Filter for the requested season
            season_data = macro_data[macro_data['season'] == season]
            
            if not season_data.empty:
                # Get the latest score for the specified season
                season_data = season_data.sort_values('year')
                bio_score = season_data['comparison_to_reference'].iloc[-1]
                condition = season_data['biological_condition'].iloc[-1]
                
                # Get the year of the latest reading
                year = season_data['year'].iloc[-1]
                date_str = f"{season} {year}"
                
                # Determine status and color based on bioassessment score
                status, color = determine_macro_status(bio_score)
                
                # Add marker
                hover_text = f"{site_name}<br>Bioassessment Score: {bio_score:.2f}<br>Status: {status}<br>Last survey: {date_str}"
                fig = add_site_marker(
                    fig=fig,
                    lat=site["lat"],
                    lon=site["lon"],
                    color=color,
                    site_name=site_name,
                    hover_text=hover_text
                )
            else:
                # No data for this season
                hover_text = f"{site_name}<br>No {season} macroinvertebrate data available"
                fig = add_site_marker(
                    fig=fig,
                    lat=site["lat"],
                    lon=site["lon"],
                    color=COLORS['unknown'],
                    site_name=site_name,
                    hover_text=hover_text
                )
        else:
            # No macroinvertebrate data
            hover_text = f"{site_name}<br>No macroinvertebrate data available"
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color=COLORS['unknown'],
                site_name=site_name,
                hover_text=hover_text
            )
    
    return fig

def create_site_map(param_type=None, param_name=None):
    """
    Create an interactive map of monitoring sites with color-coded status markers.
    
    Args:
        param_type: Type of parameter ('chem' or 'bio')
        param_name: Specific parameter name (e.g., 'DO_Percent', 'Fish_IBI')
    
    Returns:
        Plotly figure with the interactive map
    """
    try:
        # Create the base map
        fig = go.Figure()
        
        # If parameter type and name are provided, determine marker colors based on status
        if param_type and param_name:
            if param_type == 'chem':
                fig = add_chemical_markers(fig, MONITORING_SITES, param_name)
            elif param_type == 'bio':
                if param_name == 'Fish_IBI':
                    fig = add_fish_markers(fig, MONITORING_SITES)
                elif param_name == 'Macro_Summer':
                    fig = add_macro_markers(fig, MONITORING_SITES, 'Summer')
                elif param_name == 'Macro_Winter':
                    fig = add_macro_markers(fig, MONITORING_SITES, 'Winter')
        else:
            # No parameter selected, use default markers
            for site in MONITORING_SITES:
                fig = add_site_marker(
                    fig=fig,
                    lat=site["lat"],
                    lon=site["lon"],
                    color='red',
                    site_name=site["name"],
                    hover_text=site["name"]
                )
        
        # Set up map layout
        fig.update_layout(
            mapbox=dict(
                style="white-bg",  # Start with a white background
                layers=[
                    {
                        "below": 'traces',
                        "sourcetype": "raster",
                        "sourceattribution": "Esri",
                        "source": [
                            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
                        ]
                    }
                ],
                center=dict(lat=35.5, lon=-98.2),  # Center of Oklahoma
                zoom=6.2
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=600,  # Increased height for better vertical display
            showlegend=False,
            annotations=[
                dict(
                    text="Map data © Esri",
                    showarrow=False,
                    x=0.01,  
                    y=0.01,
                    xref="paper",
                    yref="paper",
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=10, color="gray")
                )
            ]
        )
        
        # Add title based on parameter type and name
        if param_type and param_name:
            display_name = PARAMETER_LABELS.get(param_name, param_name)
            title = f"Monitoring Sites - {display_name} Status"
            
            fig.update_layout(
                title=dict(
                    text=title,
                    x=0.5,
                    y=0.98
                )
            )
        
        return fig
    
    except Exception as e:
        print(f"Error creating site map: {e}")
        # Return a basic map with an error message
        fig = go.Figure()
        fig.update_layout(
            mapbox=dict(
                style="white-bg",
                center=dict(lat=35.5, lon=-98.2),
                zoom=6.2
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=600,
            annotations=[
                dict(
                    text=f"Error creating map: {str(e)}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    font=dict(size=14, color="red")
                )
            ]
        )
        return fig

# Test function if run directly
if __name__ == "__main__":
    fig = create_site_map()
    fig.show()