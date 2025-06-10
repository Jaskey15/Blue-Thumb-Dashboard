"""
fish_processing.py - Fish Community Data Processing

This module processes fish community assessment data with advanced replicate handling for 
Blue Thumb monitoring. Distinguishes between true replicates (separate collection events) 
and duplicate data entries, using BT field work records to assign correct collection dates.

Key Functions:
- load_fish_data(): Main pipeline to process and load fish data
- process_fish_csv_data(): Process fish data with NEW replicate handling
- categorize_and_process_duplicates(): Distinguish replicates from duplicates using BT data
- validate_ibi_scores(): Validate Index of Biotic Integrity calculations
- get_fish_dataframe(): Query fish data from database

Replicate Logic:
- Uses BT_fish_collection_dates.csv to identify true REP collections
- Assigns correct dates to replicate samples (original vs REP date)
- Averages duplicate entries that are not true replicates
- Supports ±1 year buffer for matching BT field work data

Fish Metrics:
- 7 IBI metrics: species counts, tolerances, feeding guilds, spawning types
- Integrity classes: Excellent, Good, Fair, Poor, Very Poor

Usage:
- Run directly to test fish data processing  
- Import functions for use in the main data pipeline
"""

import pandas as pd
import sqlite3
import difflib
import os
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data, clean_site_name
from data_processing.biological_utils import (
    insert_collection_events,
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from data_processing import setup_logging

logger = setup_logging("fish_processing", category="processing")

def load_bt_field_work_dates():
    """
    Load and process BT field work dates for fish collection validation.
    
    Returns:
        DataFrame with cleaned BT field work data
    """
    try:
        # Try multiple possible paths
        possible_paths = [
            'data/raw/BT_fish_collection_dates.csv',
            os.path.join('data', 'raw', 'BT_fish_collection_dates.csv'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw', 'BT_fish_collection_dates.csv')
        ]
        
        bt_path = None
        for path in possible_paths:
            if os.path.exists(path):
                bt_path = path
                break
        
        if not bt_path:
            logger.info("BT_fish_collection_dates.csv not found - skipping BT validation")
            return pd.DataFrame()
        
        bt_df = pd.read_csv(bt_path)
        logger.info(f"Loaded {len(bt_df)} BT field work records for date validation")
        
        # Clean and process the data
        bt_df['Date_Clean'] = pd.to_datetime(bt_df['Date'], errors='coerce')
        bt_df = bt_df.dropna(subset=['Date_Clean'])
        
        # Clean site names using same function as rest of pipeline
        bt_df['Site_Clean'] = bt_df['Name'].apply(clean_site_name)
        
        # Add year for matching
        bt_df['Year'] = bt_df['Date_Clean'].dt.year
        
        # Identify REP collections
        bt_df['Is_REP'] = bt_df['M/F/H'].astype(str).str.lower().str.contains('rep', na=False)
        
        logger.info(f"Processed {len(bt_df)} valid BT field work records")
        logger.info(f"REP collections found: {bt_df['Is_REP'].sum()}")
        return bt_df
        
    except Exception as e:
        logger.warning(f"Could not load BT field work dates: {e}")
        return pd.DataFrame()

def find_bt_site_match(db_site_name, bt_sites, threshold=0.9):
    """
    Find the best matching BT site name for a database site name.
    
    Args:
        db_site_name: Site name from database
        bt_sites: Set of cleaned BT site names
        threshold: Similarity threshold for fuzzy matching
        
    Returns:
        Best matching BT site name or None if no good match
    """
    # Try exact match first
    if db_site_name in bt_sites:
        return db_site_name
    
    # Try fuzzy matching
    best_match = None
    best_score = 0
    
    for bt_site in bt_sites:
        score = difflib.SequenceMatcher(None, db_site_name.lower(), bt_site.lower()).ratio()
        if score > threshold and score > best_score:
            best_score = score
            best_match = bt_site
    
    if best_match:
        logger.debug(f"Fuzzy match ({best_score:.3f}): '{db_site_name}' → '{best_match}'")
        return best_match
    else:
        return None

def categorize_and_process_duplicates(fish_df, bt_df):
    """
    Categorize duplicates as replicates vs true duplicates and process accordingly.
    
    Args:
        fish_df: DataFrame with fish data
        bt_df: DataFrame with BT field work data
        
    Returns:
        DataFrame with replicates assigned correct dates and duplicates averaged
    """
    if bt_df.empty:
        logger.info("No BT field work data available - averaging all duplicates")
        return average_all_duplicates(fish_df)
    
    fish_processed = fish_df.copy()
    bt_sites = set(bt_df['Site_Clean'].unique())
    
    # Track processing decisions
    rep_groups_processed = 0
    duplicate_groups_averaged = 0
    date_assignments = []
    
    logger.info(f"Starting duplicate categorization for {len(fish_processed)} fish records")
    
    # Find all groups with multiple samples
    duplicate_groups = fish_df.groupby(['site_name', 'year']).filter(lambda x: len(x) > 1)
    
    if duplicate_groups.empty:
        logger.info("No duplicate groups found")
        return fish_processed
    
    unique_duplicate_groups = duplicate_groups.groupby(['site_name', 'year']).size().reset_index()
    unique_duplicate_groups.columns = ['site_name', 'year', 'sample_count']
    
    logger.info(f"Found {len(unique_duplicate_groups)} site/year groups with multiple samples")
    
    # Process each duplicate group
    records_to_remove = []
    records_to_add = []
    
    for _, group_info in unique_duplicate_groups.iterrows():
        site_name = group_info['site_name']
        year = group_info['year']
        sample_count = group_info['sample_count']
        
        # Get the actual fish samples for this group
        group_samples = fish_df[
            (fish_df['site_name'] == site_name) & 
            (fish_df['year'] == year)
        ].copy()
        
        # Check for REP data with ±1 year buffer
        bt_site_match = find_bt_site_match(site_name, bt_sites)
        rep_data = None
        year_used = None
        
        if bt_site_match:
            # Check for REP data in target year ±1
            for check_year in [year, year-1, year+1]:
                potential_rep = bt_df[
                    (bt_df['Site_Clean'] == bt_site_match) & 
                    (bt_df['Year'] == check_year) &
                    (bt_df['Is_REP'] == True)
                ]
                
                if not potential_rep.empty:
                    # Also need the original (non-REP) collection for this site/year
                    original_collection = bt_df[
                        (bt_df['Site_Clean'] == bt_site_match) & 
                        (bt_df['Year'] == check_year) &
                        (bt_df['Is_REP'] == False)
                    ]
                    
                    if not original_collection.empty:
                        rep_data = pd.concat([original_collection, potential_rep])
                        year_used = check_year
                        break
        
        # Process based on whether we found REP data
        if rep_data is not None and len(rep_data) >= 2:
            # REPLICATE GROUP: Assign BT dates
            logger.info(f"Processing replicate group: {site_name} ({year}) with {sample_count} samples")
            
            if year_used != year:
                logger.info(f"  Using ±1 year buffer: BT data from {year_used}, fish data from {year}")
            
            # Sort BT data by date to get original and REP dates
            rep_data_sorted = rep_data.sort_values('Date_Clean')
            original_date = rep_data_sorted.iloc[0]['Date_Clean']
            rep_date = rep_data_sorted.iloc[1]['Date_Clean']
            
            # Sort fish samples to get consistent assignment
            group_samples_sorted = group_samples.sort_values('sample_id')
            
            # Assign dates (first sample gets earlier date, second gets later date)
            for i, (idx, sample) in enumerate(group_samples_sorted.iterrows()):
                if i == 0:
                    # First sample gets original date
                    fish_processed.at[idx, 'collection_date'] = original_date
                    fish_processed.at[idx, 'collection_date_str'] = original_date.strftime('%Y-%m-%d')
                    fish_processed.at[idx, 'year'] = original_date.year
                    assignment_type = "Original"
                elif i == 1:
                    # Second sample gets REP date
                    fish_processed.at[idx, 'collection_date'] = rep_date
                    fish_processed.at[idx, 'collection_date_str'] = rep_date.strftime('%Y-%m-%d')
                    fish_processed.at[idx, 'year'] = rep_date.year
                    assignment_type = "REP"
                else:
                    # Additional samples (shouldn't happen based on our analysis, but handle gracefully)
                    logger.warning(f"More than 2 samples found for replicate group {site_name} ({year})")
                    assignment_type = f"Extra_{i}"
                
                # Log the assignment
                date_assignments.append({
                    'site_name': site_name,
                    'original_year': year,
                    'bt_year_used': year_used,
                    'sample_id': sample['sample_id'],
                    'assignment_type': assignment_type,
                    'assigned_date': fish_processed.at[idx, 'collection_date_str'],
                    'year_buffer_used': year_used != year
                })
            
            rep_groups_processed += 1
            
        else:
            # DUPLICATE GROUP: Average scores
            logger.info(f"Averaging duplicate group: {site_name} ({year}) - no REP data found")
            
            # Calculate averaged record
            averaged_record = average_group_samples(group_samples)
            
            # Mark original records for removal
            for idx in group_samples.index:
                records_to_remove.append(idx)
            
            # Add averaged record
            records_to_add.append(averaged_record)
            duplicate_groups_averaged += 1
    
    # Apply removals and additions for averaged groups
    if records_to_remove:
        fish_processed = fish_processed.drop(records_to_remove)
    
    if records_to_add:
        fish_processed = pd.concat([fish_processed, pd.DataFrame(records_to_add)], ignore_index=True)
    
    # Log summary
    logger.info(f"Duplicate processing complete:")
    logger.info(f"  - Replicate groups processed: {rep_groups_processed}")
    logger.info(f"  - Duplicate groups averaged: {duplicate_groups_averaged}")
    logger.info(f"  - Total date assignments logged: {len(date_assignments)}")
    
    # Log date assignments for audit
    if date_assignments:
        logger.info(f"Date assignment details:")
        for assignment in date_assignments:
            buffer_note = " (±1 year buffer)" if assignment['year_buffer_used'] else ""
            logger.info(f"  {assignment['site_name']} Sample {assignment['sample_id']}: "
                       f"{assignment['assignment_type']} → {assignment['assigned_date']}{buffer_note}")
    
    logger.info(f"Final record count: {len(fish_processed)} (started with {len(fish_df)})")
    return fish_processed

def average_all_duplicates(fish_df):
    """
    FALLBACK FUNCTION: Average all duplicate records (original behavior).
    Used when no BT data is available.
    """
    if fish_df.empty:
        logger.info("No fish data to process")
        return fish_df
    
    # Find duplicate groups (same site and year)
    duplicate_groups = fish_df.groupby(['site_name', 'year']).filter(lambda x: len(x) > 1)
    
    if duplicate_groups.empty:
        logger.info("No duplicate records found")
        return fish_df
    
    logger.info(f"Found {len(duplicate_groups)} records that are duplicates")
    
    # Get unique records (not duplicates)
    unique_records = fish_df.groupby(['site_name', 'year']).filter(lambda x: len(x) == 1)
    
    # Process each duplicate group
    averaged_records = []
    
    for (site_name, year), group in duplicate_groups.groupby(['site_name', 'year']):
        logger.debug(f"Averaging {len(group)} records for {site_name} ({year})")
        averaged_record = average_group_samples(group)
        averaged_records.append(averaged_record)
    
    # Combine unique records with averaged duplicates
    if averaged_records:
        averaged_df = pd.DataFrame(averaged_records)
        result_df = pd.concat([unique_records, averaged_df], ignore_index=True)
    else:
        result_df = unique_records
    
    logger.info(f"Duplicate averaging complete: {len(fish_df)} → {len(result_df)} records")
    return result_df

def average_group_samples(group):
    """
    HELPER FUNCTION: Average a group of fish samples.
    """
    # Average the comparison_to_reference values
    comparison_values = group['comparison_to_reference'].dropna().tolist()
    if comparison_values:
        avg_comparison = sum(comparison_values) / len(comparison_values)
    else:
        avg_comparison = None
    
    # Use the first record as the base and update key values
    averaged_row = group.iloc[0].copy()
    averaged_row['comparison_to_reference'] = avg_comparison
    
    # Set individual metric scores to NULL since averaging 1,3,5 scale scores doesn't make sense
    score_columns = [col for col in averaged_row.index if 'score' in str(col).lower() and col != 'comparison_to_reference']
    for col in score_columns:
        averaged_row[col] = None
    
    return averaged_row

def load_fish_data(site_name=None):
    """
    Load fish data from CSV into the database.
    
    Args:
        site_name: Optional site name to filter data for (default: None, loads all sites)
    
    Returns:
        DataFrame with processed fish data
    """
    conn = get_connection()
    cursor = conn.cursor()
  
    try:
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM fish_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Load fish data from CSV
            fish_df = process_fish_csv_data(site_name)
            
            if fish_df.empty:
                logger.warning("No fish data found for processing.")
                return pd.DataFrame()
                
            # Insert collection events using shared utility
            event_id_map = insert_fish_collection_events(cursor, fish_df)
            
            # Insert metrics and summary scores
            insert_metrics_data(cursor, fish_df, event_id_map)
            
            conn.commit()
            logger.info("Fish data loaded successfully")
        else:
            logger.info("Fish data already exists in the database - skipping processing")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"SQLite error: {e}")
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading fish data: {e}")
        raise
    finally:
        close_connection(conn)

    # Always return current data state
    if site_name:
        return get_fish_dataframe(site_name)
    else:
        return get_fish_dataframe()

def process_fish_csv_data(site_name=None):
    """
    Process fish data from cleaned CSV file with NEW replicate handling.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with processed fish data
    """
    try:
        logger.info("Starting fish data processing with NEW replicate handling")
        
        # Load raw fish data from CLEANED CSV
        fish_df = load_csv_data('fish', parse_dates=['Date'])
        
        if fish_df.empty:
            logger.error("Failed to load fish data from cleaned CSV.")
            return pd.DataFrame()
        
        # Clean column names
        fish_df = clean_column_names(fish_df)
        
        # Map to standardized column names
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'date': 'collection_date',
            'year': 'year',
            'totalspecies': 'total_species',
            'sensitivebenthic': 'sensitive_benthic_species',
            'sunfishspecies': 'sunfish_species',
            'intolerantspecies': 'intolerant_species',
            'percenttolerant': 'proportion_tolerant',
            'percentinsectivore': 'proportion_insectivorous',
            'percentlithophil': 'proportion_lithophilic',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'sunfishspeciesibi': 'sunfish_species_score',
            'intolerantspeciesibi': 'intolerant_species_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score',
            'percentreference': 'comparison_to_reference',
            'fishscore': 'integrity_class'
        }
        
        # Apply column mapping
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in fish_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        fish_df = fish_df.rename(columns=valid_mapping)
        
        # Filter by site name if provided
        if site_name:
            fish_df = fish_df[fish_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(fish_df)} rows for site: {site_name}")
        
        # Handle date formatting
        if 'collection_date' in fish_df.columns:
            try:
                fish_df['collection_date'] = pd.to_datetime(fish_df['collection_date'])
                fish_df['collection_date_str'] = fish_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # NEW: Load BT field work dates and process duplicates
        bt_df = load_bt_field_work_dates()
        fish_df = categorize_and_process_duplicates(fish_df, bt_df)
        
        # Continue with standard processing
        fish_df = remove_invalid_biological_values(fish_df, invalid_values=[-999, -99])
        fish_df = convert_columns_to_numeric(fish_df)
        fish_df = validate_ibi_scores(fish_df)
        
        save_processed_data(fish_df, 'fish_data')

        logger.info(f"Fish processing complete: {len(fish_df)} final records")
        return fish_df
        
    except Exception as e:
        logger.error(f"Error processing fish CSV data: {e}")
        return pd.DataFrame()

