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
    'above_normal': '#5e35b1', # Purple-blue (Basic/Alkaline)
    'below_normal': '#f57c00', # Dark orange-red (Acidic)
    'fish': {
        'excellent': '#2e7d32',  # Dark green
        'good': '#66bb6a',       # Medium green
        'fair': '#ffca28',       # Amber/yellow
        'poor': '#f57c00',       # Dark orange
        'very poor': '#c62828',  # Dark red
    },
    'macro': {
        'non-impaired': '#1e8449',        # Green
        'slightly_impaired': '#7cb342',   # Light green
        'moderately_impaired': '#ff9800', # Orange
        'severely_impaired': '#e74c3c',   # Red
    },
    'habitat': {
        'a': '#2e7d32',    # Dark green
        'b': '#66bb6a',    # Medium green
        'c': '#ffca28',    # Amber/yellow
        'd': '#f57c00',    # Dark orange
        'f': '#c62828'     # Dark red
    }
}

# Parameter display names
PARAMETER_LABELS = {
    'do_percent': 'Dissolved Oxygen',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride',
    'Fish_IBI': 'Fish Community Health',
    'Macro_Combined': 'Biological: Macroinvertebrate Community',
    'Habitat_Grade': 'Habitat Assessment Grade'
}

# Parameter display names for map hover text
MAP_PARAMETER_LABELS = {
    'do_percent': 'Dissolved Oxygen Saturation',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride'
}

# ============================================================================
# CORE HELPER FUNCTIONS - Database and Data Processing
# ============================================================================

