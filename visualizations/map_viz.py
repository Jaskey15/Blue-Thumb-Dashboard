import pandas as pd
import plotly.graph_objects as go
from database.database import get_connection, close_connection
from utils import setup_logging

logger = setup_logging("map_viz", category="visualization")

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
    },
    'habitat': {
        'a': '#1e8449',    # Green (A grade)
        'b': '#7cb342',    # Light green (B grade)
        'c': '#ff9800',    # Orange (C grade)
        'd': '#e53e3e',    # Red-orange (D grade)
        'f': '#e74c3c'     # Red (F grade)
    }
}

MARKER_SIZES = {
    'outline': 12,
    'inner': 9
}

# Parameter thresholds configuration
PARAMETER_THRESHOLDS = {
    'do_percent': [
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
    'soluble_nitrogen': [
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

# Habitat assessment thresholds (based on total score)
HABITAT_THRESHOLDS = [
    {'min': 90, 'max': float('inf'), 'status': 'A', 'color': COLORS['habitat']['a']},
    {'min': 80, 'max': 90, 'status': 'B', 'color': COLORS['habitat']['b']},
    {'min': 70, 'max': 80, 'status': 'C', 'color': COLORS['habitat']['c']},
    {'min': 60, 'max': 70, 'status': 'D', 'color': COLORS['habitat']['d']},
    {'min': -float('inf'), 'max': 60, 'status': 'F', 'color': COLORS['habitat']['f']}
]

# Parameter display names
PARAMETER_LABELS = {
    'do_percent': 'Dissolved Oxygen',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride',
    'Fish_IBI': 'Fish Community Health',
    'Macro_Summer': 'Macroinvertebrate Community (Summer)',
    'Macro_Winter': 'Macroinvertebrate Community (Winter)',
    'Habitat_Grade': 'Habitat Assessment Grade'
}

def load_sites_from_database():
    """
    Load all monitoring sites from the database with coordinates and metadata.
    
    Returns:
        List of site dictionaries with name, lat, lon, county, river_basin, ecoregion
    """
    conn = None
    try:
        conn = get_connection()
        
        query = """
        SELECT site_name, latitude, longitude, county, river_basin, ecoregion
        FROM sites
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY site_name
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        sites = []
        for row in rows:
            site_name, lat, lon, county, river_basin, ecoregion = row
            
            # Handle missing metadata
            county = county if county is not None else "Unknown"
            river_basin = river_basin if river_basin is not None else "Unknown"
            ecoregion = ecoregion if ecoregion is not None else "Unknown"
            
            sites.append({
                "name": site_name,
                "lat": lat,
                "lon": lon,
                "county": county,
                "river_basin": river_basin,
                "ecoregion": ecoregion
            })
        
        logger.info(f"Successfully loaded {len(sites)} monitoring sites from database")
        return sites
        
    except Exception as e:
        logger.error(f"Error loading sites from database: {e}")
        raise Exception(f"Could not load monitoring sites: {str(e)}")
        
    finally:
        if conn:
            close_connection(conn)

def get_latest_data_by_type(data_type):
    """
    Get the latest data for each site by data type.
    
    Args:
        data_type: 'chemical', 'fish', 'macro', or 'habitat'
    
    Returns:
        DataFrame with latest data per site (and season for macro data)
    """
    try:
        # Call only database query functions, not processing functions
        if data_type == 'chemical':
            from data_processing.chemical_processing import get_chemical_data_from_db
            df = get_chemical_data_from_db()  # Only query, don't process
            
        elif data_type == 'fish':
            from data_processing.fish_processing import get_fish_dataframe
            df = get_fish_dataframe()  # This already only queries
            
        elif data_type == 'macro':
            from data_processing.macro_processing import get_macroinvertebrate_dataframe
            df = get_macroinvertebrate_dataframe()  # This already only queries
            
        elif data_type == 'habitat':
            from data_processing.habitat_processing import get_habitat_dataframe
            df = get_habitat_dataframe()  # This already only queries
            
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        if df.empty:
            logger.warning(f"No {data_type} data found in database")
            return pd.DataFrame()
        
        # Handle different grouping logic based on data type
        if data_type == 'chemical':
            # Chemical data uses 'Date' column and 'Site_Name'
            latest_data = df.sort_values('Date').groupby('Site_Name').last().reset_index()
        elif data_type == 'macro':
            # Macro data needs grouping by both site and season
            # Assumes columns are 'site_name', 'season', 'year'
            latest_data = df.sort_values(['season', 'year']).groupby(['site_name', 'season']).last().reset_index()
        else:
            # Fish and habitat data use 'year' column and 'site_name'
            latest_data = df.sort_values('year').groupby('site_name').last().reset_index()
        
        logger.info(f"Retrieved latest {data_type} data for {len(latest_data)} records")
        return latest_data
        
    except Exception as e:
        logger.error(f"Error getting latest {data_type} data: {e}")
        return pd.DataFrame()

def determine_status_by_type(data_type, value, parameter_name=None):
    """
    Determine the status and corresponding color for a parameter value by data type.
    
    Args:
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat')
        value: Parameter value to evaluate
        parameter_name: Specific parameter name (required for chemical data)
    
    Returns:
        Tuple of (status_text, color_code)
    """
    # Default status
    status = "Unknown"
    color = COLORS['unknown']
    
    # Check for NaN values
    if pd.isna(value):
        return status, color
    
    # Map data types to their threshold configurations
    if data_type == 'chemical':
        if parameter_name and parameter_name in PARAMETER_THRESHOLDS:
            thresholds = PARAMETER_THRESHOLDS[parameter_name]
        else:
            return status, color
    elif data_type == 'fish':
        thresholds = FISH_IBI_THRESHOLDS
    elif data_type == 'macro':
        thresholds = MACRO_THRESHOLDS
    elif data_type == 'habitat':
        thresholds = HABITAT_THRESHOLDS
    else:
        return status, color
    
    # Check value against thresholds
    for threshold in thresholds:
        if threshold['min'] <= value < threshold['max']:
            return threshold['status'], threshold['color']
    
    return status, color

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
        
    if parameter == 'do_percent':
        return f"{value:.1f}%"
    elif parameter == 'pH':
        return f"{value:.1f}"
    elif parameter in ['soluble_nitrogen', 'Phosphorus', 'Chloride']:
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

def add_data_markers(fig, sites, data_type, parameter_name=None, season=None):
    """
    Add markers to the map for any data type.
    
    Args:
        fig: The plotly figure to add markers to
        sites: List of site dictionaries with coordinates
        data_type: 'chemical', 'fish', 'macro', 'habitat'
        parameter_name: For chemical data (specific parameter like 'do_percent')
        season: For macro data ('Summer' or 'Winter')
    
    Returns:
        The updated figure
    """
    # Get the latest data for this data type
    latest_data = get_latest_data_by_type(data_type)
    
    # Data type specific configurations
    data_config = {
        'chemical': {
            'value_column': parameter_name,
            'date_column': 'Date',
            'site_column': 'Site_Name',
            'needs_reference_values': True
        },
        'fish': {
            'value_column': 'comparison_to_reference',
            'date_column': 'year',
            'site_column': 'site_name',
            'needs_reference_values': False
        },
        'macro': {
            'value_column': 'comparison_to_reference',
            'date_column': 'year',
            'site_column': 'site_name',
            'needs_reference_values': False
        },
        'habitat': {
            'value_column': 'total_score',
            'date_column': 'year',
            'site_column': 'site_name',
            'needs_reference_values': False
        }
    }
    
    config = data_config[data_type]
    
    # Get reference values if needed (for chemical data)
    reference_values = None
    if config['needs_reference_values']:
        _, key_parameters, reference_values = get_latest_data_by_type('chemical')
        # Check if parameter is valid
        if parameter_name not in key_parameters:
            return fig
    
    for site in sites:
        site_name = site["name"]
        
        # Find data for this site
        site_data = latest_data[latest_data[config['site_column']] == site_name]
        
        # Handle season filtering for macro data
        if data_type == 'macro' and season:
            site_data = site_data[site_data['season'] == season]
        
        if not site_data.empty and config['value_column'] in site_data.columns:
            # Get the value and determine status
            value = site_data[config['value_column']].iloc[0]
            
            if data_type == 'chemical':
                status, color = determine_status_by_type('chemical', value, parameter_name)
                formatted_value = format_parameter_value(parameter_name, value)
                date_str = pd.to_datetime(site_data[config['date_column']].iloc[0]).strftime('%B %d, %Y')
                hover_text = f"{site_name}<br>{parameter_name}: {formatted_value}<br>Status: {status}<br>Last reading: {date_str}"
            
            elif data_type == 'fish':
                status, color = determine_status_by_type('fish', value)
                year = site_data[config['date_column']].iloc[0]
                hover_text = f"{site_name}<br>IBI Score: {value:.2f}<br>Status: {status}<br>Last survey: {year}"
            
            elif data_type == 'macro':
                status, color = determine_status_by_type('macro', value)
                year = site_data[config['date_column']].iloc[0]
                date_str = f"{season} {year}"
                hover_text = f"{site_name}<br>Bioassessment Score: {value:.2f}<br>Status: {status}<br>Last survey: {date_str}"
            
            elif data_type == 'habitat':
                status, color = determine_status_by_type('habitat', value)
                year = site_data[config['date_column']].iloc[0]
                hover_text = f"{site_name}<br>Habitat Score: {value:.1f}<br>Grade: {status}<br>Last assessment: {year}"
            
            # Add marker with determined color
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color=color,
                site_name=site_name,
                hover_text=hover_text
            )
        else:
            # No data available - add gray marker
            if data_type == 'macro' and season:
                no_data_text = f"{site_name}<br>No {season} macroinvertebrate data available"
            else:
                data_label = PARAMETER_LABELS.get(f"{data_type.title()}_{'_'.join(parameter_name.split('_')) if parameter_name else 'Data'}", f"{data_type} data")
                no_data_text = f"{site_name}<br>No {data_label.lower()} available"
            
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color=COLORS['unknown'],
                site_name=site_name,
                hover_text=no_data_text
            )
    
    return fig

def create_site_map(param_type=None, param_name=None):
    """
    Create an interactive map of monitoring sites with color-coded status markers.
    
    Args:
        param_type: Type of parameter ('chem', 'bio', or 'habitat')
        param_name: Specific parameter name (e.g., 'do_percent', 'Fish_IBI', 'Habitat_Grade')
    
    Returns:
        Plotly figure with the interactive map
    """
    try:
        # Create the base map
        fig = go.Figure()
        
        # Check if we have sites loaded
        if not MONITORING_SITES:
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
                        text="Error: No monitoring sites available",
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
        
        # If parameter type and name are provided, determine marker colors based on status
        if param_type and param_name:
            if param_type == 'chem':
                fig = add_data_markers(fig, MONITORING_SITES, 'chemical', parameter_name=param_name)
            elif param_type == 'bio':
                if param_name == 'Fish_IBI':
                    fig = add_data_markers(fig, MONITORING_SITES, 'fish')
                elif param_name == 'Macro_Summer':
                    fig = add_data_markers(fig, MONITORING_SITES, 'macro', season='Summer')
                elif param_name == 'Macro_Winter':
                    fig = add_data_markers(fig, MONITORING_SITES, 'macro', season='Winter')
            elif param_type == 'habitat':
                fig = add_data_markers(fig, MONITORING_SITES, 'habitat')
        else:
            # No parameter selected, use default blue markers with site info
            for site in MONITORING_SITES:
                hover_text = (f"{site['name']}<br>"
                             f"County: {site['county']}<br>"
                             f"River Basin: {site['river_basin']}<br>"
                             f"Ecoregion: {site['ecoregion']}")
                
                fig = add_site_marker(
                    fig=fig,
                    lat=site["lat"],
                    lon=site["lon"],
                    color='#3366CC',  # Blue for neutral/default state
                    site_name=site["name"],
                    hover_text=hover_text
                )
        
        # Set up map layout
        fig.update_layout(
            mapbox=dict(
                style="white-bg",
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
            height=600,
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

# Load monitoring sites
try:
    MONITORING_SITES = load_sites_from_database()
except Exception as e:
    print(f"Warning: Could not load sites from database: {e}")
    MONITORING_SITES = []  # Fallback to empty list
    
# Test function if run directly
if __name__ == "__main__":
    fig = create_site_map()
    fig.show()