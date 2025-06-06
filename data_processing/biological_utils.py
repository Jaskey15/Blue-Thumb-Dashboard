"""
Biological data utilities for the Blue Thumb Water Quality Dashboard.
Shared functions for processing fish and macroinvertebrate data.
"""

import pandas as pd
import numpy as np
from utils import setup_logging

# Set up logging
logger = setup_logging("biological_utils", category="processing")

def validate_collection_event_data(df, grouping_columns, required_columns=None):
    """
    Validate that DataFrame has required columns for collection event processing.
    
    Args:
        df: DataFrame with biological data
        grouping_columns: List of columns needed for grouping (e.g., ['site_name', 'sample_id'])
        required_columns: Additional required columns (default: None)
        
    Returns:
        bool: True if validation passes, raises ValueError if validation fails
    """
    if df.empty:
        raise ValueError("DataFrame is empty")
    
    # Check grouping columns
    missing_grouping = [col for col in grouping_columns if col not in df.columns]
    if missing_grouping:
        raise ValueError(f"Missing required grouping columns: {missing_grouping}")
    
    # Check additional required columns
    if required_columns:
        missing_required = [col for col in required_columns if col not in df.columns]
        if missing_required:
            raise ValueError(f"Missing required columns: {missing_required}")
    
    # Check for null values in grouping columns
    for col in grouping_columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            logger.warning(f"Found {null_count} null values in grouping column '{col}'")
    
    logger.debug(f"Data validation passed for {len(df)} rows")
    return True

