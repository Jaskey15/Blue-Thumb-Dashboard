"""
Processes and validates chemical water quality data from CSV files for database insertion.

This module handles the entire chemical data pipeline, including loading cleaned data,
applying Below Detection Limit (BDL) conversions, calculating soluble nitrogen, 
and inserting the final, validated data into the database.
"""

import os
import pandas as pd
from data_processing.data_loader import clean_column_names, save_processed_data
from utils import get_sites_with_data
from data_processing.chemical_utils import (
    validate_chemical_data, apply_bdl_conversions, calculate_soluble_nitrogen,
    remove_empty_chemical_rows, KEY_PARAMETERS,
    insert_chemical_data, get_reference_values
)
from data_processing import setup_logging

logger = setup_logging("chemical_processing", category="processing")

def process_chemical_data_from_csv(site_name=None):
    """
    Processes and validates chemical data from a cleaned CSV file.
    
    This function orchestrates the cleaning, validation, and transformation of
    chemical data, preparing it for database insertion or further analysis.
    
    Args:
        site_name: An optional site name to filter the data for.
        
    Returns:
        A tuple containing the cleaned DataFrame, a list of key parameter names,
        and a dictionary of reference values.
    """
    try:
        # Load from the pre-cleaned CSV to ensure a consistent starting point.
        cleaned_chemical_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'interim', 'cleaned_chemical_data.csv'
        )
        
        if not os.path.exists(cleaned_chemical_path):
            logger.error("cleaned_chemical_data.csv not found. Run CSV cleaning first.")
            return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
        
        cols_to_load = [
            'SiteName', 'Date', 'DO.Saturation', 'pH.Final.1', 
            'Nitrate.Final.1', 'Nitrite.Final.1', 'Ammonia.Final.1',
            'OP.Final.1', 'Chloride.Final.1'
        ]
        
        chemical_data = pd.read_csv(
            cleaned_chemical_path,
            usecols=cols_to_load,
            parse_dates=['Date']
        )
        
        if chemical_data.empty:
            logger.error("Failed to load cleaned chemical data")
            return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
            
        logger.info(f"Successfully loaded data with {len(chemical_data)} rows from cleaned CSV")
        
        if site_name:
            chemical_data = chemical_data[chemical_data['SiteName'] == site_name]
            logger.info(f"Filtered to {len(chemical_data)} rows for site: {site_name}")
            
            if chemical_data.empty:
                logger.warning(f"No data found for site: {site_name}")
                return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()
    
    except Exception as e:
        logger.error(f"Error loading cleaned chemical data: {e}")
        return pd.DataFrame(), KEY_PARAMETERS, get_reference_values()

    chemical_data = clean_column_names(chemical_data)

    logger.info(f"Cleaned column names: {', '.join(chemical_data.columns)}")
    
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
    
    renamed_columns = {}
    for old_col, new_col in column_mapping.items():
        if old_col in chemical_data.columns:
            renamed_columns[old_col] = new_col
    
    df_clean = chemical_data.rename(columns=renamed_columns)
    logger.debug(f"Columns renamed: {', '.join(renamed_columns.keys())} -> {', '.join(renamed_columns.values())}")
    
    chemical_columns = [col for col in [
        'do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride'
    ] if col in df_clean.columns]
    
    df_clean = remove_empty_chemical_rows(df_clean, chemical_columns)
    
    if 'date' in df_clean.columns:
        df_clean.rename(columns={'date': 'Date'}, inplace=True)
    
    if 'Date' not in df_clean.columns:
        logger.warning("No 'Date' column found in the data")
        df_clean['Date'] = pd.to_datetime('today')  # Fallback for records missing a date.
    elif not pd.api.types.is_datetime64_dtype(df_clean['Date']):
        df_clean['Date'] = pd.to_datetime(df_clean['Date'])

    df_clean['Year'] = df_clean['Date'].dt.year
    df_clean['Month'] = df_clean['Date'].dt.month
    logger.debug("Date columns processed and time components extracted")

    df_clean = apply_bdl_conversions(df_clean)
 
    numeric_conversion_count = 0 
    for col in chemical_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            numeric_conversion_count += 1
    
    logger.debug(f"Converted {numeric_conversion_count} columns to numeric type")
    
    df_clean = validate_chemical_data(df_clean, remove_invalid=True)
        
    df_clean = calculate_soluble_nitrogen(df_clean)

    missing_values = df_clean.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Final dataframe contains {missing_values} missing values")

    save_processed_data(df_clean, 'chemical_data')

    logger.info(f"Data processing complete. Output dataframe has {len(df_clean)} rows and {len(df_clean.columns)} columns")
    return df_clean, KEY_PARAMETERS, get_reference_values()

def load_chemical_data_to_db(site_name=None):
    """
    Processes chemical data and loads the results into the database.
    
    This function orchestrates the entire chemical data pipeline, from processing
    the raw CSV data to inserting it into the database using a shared batch function.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        True if the data was loaded successfully, False otherwise.
    """
    try:
        logger.info("Starting chemical data pipeline...")
        
        df_clean, _, _ = process_chemical_data_from_csv(site_name)
        
        if df_clean.empty:
            logger.warning("No chemical data to load into database")
            return False
        
        stats = insert_chemical_data(
            df_clean, 
            data_source="cleaned_chemical_data.csv"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error in chemical data pipeline: {e}")
        return False
