import os
import sys
import pandas as pd

# Add project root to path 
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import utilities from data_loader and database 

# Import shared chemical utilities
from data_processing.chemical_utils import (
    validate_chemical_data, calculate_soluble_nitrogen, remove_empty_chemical_rows,
    insert_chemical_data, check_for_duplicates_against_db
)
from utils import setup_logging

# Set up logging
logger = setup_logging("updated_chemical_processing", category="processing")

# Nutrient column mappings
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

def load_updated_chemical_data():
    """
    Load the CLEANED updated chemical data CSV file.
    
    Returns:
        DataFrame: Raw data from the cleaned updated chemical CSV
    """
    try:
        cleaned_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'processed', 'cleaned_updated_chemical_data.csv'
        )
        
        if not os.path.exists(cleaned_file_path):
            logger.error("cleaned_updated_chemical_data.csv not found. Run CSV cleaning first.")
            return pd.DataFrame()
        
        # Load the CSV 
        df = pd.read_csv(cleaned_file_path, low_memory=False) 
        
        logger.info(f"Successfully loaded {len(df)} rows from cleaned updated chemical data")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading cleaned updated chemical data: {e}")
        return pd.DataFrame()

def parse_sampling_dates(df):
    """
    Parse the sampling date column that contains both date and time.
    Extract just the date portion for consistency with existing data.
    
    Args:
        df: DataFrame with 'Sampling Date' column
        
    Returns:
        DataFrame: DataFrame with parsed 'Date' column
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

def get_greater_value(row, col1, col2, tiebreaker='col1'):
    """
    Get the greater value between two columns, with tiebreaker logic.
    
    Args:
        row: Pandas Series (row of DataFrame)
        col1: Name of first column to compare
        col2: Name of second column to compare  
        tiebreaker: Which column to prefer if values are equal ('col1' or 'col2')
        
    Returns:
        float: The greater value, or None if both are null/invalid
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

def get_conditional_nutrient_value(row, range_selection_col, low_col1, low_col2, mid_col1=None, mid_col2=None, high_col1=None, high_col2=None):
    """
    Get nutrient value based on range selection with conditional logic.
    
    Args:
        row: Pandas Series (row of DataFrame)
        range_selection_col: Column name that determines which range to use
        low_col1, low_col2: Column names for low range readings
        mid_col1, mid_col2: Column names for mid range readings (optional)
        high_col1, high_col2: Column names for high range readings (optional)
        
    Returns:
        float: The selected nutrient value, or None if no valid reading
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

def process_conditional_nutrient(df, nutrient_name):
    """
    Process any conditional nutrient using the mapping dictionary.
    
    Args:
        df: DataFrame with nutrient columns
        nutrient_name: Name of nutrient in NUTRIENT_COLUMN_MAPPINGS
        
    Returns:
        Series: Processed nutrient values
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

def process_simple_nutrients(df):
    """
    Process nutrients that use simple "greater of two" logic.
    
    Args:
        df: DataFrame with nutrient columns
        
    Returns:
        DataFrame: DataFrame with processed Nitrate and Nitrite columns
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

def format_to_database_schema(df):
    """
    Format the processed data to match the existing database schema.
    
    Args:
        df: DataFrame with processed nutrient data
        
    Returns:
        DataFrame: DataFrame formatted for database insertion
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
        
        # Add calculated soluble nitrogen using shared utility
        formatted_df = calculate_soluble_nitrogen(formatted_df)
        
        # Select only the columns we need for the database
        required_columns = ['Site_Name', 'Date', 'Year', 'Month', 'do_percent', 'pH', 
                           'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride', 
                           'soluble_nitrogen']
        
        formatted_df = formatted_df[required_columns]
        
        # Convert numeric columns to proper types
        numeric_columns = ['do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 
                          'Phosphorus', 'Chloride', 'soluble_nitrogen']
        
        for col in numeric_columns:
            formatted_df[col] = pd.to_numeric(formatted_df[col], errors='coerce')
        
        logger.info(f"Successfully formatted {len(formatted_df)} rows to database schema")
        logger.info(f"Final columns: {list(formatted_df.columns)}")
        
        return formatted_df
        
    except Exception as e:
        logger.error(f"Error formatting data to database schema: {e}")
        return pd.DataFrame()

def process_updated_chemical_data():
    """
    Complete processing pipeline for updated chemical data.
    
    Returns:
        DataFrame: Fully processed data ready for database insertion
    """
    try:
        logger.info("Starting complete processing of updated chemical data...")
        
        # Load and parse dates
        df = load_updated_chemical_data()
        if df.empty:
            return pd.DataFrame()
        
        df = parse_sampling_dates(df)
        
        # Process all nutrients
        df = process_simple_nutrients(df)  # Nitrate, Nitrite
        df['Ammonia'] = process_conditional_nutrient(df, 'ammonia')
        df['Orthophosphate'] = process_conditional_nutrient(df, 'orthophosphate') 
        df['Chloride'] = process_conditional_nutrient(df, 'chloride')
        
        # Format to database schema
        formatted_df = format_to_database_schema(df)
        
        # Clean and validate 
        formatted_df = remove_empty_chemical_rows(formatted_df)
        formatted_df = validate_chemical_data(formatted_df, remove_invalid=True)
        
        logger.info(f"Complete processing finished: {len(formatted_df)} rows ready for database")
        return formatted_df
        
    except Exception as e:
        logger.error(f"Error in complete processing pipeline: {e}")
        return pd.DataFrame()

def load_updated_chemical_data_to_db():
    """
    Complete pipeline: process updated chemical data and load into database.
    Handles duplicate checking and uses existing database insertion logic.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Starting complete pipeline for updated chemical data...")
        
        # Step 1: Process the updated chemical data
        logger.info("Step 1: Processing updated chemical data...")
        processed_df = process_updated_chemical_data()
        
        if processed_df.empty:
            logger.error("Failed to process updated chemical data")
            return False
        
        logger.info(f"Successfully processed {len(processed_df)} records")
        
        # Step 2: Check for and remove duplicates 
        logger.info("Step 2: Checking for duplicates against existing database...")
        df_no_duplicates, duplicate_count, duplicate_info = check_for_duplicates_against_db(
            processed_df, prioritize_existing=True
        )
        
        if df_no_duplicates.empty:
            logger.info("No new records to insert after duplicate removal")
            return True
        
        # Step 3: Use batch insertion function
        logger.info(f"Step 3: Inserting {len(df_no_duplicates)} new records into database...")
        
        stats = insert_chemical_data(
            df_no_duplicates,
            check_duplicates=False, 
            data_source="cleaned_updated_chemical_data.csv"
        )
        
        logger.info("Successfully completed updated chemical data pipeline!")
        logger.info(f"Final summary:")
        logger.info(f"  - Processed: {len(processed_df)} total records")
        logger.info(f"  - Duplicates removed: {duplicate_count}")
        logger.info(f"  - New records inserted: {stats['measurements_added']}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error in updated chemical data pipeline: {e}")
        return False
    
# Test section if run directly
if __name__ == "__main__":
    logger.info("Testing complete updated chemical data pipeline with database insertion...")
    
    # Test the complete pipeline including database insertion
    success = load_updated_chemical_data_to_db()
    
    if success:
        print("\n🎉 SUCCESS! Updated chemical data pipeline completed successfully!")
        print("Check the logs above for detailed information about:")
        print("  - Number of records processed")
        print("  - Duplicates found and removed") 
        print("  - New records inserted into database")
    else:
        print("\n❌ FAILED! Check the logs above for error details.")