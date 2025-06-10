import os
import pandas as pd
from data_processing.data_loader import clean_column_names, save_processed_data
from data_processing.data_queries import get_sites_with_chemical_data, get_date_range_for_site
from data_processing.chemical_utils import (
    validate_chemical_data, apply_bdl_conversions, calculate_soluble_nitrogen,
    remove_empty_chemical_rows, KEY_PARAMETERS,
    insert_chemical_data, get_reference_values
)
from data_processing import setup_logging

# Configure Logging
logger = setup_logging("chemical_processing", category="processing")

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
            'data', 'interim', 'cleaned_chemical_data.csv'
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
    
    # Define chemical parameter columns for processing 
    chemical_columns = [col for col in [
        'do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride'
    ] if col in df_clean.columns]
    
    # Remove rows where all chemical parameters are null 
    df_clean = remove_empty_chemical_rows(df_clean, chemical_columns)
    
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

def load_chemical_data_to_db(site_name=None):
    """
    Process chemical data from CSV and load it into the database.
    Uses shared batch insertion logic.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Starting chemical data pipeline...")
        
        # Process the data from CSV
        df_clean, _, _ = process_chemical_data_from_csv(site_name)
        
        if df_clean.empty:
            logger.warning("No chemical data to load into database")
            return False
        
        # Use shared batch insertion function
        stats = insert_chemical_data(
            df_clean, 
            check_duplicates=True, 
            data_source="cleaned_chemical_data.csv"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error in chemical data pipeline: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing chemical data processing")
    
    # Get list of sites with chemical data
    sites = get_sites_with_chemical_data()
    if sites:
        logger.info(f"Found {len(sites)} sites with chemical data")
        
        # Process data for the first site as a test
        test_site = sites[0]
        logger.info(f"Processing data for test site: {test_site}")
        
        # Get data from database
        from data_processing.data_queries import get_chemical_data_from_db
        df_clean = get_chemical_data_from_db(test_site)
        
        if not df_clean.empty:
            logger.info(f"Successfully retrieved {len(df_clean)} records for {test_site}")
            
            # Test date range function
            min_date, max_date = get_date_range_for_site(test_site)
            if min_date and max_date:
                logger.info(f"Date range for {test_site}: {min_date} to {max_date}")
        else:
            logger.warning(f"No data found for test site: {test_site}")
    else:
        logger.error("No sites with chemical data found. Check database setup.")