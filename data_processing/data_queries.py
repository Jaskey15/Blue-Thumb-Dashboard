"""
Data query utilities for the Blue Thumb Water Quality Dashboard.
Functions for retrieving data from the database and CSV files for visualization and analysis.
"""

import pandas as pd
import sqlite3
import os
from data_processing import setup_logging

# Set up logging
logger = setup_logging("data_queries", category="processing")

# =============================================================================
# Chemical Data Queries
# =============================================================================

def get_chemical_date_range():
    """
    Get the date range (min and max years) for all chemical data in the database.
    
    Returns:
        Tuple of (min_year, max_year) or (2005, 2025) if no data found
    """
    from database.database import get_connection, close_connection
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query for min and max years from chemical collection events
        cursor.execute("SELECT MIN(year), MAX(year) FROM chemical_collection_events")
        result = cursor.fetchone()
        
        if result and result[0] is not None and result[1] is not None:
            min_year, max_year = result
            logger.info(f"Chemical data date range: {min_year} to {max_year}")
            return min_year, max_year
        else:
            logger.warning("No chemical data found in database, using default range")
            return 2005, 2025
            
    except Exception as e:
        logger.error(f"Error getting chemical date range: {e}")
        logger.info("Falling back to default date range")
        return 2005, 2025
        
    finally:
        if conn:
            close_connection(conn)

def get_chemical_data_from_db(site_name=None):
    """
    Retrieve chemical data from the database.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        DataFrame with chemical data
    """
    from database.database import get_connection, close_connection
    from data_processing.chemical_utils import KEY_PARAMETERS
    
    conn = get_connection()
    try:
        # Base query to get chemical data
        query = """
        SELECT 
            s.site_name AS Site_Name,
            c.collection_date AS Date,
            c.year AS Year,
            c.month AS Month,
            p.parameter_code AS parameter_code,
            m.value,
            m.status
        FROM 
            chemical_measurements m
        JOIN 
            chemical_collection_events c ON m.event_id = c.event_id
        JOIN 
            sites s ON c.site_id = s.site_id
        JOIN 
            chemical_parameters p ON m.parameter_id = p.parameter_id
        """
        
        # Add site filter if needed
        params = []
        if site_name:
            query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Execute query
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            logger.info(f"No chemical data found in database")
            return pd.DataFrame()
            
        # Convert date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Pivot the data to get one row per date/site
        pivot_df = df.pivot_table(
            index=['Site_Name', 'Date', 'Year', 'Month'],
            columns='parameter_code',
            values='value',
            aggfunc='first'
        ).reset_index()
        
        # Check if we have the key parameters
        for param in KEY_PARAMETERS:
            if param not in pivot_df.columns:
                logger.warning(f"Key parameter {param} not found in database data")
                
        return pivot_df
        
    except Exception as e:
        logger.error(f"Error retrieving chemical data from database: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)

# =============================================================================
# Fish Data Queries
# =============================================================================

def get_fish_date_range():
    """
    Get the date range (min and max years) for all fish data in the database.
    
    Returns:
        Tuple of (min_year, max_year) or (2005, 2025) if no data found
    """
    from database.database import get_connection, close_connection
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query for min and max years from fish collection events
        cursor.execute("SELECT MIN(year), MAX(year) FROM fish_collection_events")
        result = cursor.fetchone()
        
        if result and result[0] is not None and result[1] is not None:
            min_year, max_year = result
            logger.info(f"Fish data date range: {min_year} to {max_year}")
            return min_year, max_year
        else:
            logger.warning("No fish data found in database, using default range")
            return 2005, 2025
            
    except Exception as e:
        logger.error(f"Error getting fish date range: {e}")
        logger.info("Falling back to default date range")
        return 2005, 2025
        
    finally:
        if conn:
            close_connection(conn)

def get_fish_dataframe(site_name=None):
    """
    Query to get fish data with summary scores.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with fish data
    """
    from database.database import get_connection, close_connection
    
    conn = None
    try:
        conn = get_connection()
        
        # Base query
        fish_query = '''
        SELECT 
            e.event_id,
            s.site_name,
            e.year,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        JOIN 
            sites s ON e.site_id = s.site_id
        '''
        
        # Add filter for site if provided
        params = []
        if site_name:
            fish_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Add ordering
        fish_query += " ORDER BY e.year"
        
        # Execute query
        fish_df = pd.read_sql_query(fish_query, conn, params=params)
        
        if fish_df.empty:
            if site_name:
                logger.warning(f"No fish data found for site: {site_name}")
            else:
                logger.warning("No fish data found in the database")
        else: 
            logger.info(f"Retrieved {len(fish_df)} fish collection records")
    
        return fish_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_fish_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving fish data: {e}")
        return pd.DataFrame({'error': ['Error retrieving fish data']})
    finally:
        if conn:
            close_connection(conn)

def get_fish_metrics_data_for_table(site_name=None):
    """
    Query the database to get detailed fish metrics data for the metrics table display.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Tuple of (metrics_df, summary_df) for display
    """
    from database.database import get_connection, close_connection
    
    conn = None
    try:
        conn = get_connection()
        
        # Base query for metrics data
        metrics_query = '''
        SELECT 
            s.site_name,
            e.year,
            e.sample_id,
            m.metric_name,
            m.raw_value,
            m.metric_score
        FROM 
            fish_metrics m
        JOIN 
            fish_collection_events e ON m.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        # Base query for summary data
        summary_query = '''
        SELECT 
            s.site_name,
            e.year,
            e.sample_id,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        # Add filter for site name if provided
        params = []
        if site_name:
            where_clause = ' WHERE s.site_name = ?'
            metrics_query += where_clause
            summary_query += where_clause
            params.append(site_name)
        
        # Add order by clause
        metrics_query += ' ORDER BY s.site_name, e.year, m.metric_name'
        summary_query += ' ORDER BY s.site_name, e.year'
        
        # Execute queries
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        logger.debug(f"Retrieved fish metrics data: {len(metrics_df)} metric records and {summary_df.shape[0]} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving fish metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn) 