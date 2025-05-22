import os
import sys
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import utilities from data_loader and database
from data_processing.data_loader import (
    load_csv_data, clean_column_names, 
    save_processed_data, get_unique_sites,
)
from database.database import get_connection, close_connection

from utils import setup_logging

# Use the shared logging setup
logger = setup_logging("chemical_processing")

# Define constants for BDL values (Below Detection Limit)
# Values obtained from Blue Thumb Coordinator
BDL_VALUES = {
    'Nitrate': 0.3,    
    'Nitrite': 0.03,    
    'Ammonia': 0.03,
    'Phosphorus': 0.005,
}

# Key parameters for analysis and visualization
KEY_PARAMETERS = [    
    'do_percent', 'pH', 'soluble_nitrogen', 
    'Phosphorus', 'Chloride', 
]

# Map of parameter codes to parameter_id in the database
PARAMETER_MAP = {
    'do_percent': 1,
    'pH': 2,
    'soluble_nitrogen': 3,
    'Phosphorus': 4,
    'Chloride': 5
}

def convert_bdl_value(value, bdl_replacement):
    """
    Convert zeros to BDL replacement values.
    Keeps NaN values as NaN for visualization gaps.
    """
    if pd.isna(value):
        return np.nan  # Keep NaN as NaN for visualization
    
    # Try to convert to numeric if it's not already
    try:
        if not isinstance(value, (int, float)):
            value = float(value)
    except:
        return np.nan  
        
    if value == 0:
        return bdl_replacement  # Assume zeros are below detection limit
    
    return value  # Return the original value if not zero

def validate_data_quality(df, chemical_columns):
    """Flag any implausible values (e.g., negative concentrations)."""
    for col in chemical_columns:
        if col in df.columns:
            neg_values = (df[col] < 0).sum()
            if neg_values > 0:
                logger.warning(f"Found {neg_values} negative values in {col}. These may indicate data quality issues.")
    return df

def remove_empty_rows(df, chemical_columns):
    """Remove rows where all chemical parameters are null."""
    # Filter for columns that actually exist in the DataFrame
    existing_columns = [col for col in chemical_columns if col in df.columns]
    
    if not existing_columns:
        logger.warning("None of the specified chemical columns exist in the DataFrame")
        return df  # Return original DataFrame if no chemical columns exist
    
    # Create a subset with just the existing chemical columns
    chem_df = df[existing_columns].copy()
    
    # Count non-null values in each row
    non_null_counts = chem_df.notnull().sum(axis=1)
    
    # Keep rows that have at least one chemical parameter
    df_filtered = df[non_null_counts > 0].copy()
    
    # Log how many rows were removed
    removed_count = len(df) - len(df_filtered)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} rows with no chemical data")
    
    return df_filtered

def get_sites_with_chemical_data():
    """Return a list of sites that have chemical data."""
    conn = get_connection()
    try:
        query = """
        SELECT DISTINCT s.site_name 
        FROM sites s
        JOIN chemical_collection_events c ON s.site_id = c.site_id
        ORDER BY s.site_name
        """
        cursor = conn.cursor()
        cursor.execute(query)
        sites = [row[0] for row in cursor.fetchall()]
        
        # If no sites found in database, fall back to CSV data
        if not sites:
            sites = get_unique_sites('chemical')
            
        return sites
    except Exception as e:
        logger.error(f"Error getting sites with chemical data: {e}")
        return get_unique_sites('chemical')  # Fall back to CSV data
    finally:
        close_connection(conn)

def get_date_range_for_site(site_name):
    """Get the min and max dates for chemical data at a specific site."""
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
            # Fall back to processing data from CSV
            df = process_chemical_data(site_name)
            if not df.empty:
                return df['Date'].min(), df['Date'].max()
            return None, None
    except Exception as e:
        logger.error(f"Error getting date range for site {site_name}: {e}")
        # Fall back to processing from CSV
        df = process_chemical_data(site_name)
        if not df.empty:
            return df['Date'].min(), df['Date'].max()
        return None, None
    finally:
        close_connection(conn)

def get_site_id(cursor, site_name):
    """Get site ID for a given site name (assumes site already exists)."""
    cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        raise ValueError(f"Site '{site_name}' not found in database. Run site processing first.")

