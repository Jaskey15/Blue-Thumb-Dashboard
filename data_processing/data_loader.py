import os
import pandas as pd
import logging

def setup_logging():
    """Configure logging to use the logs directory with component-specific log file."""
    # Get the base directory of the project
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Get the module name for the log file
    module_name = os.path.basename(__file__).replace('.py', '')
    log_file = os.path.join(logs_dir, f"{module_name}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Constants
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'processed')

# Make sure directories exist
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# File paths for each data source
DATA_FILES = {
    'site': os.path.join(RAW_DATA_DIR, 'site_data.csv'),
    'chemical': os.path.join(RAW_DATA_DIR, 'chemical_data.csv'),
    'fish': os.path.join(RAW_DATA_DIR, 'fish_data.csv'),
    'macro': os.path.join(RAW_DATA_DIR, 'macro_data.csv'),
    'habitat': os.path.join(RAW_DATA_DIR, 'habitat_data.csv')
}

def get_file_path(data_type, processed=False):
    """
    Get the path to a data file.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'fish', 'macro', 'habitat')
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

def load_csv_data(data_type, usecols=None, dtype=None, parse_dates=None):
    """
    Load data from a CSV file.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'fish', 'macro', 'habitat')
        usecols: List of columns to load (default: None, load all)
        dtype: Dictionary of column data types (default: None)
        parse_dates: List of columns to parse as dates (default: None)
    
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
            low_memory=False  # Avoid DtypeWarning for mixed types
        )
        
        logger.info(f"Successfully loaded {len(df)} rows from {data_type} data")
        return df
    
    except Exception as e:
        logger.error(f"Error loading {data_type} data: {e}")
        return pd.DataFrame()

def save_processed_data(df, data_type):
    """
    Save processed data to a CSV file.
    
    Args:
        df: DataFrame to save
        data_type: Type of data ('site', 'chemical', 'fish', 'macro', 'habitat')
    
    Returns:
        bool: True if saving was successful, False otherwise
    """
    if df.empty:
        logger.warning(f"No {data_type} data to save")
        return False
    
    file_path = get_file_path(data_type, processed=True)
    
    try:
        logger.info(f"Saving processed {data_type} data to {file_path}")
        df.to_csv(file_path, index=False)
        logger.info(f"Successfully saved {len(df)} rows of processed {data_type} data")
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
    
    # Filter the data
    filtered_df = df[df[site_column].str.strip() == site_name.strip()]
    
    if filtered_df.empty:
        logger.warning(f"No data found for site: {site_name}")
    else:
        logger.info(f"Found {len(filtered_df)} rows for site: {site_name}")
    
    return filtered_df

def get_unique_sites(data_type, site_column='sitename'):
    """
    Get a list of unique site names from a data file.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'fish', 'macro', 'habitat')
        site_column: Name of the column containing site names (default: 'sitename')
    
    Returns:
        list: List of unique site names
    """
    df = load_csv_data(data_type)
    
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

def get_date_range(data_type, date_column='date'):
    """
    Get the date range (min and max dates) for a data type.
    
    Args:
        data_type: Type of data ('site', 'chemical', 'fish', 'macro', 'habitat')
        date_column: Name of the column containing dates (default: 'date')
    
    Returns:
        tuple: (min_date, max_date) or (None, None) if no dates found
    """
    df = load_csv_data(data_type, parse_dates=[date_column])
    
    if df.empty:
        return None, None
    
    # Clean column names
    df = clean_column_names(df)
    
    # Check if the date column exists
    date_column = date_column.lower()
    if date_column not in df.columns:
        # Try to find a column with 'date' in the name
        date_columns = [col for col in df.columns if 'date' in col.lower()]
        if date_columns:
            date_column = date_columns[0]
        else:
            logger.error(f"No date column found in {data_type} data")
            return None, None
    
    # Parse dates if they weren't parsed during loading
    if not pd.api.types.is_datetime64_dtype(df[date_column]):
        try:
            df[date_column] = pd.to_datetime(df[date_column])
        except:
            logger.error(f"Could not parse dates in column: {date_column}")
            return None, None
    
    # Get min and max dates
    min_date = df[date_column].min()
    max_date = df[date_column].max()
    
    logger.info(f"Date range for {data_type} data: {min_date} to {max_date}")
    
    return min_date, max_date

if __name__ == "__main__":
    # Test the data loading functions
    print("Testing data loader:")
    
    for data_type in DATA_FILES.keys():
        file_path = get_file_path(data_type)
        if check_file_exists(file_path):
            print(f"✓ {data_type.capitalize()} data file found: {file_path}")
            
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