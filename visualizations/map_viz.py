"""
map_viz.py - Interactive Map Visualization for Monitoring Sites

This module creates interactive maps displaying monitoring site locations with 
parameter-specific color coding based on water quality status, biological conditions, 
and habitat assessments for Blue Thumb stream monitoring data.

Key Functions:
- create_basic_site_map(): Basic site map with active/historic site differentiation
- add_parameter_colors_to_map(): Add parameter-specific status color coding
- add_data_markers(): Add markers for chemical, biological, or habitat data
- get_status_color(): Unified vectorized status/color mapping for single values or Series
- Helper functions for data loading and efficient hover text generation

Performance Features:
- Vectorized pandas operations for color mapping and hover text creation
- Optimized database queries with efficient SQL and indexes
- Batch marker processing for improved rendering speed

Supported Data Types:
- Chemical parameters (DO, pH, nutrients) with Normal/Caution/Poor status
- Fish IBI with Excellent/Good/Fair/Poor integrity classes  
- Macroinvertebrate bioassessment with impairment levels
- Habitat assessment with A/B/C/D/F grade classifications
"""

import pandas as pd
import plotly.graph_objects as go

from database.database import get_connection, close_connection
from utils import setup_logging

from visualizations.map_queries import (
    get_latest_chemical_data_for_maps,
    get_latest_fish_data_for_maps,
    get_latest_macro_data_for_maps,
    get_latest_habitat_data_for_maps
)

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
    'Fish_IBI': 'Fish Community',
    'Macro_Combined': 'Macroinvertebrate Community',
    'Habitat_Score': 'Habitat'
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
    Get the latest data for each site by data type using efficient SQL queries.
    Uses database indexes and window functions to get only latest data per site.
    
    Args:
        data_type: 'chemical', 'fish', 'macro', or 'habitat'
    
    Returns:
        DataFrame with latest data per site (already filtered, no Python grouping needed)
    """
    # Define query functions for each data type
    query_functions = {
        'chemical': get_latest_chemical_data_for_maps,
        'fish': get_latest_fish_data_for_maps,
        'macro': get_latest_macro_data_for_maps,
        'habitat': get_latest_habitat_data_for_maps
    }
    
    if data_type not in query_functions:
        raise ValueError(f"Unknown data type: {data_type}")
    
    # Execute the optimized query
    df = query_functions[data_type]()
    
    if df.empty:
        logger.warning(f"No {data_type} data found in database")
        return pd.DataFrame()
    
    logger.info(f"Retrieved latest {data_type} data for {len(df)} sites")
    return df

def get_status_color(data, data_type):
    """
    Map database status values to display colors for different data types.
    Handles both single values and pandas Series efficiently.
    
    Args:
        data: Single status value OR pandas Series of status values
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat')
    
    Returns:
        - For single values: Tuple of (status_text, color_code)
        - For Series: Tuple of (status_series, color_series) as pandas Series
    """
    # Define color mappings for each data type 
    color_maps = {
        'chemical': {
            'Normal': COLORS['normal'],
            'Caution': COLORS['caution'], 
            'Poor': COLORS['poor'],
            'Above Normal (Basic/Alkaline)': COLORS['above_normal'],
            'Below Normal (Acidic)': COLORS['below_normal']
        },
        'fish': {
            'Excellent': COLORS['fish']['excellent'],
            'Good': COLORS['fish']['good'],
            'Fair': COLORS['fish']['fair'],
            'Poor': COLORS['fish']['poor'],
            'Very Poor': COLORS['fish']['very poor']
        },
        'macro': {
            'Non-impaired': COLORS['macro']['non-impaired'],
            'Slightly Impaired': COLORS['macro']['slightly_impaired'],
            'Moderately Impaired': COLORS['macro']['moderately_impaired'],
            'Severely Impaired': COLORS['macro']['severely_impaired']
        },
        'habitat': {
            'A': COLORS['habitat']['a'],
            'B': COLORS['habitat']['b'],
            'C': COLORS['habitat']['c'],
            'D': COLORS['habitat']['d'],
            'F': COLORS['habitat']['f']
        }
    }
    
    # Handle single values
    if not isinstance(data, pd.Series):
        if pd.isna(data) or data is None:
            return "Unknown", 'gray'
        
        # Convert single value to series for consistent processing
        data_series = pd.Series([data])
        is_single = True
    else:
        data_series = data
        is_single = False
    
    clean_series = data_series.astype(str).str.strip()
    
    is_null = data_series.isna()
    
    # Map colors using pandas map
    color_map = color_maps.get(data_type, {})
    colors = clean_series.map(color_map).fillna('gray')
    
    # Map statuses (use clean series, with "Unknown" for nulls)
    statuses = clean_series.where(~is_null, "Unknown")
    
    # Return appropriate format based on input type
    if is_single:
        return statuses.iloc[0], colors.iloc[0]
    else:
        return statuses, colors

def filter_sites_by_active_status(sites, active_only=False):
    """
    Filter sites based on active status and return counts.
    
    Args:
        sites: List of site dictionaries
        active_only: Boolean - if True, only return active sites
    
    Returns:
        Tuple of (filtered_sites, active_count, historic_count, total_count)
    """
    if not sites:
        return [], 0, 0, 0
    
    total_count = len(sites)
    active_sites = [site for site in sites if site.get('active', False)]
    historic_sites = [site for site in sites if not site.get('active', False)]
    
    active_count = len(active_sites)
    historic_count = len(historic_sites)
    
    if active_only:
        return active_sites, active_count, historic_count, total_count
    else:
        return sites, active_count, historic_count, total_count

# ============================================================================
# UI HELPER FUNCTIONS - Display Formatting
# ============================================================================

def create_hover_text(df, data_type, config, parameter_name):
    """Create hover text using fast vectorized operations"""
    
    # Base hover info - site name
    hover_texts = "<b>Site:</b> " + df[config['site_column']].astype(str) + "<br>"
    
    # Add parameter-specific information
    if data_type == 'chemical' and parameter_name:
        # Format values properly 
        def format_chemical_value(value, param):
            if pd.isna(value):
                return "No data"
            
            # For DO and Chloride, show as integers if they're whole numbers
            if param in ['do_percent', 'Chloride']:
                if float(value) == int(float(value)):
                    return str(int(float(value)))
                else:
                    return str(value)
            else:
                return str(value)
        
        value_series = df[config['value_column']].apply(lambda x: format_chemical_value(x, parameter_name))
        
        # Add units based on parameter type
        if parameter_name == 'do_percent':
            value_series = value_series.where(value_series == "No data", value_series + "%")
        elif parameter_name == 'pH':
            # pH has no units, keep as-is
            pass
        elif parameter_name in ['soluble_nitrogen', 'Phosphorus', 'Chloride']:
            value_series = value_series.where(value_series == "No data", value_series + " mg/L")
        
        param_label = PARAMETER_LABELS.get(parameter_name, parameter_name)
        hover_texts += f"<b>{param_label}:</b> " + value_series + "<br>"
        hover_texts += "<b>Status:</b> " + df['computed_status'].astype(str) + "<br>"
        
    elif data_type == 'fish':
        hover_texts += "<b>IBI Score:</b> " + df[config['value_column']].astype(str) + "<br>"
        hover_texts += "<b>Integrity Class:</b> " + df['computed_status'].astype(str) + "<br>"
        
    elif data_type == 'macro':
        hover_texts += "<b>Bioassessment Score:</b> " + df[config['value_column']].astype(str) + "<br>"
        hover_texts += "<b>Biological Condition:</b> " + df['computed_status'].astype(str) + "<br>"
        
    elif data_type == 'habitat':
        habitat_scores = df[config['value_column']].apply(
            lambda x: str(int(float(x))) if pd.notna(x) and float(x) == int(float(x)) else str(x)
        )
        hover_texts += "<b>Habitat Score:</b> " + habitat_scores + "<br>"
        hover_texts += "<b>Grade:</b> " + df['computed_status'].astype(str) + "<br>"
    
    # Add date information
    if config['date_column'] in df.columns:
        if data_type == 'chemical':
            # Format date nicely
            dates = pd.to_datetime(df[config['date_column']]).dt.strftime('%Y-%m-%d')
            hover_texts += "<b>Latest Reading:</b> " + dates + "<br>"
        elif data_type == 'macro':
            # Special handling for macro data to include season
            years = df[config['date_column']].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and float(x) == int(float(x)) else str(x)
            )
            if 'season' in df.columns:
                seasons = df['season'].astype(str)
                hover_texts += "<b>Last Survey:</b> " + seasons + " " + years + "<br>"
            else:
                hover_texts += "<b>Last Survey:</b> " + years + "<br>"
        else:
            years = df[config['date_column']].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and float(x) == int(float(x)) else str(x)
            )
            hover_texts += "<b>Last Survey:</b> " + years + "<br>"
    
    # Add click instruction
    hover_texts += "<br><b>🔍 Click to view detailed data</b>"
    
    return hover_texts.tolist()

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
    Add markers to the map for any data type using optimized batch processing.
    
    This function uses vectorized operations for maximum performance:
    - Single pandas merge instead of individual site filtering
    - Vectorized status/color computation
    - Fast string-based hover text generation
    - Single Plotly trace addition
    
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
    import pandas as pd
    import plotly.graph_objects as go
    
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
    
    # Convert sites to DataFrame for efficient merging
    sites_df = pd.DataFrame(sites)
    sites_df = sites_df.rename(columns={'name': config['site_column']})
    
    data_to_merge = latest_data.copy()
    if data_type == 'macro' and season:
        data_to_merge = data_to_merge[data_to_merge['season'] == season]
    
    merged_data = sites_df.merge(
        data_to_merge, 
        on=config['site_column'], 
        how='left'  # Keep all sites, even those without data
    )
    
    # Vectorized data validation
    has_data_mask = (
        merged_data[config['value_column']].notna() & 
        (config['value_column'] in merged_data.columns)
    )
    
    # Apply filtering if requested
    if filter_no_data:
        sites_to_plot = merged_data[has_data_mask].copy()
    else:
        sites_to_plot = merged_data.copy()
        # For sites without data, we'll use default styling
    
    sites_with_data = has_data_mask.sum()
    total_sites = len(sites)  
    
    if total_sites == 0:
        return fig, sites_with_data, len(sites)
    
    # Compute all statuses and colors 
    if config['status_column'] in sites_to_plot.columns:
        statuses, colors = get_status_color(sites_to_plot[config['status_column']], data_type)
        sites_to_plot = sites_to_plot.copy()
        sites_to_plot['computed_status'] = statuses
        sites_to_plot['computed_color'] = colors
    else:
        # No status data available
        sites_to_plot = sites_to_plot.copy()
        sites_to_plot['computed_status'] = "Unknown"
        sites_to_plot['computed_color'] = 'gray'

    hover_texts = create_hover_text(sites_to_plot, data_type, config, parameter_name)
    
    # Batch add all markers at once u
    if len(sites_to_plot) > 0:
        lats = sites_to_plot['lat'].tolist()
        lons = sites_to_plot['lon'].tolist()
        colors_list = sites_to_plot['computed_color'].tolist()
        active_status = sites_to_plot['active'].tolist()
        
        # Vectorized marker size and color computation
        marker_sizes = []
        final_colors = []
        
        for color, active in zip(colors_list, active_status):
            if color and color != 'gray':  # Has parameter data
                marker_sizes.append(10)
                final_colors.append(color)
            else:  # No data - use active/historic styling
                if active:
                    marker_sizes.append(10)
                    final_colors.append('#3366CC')  # Blue for active
                else:
                    marker_sizes.append(6)
                    final_colors.append('#9370DB')  # Purple for historic
        
        # Add all markers in a single trace 
        fig.add_trace(go.Scattermap(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=dict(
                size=marker_sizes,
                color=final_colors,
                opacity=1.0,
                symbol='circle'
            ),
            text=hover_texts,
            name=f"{data_type}_markers",
            hoverinfo='text',
            showlegend=False
        ))
    
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
        
        # Load sites from database
        monitoring_sites = load_sites_from_database()
        
        # Check if we have sites loaded
        if not monitoring_sites:
            return create_error_map("Error: No monitoring sites available"), 0, 0, 0
        
        # Apply filtering if requested
        if active_only:
            sites_to_use, active_count, historic_count, total_original = filter_sites_by_active_status(
                monitoring_sites, active_only
            )
        else:
            sites_to_use = monitoring_sites
            active_count = sum(1 for site in sites_to_use if site.get('active', False))
            historic_count = len(sites_to_use) - active_count
        
        # Add all sites with appropriate styling handled by add_site_marker
        for site in sites_to_use:
            hover_text = (f"<b>Site:</b> {site['name']}<br>"
                         f"<b>County:</b> {site['county']}<br>"
                         f"<b>River Basin:</b> {site['river_basin']}<br>"
                         f"<b>Ecoregion:</b> {site['ecoregion']}")
            
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
        sites: List of site dictionaries to use (if None, loads from database)
    
    Returns:
        Tuple of (updated_figure, sites_with_data_count, total_sites_count)
    """
    try:        
        # Use provided sites or load from database
        if sites is not None:
            sites_to_use = sites
        else:
            sites_to_use = load_sites_from_database()
        
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