def get_reference_values():
    """Get reference values from the database."""
    conn = get_connection()
    try:
        reference_values = {}
        
        query = """
        SELECT p.parameter_code, r.threshold_type, r.value
        FROM chemical_reference_values r
        JOIN chemical_parameters p ON r.parameter_id = p.parameter_id
        """
        
        df = pd.read_sql_query(query, conn)
        
        for param in df['parameter_code'].unique():
            reference_values[param] = {}
            param_data = df[df['parameter_code'] == param]
            
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
                
        # If no reference values in database, use hardcoded defaults
        if not reference_values:
            reference_values = {
                'do_percent': {
                    'normal min': 80, 
                    'normal max': 130, 
                    'caution min': 50,
                    'caution max': 150,
                    'description': 'Normal dissolved oxygen saturation range'
                },
                'pH': {
                    'normal min': 6.5, 
                    'normal max': 9.0, 
                    'description': 'Normal range for Oklahoma streams'
                },
                'soluble_nitrogen': {
                    'normal': 0.8, 
                    'caution': 1.5, 
                    'description': 'Normal nitrogen levels for this area'
                },
                'Phosphorus': {
                    'normal': 0.05, 
                    'caution': 0.1, 
                    'description': 'Phosphorus levels for streams in Oklahoma'
                },
                'Chloride': {
                    'poor': 250,
                    'description': 'Maximum acceptable chloride level'
                }
            }
            
        return reference_values
    except Exception as e:
        logger.error(f"Error getting reference values: {e}")
        # Return default reference values
        return {
            'do_percent': {
                'normal min': 80, 
                'normal max': 130, 
                'caution min': 50,
                'caution max': 150,
                'description': 'Normal dissolved oxygen saturation range'
            },
            'pH': {
                'normal min': 6.5, 
                'normal max': 9.0, 
                'description': 'Normal range for Oklahoma streams'
            },
            'soluble_nitrogen': {
                'normal': 0.8, 
                'caution': 1.5, 
                'description': 'Normal nitrogen levels for this area'
            },
            'Phosphorus': {
                'normal': 0.05, 
                'caution': 0.1, 
                'description': 'Phosphorus levels for streams in Oklahoma'
            },
            'Chloride': {
                'poor': 250,
                'description': 'Maximum acceptable chloride level'
            }
        }
    finally:
        close_connection(conn)

