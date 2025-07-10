"""
Database queries optimized for map visualization performance.

Provides efficient SQL queries to fetch latest site data for map rendering:
- Uses window functions to get latest readings per site
- Leverages database indexes for fast retrieval
- Minimizes data transfer with targeted column selection
- Handles missing data gracefully with pandas operations

Key Functions:
- get_sites_for_maps(): Basic site info with coordinates
- get_latest_*_data_for_maps(): Latest readings for chemical/biological/habitat data
"""

import sqlite3

import pandas as pd

from data_processing.chemical_utils import KEY_PARAMETERS
from database.database import close_connection, get_connection
from utils import setup_logging

logger = setup_logging("map_queries", category="visualization")

def get_sites_for_maps(active_only=False):
    """
    Fetch site information optimized for map display performance.
    """
    conn = None
    try:
        conn = get_connection()
        
        # Essential columns for map rendering
        query = """
        SELECT 
            site_name,
            latitude,
            longitude,
            county,
            river_basin,
            ecoregion,
            active
        FROM sites
        WHERE latitude IS NOT NULL 
        AND longitude IS NOT NULL
        """
        
        params = []
        if active_only:
            query += " AND active = 1"
            
        query += " ORDER BY site_name"
        
        sites_df = pd.read_sql_query(query, conn, params=params)
        
        if sites_df.empty:
            logger.warning("No sites found in database")
            return pd.DataFrame()
        
        # Vectorized missing data handling
        sites_df['county'] = sites_df['county'].fillna('Unknown')
        sites_df['river_basin'] = sites_df['river_basin'].fillna('Unknown')
        sites_df['ecoregion'] = sites_df['ecoregion'].fillna('Unknown')
        sites_df['active'] = sites_df['active'].astype(bool)
        
        logger.info(f"Retrieved {len(sites_df)} sites for map visualization")
        return sites_df
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_sites_for_maps: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving sites for maps: {e}")
        return pd.DataFrame({'error': ['Error retrieving sites data']})
    finally:
        if conn:
            close_connection(conn)
            
