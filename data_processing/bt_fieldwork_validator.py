"""
bt_fieldwork_validator.py - Blue Thumb Field Work Data Validation

This module handles comprehensive validation and correction of fish collection data 
against Blue Thumb field work records. It corrects date mismatches using BT data 
as the authoritative source when available, and falls back to YEAR field as truth 
when no BT match exists.

Key Functions:
- load_bt_field_work_dates(): Load BT field work dates for validation
- find_bt_site_match(): Find matching BT site names using fuzzy matching
- detect_replicates_by_dates(): Detect multiple collection dates for same site/year
- correct_collection_dates(): Comprehensive date correction for ALL fish records
- categorize_and_process_duplicates(): Handle replicates vs duplicates using date-based detection

Date-Based Replicate Detection Logic:
1. For ALL fish records with multiple samples per site+year, check BT data
2. If BT shows multiple dates for same site+year, treat as replicates
3. Assign actual BT dates chronologically
4. If no multiple BT dates found, treat as duplicates and average

Comprehensive Date Correction Logic:
1. For ALL fish records, check if collection_date year matches year field
2. If mismatch found, try to find BT match for the site
3. If BT match found, use BT date as authoritative source
4. If no BT match, use YEAR field as truth (keep month/day, correct year)
5. Process collections using date-based detection
6. Average duplicate entries that are not true replicates

Usage:
- Import and use correct_collection_dates() as main entry point
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
        
        logger.info(f"Processed {len(bt_df)} valid BT field work records")
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

def detect_replicates_by_dates(bt_df, site_name, year):
    """
    Detect replicates by finding multiple collection dates for same site/year in BT data,
    regardless of REP labeling.
    
    Args:
        bt_df: BT DataFrame with cleaned data
        site_name: Site name to check
        year: Year to check
        
    Returns:
        DataFrame with multiple BT dates for this site/year, or None if not found
    """
    if bt_df.empty or 'Site_Clean' not in bt_df.columns:
        return None
        
    # Find BT site match
    bt_sites = set(bt_df['Site_Clean'].unique())
    bt_site_match = find_bt_site_match(site_name, bt_sites)
    
    if not bt_site_match:
        return None
        
    # Look for multiple dates in target year ±1 buffer
    for check_year in [year, year-1, year+1]:
        potential_dates = bt_df[
            (bt_df['Site_Clean'] == bt_site_match) & 
            (bt_df['Year'] == check_year)
        ]
        
        if len(potential_dates) >= 2:
            # Found multiple dates - these are replicates
            logger.debug(f"Found {len(potential_dates)} dates for {site_name} in {check_year}: date-based replicates")
            return potential_dates.sort_values('Date_Clean')
    
    return None

def correct_collection_dates(fish_df, bt_df=None):
    """
    Comprehensive correction of fish collection dates using BT data as authoritative source
    when available, falling back to YEAR field as truth when no BT match exists.
    
    Args:
        fish_df: DataFrame with fish data
        bt_df: Optional BT DataFrame (will load if not provided)
        
    Returns:
        DataFrame with corrected collection dates
    """
    if fish_df.empty:
        return fish_df.copy()
    
    # Load BT data if not provided
    if bt_df is None:
        bt_df = load_bt_field_work_dates()
    
    fish_corrected = fish_df.copy()
    
    # Ensure collection_date is datetime
    fish_corrected['collection_date'] = pd.to_datetime(fish_corrected['collection_date'])
    fish_corrected['year_from_date'] = fish_corrected['collection_date'].dt.year
    
    # Find records with year/date mismatches
    mismatched_mask = fish_corrected['year'] != fish_corrected['year_from_date']
    mismatched_records = fish_corrected[mismatched_mask]
    
    if len(mismatched_records) == 0:
        logger.info("No date mismatches found - all records consistent")
        return fish_corrected
    
    logger.info(f"Found {len(mismatched_records)} records with year/date mismatches")
    
    # Handle empty BT DataFrame
    if bt_df.empty or 'Site_Clean' not in bt_df.columns:
        bt_sites = set()
    else:
        bt_sites = set(bt_df['Site_Clean'].unique())
    
    corrections_applied = 0
    bt_corrections = 0
    year_field_corrections = 0
    correction_log = []
    
    # Process each mismatched record
    for idx, record in mismatched_records.iterrows():
        site_name = record['site_name']
        db_year = record['year']  # Year from database field
        date_year = record['year_from_date']  # Year from collection_date
        original_date = record['collection_date']
        
        correction_applied = False
        correction_source = None
        new_date = None
        
        # Try to find BT match for this site
        bt_site_match = find_bt_site_match(site_name, bt_sites)
        
        if bt_site_match:
            # Look for BT records that match this site and either year
            potential_bt_matches = bt_df[
                (bt_df['Site_Clean'] == bt_site_match) & 
                (bt_df['Year'].isin([db_year, date_year]))
            ]
            
            if not potential_bt_matches.empty:
                # Use the BT date as authoritative source
                # If multiple matches, prefer the one that matches the database year field
                db_year_match = potential_bt_matches[potential_bt_matches['Year'] == db_year]
                if not db_year_match.empty:
                    bt_date = db_year_match.iloc[0]['Date_Clean']
                else:
                    bt_date = potential_bt_matches.iloc[0]['Date_Clean']
                
                fish_corrected.at[idx, 'collection_date'] = bt_date
                fish_corrected.at[idx, 'collection_date_str'] = bt_date.strftime('%Y-%m-%d')
                fish_corrected.at[idx, 'year'] = bt_date.year
                
                new_date = bt_date
                correction_applied = True
                correction_source = "BT_truth"
                bt_corrections += 1
                
                correction_log.append({
                    'site_name': site_name,
                    'sample_id': record.get('sample_id', 'unknown'),
                    'original_date': original_date.strftime('%Y-%m-%d'),
                    'original_year': db_year,
                    'corrected_date': new_date.strftime('%Y-%m-%d'),
                    'corrected_year': new_date.year,
                    'correction_source': correction_source,
                    'bt_site_match': bt_site_match
                })
        
        # Fallback: use YEAR field as truth if no BT match
        if not correction_applied:
            # Keep original month/day but use database year field
            try:
                corrected_date = original_date.replace(year=db_year)
                fish_corrected.at[idx, 'collection_date'] = corrected_date
                fish_corrected.at[idx, 'collection_date_str'] = corrected_date.strftime('%Y-%m-%d')
                # year field already correct, no change needed
                
                new_date = corrected_date
                correction_applied = True
                correction_source = "year_field_truth"
                year_field_corrections += 1
                
                correction_log.append({
                    'site_name': site_name,
                    'sample_id': record.get('sample_id', 'unknown'),
                    'original_date': original_date.strftime('%Y-%m-%d'),
                    'original_year': date_year,
                    'corrected_date': new_date.strftime('%Y-%m-%d'),
                    'corrected_year': db_year,
                    'correction_source': correction_source,
                    'bt_site_match': bt_site_match if bt_site_match else 'no_match'
                })
                
            except ValueError as e:
                logger.warning(f"Could not correct date for {site_name} sample {record.get('sample_id', 'unknown')}: {e}")
        
        if correction_applied:
            corrections_applied += 1
    
    # Log summary
    if corrections_applied > 0:
        logger.info(f"Date correction complete: {corrections_applied} corrections applied")
        logger.info(f"  - BT truth corrections: {bt_corrections} ({bt_corrections/corrections_applied*100:.1f}%)")
        logger.info(f"  - Year field corrections: {year_field_corrections} ({year_field_corrections/corrections_applied*100:.1f}%)")
        logger.info("All date mismatches successfully resolved")
    
    return fish_corrected

def categorize_and_process_duplicates(fish_df, bt_df):
    """
    Categorize duplicates as replicates vs true duplicates using DATE-BASED detection
    and process accordingly.
    
    Logic:
    - Multiple dates in BT data for same site+year = replicates
    - No multiple dates found = duplicates (average)
    
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
        
        # Use date-based replicate detection
        replicate_dates = detect_replicates_by_dates(bt_df, site_name, year)
        
        # Process based on whether we found multiple dates in BT data
        if replicate_dates is not None and len(replicate_dates) >= 2:
            # REPLICATE GROUP: Multiple dates found in BT data
            # Sort BT data by date to get chronological order
            replicate_dates_sorted = replicate_dates.sort_values('Date_Clean')
            
            # Sort fish samples to get consistent assignment
            group_samples_sorted = group_samples.sort_values('sample_id')
            
            # Assign dates chronologically (first sample gets earliest date, etc.)
            for i, (idx, sample) in enumerate(group_samples_sorted.iterrows()):
                if i < len(replicate_dates_sorted):
                    # Assign the i-th BT date to the i-th sample
                    bt_date = replicate_dates_sorted.iloc[i]['Date_Clean']
                    fish_processed.at[idx, 'collection_date'] = bt_date
                    fish_processed.at[idx, 'collection_date_str'] = bt_date.strftime('%Y-%m-%d')
                    fish_processed.at[idx, 'year'] = bt_date.year
                    assignment_type = f"Date_{i+1}" if i > 0 else "Original"
                else:
                    # Extra samples beyond available BT dates
                    assignment_type = f"Extra_{i+1}"
                
                # Log the assignment
                year_used = replicate_dates_sorted.iloc[0]['Year']  # Year from BT data
                date_assignments.append({
                    'site_name': site_name,
                    'original_year': year,
                    'bt_year_used': year_used,
                    'sample_id': sample['sample_id'],
                    'assignment_type': assignment_type,
                    'assigned_date': fish_processed.at[idx, 'collection_date_str'],
                    'year_buffer_used': year_used != year,
                    'detection_method': 'date_based'
                })
            
            rep_groups_processed += 1
            logger.debug(f"Processed {site_name} ({year}) as replicates: {len(replicate_dates_sorted)} BT dates found")
            
        else:
            # DUPLICATE GROUP: No multiple dates in BT data - treat as duplicates
            # Calculate averaged record
            averaged_record = average_group_samples(group_samples)
            
            # Mark original records for removal
            for idx in group_samples.index:
                records_to_remove.append(idx)
            
            # Add averaged record
            records_to_add.append(averaged_record)
            duplicate_groups_averaged += 1
            logger.debug(f"Processed {site_name} ({year}) as duplicates: no multiple BT dates found")
    
    # Apply removals and additions for averaged groups
    if records_to_remove:
        fish_processed = fish_processed.drop(records_to_remove)
    
    if records_to_add:
        fish_processed = pd.concat([fish_processed, pd.DataFrame(records_to_add)], ignore_index=True)
    
    # Log concise summary
    logger.info(f"Fish duplicate processing (date-based): {rep_groups_processed} replicate groups, {duplicate_groups_averaged} groups averaged, {len(date_assignments)} date assignments")
    
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