"""
Data query utilities for the Blue Thumb Water Quality Dashboard.
Functions for retrieving data from the database and CSV files for visualization and analysis.
"""

import pandas as pd
import os
from data_processing import setup_logging

# Set up logging
logger = setup_logging("data_queries", category="processing")



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