def insert_collection_events(cursor, df, table_name, grouping_columns, column_mapping):
    """
    Insert biological collection events into the database.
    
    Args:
        cursor: Database cursor
        df: DataFrame with biological data
        table_name: Name of the collection events table ('fish_collection_events' or 'macro_collection_events')
        grouping_columns: List of columns to group by (e.g., ['site_name', 'sample_id'] for fish)
        column_mapping: Dictionary mapping database columns to DataFrame columns
                       Example: {'site_id': 'site_name', 'sample_id': 'sample_id', 'collection_date': 'collection_date'}
                       Note: 'site_id' will be looked up automatically from 'site_name'
        
    Returns:
        dict: Dictionary mapping grouping key to event_id
              - For fish: {sample_id: event_id}
              - For macro: {(sample_id, habitat): event_id}
    """
    try:
        # Validate input data
        validate_collection_event_data(df, grouping_columns)
        
        if df.empty:
            logger.warning(f"No data to insert into {table_name}")
            return {}
        
        # Track results
        event_id_map = {}
        events_inserted = 0
        events_skipped = 0
        
        # Get unique collection events based on grouping columns
        unique_events = df.drop_duplicates(subset=grouping_columns).copy()
        logger.info(f"Processing {len(unique_events)} unique events for {table_name}")
        
        # Process each unique event
        for _, event_row in unique_events.iterrows():
            try:
                # Get site_id (assumes site already exists in database)
                site_name = event_row['site_name']
                cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
                site_result = cursor.fetchone()
                
                if not site_result:
                    logger.error(f"Site '{site_name}' not found in database. Skipping event.")
                    events_skipped += 1
                    continue
                
                site_id = site_result[0]
                
                # Build the insert data
                insert_data = {'site_id': site_id}
                
                # Map other columns from DataFrame to database columns
                for db_column, df_column in column_mapping.items():
                    if db_column == 'site_id':
                        continue  # Already handled above
                    
                    if df_column in event_row:
                        insert_data[db_column] = event_row[df_column]
                    else:
                        logger.warning(f"Column '{df_column}' not found in data for {db_column}")
                
                # Build SQL insert statement
                columns = list(insert_data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                columns_str = ', '.join(columns)
                values = [insert_data[col] for col in columns]
                
                sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                
                # Execute insert
                cursor.execute(sql, values)
                event_id = cursor.lastrowid
                
                # Create the mapping key based on grouping strategy
                if len(grouping_columns) == 2 and 'sample_id' in grouping_columns:
                    # Fish case: key is just sample_id
                    mapping_key = event_row['sample_id']
                elif len(grouping_columns) == 3 and 'habitat' in grouping_columns:
                    # Macro case: key is tuple of (sample_id, habitat)
                    mapping_key = (event_row['sample_id'], event_row['habitat'])
                else:
                    # Fallback: use tuple of all grouping values
                    mapping_key = tuple(event_row[col] for col in grouping_columns)
                
                event_id_map[mapping_key] = event_id
                events_inserted += 1
                
            except Exception as e:
                logger.error(f"Error inserting event for site '{site_name}': {e}")
                events_skipped += 1
                continue
        
        logger.info(f"Collection events summary for {table_name}:")
        logger.info(f"  - Inserted: {events_inserted}")
        logger.info(f"  - Skipped: {events_skipped}")
        logger.info(f"  - Total event_id mappings: {len(event_id_map)}")
        
        return event_id_map
        
    except Exception as e:
        logger.error(f"Error in insert_collection_events for {table_name}: {e}")
        raise

def remove_invalid_biological_values(df, invalid_values=None, score_columns=None):
    """
    Remove rows with invalid biological values (sentinel values like -999, -99).
    
    Args:
        df: DataFrame with biological data
        invalid_values: List of values to treat as invalid (default: [-999, -99])
        score_columns: List of columns to check for invalid values (default: columns ending with '_score')
        
    Returns:
        DataFrame: DataFrame with invalid rows removed
    """
    if df.empty:
        return df
    
    if invalid_values is None:
        invalid_values = [-999, -99]
    
    if score_columns is None:
        # Default: find columns ending with '_score' plus 'comparison_to_reference'
        # Convert column names to strings to handle any integer column names
        score_columns = [col for col in df.columns if str(col).endswith('_score')]
        if 'comparison_to_reference' in df.columns:
            score_columns.append('comparison_to_reference')
    
    # Filter score columns to only those that exist
    existing_score_columns = [col for col in score_columns if col in df.columns]
    
    if not existing_score_columns:
        logger.warning("No score columns found for invalid value removal")
        return df
    
    # Create mask for invalid values
    invalid_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
    
    for col in existing_score_columns:
        for invalid_val in invalid_values:
            invalid_mask[col] = invalid_mask[col] | (df[col] == invalid_val)
    
    # Check if any row has invalid values
    rows_with_invalid = invalid_mask[existing_score_columns].any(axis=1)
    invalid_count = rows_with_invalid.sum()
    
    if invalid_count > 0:
        logger.info(f"Removing {invalid_count} rows with invalid values ({invalid_values})")
        df_clean = df[~rows_with_invalid].copy()
    else:
        logger.info("No invalid values found")
        df_clean = df.copy()
    
    return df_clean

def convert_columns_to_numeric(df, columns=None, errors='coerce'):
    """
    Convert specified columns to numeric type with error handling.
    
    Args:
        df: DataFrame to process
        columns: List of columns to convert (default: all columns except specified exclusions)
        errors: How to handle conversion errors ('coerce', 'raise', 'ignore')
        
    Returns:
        DataFrame: DataFrame with converted columns
    """
    logger.info("=== DEBUG: Starting convert_columns_to_numeric ===")
    logger.info(f"DEBUG: Input DataFrame shape: {df.shape}")
    logger.info(f"DEBUG: Input column names: {list(df.columns)}")
    logger.info(f"DEBUG: Input column types: {[type(col) for col in df.columns]}")
    
    if df.empty:
        return df
    
    df_converted = df.copy()
    conversion_count = 0
    
    # If no columns specified, convert likely numeric columns
    if columns is None:
        # Convert columns that look like they should be numeric
        numeric_patterns = ['_score', '_value', 'year', 'sample_id', 'comparison_to_reference']
        columns = []
        for col in df_converted.columns:
            logger.info(f"DEBUG: Checking column: {col} (type: {type(col)})")
            try:
                if any(pattern in str(col).lower() for pattern in numeric_patterns):
                    columns.append(col)
                    logger.info(f"DEBUG: Column {col} matches numeric pattern")
                else:
                    logger.info(f"DEBUG: Column {col} does not match any numeric pattern")
            except Exception as e:
                logger.error(f"DEBUG: Error checking column {col}: {e}")
    
    logger.info(f"DEBUG: Columns selected for conversion: {columns}")
    
    # Filter to existing columns
    existing_columns = [col for col in columns if col in df_converted.columns]
    logger.info(f"DEBUG: Existing columns for conversion: {existing_columns}")
    
    for col in existing_columns:
        try:
            logger.info(f"DEBUG: Converting column {col} (type: {type(col)})")
            original_dtype = df_converted[col].dtype
            df_converted[col] = pd.to_numeric(df_converted[col], errors=errors)
            
            if df_converted[col].dtype != original_dtype:
                conversion_count += 1
                logger.debug(f"Converted column '{col}' from {original_dtype} to {df_converted[col].dtype}")
        except Exception as e:
            logger.warning(f"Failed to convert column '{col}' to numeric: {e}")
    
    if conversion_count > 0:
        logger.info(f"Successfully converted {conversion_count} columns to numeric type")
    
    logger.info("=== DEBUG: Finished convert_columns_to_numeric ===")
    return df_converted