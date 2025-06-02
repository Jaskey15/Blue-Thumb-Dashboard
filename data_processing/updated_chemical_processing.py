import os
import sys
import pandas as pd
import numpy as np

# Add project root to path (following your existing pattern)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import utilities from data_loader and database (following your existing pattern)
from data_processing.data_loader import (
    load_csv_data, clean_column_names, 
    save_processed_data, get_unique_sites,
)
from database.database import get_connection, close_connection
from utils import setup_logging

# Set up logging
logger = setup_logging("updated_chemical_processing", category="processing")

def load_updated_chemical_data():
    """
    Load the updated chemical data CSV file.
    
    Returns:
        DataFrame: Raw data from the updated chemical CSV
    """
    try:
        # Get the file path - adjust this to match where your updated CSV is located
        base_dir = os.path.dirname(os.path.dirname(__file__))
        file_path = os.path.join(base_dir, 'data', 'raw', 'updated_chemical_data.csv')
        
        # Load the CSV without any date parsing initially
        df = pd.read_csv(file_path, encoding='cp1252') 
        
        logger.info(f"Successfully loaded {len(df)} rows from updated chemical data")
        logger.info(f"Columns found: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading updated chemical data: {e}")
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
    
# Add this after your existing functions

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
            
        # If both have values, return the greater (with tiebreaker)
        if val1 > val2:
            return val1
        elif val2 > val1:
            return val2
        else:  # They're equal
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
            mid_col1=mapping.get('mid_col1'),  # .get() handles missing keys
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
    
def calculate_soluble_nitrogen(df):
    """
    Calculate soluble nitrogen from processed Nitrate, Nitrite, and Ammonia values.
    Uses the same BDL (Below Detection Limit) logic as your existing processing.
    
    Args:
        df: DataFrame with processed nutrient columns
        
    Returns:
        DataFrame: DataFrame with soluble_nitrogen column added
    """
    try:
        # Define BDL values (same as your existing chemical_processing.py)
        BDL_VALUES = {
            'Nitrate': 0.3,    
            'Nitrite': 0.03,    
            'Ammonia': 0.03,
        }
        
        # Function to handle BDL replacement (same logic as existing)
        def convert_bdl_value(value, bdl_replacement):
            if pd.isna(value):
                return bdl_replacement  # Treat NaN as BDL for calculation
            if value == 0:
                return bdl_replacement  # Treat zeros as BDL
            return value
        
        # Apply BDL conversions for calculation
        nitrate_calc = df['Nitrate'].apply(lambda x: convert_bdl_value(x, BDL_VALUES['Nitrate']))
        nitrite_calc = df['Nitrite'].apply(lambda x: convert_bdl_value(x, BDL_VALUES['Nitrite']))
        ammonia_calc = df['Ammonia'].apply(lambda x: convert_bdl_value(x, BDL_VALUES['Ammonia']))
        
        # Calculate total soluble nitrogen
        df['soluble_nitrogen'] = nitrate_calc + nitrite_calc + ammonia_calc
        
        logger.info("Successfully calculated soluble_nitrogen from component values")
        return df
        
    except Exception as e:
        logger.error(f"Error calculating soluble_nitrogen: {e}")
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
        # Create a new dataframe with the required columns
        formatted_df = pd.DataFrame()
        
        # Map columns to match existing schema
        formatted_df['Site_Name'] = df['Site Name']  # Note: Site Name -> Site_Name
        formatted_df['Date'] = df['Date']
        formatted_df['Year'] = df['Year'] 
        formatted_df['Month'] = df['Month']
        
        # Map chemical parameters
        formatted_df['do_percent'] = df['% Oxygen Saturation']
        formatted_df['pH'] = df['pH #1']  # Using pH #1 as primary pH reading
        
        # Use our processed nutrient values
        formatted_df['Nitrate'] = df['Nitrate']
        formatted_df['Nitrite'] = df['Nitrite'] 
        formatted_df['Ammonia'] = df['Ammonia']
        formatted_df['Phosphorus'] = df['Orthophosphate']  # Map Orthophosphate -> Phosphorus
        formatted_df['Chloride'] = df['Chloride']
        
        # Add calculated soluble nitrogen
        formatted_df = calculate_soluble_nitrogen(formatted_df)
        
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

