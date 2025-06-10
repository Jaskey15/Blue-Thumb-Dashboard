"""
Chemical data utilities for the Blue Thumb Water Quality Dashboard.
Shared functions for processing and validating chemical data.
"""

import pandas as pd
import numpy as np
from data_processing import setup_logging

# Set up logging
logger = setup_logging("chemical_utils", category="processing")

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

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

# Define constants for BDL values (Below Detection Limit)
# Values provided by Blue Thumb Cordinator
BDL_VALUES = {
    'Nitrate': 0.3,    
    'Nitrite': 0.03,    
    'Ammonia': 0.03,
    'Phosphorus': 0.005,
}

# =============================================================================
# DATA VALIDATION AND CLEANING
# =============================================================================

def convert_bdl_value(value, bdl_replacement):
    """
    Convert zeros to BDL replacement values.
    Keeps NaN values as NaN for visualization gaps.
    
    Args:
        value: The value to check/convert
        bdl_replacement: The replacement value for BDL (below detection limit)
        
    Returns:
        Converted value or NaN
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

def validate_chemical_data(df, remove_invalid=True):
    """
    Validate chemical data and optionally remove invalid values.
    pH must be between 0-14, all other parameters must be > 0.
    
    Args:
        df: DataFrame with chemical data
        remove_invalid: If True, set invalid values to NaN; if False, just log warnings
        
    Returns:
        DataFrame with validated data
    """
    df_clean = df.copy()
    total_issues = 0
    
    # Define chemical parameters (excluding pH which has special handling)
    chemical_params = ['do_percent', 'Nitrate', 'Nitrite', 'Ammonia', 
                      'Phosphorus', 'Chloride', 'soluble_nitrogen']
    
    # Validate pH (must be between 0-14)
    if 'pH' in df_clean.columns:
        ph_invalid_mask = ((df_clean['pH'] < 0) | (df_clean['pH'] > 14)) & df_clean['pH'].notna()
        ph_invalid_count = ph_invalid_mask.sum()
        
        if ph_invalid_count > 0:
            total_issues += ph_invalid_count
            if remove_invalid:
                df_clean.loc[ph_invalid_mask, 'pH'] = np.nan
                logger.info(f"Removed {ph_invalid_count} pH values outside 0-14 range")
            else:
                logger.warning(f"Found {ph_invalid_count} pH values outside 0-14 range")
    
    # Validate other chemical parameters (must be > 0)
    for param in chemical_params:
        if param in df_clean.columns:
            invalid_mask = (df_clean[param] < 0) & df_clean[param].notna()
            invalid_count = invalid_mask.sum()
            
            if invalid_count > 0:
                total_issues += invalid_count
                if remove_invalid:
                    df_clean.loc[invalid_mask, param] = np.nan
                    logger.info(f"Removed {invalid_count} {param} values < 0")
                else:
                    logger.warning(f"Found {invalid_count} {param} values < 0")
    
    # Log overall summary
    if total_issues > 0:
        action = "removed" if remove_invalid else "flagged"
        logger.info(f"Data validation complete: {total_issues} total issues {action}")
    else:
        logger.info("Data validation complete: No quality issues found")
    
    return df_clean

def apply_bdl_conversions(df, bdl_columns=None):
    """
    Apply BDL (Below Detection Limit) conversions to specified columns.
    
    Args:
        df: DataFrame with chemical data
        bdl_columns: List of columns to apply BDL conversion to (default: all BDL_VALUES keys)
        
    Returns:
        DataFrame with BDL conversions applied
    """
    if bdl_columns is None:
        bdl_columns = list(BDL_VALUES.keys())
    
    df_converted = df.copy()
    conversion_count = 0
    
    for column in bdl_columns:
        if column in df_converted.columns:
            bdl_value = BDL_VALUES.get(column, 0)
            
            # Apply conversion
            df_converted[column] = df_converted[column].apply(
                lambda x: convert_bdl_value(x, bdl_value)
            )
            conversion_count += 1
            logger.debug(f"Applied BDL conversion to {column} (BDL value: {bdl_value})")
    
    if conversion_count > 0:
        logger.info(f"Applied BDL conversions to {conversion_count} columns")
    
    return df_converted

def remove_empty_chemical_rows(df, chemical_columns=None):
    """
    Remove rows where all chemical parameters are null.
    
    Args:
        df: DataFrame with chemical data
        chemical_columns: List of chemical columns to check (default: all chemical columns)
        
    Returns:
        DataFrame with empty rows removed
    """
    if chemical_columns is None:
        # Default chemical columns
        chemical_columns = ['do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 
                           'Phosphorus', 'Chloride', 'soluble_nitrogen']
    
    # Filter for columns that actually exist in the DataFrame
    existing_columns = [col for col in chemical_columns if col in df.columns]
    
    if not existing_columns:
        logger.warning("No chemical columns found for empty row removal")
        return df
    
    # Count non-null values in each row
    non_null_counts = df[existing_columns].notnull().sum(axis=1)
    
    # Keep rows that have at least one chemical parameter
    df_filtered = df[non_null_counts > 0].copy()
    
    # Log how many rows were removed
    removed_count = len(df) - len(df_filtered)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} rows with no chemical data")
    
    return df_filtered

# =============================================================================
# DATA PROCESSING AND ANALYSIS
# =============================================================================

def calculate_soluble_nitrogen(df):
    """
    Calculate soluble nitrogen from Nitrate, Nitrite, and Ammonia values.
    Uses BDL replacement values for calculation purposes.
    
    Args:
        df: DataFrame with individual nitrogen component columns
        
    Returns:
        DataFrame with soluble_nitrogen column added
    """
    try:
        # Check if we have the required columns
        required_columns = ['Nitrate', 'Nitrite', 'Ammonia']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            logger.warning(f"Cannot calculate soluble_nitrogen: Missing columns: {', '.join(missing)}")
            return df
        
        df_calc = df.copy()
        
        # For calculation purposes, treat NaN and zeros as BDL values
        def get_calc_value(series, bdl_value):
            return series.fillna(bdl_value).replace(0, bdl_value)
        
        nitrate_calc = get_calc_value(df_calc['Nitrate'], BDL_VALUES['Nitrate'])
        nitrite_calc = get_calc_value(df_calc['Nitrite'], BDL_VALUES['Nitrite'])
        ammonia_calc = get_calc_value(df_calc['Ammonia'], BDL_VALUES['Ammonia'])
        
        # Calculate total soluble nitrogen
        df_calc['soluble_nitrogen'] = nitrate_calc + nitrite_calc + ammonia_calc
        
        # Apply proper rounding to ensure consistent decimal places (2 decimal places)
        df_calc['soluble_nitrogen'] = df_calc['soluble_nitrogen'].apply(
            lambda x: float(f"{x:.2f}") if pd.notna(x) else x
        )
        
        logger.info("Successfully calculated soluble_nitrogen from component values")
        return df_calc
        
    except Exception as e:
        logger.error(f"Error calculating soluble_nitrogen: {e}")
        return df

def determine_status(parameter, value, reference_values):
    """
    Determine the status of a parameter value based on reference thresholds.
    
    Args:
        parameter: Parameter name (e.g., 'do_percent', 'pH')
        value: Parameter value to evaluate
        reference_values: Dictionary of reference values for parameters
        
    Returns:
        String status ('Normal', 'Caution', 'Poor', etc.)
    """
    if pd.isna(value):
        return "Unknown"
        
    if parameter not in reference_values:
        return "Normal"  # Default if no reference values
        
    ref = reference_values[parameter]
    
    if parameter == 'do_percent':
        if 'normal min' in ref and 'normal max' in ref:
            if 'caution min' in ref and 'caution max' in ref:
                if value < ref['caution min'] or value > ref['caution max']:
                    return "Poor"
                elif value < ref['normal min'] or value > ref['normal max']:
                    return "Caution"
                else:
                    return "Normal"
                    
    elif parameter == 'pH':
        if 'normal min' in ref and 'normal max' in ref:
            if value < ref['normal min']:
                return "Below Normal"
            elif value > ref['normal max']:
                return "Above Normal"
            else:
                return "Normal"
                
    elif parameter in ['soluble_nitrogen', 'Phosphorus', 'Chloride']:
        if 'caution' in ref and 'normal' in ref:
            if value > ref['caution']:
                return "Poor"
            elif value > ref['normal']:
                return "Caution"
            else:
                return "Normal"
                
    return "Normal"  # Default if no specific condition met

def get_reference_values():
    """
    Get reference values from the database.
    Moved from chemical_processing.py for shared use.
    
    Returns:
        dict: Reference values organized by parameter
        
    Raises:
        Exception: If reference values cannot be retrieved from database
    """
    from database.database import get_connection, close_connection
    
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

# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_existing_data(conn):
    """
    Get all existing data for batch processing and duplicate detection.
    
    Returns:
        tuple: (existing_events, event_lookup, existing_measurements, site_lookup)
    """
    # Get all existing collection events
    existing_events_query = """
    SELECT s.site_name, c.collection_date, c.event_id
    FROM chemical_collection_events c
    JOIN sites s ON c.site_id = s.site_id
    """
    existing_events_df = pd.read_sql_query(existing_events_query, conn)
    existing_events = set(zip(existing_events_df['site_name'], existing_events_df['collection_date']))
    event_lookup = dict(zip(
        zip(existing_events_df['site_name'], existing_events_df['collection_date']), 
        existing_events_df['event_id']
    ))
    
    # Get all existing measurements
    existing_measurements_query = """
    SELECT event_id, parameter_id
    FROM chemical_measurements
    """
    existing_measurements_df = pd.read_sql_query(existing_measurements_query, conn)
    existing_measurements = set(zip(existing_measurements_df['event_id'], existing_measurements_df['parameter_id']))
    
    # Get all existing sites (NO CREATION - only lookup)
    existing_sites_df = pd.read_sql_query("SELECT site_name, site_id FROM sites", conn)
    site_lookup = dict(zip(existing_sites_df['site_name'], existing_sites_df['site_id']))
    
    return existing_events, event_lookup, existing_measurements, site_lookup

def insert_collection_event(cursor, site_id, date_str, year, month, existing_events, event_lookup, site_name):
    """
    Insert collection event if it doesn't exist.
    
    Args:
        cursor: Database cursor
        site_id: Site ID (must already exist)
        date_str: Date string (YYYY-MM-DD)
        year: Year
        month: Month
        existing_events: Set of existing (site_name, date) tuples
        event_lookup: Dictionary for event lookup
        site_name: Site name for lookup
        
    Returns:
        tuple: (event_id, was_created)
    """
    if (site_name, date_str) in existing_events:
        return event_lookup[(site_name, date_str)], False
    else:
        cursor.execute("""
        INSERT INTO chemical_collection_events 
        (site_id, collection_date, year, month)
        VALUES (?, ?, ?, ?)
        """, (site_id, date_str, year, month))
        
        event_id = cursor.lastrowid
        existing_events.add((site_name, date_str))
        event_lookup[(site_name, date_str)] = event_id
        return event_id, True

def insert_chemical_measurement(cursor, event_id, parameter_id, value, status, existing_measurements):
    """
    Insert chemical measurement if it doesn't exist.
    
    Args:
        cursor: Database cursor
        event_id: Collection event ID
        parameter_id: Parameter ID
        value: Measurement value
        status: Measurement status
        existing_measurements: Set of existing (event_id, parameter_id) tuples
        
    Returns:
        bool: True if measurement was inserted, False if it already existed
    """
    if (event_id, parameter_id) not in existing_measurements:
        cursor.execute("""
        INSERT INTO chemical_measurements
        (event_id, parameter_id, value, status)
        VALUES (?, ?, ?, ?)
        """, (event_id, parameter_id, value, status))
        
        existing_measurements.add((event_id, parameter_id))
        return True
    return False

def insert_chemical_data(df, check_duplicates=True, data_source="unknown"):
    """
    Shared function to insert chemical data
 
    Args:
        df: DataFrame with processed chemical data 
        check_duplicates: Whether to check for existing data
        data_source: Description of data source for logging
        
    Returns:
        dict: Statistics about the insertion process
    """
    from database.database import get_connection, close_connection
    from utils import round_parameter_value
    
    if df.empty:
        logger.warning(f"No data to process for {data_source}")
        return {
            'sites_processed': 0,
            'events_added': 0,
            'measurements_added': 0,
            'data_source': data_source
        }
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get reference values for status determination
        reference_values = get_reference_values()
        
        # load existing data
        existing_events, event_lookup, existing_measurements, site_lookup = get_existing_data(conn)
        logger.info(f"Found {len(existing_events)} existing events, {len(existing_measurements)} existing measurements")
        
        # Track statistics
        stats = {
            'sites_processed': 0,
            'sites_created': 0,  # Always 0 - we don't create sites
            'events_added': 0,
            'measurements_added': 0,
            'data_source': data_source
        }
        
        # Process data by site and date
        for (site_name, date), group in df.groupby(['Site_Name', 'Date']):
            stats['sites_processed'] += 1
            
            # Get site_id (sites guaranteed to exist from prior processing)
            site_id = site_lookup[site_name]
            
            # Process this date group (should only be one row per site per date)
            for _, row in group.iterrows():
                date_str = row['Date'].strftime('%Y-%m-%d')
                year = row['Year']
                month = row['Month']
                
                # Insert collection event
                event_id, event_was_created = insert_collection_event(
                    cursor, site_id, date_str, year, month, 
                    existing_events, event_lookup, site_name
                )
                if event_was_created:
                    stats['events_added'] += 1
                
                # Insert measurements for each parameter
                for param_name, param_id in PARAMETER_MAP.items():
                    if param_name in row and pd.notna(row[param_name]):
                        raw_value = row[param_name]
                        
                        # Apply appropriate rounding before insertion
                        rounded_value = round_parameter_value(param_name, raw_value, 'chemical')
                        
                        if rounded_value is None:
                            continue
                            
                        # Determine status using rounded value
                        status = determine_status(param_name, rounded_value, reference_values)
                        
                        # Insert measurement
                        measurement_was_inserted = insert_chemical_measurement(
                            cursor, event_id, param_id, rounded_value, status, existing_measurements
                        )
                        if measurement_was_inserted:
                            stats['measurements_added'] += 1
        
        conn.commit()
        
        # Log results
        logger.info(f"Successfully inserted {data_source} data:")
        logger.info(f"  - Sites processed: {stats['sites_processed']}")
        logger.info(f"  - Collection events added: {stats['events_added']}")
        logger.info(f"  - Measurements added: {stats['measurements_added']}")
        
        return stats
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in batch insertion for {data_source}: {e}")
        raise Exception(f"Failed to insert {data_source} data: {e}")
    finally:
        close_connection(conn)

def check_for_duplicates_against_db(df, prioritize_existing=True):
    """
    Check for duplicates against existing data in the database.
    
    Args:
        df: DataFrame with processed chemical data
        prioritize_existing: If True, remove duplicates from df; if False, return info only
        
    Returns:
        tuple: (df_no_duplicates, duplicate_count, duplicate_info)
    """
    from database.database import get_connection, close_connection
    from data_processing.data_loader import clean_site_name
    
    try:
        conn = get_connection()
        
        # Get all existing (site_name, date) combinations from database
        existing_query = """
        SELECT DISTINCT s.site_name, c.collection_date
        FROM chemical_collection_events c
        JOIN sites s ON c.site_id = s.site_id
        """
        
        existing_df = pd.read_sql_query(existing_query, conn)
        close_connection(conn)
        
        if existing_df.empty:
            logger.info("No existing chemical data found in database - no duplicates to check")
            return df, 0, []
        
        # Convert dates to same format for comparison
        existing_df['collection_date'] = pd.to_datetime(existing_df['collection_date']).dt.date
        df['date_for_comparison'] = df['Date'].dt.date
        
        # Create sets for efficient comparison
        existing_combinations = set(zip(
            existing_df['site_name'].apply(clean_site_name), 
            existing_df['collection_date']
        ))
        
        # Check each row for duplicates
        duplicate_mask = df.apply(
            lambda row: (row['Site_Name'], row['date_for_comparison']) in existing_combinations, 
            axis=1
        )
        
        duplicate_count = duplicate_mask.sum()
        duplicate_info = []
        
        if duplicate_count > 0:
            duplicate_examples = df[duplicate_mask][['Site_Name', 'Date']].head(10)
            duplicate_info = [(row['Site_Name'], row['Date'].strftime('%Y-%m-%d')) 
                            for _, row in duplicate_examples.iterrows()]
            
            logger.info(f"Found {duplicate_count} duplicate records out of {len(df)} total records")
            
            if prioritize_existing:
                df_no_duplicates = df[~duplicate_mask].copy()
                logger.info(f"Removed {duplicate_count} duplicates. {len(df_no_duplicates)} records remaining.")
            else:
                df_no_duplicates = df.copy()
                logger.info("Duplicates found but not removed (prioritize_existing=False)")
        else:
            logger.info("No duplicates found - all records are new")
            df_no_duplicates = df.copy()
        
        # Clean up temporary column
        if 'date_for_comparison' in df_no_duplicates.columns:
            df_no_duplicates = df_no_duplicates.drop(columns=['date_for_comparison'])
        
        return df_no_duplicates, duplicate_count, duplicate_info
        
    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        logger.warning("Duplicate checking failed - returning all data")
        return df, 0, []