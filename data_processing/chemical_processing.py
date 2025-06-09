import os
import sys
import pandas as pd
import numpy as np
from utils import setup_logging, round_parameter_value

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import utilities from data_loader and database
from data_processing.data_loader import (
    load_csv_data, clean_column_names, 
    save_processed_data, get_unique_sites,
)
from database.database import get_connection, close_connection

# Import data query utilities
from data_processing.data_queries import (
    get_sites_with_chemical_data, get_date_range_for_site, 
    get_chemical_date_range, get_site_id
)

# Import shared chemical utilities
from data_processing.chemical_utils import (
    validate_chemical_data, determine_status, apply_bdl_conversions,
    calculate_soluble_nitrogen, remove_empty_chemical_rows,
    KEY_PARAMETERS, PARAMETER_MAP,
    insert_default_parameters, insert_default_reference_values
)
from utils import setup_logging

# Configure Logging
logger = setup_logging("chemical_processing", category="processing")


def get_reference_values():
    """
    Get reference values from the database.
    
    Returns:
        dict: Reference values organized by parameter
        
    Raises:
        Exception: If reference values cannot be retrieved from database
    """
    conn = get_connection()
    try:
        reference_values = {}
        
        query = """
        SELECT p.parameter_code, r.threshold_type, r.value
        FROM chemical_reference_values r
        JOIN chemical_parameters p ON r.parameter_id = p.parameter_id
        """
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            raise Exception("No chemical reference values found in database. Database initialization may have failed.")
        
        for param in df['parameter_code'].unique():
            reference_values[param] = {}
            param_data = df[df['parameter_code'] == param]
            
            # Mapping of database threshold_type to dashboard reference key
            threshold_mapping = {
                'normal_min': 'normal min',
                'normal_max': 'normal max',
                'caution_min': 'caution min',
                'caution_max': 'caution max',
                'normal': 'normal',
                'caution': 'caution',
                'poor': 'poor'
            }

            # Process all thresholds with a single loop
            for _, row in param_data.iterrows():
                if row['threshold_type'] in threshold_mapping:
                    reference_key = threshold_mapping[row['threshold_type']]
                    reference_values[param][reference_key] = row['value']
        
        # Validate that we have reference values for key parameters
        if not reference_values:
            raise Exception("Failed to parse chemical reference values from database")
            
        logger.debug(f"Successfully retrieved reference values for {len(reference_values)} parameters")
        return reference_values
        
    except Exception as e:
        logger.error(f"Error getting reference values: {e}")
        raise Exception(f"Critical error: Cannot retrieve chemical reference values from database: {e}")
    finally:
        close_connection(conn)

