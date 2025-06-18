"""
bt_fieldwork_validator.py - Blue Thumb Field Work Data Validation

This module handles validation and processing of fish collection data against 
Blue Thumb field work records. It distinguishes between true replicates 
(separate collection events) and duplicate data entries using BT field work 
records to assign correct collection dates.

Key Functions:
- load_bt_field_work_dates(): Load BT field work dates for validation
- find_bt_site_match(): Find matching BT site names using fuzzy matching
- categorize_and_process_duplicates(): Main function to distinguish replicates from duplicates
- average_group_samples(): Helper function to average duplicate sample groups

Replicate Logic:
- Uses BT_fish_collection_dates.csv to identify true REP collections
- Assigns correct dates to replicate samples (original vs REP date)
- Averages duplicate entries that are not true replicates
- Supports ±1 year buffer for matching BT field work data

Usage:
- Import and use categorize_and_process_duplicates() as main entry point
- Requires fish DataFrame and loads BT data automatically
"""

import pandas as pd
import difflib
from data_processing.data_loader import clean_site_name
from data_processing import setup_logging

logger = setup_logging("bt_fieldwork_validator", category="processing")

def load_bt_field_work_dates():
    """
    Load and process BT field work dates for fish collection validation.
    
    Returns:
        DataFrame with cleaned BT field work data
    """
    try:
        bt_path = 'data/raw/BT_fish_collection_dates.csv'
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
    fish_processed = fish_df.copy()
    
    # Handle empty fish DataFrame
    if fish_df.empty:
        return fish_processed
    
    # Handle empty BT DataFrame
    if bt_df.empty or 'Site_Clean' not in bt_df.columns:
        bt_sites = set()
    else:
        bt_sites = set(bt_df['Site_Clean'].unique())
    
    # Track processing decisions
    rep_groups_processed = 0
    duplicate_groups_averaged = 0
    date_assignments = []
    
    # Find all groups with multiple samples
    duplicate_groups = fish_df.groupby(['site_name', 'year']).filter(lambda x: len(x) > 1)
    
    if duplicate_groups.empty:
        return fish_processed
    
    unique_duplicate_groups = duplicate_groups.groupby(['site_name', 'year']).size().reset_index()
    unique_duplicate_groups.columns = ['site_name', 'year', 'sample_count']
    
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
    
    # Log concise summary
    logger.info(f"Fish duplicate processing: {rep_groups_processed} replicate groups, {duplicate_groups_averaged} groups averaged, {len(date_assignments)} date assignments")
    
    return fish_processed

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