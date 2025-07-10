"""
Provides functions for querying and retrieving data from the database.

This module centralizes all data retrieval operations for chemical, biological,
and habitat data, providing a consistent interface for other parts of the application.
"""

import sqlite3

import pandas as pd

from data_processing import setup_logging
from data_processing.chemical_utils import KEY_PARAMETERS
from database.database import close_connection, get_connection

logger = setup_logging("data_queries", category="processing")

# Chemical Data Queries

def get_chemical_date_range():
    """
    Gets the date range (min and max years) for all chemical data in the database.
    
    Returns:
        A tuple of (min_year, max_year), or a default of (2005, 2025) if no data is found.
    """
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
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
        # Falling back to a default date range ensures the application can still function.
        logger.info("Falling back to default date range")
        return 2005, 2025
        
    finally:
        if conn:
            close_connection(conn)

def get_chemical_data_from_db(site_name=None):
    """
    Retrieves chemical data from the database, including calculated status columns.
    
    Args:
        site_name: An optional site name to filter the data for.
        
    Returns:
        A DataFrame containing the chemical data, pivoted for analysis.
    """
    conn = get_connection()
    try:
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
        
        params = []
        if site_name:
            query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            logger.info(f"No chemical data found in database")
            return pd.DataFrame()
            
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Pivot the data to have parameters as columns for values and statuses separately.
        value_pivot = df.pivot_table(
            index=['Site_Name', 'Date', 'Year', 'Month'],
            columns='parameter_code',
            values='value',
            aggfunc='first'
        ).reset_index()
        
        status_pivot = df.pivot_table(
            index=['Site_Name', 'Date', 'Year', 'Month'],
            columns='parameter_code',
            values='status',
            aggfunc='first'
        ).reset_index()
        
        for param in KEY_PARAMETERS:
            if param in status_pivot.columns:
                value_pivot[f'{param}_status'] = status_pivot[param]
        
        for param in KEY_PARAMETERS:
            if param not in value_pivot.columns:
                logger.warning(f"Key parameter {param} not found in database data")
                
        return value_pivot
        
    except Exception as e:
        logger.error(f"Error retrieving chemical data from database: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            close_connection(conn)

# Fish Data Queries

def get_fish_date_range():
    """
    Gets the date range (min and max years) for all fish data in the database.
    
    Returns:
        A tuple of (min_year, max_year), or a default of (2005, 2025) if no data is found.
    """
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
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
        # Falling back to a default date range ensures the application can still function.
        logger.info("Falling back to default date range")
        return 2005, 2025
        
    finally:
        if conn:
            close_connection(conn)

def get_fish_dataframe(site_name=None):
    """
    Retrieves fish data with summary scores from the database.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A DataFrame with the fish data.
    """
    conn = None
    try:
        conn = get_connection()
        
        fish_query = '''
        SELECT 
            e.event_id,
            s.site_name,
            e.collection_date,
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
        
        params = []
        if site_name:
            fish_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Order by collection date to ensure proper chronological display.
        fish_query += " ORDER BY e.collection_date"
        
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
    Retrieves detailed fish metrics and summary data for table displays.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A tuple containing a metrics DataFrame and a summary DataFrame.
    """
    conn = None
    try:
        conn = get_connection()
        
        metrics_query = '''
        SELECT 
            s.site_name,
            e.event_id,
            e.collection_date,
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
        
        summary_query = '''
        SELECT 
            s.site_name,
            e.event_id,
            e.collection_date,
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
        
        params = []
        if site_name:
            where_clause = ' WHERE s.site_name = ?'
            metrics_query += where_clause
            summary_query += where_clause
            params.append(site_name)
        
        metrics_query += ' ORDER BY s.site_name, e.collection_date, m.metric_name'
        summary_query += ' ORDER BY s.site_name, e.collection_date'
        
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

# Macroinvertebrate Data Queries

def get_macro_date_range():
    """
    Gets the date range (min and max years) for all macroinvertebrate data in the database.
    
    Returns:
        A tuple of (min_year, max_year), or a default of (2005, 2025) if no data is found.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MIN(year), MAX(year) FROM macro_collection_events")
        result = cursor.fetchone()
        
        if result and result[0] is not None and result[1] is not None:
            min_year, max_year = result
            logger.info(f"Macroinvertebrate data date range: {min_year} to {max_year}")
            return min_year, max_year
        else:
            logger.warning("No macroinvertebrate data found in database, using default range")
            return 2005, 2025
            
    except Exception as e:
        logger.error(f"Error getting macroinvertebrate date range: {e}")
        # Falling back to a default date range ensures the application can still function.
        logger.info("Falling back to default date range")
        return 2005, 2025
        
    finally:
        if conn:
            close_connection(conn)

def get_macroinvertebrate_dataframe(site_name=None):
    """
    Retrieves macroinvertebrate data with summary scores from the database.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A DataFrame with the macroinvertebrate data.
    """
    conn = None
    try:
        conn = get_connection()
        
        macro_query = '''
        SELECT 
            m.event_id,
            s.site_name,
            e.collection_date,
            e.year,
            e.season,
            e.habitat,
            m.total_score,
            m.comparison_to_reference,
            m.biological_condition
        FROM 
            macro_summary_scores m
        JOIN 
            macro_collection_events e ON m.event_id = e.event_id
        JOIN 
            sites s ON e.site_id = s.site_id
        '''
        
        params = []
        if site_name:
            macro_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        macro_query += " ORDER BY s.site_name, e.collection_date"
        
        macro_df = pd.read_sql_query(macro_query, conn, params=params)
        
        if 'collection_date' in macro_df.columns:
            macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
        
        if macro_df.empty:
            if site_name:
                logger.warning(f"No macroinvertebrate data found for site: {site_name}")
            else:
                logger.warning("No macroinvertebrate data found in the database")
        else: 
            logger.info(f"Retrieved {len(macro_df)} macroinvertebrate collection records")

            missing_values = macro_df.isnull().sum().sum()
            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values in the macroinvertebrate data")
   
        return macro_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_macroinvertebrate_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving macroinvertebrate data: {e}")
        return pd.DataFrame({'error': ['Error retrieving macroinvertebrate data']})
    finally:
        if conn:
            close_connection(conn)

def get_macro_metrics_data_for_table(site_name=None):
    """
    Retrieves detailed macroinvertebrate metrics and summary data for table displays.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A tuple containing a metrics DataFrame and a summary DataFrame.
    """
    conn = None
    try:
        conn = get_connection()
        
        metrics_query = '''
        SELECT 
            s.site_name,
            e.event_id,
            e.collection_date,
            e.year,
            e.season,
            e.habitat,
            m.metric_name,
            m.raw_value,
            m.metric_score
        FROM 
            macro_metrics m
        JOIN 
            macro_collection_events e ON m.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        summary_query = '''
        SELECT 
            st.site_name,
            e.event_id,
            e.collection_date,
            e.year,
            e.season,
            e.habitat,
            s.total_score,
            s.comparison_to_reference,
            s.biological_condition
        FROM 
            macro_summary_scores s
        JOIN 
            macro_collection_events e ON s.event_id = e.event_id
        JOIN
            sites st ON e.site_id = st.site_id
        '''
        
        params = []
        if site_name:
            where_clause = ' WHERE s.site_name = ?'
            metrics_query += where_clause
            # Use 'st' alias in summary query to avoid a name conflict with the metrics query.
            summary_query += ' WHERE st.site_name = ?'
            params.append(site_name)
        
        metrics_query += ' ORDER BY s.site_name, e.collection_date, e.season, m.metric_name'
        summary_query += ' ORDER BY st.site_name, e.collection_date, e.season'
        
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        if 'collection_date' in metrics_df.columns:
            metrics_df['collection_date'] = pd.to_datetime(metrics_df['collection_date'])
        if 'collection_date' in summary_df.columns:
            summary_df['collection_date'] = pd.to_datetime(summary_df['collection_date'])
        
        logger.debug(f"Retrieved macro metrics data: {len(metrics_df)} metric records and {summary_df.shape[0]} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving macroinvertebrate metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)

# Habitat Data Queries

def get_habitat_date_range():
    """
    Gets the date range (min and max years) for all habitat data in the database.
    
    Returns:
        A tuple of (min_year, max_year), or a default of (2005, 2025) if no data is found.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MIN(year), MAX(year) FROM habitat_assessments")
        result = cursor.fetchone()
        
        if result and result[0] is not None and result[1] is not None:
            min_year, max_year = result
            logger.info(f"Habitat data date range: {min_year} to {max_year}")
            return min_year, max_year
        else:
            logger.warning("No habitat data found in database, using default range")
            return 2005, 2025
            
    except Exception as e:
        logger.error(f"Error getting habitat date range: {e}")
        # Falling back to a default date range ensures the application can still function.
        logger.info("Falling back to default date range")
        return 2005, 2025
        
    finally:
        if conn:
            close_connection(conn)

def get_habitat_dataframe(site_name=None):
    """
    Retrieves habitat data with summary scores from the database.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A DataFrame with the habitat data.
    """
    conn = None
    try:
        conn = get_connection()
        
        habitat_query = '''
        SELECT 
            a.assessment_id,
            s.site_name,
            a.assessment_date,
            a.year,
            h.total_score,
            h.habitat_grade
        FROM 
            habitat_summary_scores h
        JOIN 
            habitat_assessments a ON h.assessment_id = a.assessment_id
        JOIN 
            sites s ON a.site_id = s.site_id
        '''
        
        params = []
        if site_name:
            habitat_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        habitat_query += " ORDER BY a.year"
        
        habitat_df = pd.read_sql_query(habitat_query, conn, params=params)
        
        if habitat_df.empty:
            if site_name:
                logger.warning(f"No habitat data found for site: {site_name}")
            else:
                logger.warning("No habitat data found in the database")
        else: 
            logger.info(f"Retrieved {len(habitat_df)} habitat assessment records")

            missing_values = habitat_df.isnull().sum().sum()
            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values in the habitat data")
    
        return habitat_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_habitat_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving habitat data: {e}")
        return pd.DataFrame({'error': ['Error retrieving habitat data']})
    finally:
        if conn:
            close_connection(conn)

def get_habitat_metrics_data_for_table(site_name=None):
    """
    Retrieves detailed habitat metrics and summary data for table displays.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A tuple containing a metrics DataFrame and a summary DataFrame.
    """
    conn = None
    try:
        conn = get_connection()
        
        metrics_query = '''
        SELECT 
            s.site_name,
            a.year,
            a.assessment_id,
            m.metric_name,
            m.score
        FROM 
            habitat_metrics m
        JOIN 
            habitat_assessments a ON m.assessment_id = a.assessment_id
        JOIN
            sites s ON a.site_id = s.site_id
        '''
        
        summary_query = '''
        SELECT 
            s.site_name,
            a.year,
            a.assessment_id,
            h.total_score,
            h.habitat_grade
        FROM 
            habitat_summary_scores h
        JOIN 
            habitat_assessments a ON h.assessment_id = a.assessment_id
        JOIN
            sites s ON a.site_id = s.site_id
        '''
        
        params = []
        if site_name:
            where_clause = " WHERE s.site_name = ?"
            metrics_query += where_clause
            summary_query += where_clause
            params.append(site_name)
            
        metrics_query += ' ORDER BY s.site_name, a.year, m.metric_name'
        summary_query += ' ORDER BY s.site_name, a.year'
        
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        logger.debug(f"Retrieved habitat metrics data: {len(metrics_df)} metric records and {len(summary_df)} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving habitat metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)