def load_chemical_data_to_db(site_name=None):
    """
    Process chemical data from CSV and load it into the database.
    Uses batch processing and intelligent gap-filling for performance.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert default parameters once at the start - fail hard if this doesn't work
        insert_default_parameters(cursor)
        insert_default_reference_values(cursor)
        conn.commit()
        logger.info("Default chemical parameters and reference values ensured in database")
        # Process the data from CSV
        df_clean, _, _ = process_chemical_data_from_csv(site_name)
        
        if df_clean.empty:
            logger.warning("No chemical data to load into database")
            return False
        
        # BATCH LOADING: Get all existing data upfront
        logger.info("Loading existing data for comparison...")
        
        # Get all existing collection events as a set of (site_name, date_str)
        existing_events_query = """
        SELECT s.site_name, c.collection_date, c.event_id
        FROM chemical_collection_events c
        JOIN sites s ON c.site_id = s.site_id
        """
        existing_events_df = pd.read_sql_query(existing_events_query, conn)
        existing_events = set(zip(existing_events_df['site_name'], existing_events_df['collection_date']))
        event_lookup = dict(zip(zip(existing_events_df['site_name'], existing_events_df['collection_date']), 
                                existing_events_df['event_id']))
        
        # Get all existing measurements as a set of (event_id, parameter_id)
        existing_measurements_query = """
        SELECT event_id, parameter_id
        FROM chemical_measurements
        """
        existing_measurements_df = pd.read_sql_query(existing_measurements_query, conn)
        existing_measurements = set(zip(existing_measurements_df['event_id'], existing_measurements_df['parameter_id']))
        
        # Get all existing sites
        existing_sites_df = pd.read_sql_query("SELECT site_name, site_id FROM sites", conn)
        site_lookup = dict(zip(existing_sites_df['site_name'], existing_sites_df['site_id']))
        
        logger.info(f"Found {len(existing_events)} existing events, {len(existing_measurements)} existing measurements")
        
        # Track what we're adding
        sites_processed = 0
        samples_added = 0
        measurements_added = 0
        sites_created = 0
        
        # INTELLIGENT GAP FILLING: Only process what's missing
        reference_values = get_reference_values()
        
        # Group by site name
        for site, site_df in df_clean.groupby('Site_Name'):
            sites_processed += 1
            
            # Get or create site_id (batch lookup first)
            if site in site_lookup:
                site_id = site_lookup[site]
            else:
                cursor.execute("INSERT INTO sites (site_name) VALUES (?)", (site,))
                site_id = cursor.lastrowid
                site_lookup[site] = site_id  # Update our lookup
                sites_created += 1
            
            # Process collection events for this site
            for date, date_df in site_df.groupby('Date'):
                date_str = pd.to_datetime(date).strftime('%Y-%m-%d')
                year = pd.to_datetime(date).year
                month = pd.to_datetime(date).month
                
                # Check if this event already exists (batch lookup)
                if (site, date_str) in existing_events:
                    event_id = event_lookup[(site, date_str)]
                else:
                    # Insert new collection event
                    cursor.execute("""
                    INSERT INTO chemical_collection_events 
                    (site_id, collection_date, year, month)
                    VALUES (?, ?, ?, ?)
                    """, (site_id, date_str, year, month))
                    
                    event_id = cursor.lastrowid
                    existing_events.add((site, date_str))  # Update our lookup
                    event_lookup[(site, date_str)] = event_id
                    samples_added += 1
                
                # Process measurements for this event
                for parameter in KEY_PARAMETERS:
                    if parameter in date_df.columns:
                        value = date_df[parameter].iloc[0]
                        
                        if pd.isna(value):
                            continue  # Skip null values
                            
                        if parameter in PARAMETER_MAP:
                            parameter_id = PARAMETER_MAP[parameter]
                            
                            # Check if this measurement already exists 
                            if (event_id, parameter_id) not in existing_measurements:
                                # Calculate status using shared utility
                                status = determine_status(parameter, value, reference_values)
                                
                                # Apply appropriate rounding before insertion
                                rounded_value = round_parameter_value(parameter, value, 'chemical')

                                # Skip if rounding failed
                                if rounded_value is None:
                                    continue
                                    
                                # Recalculate status with rounded value
                                status = determine_status(parameter, rounded_value, reference_values)

                                cursor.execute("""
                                INSERT INTO chemical_measurements
                                (event_id, parameter_id, value, status)
                                VALUES (?, ?, ?, ?)
                                """, (event_id, parameter_id, rounded_value, status))

                                existing_measurements.add((event_id, parameter_id))  
                                measurements_added += 1
        
        conn.commit()
        logger.info(f"Successfully processed chemical data for {sites_processed} sites:")
        logger.info(f"  - Created {sites_created} new sites")
        logger.info(f"  - Added {samples_added} new collection events")
        logger.info(f"  - Added {measurements_added} new measurements")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading chemical data to database: {e}")
        return False
    finally:
        close_connection(conn)

def process_chemical_data_from_csv(site_name=None):
    """
    Process chemical data from CLEANED CSV file without database integration.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        Tuple of (cleaned_dataframe, key_parameters, reference_values)
    """
    try:
        # NEW: Load from cleaned CSV instead of using data_loader
        cleaned_chemical_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'processed', 'cleaned_chemical_data.csv'
        )
        
        if not os.path.exists(cleaned_chemical_path):
            logger.error("cleaned_chemical_data.csv not found. Run CSV cleaning first.")
            return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
        
        # Define columns to load (same as before)
        cols_to_load = [
            'SiteName', 'Date', 'DO.Saturation', 'pH.Final.1', 
            'Nitrate.Final.1', 'Nitrite.Final.1', 'Ammonia.Final.1',
            'OP.Final.1', 'Chloride.Final.1'
        ]
        
        # Load cleaned chemical data
        chemical_data = pd.read_csv(
            cleaned_chemical_path,
            usecols=cols_to_load,
            parse_dates=['Date']
        )
        
        if chemical_data.empty:
            logger.error("Failed to load cleaned chemical data")
            return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
            
        logger.info(f"Successfully loaded data with {len(chemical_data)} rows from cleaned CSV")
        
        # Filter by site name if provided
        if site_name:
            chemical_data = chemical_data[chemical_data['SiteName'] == site_name]
            logger.info(f"Filtered to {len(chemical_data)} rows for site: {site_name}")
            
            if chemical_data.empty:
                logger.warning(f"No data found for site: {site_name}")
                return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
    
    except Exception as e:
        logger.error(f"Error loading cleaned chemical data: {e}")
        return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()

    # Clean column names using data_loader's function (same as before)
    chemical_data = clean_column_names(chemical_data)

    logger.info(f"Cleaned column names: {', '.join(chemical_data.columns)}")
    
    # Map of expected columns to actual columns in the data (same as before)
    column_mapping = {
        'sitename': 'Site_Name',
        'dosaturation': 'do_percent',  
        'phfinal1': 'pH',              
        'nitratefinal1': 'Nitrate',    
        'nitritefinal1': 'Nitrite',    
        'ammoniafinal1': 'Ammonia',   
        'opfinal1': 'Phosphorus',     
        'chloridefinal1': 'Chloride',  
    }
    
    # Rename columns for clarity (same as before)
    renamed_columns = {}
    for old_col, new_col in column_mapping.items():
        if old_col in chemical_data.columns:
            renamed_columns[old_col] = new_col
    
    # Create a clean version for analysis and plotting
    df_clean = chemical_data.rename(columns=renamed_columns)
    logger.debug(f"Columns renamed: {', '.join(renamed_columns.keys())} -> {', '.join(renamed_columns.values())}")
    
    # Define chemical parameter columns for processing (same as before)
    chemical_columns = [col for col in [
        'do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride'
    ] if col in df_clean.columns]
    
    # Remove rows where all chemical parameters are null (same as before)
    df_clean = remove_empty_chemical_rows(df_clean, chemical_columns)
    
    # Ensure Date column exists and is datetime (same as before)
    if 'date' in df_clean.columns:
        df_clean.rename(columns={'date': 'Date'}, inplace=True)
    
    if 'Date' not in df_clean.columns:
        logger.warning("No 'Date' column found in the data")
        df_clean['Date'] = pd.to_datetime('today')  # Fallback value
    elif not pd.api.types.is_datetime64_dtype(df_clean['Date']):
        # Convert to datetime if it's not already
        df_clean['Date'] = pd.to_datetime(df_clean['Date'])

    # Extract additional time components (same as before)
    df_clean['Year'] = df_clean['Date'].dt.year
    df_clean['Month'] = df_clean['Date'].dt.month
    logger.debug("Date columns processed and time components extracted")

    # Apply BDL conversions using shared utility (same as before)
    df_clean = apply_bdl_conversions(df_clean)
 
    # Convert all numeric columns (same as before)
    numeric_conversion_count = 0 
    for col in chemical_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            numeric_conversion_count += 1
    
    logger.debug(f"Converted {numeric_conversion_count} columns to numeric type")
    
    # Validate data quality using shared utility (removes invalid values) (same as before)
    df_clean = validate_chemical_data(df_clean, remove_invalid=True)
        
    # Calculate total nitrogen using shared utility (same as before)
    df_clean = calculate_soluble_nitrogen(df_clean)

    # Check for missing values in final dataframe (same as before)
    missing_values = df_clean.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Final dataframe contains {missing_values} missing values")

    # Save processed data (same as before)
    save_processed_data(df_clean, 'chemical_data')

    logger.info(f"Data processing complete. Output dataframe has {len(df_clean)} rows and {len(df_clean.columns)} columns")
    return df_clean, KEY_PARAMETERS, get_reference_values()

def process_chemical_data(site_name=None, use_db=True):
    """
    Process chemical data and return cleaned dataframe.
    This function attempts to use the database first, then falls back to CSV if needed.
    
    Args:
        site_name: Optional site name to filter data for
        use_db: Whether to try using the database first (default: True)
        
    Returns:
        Tuple of (cleaned_dataframe, key_parameters, reference_values)
    """
    # Check if we should use the database
    if use_db:
        # Try to get data from database
        df = get_chemical_data_from_db(site_name)
        
        if not df.empty:
            logger.info(f"Retrieved {len(df)} records from database")
            return df, KEY_PARAMETERS, get_reference_values()
        
        # If no data in database, load from CSV into database first
        logger.info("No data found in database, loading from CSV")
        if load_chemical_data_to_db(site_name):
            # Try again to get from database
            df = get_chemical_data_from_db(site_name)
            
            if not df.empty:
                logger.info(f"Successfully loaded and retrieved {len(df)} records")
                return df, KEY_PARAMETERS, get_reference_values()
    
    # Fall back to processing from CSV directly
    logger.info("Falling back to processing directly from CSV")
    return process_chemical_data_from_csv(site_name)

def get_chemical_data_from_db(site_name=None):
    """
    Retrieve chemical data from the database.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        DataFrame with chemical data
    """
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

if __name__ == "__main__":
    logger.info("Testing chemical data processing")
    
    # Get list of sites with chemical data
    sites = get_sites_with_chemical_data()
    if sites:
        logger.info(f"Found {len(sites)} sites with chemical data")
        
        # Process data for the first site as a test
        test_site = sites[0]
        logger.info(f"Processing data for test site: {test_site}")
        
        # Try to get from database first
        df_clean, key_parameters, reference_values = process_chemical_data(test_site, use_db=True)
        
        if not df_clean.empty:
            logger.info(f"Successfully processed {len(df_clean)} records for {test_site}")
            
            # Test date range function
            min_date, max_date = get_date_range_for_site(test_site)
            if min_date and max_date:
                logger.info(f"Date range for {test_site}: {min_date} to {max_date}")
        else:
            logger.warning(f"No data found for test site: {test_site}")
    else:
        logger.error("No sites with chemical data found. Check database setup.")