def load_sites_from_database():
    """
    Load all monitoring sites from the database with coordinates and metadata.
    
    Returns:
        List of site dictionaries with name, lat, lon, county, river_basin, ecoregion, active
    """
    conn = None
    try:
        conn = get_connection()
        
        query = """
        SELECT site_name, latitude, longitude, county, river_basin, ecoregion, active
        FROM sites
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY site_name
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        sites = []
        for row in rows:
            site_name, lat, lon, county, river_basin, ecoregion, active = row
            
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
                "ecoregion": ecoregion,
                "active": bool(active)  # Convert to boolean for clarity
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
    if data_type == 'chemical':
        from data_processing.data_queries import get_chemical_data_from_db
        df = get_chemical_data_from_db() 
        
    elif data_type == 'fish':
        from data_processing.data_queries import get_fish_dataframe
        df = get_fish_dataframe()  
        
    elif data_type == 'macro':
        from data_processing.data_queries import get_macroinvertebrate_dataframe
        df = get_macroinvertebrate_dataframe()  
        
    elif data_type == 'habitat':
        from data_processing.data_queries import get_habitat_dataframe
        df = get_habitat_dataframe() 
        
    else:
        raise ValueError(f"Unknown data type: {data_type}")
    
    if df.empty:
        logger.warning(f"No {data_type} data found in database")
        return pd.DataFrame()
    
    # Handle different grouping logic based on data type
    if data_type == 'chemical':
        latest_data = df.sort_values('Date').groupby('Site_Name').last().reset_index()
    else:
        latest_data = df.sort_values('year').groupby('site_name').last().reset_index()
    
    logger.info(f"Retrieved latest {data_type} data for {len(latest_data)} records")
    return latest_data

def get_status_color_from_database(data_type, status_value):
    """
    Map database status values to display colors for different data types.
    
    Args:
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat')
        status_value: Status value from database
    
    Returns:
        Tuple of (status_text, color_code)
    """
    # Handle NaN or None values
    if pd.isna(status_value) or status_value is None:
        return "Unknown", 'gray'
    
    # Convert to string and handle case variations
    status_str = str(status_value).strip()
    
    if data_type == 'chemical':
        chemical_color_map = {
            'Normal': COLORS['normal'],
            'Caution': COLORS['caution'], 
            'Poor': COLORS['poor'],
            'Above Normal (Basic/Alkaline)': COLORS['above_normal'],
            'Below Normal (Acidic)': COLORS['below_normal']
        }
        return status_str, chemical_color_map.get(status_str, 'gray')
        
    elif data_type == 'fish':
        fish_color_map = {
            'Excellent': COLORS['fish']['excellent'],
            'Good': COLORS['fish']['good'], 
            'Fair': COLORS['fish']['fair'],
            'Poor': COLORS['fish']['poor'],
            'Very Poor': COLORS['fish']['very poor']
        }
        return status_str, fish_color_map.get(status_str, 'gray')
        
    elif data_type == 'macro':
        macro_color_map = {
            'Non-impaired': COLORS['macro']['non-impaired'],
            'Slightly Impaired': COLORS['macro']['slightly_impaired'],
            'Moderately Impaired': COLORS['macro']['moderately_impaired'],
            'Severely Impaired': COLORS['macro']['severely_impaired']
        }
        return status_str, macro_color_map.get(status_str, 'gray')
        
    elif data_type == 'habitat':
        habitat_color_map = {
            'A': COLORS['habitat']['a'],
            'B': COLORS['habitat']['b'],
            'C': COLORS['habitat']['c'],
            'D': COLORS['habitat']['d'],
            'F': COLORS['habitat']['f']
        }
        return status_str, habitat_color_map.get(status_str, 'gray')
    
    return "Unknown", 'gray'

def filter_sites_by_active_status(sites, active_only=False):
    """
    Filter monitoring sites based on active status.
    
    Args:
        sites: List of site dictionaries with 'active' property
        active_only: Boolean - if True, return only active sites; if False, return all sites
    
    Returns:
        Tuple of (filtered_sites, active_count, historic_count, total_count)
    """
    if not active_only:
        # Return all sites with counts
        active_count = sum(1 for site in sites if site.get('active', False))
        historic_count = len(sites) - active_count
        return sites, active_count, historic_count, len(sites)
    
    # Filter to only active sites
    filtered_sites = [site for site in sites if site.get('active', False)]
    active_count = len(filtered_sites)
    historic_count = 0  # No historic sites when filtering
    total_original = len(sites)
    
    return filtered_sites, active_count, historic_count, total_original

# ============================================================================
# UI HELPER FUNCTIONS - Formatting and Text Creation
# ============================================================================

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
        return f"{value:.0f}%"  
    elif parameter == 'pH':
        return f"{value:.1f}"  
    elif parameter == 'soluble_nitrogen':
        return f"{value:.2f} mg/L"  
    elif parameter == 'Phosphorus':
        return f"{value:.3f} mg/L"  
    elif parameter == 'Chloride':
        return f"{value:.0f} mg/L"  
    else:
        return f"{value}"

def _create_hover_text(data_type, site_name, value, status, site_data, config, parameter_name=None):
    """
    Helper function to create hover text for different data types.
    
    Args:
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat')
        site_name: Name of the site
        value: Parameter value
        status: Status text
        site_data: Site data row
        config: Data configuration dict
        parameter_name: Parameter name (for chemical data)
    
    Returns:
        Formatted hover text string
    """
    if data_type == 'chemical':
        formatted_value = format_parameter_value(parameter_name, value)
        friendly_name = MAP_PARAMETER_LABELS.get(parameter_name, parameter_name)
        date_str = pd.to_datetime(site_data[config['date_column']].iloc[0]).strftime('%B %d, %Y')
        return f"Site: {site_name}<br>{friendly_name}: {formatted_value}<br>Status: {status}<br>Last reading: {date_str}"
    
    elif data_type == 'fish':
        year = site_data[config['date_column']].iloc[0]
        return f"Site: {site_name}<br>IBI Score: {value:.2f}<br>Status: {status}<br>Last survey: {year}"
    
    elif data_type == 'macro':
        year = site_data[config['date_column']].iloc[0]
        season_from_data = site_data['season'].iloc[0]
        date_str = f"{season_from_data} {year}"
        return f"Site: {site_name}<br>Bioassessment Score: {value:.2f}<br>Status: {status}<br>Last survey: {date_str}"
    
    elif data_type == 'habitat':
        year = site_data[config['date_column']].iloc[0]  
        return f"Site: {site_name}<br>Habitat Score: {value:.0f}<br>Grade: {status}<br>Last assessment: {year}<br><br><b>🔍 Click to view detailed data</b>"
    
    return f"Site: {site_name}<br>Status: {status}"

# ============================================================================
# MAP LAYOUT HELPER FUNCTIONS
# ============================================================================

def _create_base_map_layout(fig, title="Monitoring Sites"):
    """
    Helper function to apply consistent map layout configuration.
    
    Args:
        fig: Plotly figure to configure
        title: Map title
    
    Returns:
        Updated figure with standard layout
    """
    fig.update_layout(
        map=dict(
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
            center=dict(lat=35.5, lon=-98.2),
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
        ],
        title=dict(text=title, x=0.5, y=0.98)
    )
    return fig

def add_site_marker(fig, lat, lon, color, site_name, hover_text=None, active=True):
    """
    Add a site marker to the map with different styling for active vs historic sites.
    
    Args:
        fig: The plotly figure to add the marker to
        lat: Latitude of the marker
        lon: Longitude of the marker
        color: Color of the marker (if provided, overrides active/historic styling)
        site_name: Name of the site
        hover_text: Text to display on hover (defaults to site_name if None)
        active: Whether the site is active (True) or historic (False)
    
    Returns:
        The updated figure
    """
    
    # If a specific color is provided (for parameter data), use it
    if color and color != '':
        marker_color = color
        marker_size = 10  
    else:
        # Use active/historic styling
        if active:
            marker_color = '#3366CC'  # Blue for active sites
            marker_size = 10
        else:
            marker_color = '#9370DB'  # Medium slate blue for historic sites
            marker_size = 6  
    
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers',
        marker=dict(
            size=marker_size,
            color=marker_color,
            opacity=1.0,
            symbol='circle'
        ),
        text=[hover_text if hover_text else site_name],
        name=site_name,
        hoverinfo='text'
    ))
    
    return fig

def create_error_map(error_message):
    """
    Create a basic map with an error message.
    
    Args:
        error_message: Error message to display
    
    Returns:
        Plotly figure with error message
    """
    fig = go.Figure()
    fig.update_layout(
        map=dict(
            style="white-bg",
            center=dict(lat=35.5, lon=-98.2),
            zoom=6.2
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        annotations=[
            dict(
                text=error_message,
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

# ============================================================================
# MAIN VISUALIZATION FUNCTIONS - Public API
# ============================================================================

def add_data_markers(fig, sites, data_type, parameter_name=None, season=None, filter_no_data=True):
    """
    Add markers to the map for any data type.
    
    Args:
        fig: The plotly figure to add markers to
        sites: List of site dictionaries with coordinates
        data_type: 'chemical', 'fish', 'macro', 'habitat'
        parameter_name: For chemical data (specific parameter like 'do_percent')
        season: For macro data ('Summer' or 'Winter')
        filter_no_data: Whether to filter out sites with no data (default: True)
    
    Returns:
        Tuple of (updated_figure, sites_with_data_count, total_sites_count)
    """
    # Get the latest data for this data type
    latest_data = get_latest_data_by_type(data_type)

    # Handle empty data
    if latest_data.empty:
        logger.warning(f"No {data_type} data available for mapping")
        return fig, 0, len(sites)
    
    # Data type specific configurations
    data_config = {
        'chemical': {
            'value_column': parameter_name,
            'status_column': f'{parameter_name}_status',
            'date_column': 'Date',
            'site_column': 'Site_Name'
        },
        'fish': {
            'value_column': 'comparison_to_reference',
            'status_column': 'integrity_class',
            'date_column': 'year',
            'site_column': 'site_name'
        },
        'macro': {
            'value_column': 'comparison_to_reference',
            'status_column': 'biological_condition',
            'date_column': 'year',
            'site_column': 'site_name'
        },
        'habitat': {
            'value_column': 'total_score',
            'status_column': 'habitat_grade',
            'date_column': 'year',
            'site_column': 'site_name'
        }
    }
    
    config = data_config[data_type]
    
    # Track sites with data for counting
    sites_with_data = 0
    total_sites = len(sites)
    
    for site in sites:
        site_name = site["name"]
        
        # Find data for this site
        site_data = latest_data[latest_data[config['site_column']] == site_name]
        
        # Handle season filtering for macro data (only when season is specified)
        if data_type == 'macro' and season:
            site_data = site_data[site_data['season'] == season]
        
        has_data = not site_data.empty and config['value_column'] in site_data.columns
        
        # If filtering is enabled and site has no data, skip it
        if filter_no_data and not has_data:
            continue
            
        if has_data:
            sites_with_data += 1
            
            # Get the value and status from database
            value = site_data[config['value_column']].iloc[0]
            
            # Get status from database 
            if config['status_column'] in site_data.columns and not pd.isna(site_data[config['status_column']].iloc[0]):
                database_status = site_data[config['status_column']].iloc[0]
                status, color = get_status_color_from_database(data_type, database_status)
            else:
                # If database status not available, use unknown status
                logger.warning(f"No database status found for {data_type} data at site {site_name}")
                status, color = "Unknown", 'gray'
            
            # Create hover text using helper function
            hover_text = _create_hover_text(data_type, site_name, value, status, site_data, config, parameter_name)
            
            # Add marker with determined color
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color=color,
                site_name=site_name,
                hover_text=hover_text,
                active=site["active"] 
            )
    
    return fig, sites_with_data, total_sites

def create_basic_site_map(active_only=False):
    """
    Create a basic interactive map with all monitoring sites shown with different shapes/colors for active vs historic.
    
    Args:
        active_only: Boolean - if True, show only active sites; if False, show all sites
        
    Returns:
        Tuple of (figure, active_count, historic_count, total_count)
    """
    try:
        # Create the base map
        fig = go.Figure()
        
        # Check if we have sites loaded
        if not MONITORING_SITES:
            return create_error_map("Error: No monitoring sites available"), 0, 0, 0
        
        # Apply filtering if requested
        if active_only:
            sites_to_use, active_count, historic_count, total_original = filter_sites_by_active_status(
                MONITORING_SITES, active_only
            )
        else:
            sites_to_use = MONITORING_SITES
            active_count = sum(1 for site in sites_to_use if site.get('active', False))
            historic_count = len(sites_to_use) - active_count
        
        # Add all sites with appropriate styling handled by add_site_marker
        for site in sites_to_use:
            hover_text = (f"Site: {site['name']}<br>"
                         f"County: {site['county']}<br>"
                         f"River Basin: {site['river_basin']}<br>"
                         f"Ecoregion: {site['ecoregion']}")
            
            # Add marker (styling handled internally by add_site_marker)
            fig = add_site_marker(
                fig=fig,
                lat=site["lat"],
                lon=site["lon"],
                color='',  # Empty since styling is handled internally
                site_name=site["name"],
                hover_text=hover_text,
                active=site["active"]
            )
        
        # Apply standard map layout
        fig = _create_base_map_layout(fig, "Monitoring Sites")
        
        # Return the correct count based on filtering
        total_count = len(sites_to_use)
        
        return fig, active_count, historic_count, total_count
    
    except Exception as e:
        print(f"Error creating basic site map: {e}")
        return create_error_map(f"Error creating map: {str(e)}"), 0, 0, 0

def add_parameter_colors_to_map(fig, param_type, param_name, sites=None):
    """
    Update an existing map figure with parameter-specific color coding.
    
    Args:
        fig: Existing plotly figure with basic markers
        param_type: Type of parameter ('chem', 'bio', or 'habitat')
        param_name: Specific parameter name (e.g., 'do_percent', 'Fish_IBI')
        sites: List of site dictionaries to use (defaults to MONITORING_SITES if None)
    
    Returns:
        Tuple of (updated_figure, sites_with_data_count, total_sites_count)
    """
    try:        
        # Use provided sites or default to all monitoring sites
        sites_to_use = sites if sites is not None else MONITORING_SITES
        
        # Clear existing traces (basic blue markers)
        fig.data = []
        
        # Add parameter-specific markers with filtering enabled
        if param_type == 'chem':
            fig, sites_with_data, total_sites = add_data_markers(
                fig, sites_to_use, 'chemical', parameter_name=param_name, filter_no_data=True
            )
        elif param_type == 'bio':
            if param_name == 'Fish_IBI':
                fig, sites_with_data, total_sites = add_data_markers(
                    fig, sites_to_use, 'fish', filter_no_data=True
                )
            elif param_name == 'Macro_Combined':
                fig, sites_with_data, total_sites = add_data_markers(
                    fig, sites_to_use, 'macro', filter_no_data=True
                )
        elif param_type == 'habitat':
            fig, sites_with_data, total_sites = add_data_markers(
                fig, sites_to_use, 'habitat', filter_no_data=True
            )
        
        # Apply standard map layout with parameter-specific title
        display_name = PARAMETER_LABELS.get(param_name, param_name)
        fig = _create_base_map_layout(fig, f"Monitoring Sites - {display_name} Status")
        
        return fig, sites_with_data, total_sites
        
    except Exception as e:
        logger.error(f"Error adding parameter colors: {e}")
        return fig, 0, len(sites_to_use)  # Return original figure if coloring fails

# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

try:
    MONITORING_SITES = load_sites_from_database()
except Exception as e:
    print(f"Warning: Could not load sites from database: {e}")
    MONITORING_SITES = []  # Fallback to empty list