def determine_status(parameter, value, reference_values):
    """Determine the status of a parameter value based on reference thresholds."""
    if pd.isna(value):
        return "Unknown"
        
    if parameter not in reference_values:
        return "Normal"  # Default if no reference values
        
    ref = reference_values[parameter]
    
    if parameter == 'do_percent':
        if 'normal min' in ref and 'normal max' in ref:
            if value < ref['caution min'] or value > ref['caution max']:
                return "Poor"
            elif value < ref['normal min'] or value > ref['normal max']:
                return "Caution"
            else:
                return "Normal"
                
    elif parameter == 'pH':
        if 'normal min' in ref and 'normal max' in ref:
            if value < ref['normal min'] or value > ref['normal max']:
                return "Outside Normal"
            else:
                return "Normal"
                
    elif parameter in ['soluble_nitrogen', 'Phosphorus']:
        if 'caution' in ref and 'normal' in ref:
            if value > ref['caution']:
                return "Poor"
            elif value > ref['normal']:
                return "Caution"
            else:
                return "Normal"
                
    elif parameter == 'Chloride':
        if 'poor' in ref:
            if value > ref['poor']:
                return "Poor"
            else:
                return "Normal"
                
    return "Normal"  # Default if no specific condition met

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
                            
                            # Check if this measurement already exists (batch lookup)
                            if (event_id, parameter_id) not in existing_measurements:
                                # Calculate status
                                status = determine_status(parameter, value, reference_values)
                                
                                # Insert new measurement
                                cursor.execute("""
                                INSERT INTO chemical_measurements
                                (event_id, parameter_id, value, status)
                                VALUES (?, ?, ?, ?)
                                """, (event_id, parameter_id, value, status))
                                
                                existing_measurements.add((event_id, parameter_id))  # Update our lookup
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
    Process chemical data from CSV file without database integration.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        Tuple of (cleaned_dataframe, key_parameters, reference_values)
    """
    try:
        # Define columns to load
        cols_to_load = [
            'SiteName', 'Date', 'DO.Saturation', 'pH.Final.1', 
            'Nitrate.Final.1', 'Nitrite.Final.1', 'Ammonia.Final.1',
            'OP.Final.1', 'Chloride.Final.1'
        ]
        
        # Load chemical data using data_loader's function
        chemical_data = load_csv_data('chemical', usecols=cols_to_load, parse_dates=['Date'])
        
        if chemical_data.empty:
            logger.error("Failed to load chemical data")
            return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
            
        logger.info(f"Successfully loaded data with {len(chemical_data)} rows")
        
        # Filter by site name if provided
        if site_name:
            chemical_data = chemical_data[chemical_data['SiteName'] == site_name]
            logger.info(f"Filtered to {len(chemical_data)} rows for site: {site_name}")
            
            if chemical_data.empty:
                logger.warning(f"No data found for site: {site_name}")
                return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
    
    except Exception as e:
        logger.error(f"Error loading chemical data: {e}")
        return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()

    # Clean column names using data_loader's function
    chemical_data = clean_column_names(chemical_data)

    logger.info(f"Cleaned column names: {', '.join(chemical_data.columns)}")
    
    # Map of expected columns to actual columns in the data
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
    
    # Rename columns for clarity
    renamed_columns = {}
    for old_col, new_col in column_mapping.items():
        if old_col in chemical_data.columns:
            renamed_columns[old_col] = new_col
    
    # Create a clean version for analysis and plotting
    df_clean = chemical_data.rename(columns=renamed_columns)
    logger.debug(f"Columns renamed: {', '.join(renamed_columns.keys())} -> {', '.join(renamed_columns.values())}")
    
    # Define chemical parameter columns for validation and filtering
    chemical_columns = [col for col in [
        'do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride'
    ] if col in df_clean.columns]
    
    # Remove rows where all chemical parameters are null
    df_clean = remove_empty_rows(df_clean, chemical_columns)
    
    # Ensure Date column exists and is datetime
    if 'date' in df_clean.columns:
        df_clean.rename(columns={'date': 'Date'}, inplace=True)
    
    if 'Date' not in df_clean.columns:
        logger.warning("No 'Date' column found in the data")
        df_clean['Date'] = pd.to_datetime('today')  # Fallback value
    elif not pd.api.types.is_datetime64_dtype(df_clean['Date']):
        # Convert to datetime if it's not already
        df_clean['Date'] = pd.to_datetime(df_clean['Date'])

    # Extract additional time components
    df_clean['Year'] = df_clean['Date'].dt.year
    df_clean['Month'] = df_clean['Date'].dt.month
    logger.debug("Date columns processed and time components extracted")

    # Check for missing BDL columns and log warnings
    missing_bdl_columns = [col for col in BDL_VALUES.keys() if col not in df_clean.columns]
    if missing_bdl_columns:
        logger.warning(f"BDL conversion: Could not find these columns: {', '.join(missing_bdl_columns)}")

    # Apply BDL conversions for specific columns
    bdl_conversion_count = 0
    for column, bdl_value in BDL_VALUES.items():
        if column in df_clean.columns:
            df_clean[column] = df_clean[column].apply(
                lambda x: convert_bdl_value(x, bdl_value)
            )
            bdl_conversion_count += 1

    logger.debug(f"Applied BDL conversions to {bdl_conversion_count} columns")
 
    # Convert all numeric columns
    numeric_conversion_count = 0 
    for col in chemical_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            numeric_conversion_count += 1
    
    logger.debug(f"Converted {numeric_conversion_count} columns to numeric type")
    
    # Validate data quality (check for negative values)
    df_clean = validate_data_quality(df_clean, chemical_columns)
        
    # Calculate total nitrogen using converted values
    required_nitrogen_cols = ['Nitrate', 'Nitrite', 'Ammonia']
    if all(col in df_clean.columns for col in required_nitrogen_cols):
        # For calculation purposes, treat both NaN and zeros as BDL values
        nitrate_values = df_clean['Nitrate'].replace({0: BDL_VALUES['Nitrate']}).fillna(BDL_VALUES['Nitrate'])
        nitrite_values = df_clean['Nitrite'].replace({0: BDL_VALUES['Nitrite']}).fillna(BDL_VALUES['Nitrite'])
        ammonia_values = df_clean['Ammonia'].replace({0: BDL_VALUES['Ammonia']}).fillna(BDL_VALUES['Ammonia'])
        
        df_clean['soluble_nitrogen'] = nitrate_values + nitrite_values + ammonia_values
        logger.debug("Calculated soluble_nitrogen from component values")
    else:   
        missing_nitrogen_cols = [col for col in required_nitrogen_cols if col not in df_clean.columns]
        logger.warning(f"Cannot calculate soluble_nitrogen: Missing columns: {', '.join(missing_nitrogen_cols)}")

    # Check for missing values in final dataframe
    missing_values = df_clean.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Final dataframe contains {missing_values} missing values")

    # Save processed data 
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

def verify_parameters():
    """
    Verify that the chemical_parameters table contains expected parameters.
    If not, populate it with default values.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chemical_parameters'")
        if cursor.fetchone() is None:
            logger.error("chemical_parameters table does not exist")
            return False
            
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM chemical_parameters")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"chemical_parameters table has {count} entries")
            return True
            
        # If no values, import the function to insert defaults
        from database.db_schema import insert_default_parameters
        insert_default_parameters(cursor)
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM chemical_parameters")
        new_count = cursor.fetchone()[0]
        
        logger.info(f"Inserted {new_count} parameters")
        return new_count > 0
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error verifying parameters: {e}")
        return False
    finally:
        close_connection(conn)