def remove_empty_chemical_rows(df):
    """
    Remove rows where all chemical parameters are null.
    Same logic as your existing chemical_processing.py
    
    Args:
        df: DataFrame with chemical data
        
    Returns:
        DataFrame: Filtered DataFrame
    """
    try:
        chemical_columns = ['do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 
                           'Phosphorus', 'Chloride', 'soluble_nitrogen']
        
        # Count non-null values in each row
        non_null_counts = df[chemical_columns].notnull().sum(axis=1)
        
        # Keep rows that have at least one chemical parameter
        df_filtered = df[non_null_counts > 0].copy()
        
        # Log how many rows were removed
        removed_count = len(df) - len(df_filtered)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} rows with no chemical data")
        
        return df_filtered
        
    except Exception as e:
        logger.error(f"Error removing empty chemical rows: {e}")
        return df

def validate_data_quality(df):
    """
    Basic validation to flag implausible values.
    Same logic as your existing chemical_processing.py
    
    Args:
        df: DataFrame with chemical data
        
    Returns:
        DataFrame: Validated DataFrame
    """
    try:
        chemical_columns = ['do_percent', 'pH', 'Nitrate', 'Nitrite', 'Ammonia', 
                           'Phosphorus', 'Chloride', 'soluble_nitrogen']
        
        for col in chemical_columns:
            if col in df.columns:
                # Check for negative values
                neg_values = (df[col] < 0).sum()
                if neg_values > 0:
                    logger.warning(f"Found {neg_values} negative values in {col}. These may indicate data quality issues.")
                
                # Check for extremely high values (basic sanity check)
                if col == 'pH':
                    extreme_values = ((df[col] < 0) | (df[col] > 14)).sum()
                    if extreme_values > 0:
                        logger.warning(f"Found {extreme_values} pH values outside 0-14 range.")
                elif col == 'do_percent':
                    extreme_values = (df[col] > 200).sum()  # Over 200% saturation seems extreme
                    if extreme_values > 0:
                        logger.warning(f"Found {extreme_values} DO values over 200% saturation.")
        
        return df
        
    except Exception as e:
        logger.error(f"Error validating data quality: {e}")
        return df

def process_updated_chemical_data_complete():
    """
    Complete processing pipeline for updated chemical data.
    
    Returns:
        DataFrame: Fully processed data ready for database insertion
    """
    try:
        logger.info("Starting complete processing of updated chemical data...")
        
        # Step 1: Load and parse dates
        df = load_updated_chemical_data()
        if df.empty:
            return pd.DataFrame()
        
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
        formatted_df = validate_data_quality(formatted_df)
        
        logger.info(f"Complete processing finished: {len(formatted_df)} rows ready for database")
        return formatted_df
        
    except Exception as e:
        logger.error(f"Error in complete processing pipeline: {e}")
        return pd.DataFrame()
    
