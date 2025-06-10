"""
data_loader.py - CSV Data Loading and Utilities

This module provides core data loading functionality for the Blue Thumb Water Quality Dashboard.
Handles loading cleaned CSV files from the interim directory, site name standardization, 
column cleaning, and data validation utilities used across all data processing modules.

Key Functions:
- load_csv_data(): Load any CSV data type with automatic site name cleaning
- clean_site_name(), clean_site_names_column(): Standardize site name formatting
- clean_column_names(): Standardize column name formatting
- save_processed_data(): Save processed data to the processed directory
- get_unique_sites(): Extract unique site lists from data files
- filter_data_by_site(): Filter data for specific sites

Data Types Supported:
- site, chemical, updated_chemical, fish, macro, habitat, fish_collection_dates

Usage:
- Import functions for consistent data loading across all processing modules
- Run directly to test data loading functionality
"""

import os
import pandas as pd
import re
from data_processing import setup_logging

# Initialize logger
logger = setup_logging("data_loader", category="processing")

# Constants
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'processed')
INTERIM_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'interim')

# Make sure directories exist
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(INTERIM_DATA_DIR, exist_ok=True)

# File paths for each data source (cleaned files are now in interim directory)
DATA_FILES = {
    'site': os.path.join(INTERIM_DATA_DIR, 'cleaned_site_data.csv'),  
    'chemical': os.path.join(INTERIM_DATA_DIR, 'cleaned_chemical_data.csv'),  
    'updated_chemical': os.path.join(INTERIM_DATA_DIR, 'cleaned_updated_chemical_data.csv'), 
    'fish': os.path.join(INTERIM_DATA_DIR, 'cleaned_fish_data.csv'),  
    'macro': os.path.join(INTERIM_DATA_DIR, 'cleaned_macro_data.csv'),  
    'habitat': os.path.join(INTERIM_DATA_DIR, 'cleaned_habitat_data.csv'),
    'fish_collection_dates': os.path.join(INTERIM_DATA_DIR, 'cleaned_BT_fish_collection_dates.csv')
}

def get_file_path(data_type, processed=False):
    """
    Get the path to a data file.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'updated_chemical', 'fish', 'macro', 'habitat', 'fish_collection_dates')
        processed: Whether to return path for processed data (default: False)
    
    Returns:
        str: Path to the specified data file
    """
    if not data_type in DATA_FILES:
        logger.error(f"Unknown data type: {data_type}")
        return None
    
    if processed:
        # Use processed data directory with standardized naming
        filename = f"processed_{data_type}_data.csv"
        return os.path.join(PROCESSED_DATA_DIR, filename)
    else:
        return DATA_FILES[data_type]

def check_file_exists(file_path):
    """
    Check if a file exists.
    
    Args:
        file_path: Path to the file
    
    Returns:
        bool: True if file exists, False otherwise
    """
    exists = os.path.exists(file_path)
    if not exists:
        logger.error(f"File not found: {file_path}")
    return exists

def clean_site_name(site_name):
    """
    Clean and standardize site names.
    
    Args:
        site_name: Raw site name string
    
    Returns:
        str: Cleaned site name
    """
    if pd.isna(site_name):
        return site_name
    
    # Convert to string and strip leading/trailing whitespace
    cleaned = str(site_name).strip()
    
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned

def clean_site_names_column(df, site_column='sitename', log_changes=True):
    """
    Clean site names in a DataFrame column and optionally log changes.
    
    Args:
        df: DataFrame containing site names
        site_column: Name of the column containing site names
        log_changes: Whether to log the changes made
    
    Returns:
        DataFrame: DataFrame with cleaned site names
    """
    if site_column not in df.columns:
        logger.warning(f"Site column '{site_column}' not found in DataFrame")
        return df
    
    df_clean = df.copy()
    changes_made = 0
    
    # Apply cleaning and track changes
    for idx, original_name in df_clean[site_column].items():
        cleaned_name = clean_site_name(original_name)
        
        if pd.notna(original_name) and str(original_name) != str(cleaned_name):
            if log_changes:
                logger.info(f"Cleaned site name: '{original_name}' -> '{cleaned_name}'")
            changes_made += 1
        
        df_clean.at[idx, site_column] = cleaned_name
    
    if log_changes and changes_made > 0:
        logger.info(f"Cleaned {changes_made} site names in {site_column} column")
    elif log_changes:
        logger.info(f"No site name changes needed in {site_column} column")
    
    return df_clean

