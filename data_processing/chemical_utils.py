"""
Chemical data utilities for the Blue Thumb Water Quality Dashboard.
Shared functions for processing and validating chemical data.
"""

import pandas as pd
import numpy as np
from utils import setup_logging

# Set up logging
logger = setup_logging("chemical_utils", category="processing")

# Define constants for BDL values (Below Detection Limit)
# Values provided by Blue Thumb Cordinator
BDL_VALUES = {
    'Nitrate': 0.3,    
    'Nitrite': 0.03,    
    'Ammonia': 0.03,
    'Phosphorus': 0.005,
}

# Chemical parameter validation limits
VALIDATION_LIMITS = {
    'pH': {'min': 0, 'max': 14},
    'do_percent': {'min': 0, 'max': 200},
    'Nitrate': {'min': 0, 'max': None},
    'Nitrite': {'min': 0, 'max': None},
    'Ammonia': {'min': 0, 'max': None},
    'Phosphorus': {'min': 0, 'max': None},
    'Chloride': {'min': 0, 'max': None},
    'soluble_nitrogen': {'min': 0, 'max': None}
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

CHEMICAL_PARAMETERS = [
    (1, 'Dissolved Oxygen', 'do_percent', 'Dissolved Oxygen', 'Percent saturation of dissolved oxygen', '%'),
    (2, 'pH', 'pH', 'pH', 'Measure of acidity/alkalinity', 'pH units'),
    (3, 'Soluble Nitrogen', 'soluble_nitrogen', 'Nitrogen', 'Total soluble nitrogen including nitrate, nitrite, and ammonia', 'mg/L'),
    (4, 'Phosphorus', 'Phosphorus', 'Phosphorus', 'Orthophosphate phosphorus', 'mg/L'),
    (5, 'Chloride', 'Chloride', 'Chloride', 'Chloride ion concentration', 'mg/L')
]

CHEMICAL_REFERENCE_VALUES = [
    # do_percent reference values
    (1, 1, 'normal_min', 80, 'Minimum for normal range'),
    (2, 1, 'normal_max', 130, 'Maximum for normal range'),
    (3, 1, 'caution_min', 50, 'Minimum for caution range'),
    (4, 1, 'caution_max', 150, 'Maximum for caution range'),
    
    # pH reference values
    (5, 2, 'normal_min', 6.5, 'Minimum for normal range'),
    (6, 2, 'normal_max', 9.0, 'Maximum for normal range'),
    
    # Soluble Nitrogen reference values
    (7, 3, 'normal', 0.8, 'Normal threshold'),
    (8, 3, 'caution', 1.5, 'Caution threshold'),
    
    # Phosphorus reference values
    (9, 4, 'normal', 0.05, 'Normal threshold'),
    (10, 4, 'caution', 0.1, 'Caution threshold'),
    
    # Chloride reference values
    (11, 5, 'poor', 250, 'Poor threshold')
]

def insert_default_parameters(cursor):
    """
    Insert default chemical parameters into the database.
    
    Args:
        cursor: Database cursor
        
    Raises:
        Exception: If insertion fails
    """
    try:
        # Insert the parameters
        cursor.executemany('''
        INSERT OR IGNORE INTO chemical_parameters 
        (parameter_id, parameter_name, parameter_code, display_name, description, unit)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', CHEMICAL_PARAMETERS)
        
        logger.info(f"Inserted {len(CHEMICAL_PARAMETERS)} chemical parameters")
    except Exception as e:
        logger.error(f"Error inserting default parameters: {e}")
        raise Exception(f"Failed to insert default chemical parameters: {e}")

def insert_default_reference_values(cursor):
    """
    Insert default chemical reference values into the database.
    
    Args:
        cursor: Database cursor
        
    Raises:
        Exception: If insertion fails
    """
    try:
        # Insert the reference values
        cursor.executemany('''
        INSERT OR IGNORE INTO chemical_reference_values
        (reference_id, parameter_id, threshold_type, value, description)
        VALUES (?, ?, ?, ?, ?)
        ''', CHEMICAL_REFERENCE_VALUES)
        
        logger.info(f"Inserted {len(CHEMICAL_REFERENCE_VALUES)} chemical reference values")
    except Exception as e:
        logger.error(f"Error inserting default reference values: {e}")
        raise Exception(f"Failed to insert default chemical reference values: {e}")

def ensure_default_parameters_exist():
    """
    Ensure that default chemical parameters and reference values exist in the database.
    This function should be called during chemical processing initialization.
    
    Raises:
        Exception: If parameters cannot be created or verified
    """
    try:
        from database.database import get_connection, close_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if parameters table has data
        cursor.execute("SELECT COUNT(*) FROM chemical_parameters")
        param_count = cursor.fetchone()[0]
        
        if param_count == 0:
            logger.info("No chemical parameters found in database, inserting defaults...")
            insert_default_parameters(cursor)
            insert_default_reference_values(cursor)
            conn.commit()
            logger.info("Default chemical parameters and reference values added")
        else:
            logger.debug(f"Found {param_count} existing chemical parameters in database")
        
        close_connection(conn)
        
    except Exception as e:
        logger.error(f"Error ensuring default parameters exist: {e}")
        raise Exception(f"Critical error: Cannot ensure chemical parameters exist in database: {e}")

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
    
    Args:
        df: DataFrame with chemical data
        remove_invalid: If True, set invalid values to NaN; if False, just log warnings
        
    Returns:
        DataFrame with validated data
    """
    df_clean = df.copy()
    
    # Get chemical columns that exist in the dataframe
    chemical_columns = [col for col in VALIDATION_LIMITS.keys() if col in df_clean.columns]
    
    validation_summary = {
        'total_issues': 0,
        'issues_by_parameter': {}
    }
    
    for column in chemical_columns:
        if column not in df_clean.columns:
            continue
            
        limits = VALIDATION_LIMITS[column]
        original_values = df_clean[column].copy()
        issues_found = 0
        
        # Check minimum values
        if limits['min'] is not None:
            below_min_mask = (df_clean[column] < limits['min']) & df_clean[column].notna()
            below_min_count = below_min_mask.sum()
            
            if below_min_count > 0:
                issues_found += below_min_count
                if remove_invalid:
                    df_clean.loc[below_min_mask, column] = np.nan
                    logger.info(f"Removed {below_min_count} {column} values below {limits['min']}")
                else:
                    logger.warning(f"Found {below_min_count} {column} values below {limits['min']}")
        
        # Check maximum values
        if limits['max'] is not None:
            above_max_mask = (df_clean[column] > limits['max']) & df_clean[column].notna()
            above_max_count = above_max_mask.sum()
            
            if above_max_count > 0:
                issues_found += above_max_count
                if column in ['pH']:  # Remove pH values outside range
                    if remove_invalid:
                        df_clean.loc[above_max_mask, column] = np.nan
                        logger.info(f"Removed {above_max_count} {column} values above {limits['max']}")
                    else:
                        logger.warning(f"Found {above_max_count} {column} values above {limits['max']}")
                else:  # Just warn for DO and other parameters
                    logger.warning(f"Found {above_max_count} {column} values above {limits['max']} (keeping values)")
        
        # Track issues for this parameter
        if issues_found > 0:
            validation_summary['issues_by_parameter'][column] = issues_found
            validation_summary['total_issues'] += issues_found
    
    # Log overall summary
    if validation_summary['total_issues'] > 0:
        logger.info(f"Data validation complete: {validation_summary['total_issues']} total issues found")
        for param, count in validation_summary['issues_by_parameter'].items():
            action = "removed" if remove_invalid else "flagged"
            logger.info(f"  - {param}: {count} issues {action}")
    else:
        logger.info("Data validation complete: No quality issues found")
    
    return df_clean

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