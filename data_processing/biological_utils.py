"""
Shared utilities for validating, inserting, and cleaning biological data.
"""

import pandas as pd
from data_processing import setup_logging

# Configure logging
logger = setup_logging("biological_utils", category="processing")

def validate_collection_event_data(df, grouping_columns, required_columns=None):
    """
    Ensure data meets requirements for collection event processing.
    
    Priority checks:
    1. DataFrame has required grouping columns (e.g., site_name, sample_id)
    2. Required columns exist and contain valid data
    3. No null values in critical grouping columns
    """
    if df.empty:
        raise ValueError("DataFrame is empty")
    
    missing_grouping = [col for col in grouping_columns if col not in df.columns]
    if missing_grouping:
        raise ValueError(f"Missing required grouping columns: {missing_grouping}")
    
    if required_columns:
        missing_required = [col for col in required_columns if col not in df.columns]
        if missing_required:
            raise ValueError(f"Missing required columns: {missing_required}")
    
    for col in grouping_columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            logger.warning(f"Found {null_count} null values in grouping column '{col}'")
    
    logger.debug(f"Data validation passed for {len(df)} rows")
    return True

def insert_collection_events(cursor, df, table_name, grouping_columns, column_mapping):
    """
    Insert biological collection events with proper site relationships.
    
    Workflow:
    1. Validate input data structure
    2. Look up site_id for each event
    3. Map DataFrame columns to database schema
    4. Create event_id mapping for child records
    
    Returns dict mapping sample keys to event_ids:
    - Fish: {sample_id: event_id}
    - Macro: {(sample_id, habitat): event_id}
    """
    try:
        validate_collection_event_data(df, grouping_columns)
        
        if df.empty:
            logger.warning(f"No data to insert into {table_name}")
            return {}
        
        event_id_map = {}
        events_inserted = 0
        events_skipped = 0
        
        unique_events = df.drop_duplicates(subset=grouping_columns).copy()
        logger.info(f"Processing {len(unique_events)} unique events for {table_name}")
        
        for _, event_row in unique_events.iterrows():
            try:
                site_name = event_row['site_name']
                cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
                site_result = cursor.fetchone()
                
                if not site_result:
                    logger.error(f"Site '{site_name}' not found in database. Skipping event.")
                    events_skipped += 1
                    continue
                
                site_id = site_result[0]
                
                insert_data = {'site_id': site_id}
                
                for db_column, df_column in column_mapping.items():
                    if db_column == 'site_id':
                        continue  # Already handled
                    
                    if df_column in event_row:
                        insert_data[db_column] = event_row[df_column]
                    else:
                        logger.warning(f"Column '{df_column}' not found in data for {db_column}")
                
                columns = list(insert_data.keys())
                placeholders = ', '.join(['?' for _ in columns])
                columns_str = ', '.join(columns)
                values = [insert_data[col] for col in columns]
                
                sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                cursor.execute(sql, values)
                event_id = cursor.lastrowid
                
                # Create mapping key based on data type (fish vs. macroinvertebrate)
                if len(grouping_columns) == 2 and 'sample_id' in grouping_columns:
                    # Fish events are identified by a single sample_id
                    mapping_key = event_row['sample_id']
                elif len(grouping_columns) == 3 and 'habitat' in grouping_columns:
                    # Macroinvertebrate events are unique by sample_id and habitat
                    mapping_key = (event_row['sample_id'], event_row['habitat'])
                else:
                    # Fallback for other biological data types
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
    Remove rows containing known invalid sentinel values (-999, -99).
    
    Focuses on:
    1. Score columns (ending with '_score')
    2. Comparison to reference values
    3. Custom invalid value lists
    """
    if df.empty:
        return df
    
    if invalid_values is None:
        invalid_values = [-999, -99]
    
    if score_columns is None:
        # Auto-detect score columns if not provided
        score_columns = [col for col in df.columns if str(col).endswith('_score')]
        if 'comparison_to_reference' in df.columns:
            score_columns.append('comparison_to_reference')
    
    existing_score_columns = [col for col in score_columns if col in df.columns]
    
    if not existing_score_columns:
        logger.warning("No score columns found for invalid value removal")
        return df
    
    invalid_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
    
    for col in existing_score_columns:
        for invalid_val in invalid_values:
            invalid_mask[col] = invalid_mask[col] | (df[col] == invalid_val)
    
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
    Convert likely numeric columns to proper numeric type.
    
    Auto-detects numeric columns based on:
    - Score columns (_score)
    - Value columns (_value)
    - Year/sample ID fields
    - Comparison values
    """
    if df.empty:
        return df
    
    df_converted = df.copy()
    conversion_count = 0
    
    if columns is None:
        # Auto-detect numeric columns if none are specified
        numeric_patterns = ['_score', '_value', 'year', 'sample_id', 'comparison_to_reference']
        columns = []
        for col in df_converted.columns:
            try:
                if any(pattern in str(col).lower() for pattern in numeric_patterns):
                    columns.append(col)
            except Exception as e:
                logger.warning(f"Error checking column {col}: {e}")
    
    existing_columns = [col for col in columns if col in df_converted.columns]
    
    for col in existing_columns:
        try:
            original_dtype = df_converted[col].dtype
            df_converted[col] = pd.to_numeric(df_converted[col], errors=errors)
            
            if df_converted[col].dtype != original_dtype:
                conversion_count += 1
                logger.debug(f"Converted column '{col}' from {original_dtype} to {df_converted[col].dtype}")
        except Exception as e:
            logger.warning(f"Failed to convert column '{col}' to numeric: {e}")
    
    if conversion_count > 0:
        logger.info(f"Successfully converted {conversion_count} columns to numeric type")
    
    return df_converted