def load_csv_data(data_type, usecols=None, dtype=None, parse_dates=None, 
                  clean_site_names=True, encoding=None):
    """
    Load data from a CSV file with optional site name cleaning.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'updated_chemical', 'fish', 'macro', 'habitat', 'fish_collection_dates')
        usecols: List of columns to load (default: None, load all)
        dtype: Dictionary of column data types (default: None)
        parse_dates: List of columns to parse as dates (default: None)
        clean_site_names: Whether to automatically clean site names (default: True)
    
    Returns:
        DataFrame: Loaded data or empty DataFrame if loading fails
    """
    file_path = get_file_path(data_type)
    
    if not file_path or not check_file_exists(file_path):
        return pd.DataFrame()
    
    try:
        logger.info(f"Loading {data_type} data from {file_path}")
        
        # Load the data
        df = pd.read_csv(
            file_path,
            usecols=usecols,
            dtype=dtype,
            parse_dates=parse_dates,
            encoding=encoding,
            low_memory=False 
        )
        
        logger.info(f"Successfully loaded {len(df)} rows from {data_type} data")
        
        # Automatically clean site names if requested
        if clean_site_names:
            # Try to find the site name column
            site_column = None
            for col in df.columns:
                if col.lower() in ['sitename', 'site_name', 'site name']:
                    site_column = col
                    break
            
            if site_column:
                df = clean_site_names_column(df, site_column, log_changes=True)
        
        return df
    
    except Exception as e:
        logger.error(f"Error loading {data_type} data: {e}")
        return pd.DataFrame()

def save_processed_data(df, data_type):
    """
    Save processed data to a CSV file.
    
    Args:
        df: DataFrame to save
        data_type: Type of data or filename identifier
    
    Returns:
        bool: True if saving was successful, False otherwise
    """
    if df.empty:
        logger.warning(f"No {data_type} data to save")
        return False
    
    # Sanitize the data_type for use as a filename
    # Replace spaces, colons, and other special characters with underscores
    sanitized_type = data_type
    for char in [' ', ':', ';', ',', '.', '/', '\\', '(', ')', '[', ']', '{', '}', '|', '*', '?', '&', '^', '%', '$', '#', '@', '!']:
        sanitized_type = sanitized_type.replace(char, '_')
    
    # Make sure we don't have multiple consecutive underscores
    while '__' in sanitized_type:
        sanitized_type = sanitized_type.replace('__', '_')
    
    file_path = os.path.join(INTERIM_DATA_DIR, f"{sanitized_type}.csv")
    
    try:
        logger.info(f"Saving {data_type} data to {file_path}")
        df.to_csv(file_path, index=False)
        logger.info(f"Successfully saved {len(df)} rows of {data_type} data")
        return True
    
    except Exception as e:
        logger.error(f"Error saving processed {data_type} data: {e}")
        return False

def clean_column_names(df):
    """
    Clean column names to a standardized format.
    
    Args:
        df: DataFrame with columns to clean
    
    Returns:
        DataFrame: DataFrame with cleaned column names
    """
    # Make a copy to avoid modifying the original
    df_copy = df.copy()
    
    # Clean column names
    df_copy.columns = [
        col.replace(' \n', '_')
           .replace('\n', '_')
           .replace(' ', '_')
           .replace('-', '_')
           .replace('.', '')
           .replace('(', '')
           .replace(')', '')
           .lower()
        for col in df_copy.columns
    ]
    
    return df_copy

def filter_data_by_site(df, site_name, site_column='sitename'):
    """
    Filter a DataFrame to include only rows for a specific site.
    
    Args:
        df: DataFrame to filter
        site_name: Name of the site to filter for
        site_column: Name of the column containing site names (default: 'sitename')
    
    Returns:
        DataFrame: Filtered data for the specified site
    """
    # Clean the site name for comparison
    clean_site_name_to_match = clean_site_name(site_name)
    
    # Check if the site column exists
    if site_column not in df.columns:
        # Try to find a column with 'site' in the name
        site_columns = [col for col in df.columns if 'site' in col.lower()]
        if site_columns:
            site_column = site_columns[0]
            logger.info(f"Using {site_column} as the site column")
        else:
            logger.error(f"No site column found in DataFrame")
            return pd.DataFrame()
    
    # Filter the data using cleaned names for comparison
    filtered_df = df[df[site_column].apply(clean_site_name) == clean_site_name_to_match]
    
    if filtered_df.empty:
        logger.warning(f"No data found for site: {site_name}")
    else:
        logger.info(f"Found {len(filtered_df)} rows for site: {site_name}")
    
    return filtered_df

