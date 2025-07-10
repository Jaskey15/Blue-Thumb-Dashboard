"""
Interactive Map Visualization for Blue Thumb Monitoring Sites

Creates interactive maps showing monitoring site locations with color-coded markers 
based on water quality parameters, biological conditions, and habitat assessments.

Core Features:
- Basic site map with active/historic differentiation
- Parameter-specific status coloring (chemical, biological, habitat)
- Efficient data loading with optimized SQL queries
- Vectorized operations for color mapping and hover text
- Batch marker processing for improved performance

Status Categories:
- Chemical: Normal/Caution/Poor
- Fish: Excellent/Good/Fair/Poor/Very Poor
- Macroinvertebrate: Non-impaired through Severely Impaired
- Habitat: A through F grades
"""

import pandas as pd
import plotly.graph_objects as go

from database.database import close_connection, get_connection
from utils import setup_logging
from visualizations.map_queries import (
    get_latest_chemical_data_for_maps,
    get_latest_fish_data_for_maps,
    get_latest_habitat_data_for_maps,
    get_latest_macro_data_for_maps,
    get_sites_for_maps,
)

logger = setup_logging("map_viz", category="visualization")

# Status-based color scheme for all parameter types
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

# Parameter display names for UI consistency
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

# Parameter labels for hover text
MAP_PARAMETER_LABELS = {
    'do_percent': 'Dissolved Oxygen Saturation',
    'pH': 'pH',
    'soluble_nitrogen': 'Soluble Nitrogen',
    'Phosphorus': 'Phosphorus',
    'Chloride': 'Chloride'
}

# CORE MAP FUNCTIONS

def create_basic_site_map(active_only=False):
    """
    Create base map with active/historic site differentiation using batch operations.
    """
    try:
        sites_df = get_sites_for_maps(active_only=active_only)
        
        if sites_df.empty:
            return create_error_map("Error: No monitoring sites available"), 0, 0, 0
        
        # Site count calculations
        if active_only:
            active_count = len(sites_df)
            historic_count = 0
            total_count = active_count
        else:
            active_count = (sites_df['active'] == True).sum()
            historic_count = (sites_df['active'] == False).sum()
            total_count = len(sites_df)
        
        # Vectorized hover text generation
        hover_texts = (
            "<b>Site:</b> " + sites_df['site_name'].astype(str) + "<br>" +
            "<b>County:</b> " + sites_df['county'].astype(str) + "<br>" +
            "<b>River Basin:</b> " + sites_df['river_basin'].astype(str) + "<br>" +
            "<b>Ecoregion:</b> " + sites_df['ecoregion'].astype(str)
        ).tolist()
        
        # Vectorized marker styling
        marker_colors = sites_df['active'].map({True: '#3366CC', False: '#9370DB'}).tolist()
        marker_sizes = sites_df['active'].map({True: 10, False: 6}).tolist()
        
        fig = go.Figure()
        
        if len(sites_df) > 0:
            fig.add_trace(go.Scattermap(
                lat=sites_df['latitude'].tolist(),
                lon=sites_df['longitude'].tolist(),
                mode='markers',
                marker=dict(
                    size=marker_sizes,
                    color=marker_colors,
                    opacity=1.0,
                    symbol='circle'
                ),
                text=hover_texts,
                name="monitoring_sites",
                hoverinfo='text',
                showlegend=False
            ))
        
        fig = _create_base_map_layout(fig, "Monitoring Sites")
        
        return fig, active_count, historic_count, total_count
        
    except Exception as e:
        logger.error(f"Error creating site map: {e}")
        return create_error_map(f"Error creating map: {str(e)}"), 0, 0, 0