def validate_ibi_scores(fish_df):
    """
    Validate that total_score equals the sum of IBI component scores.
    
    Args:
        fish_df: DataFrame with fish metrics data
    
    Returns:
        DataFrame with validated data
    """
    try:
        df = fish_df.copy()
        
        # Calculate sum of component scores
        score_columns = ['total_species_score', 'sensitive_benthic_score', 
                         'sunfish_species_score', 'intolerant_species_score',
                         'tolerant_score', 'insectivorous_score', 
                         'lithophilic_score']
        
        # Check which columns exist
        existing_columns = [col for col in score_columns if col in df.columns]
        
        if len(existing_columns) < len(score_columns):
            missing = set(score_columns) - set(existing_columns)
            logger.warning(f"Missing some IBI component columns: {missing}")
        
        if existing_columns and 'total_score' in df.columns:
            df['calculated_score'] = df[existing_columns].sum(axis=1)
            
            # Find mismatches
            mismatch_mask = df['calculated_score'] != df['total_score']
            mismatches = df[mismatch_mask]
            
            if not mismatches.empty:
                logger.warning(f"Found {len(mismatches)} records where total_score doesn't match sum of components.")
                df['score_validated'] = ~mismatch_mask
            else:
                logger.info("All total_score values match sum of components.")
                df['score_validated'] = True
            
            # Drop the calculated column
            df = df.drop(columns=['calculated_score'])
        
        return df
    
    except Exception as e:
        logger.error(f"Error validating IBI scores: {e}")
        return fish_df

