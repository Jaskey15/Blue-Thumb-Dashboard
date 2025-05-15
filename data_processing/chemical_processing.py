import logging
import os
import pandas as pd
import numpy as np

# Import utilities from data_loader
from data_processing.data_loader import (
    setup_logging, load_csv_data, clean_column_names, 
    save_processed_data, get_file_path, get_unique_sites
)

# Use the shared logging setup
logger = setup_logging()

# Define constants for BDL values (Below Detection Limit)
# Values obtained from Blue Thumb Coordinator
BDL_VALUES = {
    'Nitrate': 0.3,    
    'Nitrite': 0.03,    
    'Ammonia': 0.03,
    'Phosphorus': 0.005,
}

# Define reference values (based on Blue Thumb documentation)
REFERENCE_VALUES = {
    'DO_Percent': {
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
    'Soluble_Nitrogen': {
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

# List of key parameters for analysis and visualization
KEY_PARAMETERS = [    
    'DO_Percent', 'pH', 'Soluble_Nitrogen', 
    'Phosphorus', 'Chloride', 
]

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
    # Create a subset with just the chemical columns
    chem_df = df[chemical_columns].copy()
    
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
    return get_unique_sites('chemical')

def get_date_range_for_site(site_name):
    """Get the min and max dates for chemical data at a specific site."""
    try:
        # Load the data for the specified site
        df = process_chemical_data(site_name)
        
        if df.empty:
            return None, None
            
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        
        return min_date, max_date
    
    except Exception as e:
        logger.error(f"Error getting date range for site {site_name}: {e}")
        return None, None

def process_chemical_data(site_name=None):
    """
    Process chemical data from CSV file and return cleaned dataframe.
    
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
            return pd.DataFrame(), KEY_PARAMETERS, REFERENCE_VALUES
            
        logger.info(f"Successfully loaded data with {len(chemical_data)} rows")
        
        # Filter by site name if provided
        if site_name:
            chemical_data = chemical_data[chemical_data['SiteName'] == site_name]
            logger.info(f"Filtered to {len(chemical_data)} rows for site: {site_name}")
            
            if chemical_data.empty:
                logger.warning(f"No data found for site: {site_name}")
                return pd.DataFrame(), KEY_PARAMETERS, REFERENCE_VALUES
    
    except Exception as e:
        logger.error(f"Error loading chemical data: {e}")
        return pd.DataFrame(), KEY_PARAMETERS, REFERENCE_VALUES

    # Clean column names using data_loader's function
    chemical_data = clean_column_names(chemical_data)
    
    # Map of expected columns to actual columns in the data
    column_mapping = {
        'sitename': 'Site_Name',
        'do_saturation': 'DO_Percent',
        'ph_final_1': 'pH',
        'nitrate_final_1': 'Nitrate',
        'nitrite_final_1': 'Nitrite',
        'ammonia_final_1': 'Ammonia',
        'op_final_1': 'Phosphorus',
        'chloride_final_1': 'Chloride',
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
        'DO_Percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride'
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
        
        df_clean['Soluble_Nitrogen'] = nitrate_values + nitrite_values + ammonia_values
        logger.debug("Calculated Soluble_Nitrogen from component values")
    else:   
        missing_nitrogen_cols = [col for col in required_nitrogen_cols if col not in df_clean.columns]
        logger.warning(f"Cannot calculate Soluble_Nitrogen: Missing columns: {', '.join(missing_nitrogen_cols)}")

    # Check for missing values in final dataframe
    missing_values = df_clean.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Final dataframe contains {missing_values} missing values")

    # Save processed data if a site was specified
    if site_name:
        save_processed_data(df_clean, f"chemical_{site_name.replace(' ', '_').lower()}")

    logger.info(f"Data processing complete. Output dataframe has {len(df_clean)} rows and {len(df_clean.columns)} columns")
    return df_clean, KEY_PARAMETERS, REFERENCE_VALUES

if __name__ == "__main__":
    try:
        logger.info("Testing chemical data processing")
        
        # Get list of sites with chemical data
        sites = get_sites_with_chemical_data()
        logger.info(f"Found {len(sites)} sites with chemical data")
        
        if sites:
            # Process data for the first site as a test
            test_site = sites[0]
            logger.info(f"Processing data for test site: {test_site}")
            
            df_clean, key_parameters, reference_values = process_chemical_data(test_site)
            
            if not df_clean.empty:
                logger.info(f"Successfully processed {len(df_clean)} records for {test_site}")
                
                # Test date range function
                min_date, max_date = get_date_range_for_site(test_site)
                if min_date and max_date:
                    logger.info(f"Date range for {test_site}: {min_date} to {max_date}")
            else:
                logger.warning(f"No data found for test site: {test_site}")
        
    except Exception as e:
        logger.error(f"Error in chemical data processing test: {e}")