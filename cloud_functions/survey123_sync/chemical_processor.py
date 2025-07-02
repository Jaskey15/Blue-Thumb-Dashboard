"""
Chemical Processing Module for Cloud Function

This module adapts the existing updated_chemical_processing.py logic
for use in the Survey123 sync Cloud Function. It includes all the
nutrient processing, BDL conversions, and database insertion logic.
"""

import logging
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Nutrient column mappings (from original updated_chemical_processing.py)
NUTRIENT_COLUMN_MAPPINGS = {
    'ammonia': {
        'range_selection': 'Ammonia Nitrogen Range Selection',
        'low_col1': 'Ammonia Nitrogen Low Reading #1',
        'low_col2': 'Ammonia Nitrogen Low Reading #2', 
        'mid_col1': 'Ammonia_nitrogen_midrange1_Final',
        'mid_col2': 'Ammonia_nitrogen_midrange2_Final'
    },
    'orthophosphate': {
        'range_selection': 'Orthophosphate Range Selection',
        'low_col1': 'Orthophosphate_Low1_Final',
        'low_col2': 'Orthophosphate_Low2_Final',
        'mid_col1': 'Orthophosphate_Mid1_Final', 
        'mid_col2': 'Orthophosphate_Mid2_Final',
        'high_col1': 'Orthophosphate_High1_Final',
        'high_col2': 'Orthophosphate_High2_Final'
    },
    'chloride': {
        'range_selection': 'Chloride Range Selection',
        'low_col1': 'Chloride_Low1_Final',
        'low_col2': 'Chloride_Low2_Final',
        'high_col1': 'Chloride_High1_Final',
        'high_col2': 'Chloride_High2_Final'
    }
}

# BDL (Below Detection Limit) conversion values
BDL_CONVERSIONS = {
    'pH': None,  # pH doesn't have BDL conversions
    'do_percent': None,  # DO saturation doesn't have BDL conversions
    'Nitrate': 0.01,     # If 0, convert to 0.01
    'Nitrite': 0.004,    # If 0, convert to 0.004
    'Ammonia': 0.03,     # If 0, convert to 0.03
    'Phosphorus': 0.006, # If 0, convert to 0.006
    'Chloride': 0.5      # If 0, convert to 0.5
}

# Parameter reference values for status determination
REFERENCE_VALUES = {
    'pH': {'good_min': 6.5, 'good_max': 8.5},
    'do_percent': {'good_min': 80, 'good_max': float('inf')},
    'Nitrate': {'good_max': 1.0},
    'Nitrite': {'good_max': 0.05},
    'Ammonia': {'good_max': 0.1},
    'Phosphorus': {'good_max': 0.05},
    'Chloride': {'good_max': 25.0},
    'soluble_nitrogen': {'good_max': 1.0}
}