def check_for_duplicates(df):
    """
    Check for duplicates against existing data in the database.
    Remove duplicates (prioritizing original data over updated data).
    
    Args:
        df: DataFrame with processed updated chemical data
        
    Returns:
        DataFrame: DataFrame with duplicates removed
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
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
            return df
        
        # Convert dates to same format for comparison
        existing_df['collection_date'] = pd.to_datetime(existing_df['collection_date']).dt.date
        df['date_for_comparison'] = df['Date'].dt.date
        
        # Create sets of (site_name, date) tuples for efficient comparison
        existing_combinations = set(zip(existing_df['site_name'], existing_df['collection_date']))
        
        # Check each row in our updated data for duplicates
        duplicate_mask = df.apply(
            lambda row: (row['Site_Name'], row['date_for_comparison']) in existing_combinations, 
            axis=1
        )
        
        # Count and log duplicates found
        duplicates_found = duplicate_mask.sum()
        total_records = len(df)
        
        if duplicates_found > 0:
            logger.info(f"Found {duplicates_found} duplicate records out of {total_records} total records")
            
            # Log some example duplicates for reference
            duplicate_examples = df[duplicate_mask][['Site_Name', 'Date']].head(5)
            logger.info("Example duplicate records (keeping original data):")
            for _, row in duplicate_examples.iterrows():
                logger.info(f"  - {row['Site_Name']} on {row['Date'].strftime('%Y-%m-%d')}")
            
            # Remove duplicates (keep original data, remove updated data)
            df_no_duplicates = df[~duplicate_mask].copy()
            
            logger.info(f"Removed {duplicates_found} duplicates. {len(df_no_duplicates)} records remaining for insertion.")
        else:
            logger.info("No duplicates found - all records are new")
            df_no_duplicates = df.copy()
        
        # Clean up the temporary comparison column
        df_no_duplicates = df_no_duplicates.drop(columns=['date_for_comparison'])
        
        return df_no_duplicates
        
    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        # If duplicate checking fails, return original data and let user decide
        logger.warning("Duplicate checking failed - returning all data. Manual review recommended.")
        return df

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
        processed_df = process_updated_chemical_data_complete()
        
        if processed_df.empty:
            logger.error("Failed to process updated chemical data")
            return False
        
        logger.info(f"Successfully processed {len(processed_df)} records")
        
        # Step 2: Check for and remove duplicates
        logger.info("Step 2: Checking for duplicates against existing database...")
        df_no_duplicates = check_for_duplicates(processed_df)
        
        if df_no_duplicates.empty:
            logger.info("No new records to insert after duplicate removal")
            return True
        
        # Step 3: Use existing database insertion function
        logger.info(f"Step 3: Inserting {len(df_no_duplicates)} new records into database...")
        
        # Import the existing function (we need to add this import at the top)
        from data_processing.chemical_processing import load_chemical_data_to_db
        
        # The existing function expects to process from CSV, but we can adapt it
        # We'll create a temporary approach using the core database logic
        success = insert_processed_chemical_data(df_no_duplicates)
        
        if success:
            logger.info("Successfully completed updated chemical data pipeline!")
            logger.info(f"Final summary:")
            logger.info(f"  - Processed: {len(processed_df)} total records")
            logger.info(f"  - Duplicates removed: {len(processed_df) - len(df_no_duplicates)}")
            logger.info(f"  - New records inserted: {len(df_no_duplicates)}")
            return True
        else:
            logger.error("Database insertion failed")
            return False
            
    except Exception as e:
        logger.error(f"Error in updated chemical data pipeline: {e}")
        return False

def insert_processed_chemical_data(df):
    """
    Insert processed chemical data directly into database.
    Uses the same logic as your existing chemical_processing.py but works with already-processed data.
    
    Args:
        df: DataFrame with processed chemical data (formatted to schema)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Import required functions from existing chemical processing
        from data_processing.chemical_processing import get_reference_values, determine_status
        
        # Get reference values for status determination
        reference_values = get_reference_values()
        
        # Track insertion counts
        sites_processed = set()
        samples_added = 0
        measurements_added = 0
        
        # Group by site and date for insertion
        for (site_name, date), group in df.groupby(['Site_Name', 'Date']):
            sites_processed.add(site_name)
            
            # Get site_id (create site if it doesn't exist)
            cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
            site_result = cursor.fetchone()
            
            if site_result:
                site_id = site_result[0]
            else:
                # Create new site (minimal info for now)
                cursor.execute("INSERT INTO sites (site_name) VALUES (?)", (site_name,))
                site_id = cursor.lastrowid
                logger.info(f"Created new site: {site_name}")
            
            # Process this date group (should only be one row per site per date)
            for _, row in group.iterrows():
                date_str = row['Date'].strftime('%Y-%m-%d')
                year = row['Year']
                month = row['Month']
                
                # Insert collection event
                cursor.execute("""
                INSERT INTO chemical_collection_events 
                (site_id, collection_date, year, month)
                VALUES (?, ?, ?, ?)
                """, (site_id, date_str, year, month))
                
                event_id = cursor.lastrowid
                samples_added += 1
                
                # Insert measurements for each parameter
                parameter_map = {
                    'do_percent': 1,
                    'pH': 2, 
                    'soluble_nitrogen': 3,
                    'Phosphorus': 4,
                    'Chloride': 5
                }
                
                for param_name, param_id in parameter_map.items():
                    if param_name in row and pd.notna(row[param_name]):
                        value = row[param_name]
                        
                        # Determine status using existing logic
                        status = determine_status(param_name, value, reference_values)
                        
                        # Insert measurement
                        cursor.execute("""
                        INSERT INTO chemical_measurements
                        (event_id, parameter_id, value, status)
                        VALUES (?, ?, ?, ?)
                        """, (event_id, param_id, value, status))
                        
                        measurements_added += 1
        
        conn.commit()
        close_connection(conn)
        
        logger.info(f"Successfully inserted data:")
        logger.info(f"  - Sites processed: {len(sites_processed)}")
        logger.info(f"  - Collection events added: {samples_added}")
        logger.info(f"  - Measurements added: {measurements_added}")
        
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
            close_connection(conn)
        logger.error(f"Error inserting processed chemical data: {e}")
        return False

# Update the test section at the bottom
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