def insert_fish_collection_events(cursor, fish_df):
    """
    Insert fish collection events using the shared biological utility.
    
    Args:
        cursor: Database cursor
        fish_df: DataFrame with fish data
    
    Returns:
        dict: Dictionary mapping sample_id to event_id
    """
    try:
        # Define parameters for fish collection events
        table_name = 'fish_collection_events'
        grouping_columns = ['site_name', 'sample_id']
        column_mapping = {
            'site_id': 'site_name',  # Will be looked up automatically
            'sample_id': 'sample_id',
            'collection_date': 'collection_date_str',
            'year': 'year'
        }
        
        # Use shared utility function
        event_id_map = insert_collection_events(
            cursor=cursor,
            df=fish_df,
            table_name=table_name,
            grouping_columns=grouping_columns,
            column_mapping=column_mapping
        )
        
        return event_id_map
        
    except Exception as e:
        logger.error(f"Error inserting fish collection events: {e}")
        return {}

def insert_metrics_data(cursor, fish_df, event_id_map):
    """
    Insert fish metrics and summary scores into the database.
    
    Args:
        cursor: Database cursor
        fish_df: DataFrame with fish data
        event_id_map: Dictionary mapping sample_id to event_id
    
    Returns:
        int: Number of metrics records inserted
    """
    try:
        # Define metric mappings
        metric_mappings = [
            ('Total No. of species', 'total_species', 'total_species_score'),
            ('No. of sensitive benthic species', 'sensitive_benthic_species', 'sensitive_benthic_score'),
            ('No. of sunfish species', 'sunfish_species', 'sunfish_species_score'),
            ('No. of intolerant species', 'intolerant_species', 'intolerant_species_score'),
            ('Proportion tolerant individuals', 'proportion_tolerant', 'tolerant_score'),
            ('Proportion insectivorous cyprinid', 'proportion_insectivorous', 'insectivorous_score'),
            ('Proportion lithophilic spawners', 'proportion_lithophilic', 'lithophilic_score')
        ]
        
        # Track counts
        metrics_count = 0
        summary_count = 0
        
        # Check which metrics are available
        available_metrics = []
        for metric_name, raw_col, score_col in metric_mappings:
            if raw_col in fish_df.columns and score_col in fish_df.columns:
                available_metrics.append((metric_name, raw_col, score_col))
        
        if not available_metrics:
            logger.error("No metric data available in CSV")
            return 0
            
        # For each unique sample, insert metrics and summary
        for sample_id, sample_df in fish_df.groupby('sample_id'):
            # Skip if no sample_id or not in event_id_map
            if pd.isna(sample_id) or sample_id not in event_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No event_id found for sample_id={sample_id}")
                continue
                
            event_id = event_id_map[sample_id]
            
            # Clear existing data for this event (to handle updates)
            cursor.execute('DELETE FROM fish_metrics WHERE event_id = ?', (event_id,))
            cursor.execute('DELETE FROM fish_summary_scores WHERE event_id = ?', (event_id,))
            
            # Get the data (first row in case of duplicates)
            row = sample_df.iloc[0]
            
            # Insert metrics for this event (only if scores are not None)
            for metric_name, raw_col, score_col in available_metrics:
                if pd.notna(row.get(raw_col)) and pd.notna(row.get(score_col)):
                    # For proportion metrics, use raw value as result
                    metric_result = row[raw_col] if metric_name.startswith('Proportion') else None
                    
                    cursor.execute('''
                        INSERT INTO fish_metrics 
                        (event_id, metric_name, raw_value, metric_result, metric_score)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        event_id,
                        metric_name,
                        row[raw_col],
                        metric_result,
                        row[score_col]
                    ))
                    metrics_count += 1
            
            # Determine integrity class - use CSV value first, calculate as fallback
            integrity_class = "Unknown"

            # Primary: Use pre-calculated integrity_class from CSV
            if 'integrity_class' in row and pd.notna(row['integrity_class']) and str(row['integrity_class']).strip():
                integrity_class = str(row['integrity_class']).strip()
            else:
                # Fallback: Calculate using simplified cutoffs
                if 'comparison_to_reference' in row and pd.notna(row['comparison_to_reference']):
                    comparison_value = float(row['comparison_to_reference']) * 100  # Convert to percentage
                    
                    if comparison_value >= 97:
                        integrity_class = "Excellent"
                    elif comparison_value >= 76:
                        integrity_class = "Good"
                    elif comparison_value >= 60:
                        integrity_class = "Fair"
                    elif comparison_value >= 47:
                        integrity_class = "Poor"
                    else:
                        integrity_class = "Very Poor"

            # Validate the integrity class value
            valid_classes = ["Excellent", "Good", "Fair", "Poor", "Very Poor"]
            if integrity_class not in valid_classes:
                logger.warning(f"Invalid integrity_class '{integrity_class}' for sample_id={sample_id}, setting to Unknown")
                integrity_class = "Unknown"

            # Insert summary score
            if all(col in row for col in ['total_score', 'comparison_to_reference']) and integrity_class != "Unknown":
                cursor.execute('''
                    INSERT INTO fish_summary_scores
                    (event_id, total_score, comparison_to_reference, integrity_class)
                    VALUES (?, ?, ?, ?)
                ''', (
                    event_id,
                    row['total_score'],
                    row['comparison_to_reference'],
                    integrity_class
                ))
                summary_count += 1
            else:
                logger.warning(f"Missing required columns for summary scores for sample_id={sample_id}")
        
        logger.info(f"Inserted {metrics_count} fish metrics and {summary_count} summary records")
        return metrics_count
        
    except Exception as e:
        logger.error(f"Error inserting metrics data: {e}")
        return 0

def get_fish_dataframe(site_name=None):
    """
    Query to get fish data with summary scores.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with fish data
    """
    conn = None
    try:
        conn = get_connection()
        
        # Base query
        fish_query = '''
        SELECT 
            e.event_id,
            s.site_name,
            e.year,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        JOIN 
            sites s ON e.site_id = s.site_id
        '''
        
        # Add filter for site if provided
        params = []
        if site_name:
            fish_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Add ordering
        fish_query += " ORDER BY e.year"
        
        # Execute query
        fish_df = pd.read_sql_query(fish_query, conn, params=params)
        
        if fish_df.empty:
            if site_name:
                logger.warning(f"No fish data found for site: {site_name}")
            else:
                logger.warning("No fish data found in the database")
        else: 
            logger.info(f"Retrieved {len(fish_df)} fish collection records")
    
        return fish_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_fish_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving fish data: {e}")
        return pd.DataFrame({'error': ['Error retrieving fish data']})
    finally:
        if conn:
            close_connection(conn)

def get_fish_metrics_data_for_table(site_name=None):
    """
    Query the database to get detailed fish metrics data for the metrics table display.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Tuple of (metrics_df, summary_df) for display
    """
    conn = None
    try:
        conn = get_connection()
        
        # Base query for metrics data
        metrics_query = '''
        SELECT 
            s.site_name,
            e.year,
            e.sample_id,
            m.metric_name,
            m.raw_value,
            m.metric_score
        FROM 
            fish_metrics m
        JOIN 
            fish_collection_events e ON m.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        # Base query for summary data
        summary_query = '''
        SELECT 
            s.site_name,
            e.year,
            e.sample_id,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        # Add filter for site name if provided
        params = []
        if site_name:
            where_clause = ' WHERE s.site_name = ?'
            metrics_query += where_clause
            summary_query += where_clause
            params.append(site_name)
        
        # Add order by clause
        metrics_query += ' ORDER BY s.site_name, e.year, m.metric_name'
        summary_query += ' ORDER BY s.site_name, e.year'
        
        # Execute queries
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        logger.debug(f"Retrieved fish metrics data: {len(metrics_df)} metric records and {summary_df.shape[0]} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving fish metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)

def get_sites_with_fish_data():
    """
    Get a list of sites that have fish data.
    
    Returns:
        List of site names
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT s.site_name
            FROM sites s
            JOIN fish_collection_events e ON s.site_id = e.site_id
            ORDER BY s.site_name
        ''')
        
        sites = [row[0] for row in cursor.fetchall()]
        logger.debug(f"Found {len(sites)} sites with fish data")
        return sites
        
    except Exception as e:
        logger.error(f"Error getting sites with fish data: {e}")
        return []
        
    finally:
        if conn:
            close_connection(conn)

if __name__ == "__main__":
    # Test loading fish data
    fish_df = load_fish_data()
    if not fish_df.empty:
        logger.info("Fish data summary:")
        logger.info(f"Number of records: {len(fish_df)}")
        sites = get_sites_with_fish_data()
        logger.info(f"Sites with fish data: {', '.join(sites[:10])}")  # Show first 10 sites
    else:
        logger.error("No fish data loaded. Check database setup.")