def parse_sampling_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the sampling date column that contains both date and time.
    Extract just the date portion for consistency with existing data.
    """
    try:
        # Parse the datetime string (format appears to be "m/d/yyyy, h:mm AM/PM")
        df['parsed_datetime'] = pd.to_datetime(df['Sampling Date'], format='%m/%d/%Y, %I:%M %p')
        
        # Extract just the date portion
        df['Date'] = df['parsed_datetime'].dt.date
        
        # Convert back to datetime for consistency with existing processing
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Add year and month columns (following your existing pattern)
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month
        
        logger.info(f"Successfully parsed {len(df)} dates")
        logger.info(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
        
        # Drop the intermediate column
        df = df.drop(columns=['parsed_datetime'])
        
        return df
        
    except Exception as e:
        logger.error(f"Error parsing sampling dates: {e}")
        return df

def get_greater_value(row: pd.Series, col1: str, col2: str, tiebreaker: str = 'col1') -> Optional[float]:
    """
    Get the greater value between two columns, with tiebreaker logic.
    """
    try:
        # Get values and convert to numeric, handling non-numeric values
        val1 = pd.to_numeric(row[col1], errors='coerce') if pd.notna(row[col1]) else None
        val2 = pd.to_numeric(row[col2], errors='coerce') if pd.notna(row[col2]) else None
        
        # If both are null, return None
        if val1 is None and val2 is None:
            return None
            
        # If one is null, return the other
        if val1 is None:
            return val2
        if val2 is None:
            return val1
            
        # If both have values, return the greater 
        if val1 > val2:
            return val1
        elif val2 > val1:
            return val2
        else:  
            return val1 if tiebreaker == 'col1' else val2
            
    except Exception as e:
        logger.warning(f"Error comparing {col1} and {col2}: {e}")
        return None

def get_conditional_nutrient_value(row: pd.Series, range_selection_col: str, low_col1: str, 
                                 low_col2: str, mid_col1: str = None, mid_col2: str = None, 
                                 high_col1: str = None, high_col2: str = None) -> Optional[float]:
    """
    Get nutrient value based on range selection with conditional logic.
    """
    try:
        range_selection = row[range_selection_col]
        
        # Handle null/empty range selection
        if pd.isna(range_selection) or range_selection == '':
            return None
            
        # Convert to string and clean up
        range_selection = str(range_selection).strip()
        
        # Select appropriate columns based on range
        if 'Low' in range_selection:
            return get_greater_value(row, low_col1, low_col2, tiebreaker='col1')
        elif 'Mid' in range_selection and mid_col1 and mid_col2:
            return get_greater_value(row, mid_col1, mid_col2, tiebreaker='col1')
        elif 'High' in range_selection and high_col1 and high_col2:
            return get_greater_value(row, high_col1, high_col2, tiebreaker='col1')
        else:
            logger.warning(f"Unknown range selection: {range_selection}")
            return None
            
    except Exception as e:
        logger.warning(f"Error processing conditional nutrient value: {e}")
        return None

def process_conditional_nutrient(df: pd.DataFrame, nutrient_name: str) -> pd.Series:
    """
    Process any conditional nutrient using the mapping dictionary.
    """
    try:
        mapping = NUTRIENT_COLUMN_MAPPINGS[nutrient_name]
        
        result = df.apply(lambda row: get_conditional_nutrient_value(
            row,
            range_selection_col=mapping['range_selection'],
            low_col1=mapping['low_col1'],
            low_col2=mapping['low_col2'],
            mid_col1=mapping.get('mid_col1'),  
            mid_col2=mapping.get('mid_col2'),
            high_col1=mapping.get('high_col1'),
            high_col2=mapping.get('high_col2')
        ), axis=1)
        
        logger.info(f"Successfully processed {nutrient_name} values")
        return result
        
    except Exception as e:
        logger.error(f"Error processing {nutrient_name}: {e}")
        return pd.Series([None] * len(df))

def process_simple_nutrients(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process nutrients that use simple "greater of two" logic.
    """
    try:
        # Process Nitrate (simple greater of two)
        df['Nitrate'] = df.apply(lambda row: get_greater_value(row, 'Nitrate #1', 'Nitrate #2'), axis=1)
        
        # Process Nitrite (simple greater of two)  
        df['Nitrite'] = df.apply(lambda row: get_greater_value(row, 'Nitrite #1', 'Nitrite #2'), axis=1)
        
        logger.info("Successfully processed Nitrate and Nitrite values")
        return df
        
    except Exception as e:
        logger.error(f"Error processing simple nutrients: {e}")
        return df

def apply_bdl_conversions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply Below Detection Limit (BDL) conversions to chemical parameters.
    """
    try:
        for param, bdl_value in BDL_CONVERSIONS.items():
            if param in df.columns and bdl_value is not None:
                # Convert zeros to BDL value
                df[param] = df[param].apply(lambda x: bdl_value if x == 0 else x)
        
        logger.info("Applied BDL conversions")
        return df
        
    except Exception as e:
        logger.error(f"Error applying BDL conversions: {e}")
        return df

def calculate_soluble_nitrogen(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate soluble nitrogen from nitrate, nitrite, and ammonia.
    """
    try:
        # Only calculate if all required columns exist
        required_cols = ['Nitrate', 'Nitrite', 'Ammonia']
        if all(col in df.columns for col in required_cols):
            df['soluble_nitrogen'] = df[required_cols].sum(axis=1, skipna=True)
            logger.info("Calculated soluble nitrogen values")
        else:
            logger.warning("Cannot calculate soluble nitrogen - missing required columns")
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating soluble nitrogen: {e}")
        return df

