"""
Data query utilities for the Blue Thumb Water Quality Dashboard.
Functions for retrieving data from the database and CSV files for visualization and analysis.
"""

import pandas as pd
import os
from utils import setup_logging

# Set up logging
logger = setup_logging("data_queries", category="processing")

def get_site_id(cursor, site_name):
    """Get site ID for a given site name (assumes site already exists)."""
    cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        raise ValueError(f"Site '{site_name}' not found in database. Run site processing first.")

def get_sites_with_chemical_data():
    """Return a list of sites that have chemical data."""
    from database.database import get_connection, close_connection
    
    conn = get_connection()
    try:
        # Database query stays the same
        query = """
        SELECT DISTINCT s.site_name 
        FROM sites s
        JOIN chemical_collection_events c ON s.site_id = c.site_id
        ORDER BY s.site_name
        """
        cursor = conn.cursor()
        cursor.execute(query)
        sites = [row[0] for row in cursor.fetchall()]
        
        # If no sites found in database, fall back to CLEANED CSV data
        if not sites:
            cleaned_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'data', 'processed', 'cleaned_chemical_data.csv'
            )
            df = pd.read_csv(cleaned_path)
            sites = df['SiteName'].dropna().unique().tolist()
            
        return sites
    except Exception as e:
        logger.error(f"Error getting sites with chemical data: {e}")
        # Fallback to cleaned data
        cleaned_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'processed', 'cleaned_chemical_data.csv'
        )
        df = pd.read_csv(cleaned_path)
        return df['SiteName'].dropna().unique().tolist()
    finally:
        close_connection(conn)

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

def get_date_range_for_site(site_name):
    """Get the min and max dates for chemical data at a specific site."""
    from database.database import get_connection, close_connection
    
    conn = get_connection()
    try:
        query = """
        SELECT MIN(collection_date), MAX(collection_date)
        FROM chemical_collection_events c
        JOIN sites s ON c.site_id = s.site_id
        WHERE s.site_name = ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (site_name,))
        min_date, max_date = cursor.fetchone()
        
        if min_date and max_date:
            min_date = pd.to_datetime(min_date)
            max_date = pd.to_datetime(max_date)
            return min_date, max_date
        else:
            # Fall back to CSV data if no database data
            logger.warning(f"No database data found for site {site_name}, checking CSV files")
            try:
                # Try cleaned_chemical_data.csv first
                cleaned_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    'data', 'processed', 'cleaned_chemical_data.csv'
                )
                if os.path.exists(cleaned_path):
                    df = pd.read_csv(cleaned_path, parse_dates=['Date'])
                    site_data = df[df['SiteName'] == site_name]
                    if not site_data.empty:
                        return site_data['Date'].min(), site_data['Date'].max()
                
                # Try cleaned_updated_chemical_data.csv
                updated_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    'data', 'processed', 'cleaned_updated_chemical_data.csv'
                )
                if os.path.exists(updated_path):
                    df = pd.read_csv(updated_path)
                    # Parse the "Sampling Date" column
                    if 'Sampling Date' in df.columns:
                        df['Date'] = pd.to_datetime(df['Sampling Date'], format='%m/%d/%Y, %I:%M %p').dt.date
                        df['Date'] = pd.to_datetime(df['Date'])
                        site_data = df[df['Site Name'] == site_name]
                        if not site_data.empty:
                            return site_data['Date'].min(), site_data['Date'].max()
                            
                return None, None
            except Exception as csv_e:
                logger.error(f"Error reading CSV files for site {site_name}: {csv_e}")
                return None, None
    except Exception as e:
        logger.error(f"Error getting date range for site {site_name}: {e}")
        return None, None
    finally:
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