def add_parameter_colors_to_map(fig, param_type, param_name, sites_df=None, active_only=False):
    """
    Updates map with parameter-specific color coding using vectorized operations.
    
    Args:
        fig: Existing plotly figure with basic markers
        param_type: Parameter category ('chem', 'bio', 'habitat')
        param_name: Specific parameter (e.g., 'do_percent', 'Fish_IBI')
        sites_df: Optional pre-loaded site information
        active_only: If True, shows only active sites
    
    Returns:
        (updated_figure, sites_with_data_count, total_sites_count)
    """
    try:        
        if sites_df is None:
            sites_df = get_sites_for_maps(active_only=active_only)
        
        if sites_df.empty:
            return fig, 0, 0
        
        fig.data = []  # Clear existing markers
        
        # Convert DataFrame to list for marker processing
        sites_list = []
        for _, row in sites_df.iterrows():
            sites_list.append({
                "name": row['site_name'],
                "lat": row['latitude'],
                "lon": row['longitude'],
                "county": row['county'],
                "river_basin": row['river_basin'],
                "ecoregion": row['ecoregion'],
                "active": row['active']
            })
        
        # Parameter-specific marker addition
        if param_type == 'chem':
            fig, sites_with_data, total_sites = add_data_markers(
                fig, sites_list, 'chemical', parameter_name=param_name, filter_no_data=True
           )
        elif param_type == 'bio':
            if param_name == 'Fish_IBI':
                fig, sites_with_data, total_sites = add_data_markers(
                    fig, sites_list, 'fish', filter_no_data=True
                )
            elif param_name == 'Macro_Combined':
                fig, sites_with_data, total_sites = add_data_markers(
                    fig, sites_list, 'macro', filter_no_data=True
                )
        elif param_type == 'habitat':
            fig, sites_with_data, total_sites = add_data_markers(
                fig, sites_list, 'habitat', filter_no_data=True
            )
        
        display_name = PARAMETER_LABELS.get(param_name, param_name)
        fig = _create_base_map_layout(fig, f"Monitoring Sites - {display_name} Status")
        
        return fig, sites_with_data, total_sites
        
    except Exception as e:
        logger.error(f"Error adding parameter colors: {e}")
        return fig, 0, len(sites_df) if sites_df is not None and not sites_df.empty else 0

# DATA PROCESSING FUNCTIONS

def get_latest_data_by_type(data_type):
    """
    Retrieves latest data per site using optimized SQL queries with window functions.
    
    Args:
        data_type: Data category ('chemical', 'fish', 'macro', 'habitat')
    
    Returns:
        DataFrame with latest data per site
    """
    query_functions = {
        'chemical': get_latest_chemical_data_for_maps,
        'fish': get_latest_fish_data_for_maps,
        'macro': get_latest_macro_data_for_maps,
        'habitat': get_latest_habitat_data_for_maps
    }
    
    if data_type not in query_functions:
        raise ValueError(f"Unknown data type: {data_type}")
    
    df = query_functions[data_type]()
    
    if df.empty:
        logger.warning(f"No {data_type} data found in database")
        return pd.DataFrame()
    
    logger.info(f"Retrieved latest {data_type} data for {len(df)} sites")
    return df

def get_status_color(data, data_type):
    """
    Maps status values to display colors using vectorized operations.
    
    Args:
        data: Single status value or pandas Series
        data_type: Data category ('chemical', 'fish', 'macro', 'habitat')
    
    Returns:
        For single values: (status_text, color_code)
        For Series: (status_series, color_series)
    """
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
    
    # Single value handling
    if not isinstance(data, pd.Series):
        if pd.isna(data) or data is None:
            return "Unknown", 'gray'
        
        data_series = pd.Series([data])
        is_single = True
    else:
        data_series = data
        is_single = False
    
    clean_series = data_series.astype(str).str.strip()
    is_null = data_series.isna()
    
    # Vectorized color mapping
    color_map = color_maps.get(data_type, {})
    colors = clean_series.map(color_map).fillna('gray')
    statuses = clean_series.where(~is_null, "Unknown")
    
    return (statuses.iloc[0], colors.iloc[0]) if is_single else (statuses, colors)

def get_total_site_count(active_only=False):
    """
    Get total site count using optimized SQL query for performance.
    """
    conn = None
    try:
        conn = get_connection()
        
        if active_only:
            query = "SELECT COUNT(*) FROM sites WHERE active = 1 AND latitude IS NOT NULL AND longitude IS NOT NULL"
        else:
            query = "SELECT COUNT(*) FROM sites WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        
        cursor = conn.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        
        return count
        
    except Exception as e:
        logger.error(f"Error getting site count: {e}")
        return 0
        
    finally:
        if conn:
            close_connection(conn)