def validate_chemical_data(df: pd.DataFrame, remove_invalid: bool = True) -> pd.DataFrame:
    """
    Validate chemical data and optionally remove invalid values.
    """
    try:
        initial_count = len(df)
        
        # Define reasonable ranges for each parameter
        validation_ranges = {
            'pH': (0, 14),
            'do_percent': (0, 200),
            'Nitrate': (0, 50),
            'Nitrite': (0, 10),
            'Ammonia': (0, 20),
            'Phosphorus': (0, 5),
            'Chloride': (0, 1000),
            'soluble_nitrogen': (0, 100)
        }
        
        if remove_invalid:
            for param, (min_val, max_val) in validation_ranges.items():
                if param in df.columns:
                    # Remove rows with invalid values
                    invalid_mask = (df[param] < min_val) | (df[param] > max_val)
                    df.loc[invalid_mask, param] = np.nan
        
        final_count = len(df)
        logger.info(f"Validation complete: {initial_count} -> {final_count} rows")
        
        return df
        
    except Exception as e:
        logger.error(f"Error validating chemical data: {e}")
        return df

def format_to_database_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format the processed data to match the existing database schema.
    """
    try:
        # Start with a copy of the existing dataframe
        formatted_df = df.copy()
        
        # Remap columns that actually need to change
        column_mappings = {
            'Site Name': 'Site_Name',
            '% Oxygen Saturation': 'do_percent', 
            'pH #1': 'pH',
            'Orthophosphate': 'Phosphorus'
        }
        
        # Apply the mappings
        formatted_df = formatted_df.rename(columns=column_mappings)
        
        # Add calculated soluble nitrogen
        formatted_df = calculate_soluble_nitrogen(formatted_df)
        
        # Select only the columns we need for the database
        required_columns = ['Site_Name', 'Date', 'Year', 'Month', 'do_percent', 'pH', 
                           'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride', 
                           'soluble_nitrogen']
        
        # Keep only columns that exist
        available_columns = [col for col in required_columns if col in formatted_df.columns]
        formatted_df = formatted_df[available_columns]
        
        # Convert numeric columns to proper types
        numeric_columns = ['do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 
                          'Phosphorus', 'Chloride', 'soluble_nitrogen']
        
        for col in numeric_columns:
            if col in formatted_df.columns:
                formatted_df[col] = pd.to_numeric(formatted_df[col], errors='coerce')
        
        logger.info(f"Successfully formatted {len(formatted_df)} rows to database schema")
        logger.info(f"Final columns: {list(formatted_df.columns)}")
        
        return formatted_df
        
    except Exception as e:
        logger.error(f"Error formatting data to database schema: {e}")
        return pd.DataFrame()

def remove_empty_chemical_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows where all chemical parameters are null.
    """
    try:
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
        
    except Exception as e:
        logger.error(f"Error removing empty rows: {e}")
        return df