def verify_reference_values():
    """
    Verify that the chemical_reference_values table contains expected values.
    If not, populate it with default values.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chemical_reference_values'")
        if cursor.fetchone() is None:
            logger.error("chemical_reference_values table does not exist")
            return False
            
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM chemical_reference_values")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"chemical_reference_values table has {count} entries")
            return True
            
        # If no values, import the function to insert defaults
        from database.db_schema import insert_default_reference_values
        insert_default_reference_values(cursor)
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM chemical_reference_values")
        new_count = cursor.fetchone()[0]
        
        logger.info(f"Inserted {new_count} reference values")
        return new_count > 0
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error verifying reference values: {e}")
        return False
    finally:
        close_connection(conn)

def verify_db_structure():
   """
   Verify that the database structure is set up correctly for chemical data.
   
   Returns:
       bool: True if structure is valid, False otherwise
   """
   conn = get_connection()
   cursor = conn.cursor()
   
   try:
       # Check for required tables
       required_tables = [
           'sites',
           'chemical_collection_events',
           'chemical_parameters',
           'chemical_reference_values',
           'chemical_measurements'
       ]
       
       for table in required_tables:
           cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
           if cursor.fetchone() is None:
               logger.error(f"Missing required table: {table}")
               return False
       
       # Verify parameters and reference values
       if not verify_parameters():
           logger.warning("Failed to verify chemical parameters")
           return False
           
       if not verify_reference_values():
           logger.warning("Failed to verify reference values")
           return False
       
       logger.info("Chemical database structure verified successfully")
       return True
       
   except Exception as e:
       logger.error(f"Error verifying database structure: {e}")
       return False
       
   finally:
       close_connection(conn)

def run_initial_db_setup():
   """
   Perform initial database setup for chemical data.
   
   Returns:
       bool: True if setup successful, False otherwise
   """
   if not verify_db_structure():
       logger.error("Database verification failed. Schema may need to be updated.")
       return False
       
   # Load data for all sites
   success = load_chemical_data_to_db()
   
   if success:
       logger.info("Initial database setup completed successfully")
   else:
       logger.error("Failed to load chemical data into database")
       
   return success

if __name__ == "__main__":
   try:
       logger.info("Testing chemical data processing")
       
       # Verify database structure
       if verify_db_structure():
           logger.info("Database structure is valid")
           
           # Get list of sites with chemical data
           sites = get_sites_with_chemical_data()
           logger.info(f"Found {len(sites)} sites with chemical data")
           
           if sites:
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
           logger.error("Database verification failed, running initial setup")
           run_initial_db_setup()
       
   except Exception as e:
       logger.error(f"Error in chemical data processing test: {e}")