def get_unique_sites(data_type, site_column='sitename'):
    """
    Get a list of unique site names from a data file.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'updated_chemical', 'fish', 'macro', 'habitat', 'fish_collection_dates')
        site_column: Name of the column containing site names (default: 'sitename')
    
    Returns:
        list: List of unique site names
    """
    df = load_csv_data(data_type, clean_site_names=True)  # Enable automatic site name cleaning
    
    if df.empty:
        return []
    
    # Clean column names
    df = clean_column_names(df)
    
    # Check if the site column exists
    if site_column not in df.columns:
        # Try to find a column with 'site' in the name
        site_columns = [col for col in df.columns if 'site' in col.lower()]
        if site_columns:
            site_column = site_columns[0]
        else:
            logger.error(f"No site column found in {data_type} data")
            return []
    
    # Get unique sites
    unique_sites = df[site_column].dropna().unique().tolist()
    logger.info(f"Found {len(unique_sites)} unique sites in {data_type} data")
    
    return unique_sites

def convert_bdl_values(df, bdl_columns, bdl_replacements):
    """
    Convert 'BDL' (Below Detection Limit) values to numeric values.
    
    Args:
        df: DataFrame containing the data
        bdl_columns: List of columns that may contain BDL values
        bdl_replacements: Dictionary mapping column names to their BDL replacement values
    
    Returns:
        DataFrame: DataFrame with BDL values converted
    """
    df_copy = df.copy()
    
    for column in bdl_columns:
        if column in df_copy.columns:
            # Define a function to replace BDL values
            def convert_value(value):
                if isinstance(value, (int, float)):
                    return value
                elif isinstance(value, str) and value.upper() == 'BDL':
                    return bdl_replacements.get(column, 0)
                else:
                    try:
                        return float(value)
                    except:
                        return None
            
            # Apply the conversion
            df_copy[column] = df_copy[column].apply(convert_value)
            logger.debug(f"Converted BDL values in column: {column}")
    
    return df_copy

def get_date_range(data_type, date_column='Date'):
    """
    Get the date range (min and max dates) for a data type.
    
    Args:
        data_type: Type of data ('chemical', 'updated_chemical', 'fish', 'macro', 'habitat', 'fish_collection_dates')
        date_column: Name of the column containing dates (default: 'Date')
    
    Returns:
        tuple: (min_date, max_date) or (None, None) if no dates found
    """
    # Skip site data since it doesn't need date processing
    if data_type == 'site':
        logger.info(f"Date range not applicable for site data")
        return None, None
        
    # Load the data with the date column
    try:
        df = load_csv_data(data_type, parse_dates=[date_column], clean_site_names=False)  # Skip site cleaning for date range check
    except Exception as e:
        logger.error(f"Error loading {data_type} data for date range: {e}")
        return None, None
    
    if df.empty:
        return None, None
    
    # Clean column names
    df = clean_column_names(df)
    
    # After cleaning, the date column name will be lowercase
    date_column_lower = date_column.lower()
    
    # Get min and max dates
    min_date = df[date_column_lower].min()
    max_date = df[date_column_lower].max()
    
    logger.info(f"Date range for {data_type} data: {min_date} to {max_date}")
    
    return min_date, max_date

if __name__ == "__main__":
    # Test the data loading functions
    print("Testing data loader:")
    
    for data_type in DATA_FILES.keys():
        # Skip site data for date range
        if data_type == 'site':
            continue
            
        min_date, max_date = get_date_range(data_type)
        if min_date and max_date:
            print(f"  - Date range: {min_date} to {max_date}")
            
            # Load a sample of the data
            df = load_csv_data(data_type)
            if not df.empty:
                print(f"  - Loaded {len(df)} rows and {len(df.columns)} columns")
                print(f"  - Column sample: {', '.join(df.columns[:5])}")
                
                # Get some sample sites
                sites = get_unique_sites(data_type)
                if sites:
                    print(f"  - Sample sites: {', '.join(sites[:5])}")
                    
                    # Get date range
                    min_date, max_date = get_date_range(data_type)
                    if min_date and max_date:
                        print(f"  - Date range: {min_date} to {max_date}")
            else:
                print(f"✗ Could not load {data_type} data")
        else:
            print(f"✗ {data_type.capitalize()} data file not found")
    
    print("\nData loader module test complete.")