def process_survey123_chemical_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Complete processing pipeline for Survey123 chemical data.
    
    This is the main function that orchestrates all the processing steps.
    """
    try:
        logger.info("Starting complete processing of Survey123 chemical data...")
        
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return pd.DataFrame()
        
        # Step 1: Parse dates
        df = parse_sampling_dates(df)
        
        # Step 2: Process all nutrients
        df = process_simple_nutrients(df)  # Nitrate, Nitrite
        df['Ammonia'] = process_conditional_nutrient(df, 'ammonia')
        df['Orthophosphate'] = process_conditional_nutrient(df, 'orthophosphate') 
        df['Chloride'] = process_conditional_nutrient(df, 'chloride')
        
        # Step 3: Format to database schema
        formatted_df = format_to_database_schema(df)
        
        # Step 4: Clean and validate 
        formatted_df = remove_empty_chemical_rows(formatted_df)
        formatted_df = validate_chemical_data(formatted_df, remove_invalid=True)
        
        # Step 5: Apply BDL conversions
        formatted_df = apply_bdl_conversions(formatted_df)
        
        logger.info(f"Complete processing finished: {len(formatted_df)} rows ready for database")
        return formatted_df
        
    except Exception as e:
        logger.error(f"Error in complete processing pipeline: {e}")
        return pd.DataFrame()

def insert_processed_data_to_db(df: pd.DataFrame, db_path: str) -> Dict[str, Any]:
    """
    Insert processed chemical data into the SQLite database.
    """
    if df.empty:
        return {'records_inserted': 0, 'error': 'No data to insert'}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get site lookup
        site_query = "SELECT site_id, site_name FROM sites"
        site_df = pd.read_sql_query(site_query, conn)
        site_lookup = dict(zip(site_df['site_name'], site_df['site_id']))
        
        records_inserted = 0
        
        for _, row in df.iterrows():
            site_name = row['Site_Name']
            
            # Check if site exists
            if site_name not in site_lookup:
                logger.warning(f"Site {site_name} not found in database - skipping")
                continue
            
            site_id = site_lookup[site_name]
            date_str = row['Date'].strftime('%Y-%m-%d')
            
            # Insert collection event
            event_query = """
                INSERT OR IGNORE INTO collection_events (site_id, collection_date, year, month)
                VALUES (?, ?, ?, ?)
            """
            cursor.execute(event_query, (site_id, date_str, row['Year'], row['Month']))
            
            # Get event ID
            event_id_query = """
                SELECT event_id FROM collection_events 
                WHERE site_id = ? AND collection_date = ?
            """
            cursor.execute(event_id_query, (site_id, date_str))
            event_id = cursor.fetchone()[0]
            
            # Insert chemical measurements
            parameter_map = {
                'do_percent': 1, 'pH': 2, 'Nitrate': 3, 'Nitrite': 4, 
                'Ammonia': 5, 'Phosphorus': 6, 'Chloride': 7, 'soluble_nitrogen': 8
            }
            
            for param_name, param_id in parameter_map.items():
                if param_name in row and pd.notna(row[param_name]):
                    value = row[param_name]
                    
                    # Determine status
                    status = determine_parameter_status(param_name, value)
                    
                    # Insert measurement
                    measurement_query = """
                        INSERT OR REPLACE INTO chemical_measurements 
                        (event_id, parameter_id, value, status)
                        VALUES (?, ?, ?, ?)
                    """
                    cursor.execute(measurement_query, (event_id, param_id, value, status))
                    records_inserted += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully inserted {records_inserted} measurements")
        return {'records_inserted': records_inserted}
        
    except Exception as e:
        logger.error(f"Error inserting data to database: {e}")
        return {'records_inserted': 0, 'error': str(e)}

def determine_parameter_status(param_name: str, value: float) -> str:
    """
    Determine the status (Good/Fair/Poor) for a parameter value.
    """
    try:
        ref = REFERENCE_VALUES.get(param_name, {})
        
        if 'good_min' in ref and 'good_max' in ref:
            # pH case - has both min and max
            if ref['good_min'] <= value <= ref['good_max']:
                return 'Good'
            else:
                return 'Poor'
        elif 'good_max' in ref:
            # Other parameters - only max threshold
            if value <= ref['good_max']:
                return 'Good'
            elif value <= ref['good_max'] * 2:  # Fair range
                return 'Fair'
            else:
                return 'Poor'
        else:
            return 'Unknown'
            
    except Exception as e:
        logger.warning(f"Error determining status for {param_name}: {e}")
        return 'Unknown' 