# UI HELPER FUNCTIONS

def create_hover_text(df, data_type, config, parameter_name):
    """
    Generates hover text for map markers using vectorized string operations.
    
    Args:
        df: DataFrame with site and parameter data
        data_type: Data category ('chemical', 'fish', 'macro', 'habitat')
        config: Dictionary with column mappings
        parameter_name: Specific parameter for chemical data
    
    Returns:
        List of formatted hover text strings
    """
    hover_texts = "<b>Site:</b> " + df[config['site_column']].astype(str) + "<br>"
    
    # Parameter-specific information formatting
    if data_type == 'chemical' and parameter_name:
        def format_chemical_value(value, param):
            if pd.isna(value):
                return "No data"
            
            if param in ['do_percent', 'Chloride']:
                if float(value) == int(float(value)):
                    return str(int(float(value)))
                else:
                    return str(value)
            else:
                return str(value)
        
        value_series = df[config['value_column']].apply(lambda x: format_chemical_value(x, parameter_name))
        
        # Unit application based on parameter type
        if parameter_name == 'do_percent':
            value_series = value_series.where(value_series == "No data", value_series + "%")
        elif parameter_name == 'pH':
            pass  # pH has no units
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
    
    # Date information with consistent formatting
    if config['date_column'] in df.columns:
        if data_type == 'chemical':
            dates = pd.to_datetime(df[config['date_column']]).dt.strftime('%m-%d-%Y')
            hover_texts += "<b>Latest Reading:</b> " + dates + "<br>"
        elif data_type == 'macro':
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
    
    hover_texts += "<br><b>🔍 Click to view detailed data</b>"
    
    return hover_texts.tolist()

def _create_base_map_layout(fig, title="Monitoring Sites"):
    """
    Apply consistent layout configuration across all map instances.
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

def create_error_map(error_message):
    """
    Create basic map with error message overlay for troubleshooting.
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

def add_data_markers(fig, sites, data_type, parameter_name=None, season=None, filter_no_data=True):
    """
    Adds data markers to map using optimized batch processing.
    
    Args:
        fig: Plotly figure to add markers to
        sites: List of site dictionaries with coordinates
        data_type: Data category ('chemical', 'fish', 'macro', 'habitat')
        parameter_name: Chemical parameter name (for chemical data)
        season: Season filter for macro data ('Summer'/'Winter')
        filter_no_data: If True, excludes sites without data
    
    Returns:
        (updated_figure, sites_with_data_count, total_sites_count)
    """
    latest_data = get_latest_data_by_type(data_type)

    if latest_data.empty:
        logger.warning(f"No {data_type} data available for mapping")
        return fig, 0, len(sites)
    
    # Data type configuration for consistent processing
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
    
    # Efficient DataFrame merging for site data
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
    
    if filter_no_data:
        sites_to_plot = merged_data[has_data_mask].copy()
    else:
        sites_to_plot = merged_data.copy()
    
    sites_with_data = has_data_mask.sum()
    total_sites = len(sites)  
    
    if total_sites == 0:
        return fig, sites_with_data, len(sites)
    
    # Vectorized status and color computation
    if config['status_column'] in sites_to_plot.columns:
        statuses, colors = get_status_color(sites_to_plot[config['status_column']], data_type)
        sites_to_plot = sites_to_plot.copy()
        sites_to_plot['computed_status'] = statuses
        sites_to_plot['computed_color'] = colors
    else:
        sites_to_plot = sites_to_plot.copy()
        sites_to_plot['computed_status'] = "Unknown"
        sites_to_plot['computed_color'] = 'gray'

    hover_texts = create_hover_text(sites_to_plot, data_type, config, parameter_name)
    
    # Batch marker addition for improved performance
    if len(sites_to_plot) > 0:
        lats = sites_to_plot['lat'].tolist()
        lons = sites_to_plot['lon'].tolist()
        colors_list = sites_to_plot['computed_color'].tolist()
        active_status = sites_to_plot['active'].tolist()
        
        # Vectorized marker styling
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
        
        # Single trace for all markers for performance
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