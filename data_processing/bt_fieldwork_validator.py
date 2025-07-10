"""
Validates fish collection dates and identifies replicates using Blue Thumb field data.
"""

import pandas as pd
import difflib
from data_processing.data_loader import clean_site_name
from data_processing import setup_logging

logger = setup_logging("bt_fieldwork_validator", category="processing")

def load_bt_field_work_dates():
    """Load and process Blue Thumb field work dates for authoritative validation."""
    try:
        bt_path = 'data/raw/BT_fish_collection_dates.csv'
        bt_df = pd.read_csv(bt_path)
        logger.info(f"Loaded {len(bt_df)} BT field work records for date validation")
        
        bt_df['Date_Clean'] = pd.to_datetime(bt_df['Date'], errors='coerce')
        bt_df = bt_df.dropna(subset=['Date_Clean'])
        
        bt_df['Site_Clean'] = bt_df['Name'].apply(clean_site_name)
        bt_df['Year'] = bt_df['Date_Clean'].dt.year
        
        logger.info(f"Processed {len(bt_df)} valid BT field work records")
        return bt_df
        
    except Exception as e:
        logger.warning(f"Could not load BT field work dates: {e}")
        return pd.DataFrame()

def find_bt_site_match(db_site_name, bt_sites, threshold=0.9):
    """
    Find matching BT site using exact and fuzzy matching.
    
    Matching priority:
    1. Exact match lookup
    2. Fuzzy match above threshold
    """
    if db_site_name in bt_sites:
        return db_site_name
    
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
    Find legitimate replicates by checking for multiple collection dates.
    
    Detection logic:
    1. Find matching BT site name
    2. Check target year ±1 for multiple dates
    3. Conclude that multiple dates indicate legitimate replicates
    """
    if bt_df.empty or 'Site_Clean' not in bt_df.columns:
        return None

    bt_sites = set(bt_df['Site_Clean'].unique())
    bt_site_match = find_bt_site_match(site_name, bt_sites)
    
    if not bt_site_match:
        return None

    for check_year in [year, year-1, year+1]:
        potential_dates = bt_df[
            (bt_df['Site_Clean'] == bt_site_match) & 
            (bt_df['Year'] == check_year)
        ]
        
        if len(potential_dates) >= 2:
            logger.debug(f"Found {len(potential_dates)} dates for {site_name} in {check_year}: date-based replicates")
            return potential_dates.sort_values('Date_Clean')
    
    return None

def correct_collection_dates(fish_df, bt_df=None):
    """
    Correct fish collection dates using authoritative BT records.
    
    Resolution priority:
    1. Use BT date if site+year match found
    2. Fall back to YEAR field if no BT match
    3. Keep month/day but correct year when using fallback
    """
    if fish_df.empty:
        return fish_df.copy()
    
    if bt_df is None:
        bt_df = load_bt_field_work_dates()
    
    fish_corrected = fish_df.copy()
    
    fish_corrected['collection_date'] = pd.to_datetime(fish_corrected['collection_date'])
    fish_corrected['year_from_date'] = fish_corrected['collection_date'].dt.year
    
    mismatched_mask = fish_corrected['year'] != fish_corrected['year_from_date']
    mismatched_records = fish_corrected[mismatched_mask]
    
    if len(mismatched_records) == 0:
        logger.info("No date mismatches found - all records consistent")
        return fish_corrected
    
    logger.info(f"Found {len(mismatched_records)} records with year/date mismatches")
    
    if bt_df.empty or 'Site_Clean' not in bt_df.columns:
        bt_sites = set()
    else:
        bt_sites = set(bt_df['Site_Clean'].unique())
    
    corrections_applied = 0
    bt_corrections = 0
    year_field_corrections = 0
    correction_log = []
    
    for idx, record in mismatched_records.iterrows():
        site_name = record['site_name']
        db_year = record['year']  
        date_year = record['year_from_date']  
        original_date = record['collection_date']
        
        correction_applied = False
        correction_source = None
        new_date = None
        
        bt_site_match = find_bt_site_match(site_name, bt_sites)
        
        if bt_site_match:
            potential_bt_matches = bt_df[
                (bt_df['Site_Clean'] == bt_site_match) & 
                (bt_df['Year'].isin([db_year, date_year]))
            ]
            
            if not potential_bt_matches.empty:
                # Prefer database year match if available
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
        
        # Fall back to YEAR field if no BT match is found
        if not correction_applied:
            try:
                corrected_date = original_date.replace(year=db_year)
                fish_corrected.at[idx, 'collection_date'] = corrected_date
                fish_corrected.at[idx, 'collection_date_str'] = corrected_date.strftime('%Y-%m-%d')
                
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
    
    if corrections_applied > 0:
        logger.info(f"Date correction complete: {corrections_applied} corrections applied")
        logger.info(f"  - BT truth corrections: {bt_corrections} ({bt_corrections/corrections_applied*100:.1f}%)")
        logger.info(f"  - Year field corrections: {year_field_corrections} ({year_field_corrections/corrections_applied*100:.1f}%)")
        logger.info("All date mismatches successfully resolved")
    
    return fish_corrected

def categorize_and_process_duplicates(fish_df, bt_df):
    """
    Process duplicates using date-based detection for replicates.
    
    Detection strategy:
    1. Multiple BT dates = legitimate replicates
    2. No multiple dates = duplicates to average
    3. Assign dates chronologically to replicates
    """
    fish_processed = fish_df.copy()
    
    if fish_df.empty:
        return fish_processed
    
    if bt_df.empty or 'Site_Clean' not in bt_df.columns:
        bt_sites = set()
    else:
        bt_sites = set(bt_df['Site_Clean'].unique())
    
    rep_groups_processed = 0
    duplicate_groups_averaged = 0
    date_assignments = []
    
    duplicate_groups = fish_df.groupby(['site_name', 'year']).filter(lambda x: len(x) > 1)
    
    if duplicate_groups.empty:
        return fish_processed
    
    unique_duplicate_groups = duplicate_groups.groupby(['site_name', 'year']).size().reset_index()
    unique_duplicate_groups.columns = ['site_name', 'year', 'sample_count']
    
    records_to_remove = []
    records_to_add = []
    
    for _, group_info in unique_duplicate_groups.iterrows():
        site_name = group_info['site_name']
        year = group_info['year']
        sample_count = group_info['sample_count']
        
        group_samples = fish_df[
            (fish_df['site_name'] == site_name) & 
            (fish_df['year'] == year)
        ].copy()
        
        replicate_dates = detect_replicates_by_dates(bt_df, site_name, year)
        
        if replicate_dates is not None and len(replicate_dates) >= 2:
            # Replicates: Multiple BT dates were found, so assign them chronologically
            replicate_dates_sorted = replicate_dates.sort_values('Date_Clean')
            group_samples_sorted = group_samples.sort_values('sample_id')
            
            for i, (idx, sample) in enumerate(group_samples_sorted.iterrows()):
                if i < len(replicate_dates_sorted):
                    bt_date = replicate_dates_sorted.iloc[i]['Date_Clean']
                    fish_processed.at[idx, 'collection_date'] = bt_date
                    fish_processed.at[idx, 'collection_date_str'] = bt_date.strftime('%Y-%m-%d')
                    fish_processed.at[idx, 'year'] = bt_date.year
                    assignment_type = f"Date_{i+1}" if i > 0 else "Original"
                else:
                    assignment_type = f"Extra_{i+1}"
                
                year_used = replicate_dates_sorted.iloc[0]['Year']
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
            # Duplicates: No multiple BT dates were found, so average the records
            averaged_record = average_group_samples(group_samples)
            records_to_remove.extend(group_samples.index)
            records_to_add.append(averaged_record)
            duplicate_groups_averaged += 1
            logger.debug(f"Processed {site_name} ({year}) as duplicates: no multiple BT dates found")
    
    if records_to_remove:
        fish_processed = fish_processed.drop(records_to_remove)
    
    if records_to_add:
        fish_processed = pd.concat([fish_processed, pd.DataFrame(records_to_add)], ignore_index=True)
    
    logger.info(f"Fish duplicate processing (date-based): {rep_groups_processed} replicate groups, {duplicate_groups_averaged} groups averaged, {len(date_assignments)} date assignments")
    
    return fish_processed

def average_group_samples(group):
    """
    Average duplicate samples while preserving key metadata.
    
    Averaging rules:
    1. Average comparison_to_reference values
    2. Keep first record's metadata
    3. Set individual scores to NULL to avoid misinterpretation of an averaged categorical scale
    """
    comparison_values = group['comparison_to_reference'].dropna().tolist()
    if comparison_values:
        avg_comparison = sum(comparison_values) / len(comparison_values)
    else:
        avg_comparison = None
    
    averaged_row = group.iloc[0].copy()
    averaged_row['comparison_to_reference'] = avg_comparison
    
    score_columns = [col for col in averaged_row.index if 'score' in str(col).lower() and col != 'comparison_to_reference']
    for col in score_columns:
        averaged_row[col] = None
    
    return averaged_row