def get_latest_chemical_data_for_maps(site_name=None):
    """
    Fetch latest chemical readings per site using window functions for efficiency.
    """
    conn = get_connection()
    try:
        # Window function to get most recent measurement per parameter
        query = """
        WITH latest_measurements AS (
            SELECT 
                s.site_name AS Site_Name,
                c.collection_date AS Date,
                c.year AS Year,
                c.month AS Month,
                p.parameter_code,
                m.value,
                m.status,
                ROW_NUMBER() OVER (
                    PARTITION BY s.site_id, p.parameter_code 
                    ORDER BY c.collection_date DESC
                ) as rn
            FROM chemical_measurements m
            JOIN chemical_collection_events c ON m.event_id = c.event_id
            JOIN sites s ON c.site_id = s.site_id
            JOIN chemical_parameters p ON m.parameter_id = p.parameter_id
        )
        SELECT 
            Site_Name,
            Date,
            Year,
            Month,
            parameter_code,
            value,
            status
        FROM latest_measurements
        WHERE rn = 1
        """
        
        params = []
        if site_name:
            query = query.replace("WHERE rn = 1", "WHERE rn = 1 AND Site_Name = ?")
            params.append(site_name)
            
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            logger.info(f"No chemical data found in database")
            return pd.DataFrame()
            
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Pivot data for map display format
        value_pivot = df.pivot_table(
            index='Site_Name',
            columns='parameter_code',
            values='value',
            aggfunc='first'
        ).reset_index()
        
        status_pivot = df.pivot_table(
            index='Site_Name',
            columns='parameter_code',
            values='status',
            aggfunc='first'
        ).reset_index()
        
        # Aggregate latest date information per site
        site_dates = df.groupby('Site_Name')['Date'].max().reset_index()
        site_years = df.groupby('Site_Name')['Year'].max().reset_index()
        site_months = df.groupby('Site_Name')['Month'].max().reset_index()
        
        value_pivot = value_pivot.merge(site_dates, on='Site_Name', how='left')
        value_pivot = value_pivot.merge(site_years, on='Site_Name', how='left')
        value_pivot = value_pivot.merge(site_months, on='Site_Name', how='left')
        
        # Combine status information with values
        for param in KEY_PARAMETERS:
            if param in status_pivot.columns:
                value_pivot[f'{param}_status'] = status_pivot[param]
        
        logger.info(f"Retrieved latest chemical data for {len(value_pivot)} sites")
        return value_pivot
        
    except Exception as e:
        logger.error(f"Error retrieving latest chemical data: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)

def get_latest_fish_data_for_maps(site_name=None):
    """
    Fetch latest fish survey data per site using window functions.
    """
    conn = None
    try:
        conn = get_connection()
        
        # Most recent fish survey per site
        query = '''
        WITH latest_fish AS (
            SELECT 
                e.event_id,
                s.site_name,
                e.year,
                f.total_score,
                f.comparison_to_reference,
                f.integrity_class,
                ROW_NUMBER() OVER (PARTITION BY s.site_name ORDER BY e.year DESC) as rn
            FROM 
                fish_summary_scores f
            JOIN 
                fish_collection_events e ON f.event_id = e.event_id
            JOIN 
                sites s ON e.site_id = s.site_id
        )
        SELECT 
            event_id,
            site_name,
            year,
            total_score,
            comparison_to_reference,
            integrity_class
        FROM latest_fish
        WHERE rn = 1
        '''
        
        params = []
        if site_name:
            query = query.replace("WHERE rn = 1", "WHERE rn = 1 AND site_name = ?")
            params.append(site_name)
            
        query += " ORDER BY site_name"
        
        fish_df = pd.read_sql_query(query, conn, params=params)
        
        if fish_df.empty:
            if site_name:
                logger.warning(f"No fish data found for site: {site_name}")
            else:
                logger.warning("No fish data found in the database")
        else: 
            logger.info(f"Retrieved latest fish data for {len(fish_df)} sites")
    
        return fish_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_latest_fish_data_for_maps: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving latest fish data: {e}")
        return pd.DataFrame({'error': ['Error retrieving fish data']})
    finally:
        if conn:
            close_connection(conn)

def get_latest_macro_data_for_maps(site_name=None):
    """
    Fetch latest macroinvertebrate survey data per site using window functions.
    """
    conn = None
    try:
        conn = get_connection()
        
        # Most recent macro survey per site
        query = '''
        WITH latest_macro AS (
            SELECT 
                m.event_id,
                s.site_name,
                e.collection_date,
                e.year,
                e.season,
                e.habitat,
                m.total_score,
                m.comparison_to_reference,
                m.biological_condition,
                ROW_NUMBER() OVER (PARTITION BY s.site_name ORDER BY e.collection_date DESC) as rn
            FROM 
                macro_summary_scores m
            JOIN 
                macro_collection_events e ON m.event_id = e.event_id
            JOIN 
                sites s ON e.site_id = s.site_id
        )
        SELECT 
            event_id,
            site_name,
            collection_date,
            year,
            season,
            habitat,
            total_score,
            comparison_to_reference,
            biological_condition
        FROM latest_macro
        WHERE rn = 1
        '''
        
        params = []
        if site_name:
            query = query.replace("WHERE rn = 1", "WHERE rn = 1 AND site_name = ?")
            params.append(site_name)
            
        query += " ORDER BY site_name"
        
        macro_df = pd.read_sql_query(query, conn, params=params)
        
        # Consistent date handling across functions
        if 'collection_date' in macro_df.columns and not macro_df.empty:
            macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
        
        if macro_df.empty:
            if site_name:
                logger.warning(f"No macro data found for site: {site_name}")
            else:
                logger.warning("No macro data found in the database")
        else: 
            logger.info(f"Retrieved latest macro data for {len(macro_df)} sites")
    
        return macro_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_latest_macro_data_for_maps: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving latest macro data: {e}")
        return pd.DataFrame({'error': ['Error retrieving macro data']})
    finally:
        if conn:
            close_connection(conn)

def get_latest_habitat_data_for_maps(site_name=None):
    """
    Fetch latest habitat assessment data per site using window functions.
    """
    conn = None
    try:
        conn = get_connection()
        
        # Most recent habitat assessment per site
        query = '''
        WITH latest_habitat AS (
            SELECT 
                a.assessment_id,
                s.site_name,
                a.assessment_date,
                a.year,
                h.total_score,
                h.habitat_grade,
                ROW_NUMBER() OVER (PARTITION BY s.site_name ORDER BY a.year DESC) as rn
            FROM 
                habitat_summary_scores h
            JOIN 
                habitat_assessments a ON h.assessment_id = a.assessment_id
            JOIN 
                sites s ON a.site_id = s.site_id
        )
        SELECT 
            assessment_id,
            site_name,
            assessment_date,
            year,
            total_score,
            habitat_grade
        FROM latest_habitat
        WHERE rn = 1
        '''
        
        params = []
        if site_name:
            query = query.replace("WHERE rn = 1", "WHERE rn = 1 AND site_name = ?")
            params.append(site_name)
            
        query += " ORDER BY site_name"
        
        habitat_df = pd.read_sql_query(query, conn, params=params)
        
        if habitat_df.empty:
            if site_name:
                logger.warning(f"No habitat data found for site: {site_name}")
            else:
                logger.warning("No habitat data found in the database")
        else: 
            logger.info(f"Retrieved latest habitat data for {len(habitat_df)} sites")

        return habitat_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_latest_habitat_data_for_maps: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving latest habitat data: {e}")
        return pd.DataFrame({'error': ['Error retrieving habitat data']})
    finally:
        if conn:
            close_connection(conn)


