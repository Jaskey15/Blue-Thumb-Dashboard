"""
Fish Data Validation Against BT Field Work Dates - Phase 2
==========================================================

This script validates database fish records against the authoritative Blue Thumb
field work dates to identify legitimate Blue Thumb collections vs. mixed-in data.

Author: [Your Name]
Date: [Current Date]
Purpose: Validate fish data against BT field work records for cleaning
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import difflib
import os

# Database connection
def get_connection():
    """Get database connection"""
    db_path = 'database/tenmile_biology.db'
    return sqlite3.connect(db_path)

def load_and_process_bt_dates():
    """Load and process BT field work dates for comparison"""
    
    print("=" * 60)
    print("LOADING BT FIELD WORK DATES")
    print("=" * 60)
    
    try:
        # Load the CSV
        csv_path = 'data/raw/BT field work dates.csv'
        bt_dates = pd.read_csv(csv_path)
        
        print(f"Loaded {len(bt_dates)} BT field work records")
        print(f"Columns: {list(bt_dates.columns)}")
        
        # Filter for fish collections only
        fish_records = bt_dates[bt_dates['M/F/H'].str.contains('fish', case=False, na=False)].copy()
        print(f"Fish collection records: {len(fish_records)}")
        
        # Clean and standardize dates
        fish_records['Date_Clean'] = pd.to_datetime(fish_records['Date'], errors='coerce')
        fish_records = fish_records.dropna(subset=['Date_Clean'])
        
        # Clean site names
        fish_records['Site_Clean'] = fish_records['Name'].str.strip()
        
        # Add year for easier comparison
        fish_records['Year'] = fish_records['Date_Clean'].dt.year
        
        print(f"After date cleaning: {len(fish_records)} valid fish records")
        print(f"Date range: {fish_records['Date_Clean'].min()} to {fish_records['Date_Clean'].max()}")
        print(f"Year range: {fish_records['Year'].min()} to {fish_records['Year'].max()}")
        print(f"Unique sites: {fish_records['Site_Clean'].nunique()}")
        
        return fish_records
        
    except Exception as e:
        print(f"Error loading BT field work dates: {e}")
        return pd.DataFrame()

def load_database_fish_data():
    """Load fish data from database for comparison"""
    
    print("\n" + "=" * 60)
    print("LOADING DATABASE FISH DATA")
    print("=" * 60)
    
    conn = get_connection()
    
    query = """
    SELECT 
        f.event_id,
        f.sample_id,
        s.site_name,
        f.collection_date,
        f.year as db_year,
        strftime('%Y', f.collection_date) as date_year,
        fs.total_score,
        fs.comparison_to_reference,
        fs.integrity_class
    FROM fish_collection_events f
    JOIN sites s ON f.site_id = s.site_id
    LEFT JOIN fish_summary_scores fs ON f.event_id = fs.event_id
    ORDER BY s.site_name, f.collection_date
    """
    
    db_fish = pd.read_sql_query(query, conn)
    conn.close()
    
    # Process database data
    db_fish['collection_date_clean'] = pd.to_datetime(db_fish['collection_date'])
    db_fish['site_name_clean'] = db_fish['site_name'].str.strip()
    
    print(f"Database fish records: {len(db_fish)}")
    print(f"Date range: {db_fish['collection_date_clean'].min()} to {db_fish['collection_date_clean'].max()}")
    print(f"Unique sites: {db_fish['site_name_clean'].nunique()}")
    
    return db_fish

def find_site_name_matches(bt_sites, db_sites, threshold=0.8):
    """Find matches between BT and database site names using fuzzy matching"""
    
    print("\n" + "=" * 60)
    print("SITE NAME MATCHING ANALYSIS")
    print("=" * 60)
    
    # Get unique site lists
    bt_unique = set(bt_sites)
    db_unique = set(db_sites)
    
    print(f"Unique BT sites: {len(bt_unique)}")
    print(f"Unique DB sites: {len(db_unique)}")
    
    # Find exact matches
    exact_matches = bt_unique.intersection(db_unique)
    print(f"Exact matches: {len(exact_matches)}")
    
    # Find fuzzy matches for non-exact matches
    bt_unmatched = bt_unique - exact_matches
    db_unmatched = db_unique - exact_matches
    
    fuzzy_matches = []
    site_mapping = {}
    
    # Add exact matches to mapping
    for site in exact_matches:
        site_mapping[site] = site
    
    # Find fuzzy matches
    for bt_site in bt_unmatched:
        best_match = None
        best_score = 0
        
        for db_site in db_unmatched:
            # Use difflib for fuzzy matching
            score = difflib.SequenceMatcher(None, bt_site.lower(), db_site.lower()).ratio()
            
            if score > threshold and score > best_score:
                best_score = score
                best_match = db_site
        
        if best_match:
            fuzzy_matches.append((bt_site, best_match, best_score))
            site_mapping[bt_site] = best_match
    
    print(f"Fuzzy matches (>{threshold}): {len(fuzzy_matches)}")
    
    if len(fuzzy_matches) > 0:
        print("\nTop 10 fuzzy matches:")
        for bt_site, db_site, score in sorted(fuzzy_matches, key=lambda x: x[2], reverse=True)[:10]:
            print(f"  {score:.3f}: '{bt_site}' → '{db_site}'")
    
    # Show unmatched sites
    bt_unmatched_final = bt_unique - set(site_mapping.keys())
    db_unmatched_final = db_unique - set(site_mapping.values())
    
    print(f"\nBT sites without matches: {len(bt_unmatched_final)}")
    if len(bt_unmatched_final) > 0 and len(bt_unmatched_final) <= 20:
        print("BT unmatched sites:")
        for site in sorted(bt_unmatched_final):
            print(f"  - {site}")
    
    print(f"\nDB sites without matches: {len(db_unmatched_final)}")
    if len(db_unmatched_final) > 0 and len(db_unmatched_final) <= 20:
        print("DB unmatched sites:")
        for site in sorted(db_unmatched_final):
            print(f"  - {site}")
    
    return site_mapping, exact_matches, fuzzy_matches

def validate_fish_records(bt_fish, db_fish, site_mapping, date_tolerance_days=7):
    """Validate database fish records against BT field work dates"""
    
    print("\n" + "=" * 60)
    print("FISH RECORD VALIDATION")
    print("=" * 60)
    
    validation_results = []
    
    for _, db_record in db_fish.iterrows():
        db_site = db_record['site_name_clean']
        db_date = db_record['collection_date_clean']
        
        # Find corresponding BT site name
        bt_site = None
        for bt_name, db_name in site_mapping.items():
            if db_name == db_site:
                bt_site = bt_name
                break
        
        if not bt_site:
            # No site mapping found
            validation_results.append({
                'event_id': db_record['event_id'],
                'sample_id': db_record['sample_id'],
                'db_site': db_site,
                'bt_site': None,
                'db_date': db_date,
                'bt_date': None,
                'date_diff': None,
                'validation_status': 'NO_SITE_MATCH',
                'bt_record_found': False
            })
            continue
        
        # Look for matching BT records for this site
        bt_site_records = bt_fish[bt_fish['Site_Clean'] == bt_site]
        
        if bt_site_records.empty:
            # Site maps but no BT records found
            validation_results.append({
                'event_id': db_record['event_id'],
                'sample_id': db_record['sample_id'],
                'db_site': db_site,
                'bt_site': bt_site,
                'db_date': db_date,
                'bt_date': None,
                'date_diff': None,
                'validation_status': 'NO_BT_RECORDS',
                'bt_record_found': False
            })
            continue
        
        # Find closest date match within tolerance
        bt_site_records = bt_site_records.copy()
        bt_site_records['date_diff'] = abs((bt_site_records['Date_Clean'] - db_date).dt.days)
        
        closest_match = bt_site_records.loc[bt_site_records['date_diff'].idxmin()]
        
        if closest_match['date_diff'] <= date_tolerance_days:
            # Valid match found
            validation_results.append({
                'event_id': db_record['event_id'],
                'sample_id': db_record['sample_id'],
                'db_site': db_site,
                'bt_site': bt_site,
                'db_date': db_date,
                'bt_date': closest_match['Date_Clean'],
                'date_diff': closest_match['date_diff'],
                'validation_status': 'VALID_MATCH',
                'bt_record_found': True
            })
        else:
            # No close date match
            validation_results.append({
                'event_id': db_record['event_id'],
                'sample_id': db_record['sample_id'],
                'db_site': db_site,
                'bt_site': bt_site,
                'db_date': db_date,
                'bt_date': closest_match['Date_Clean'],
                'date_diff': closest_match['date_diff'],
                'validation_status': 'DATE_MISMATCH',
                'bt_record_found': False
            })
    
    validation_df = pd.DataFrame(validation_results)
    
    # Summary statistics
    print("VALIDATION SUMMARY:")
    print("-" * 40)
    status_counts = validation_df['validation_status'].value_counts()
    for status, count in status_counts.items():
        percentage = (count / len(validation_df)) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    
    print(f"\nTotal database records: {len(validation_df)}")
    print(f"Valid BT matches: {status_counts.get('VALID_MATCH', 0)}")
    print(f"Suspicious records: {len(validation_df) - status_counts.get('VALID_MATCH', 0)}")
    
    return validation_df

def analyze_suspicious_records(validation_df, db_fish):
    """Analyze records that don't match BT field work dates"""
    
    print("\n" + "=" * 60)
    print("SUSPICIOUS RECORDS ANALYSIS")
    print("=" * 60)
    
    # Get suspicious records
    suspicious = validation_df[validation_df['validation_status'] != 'VALID_MATCH']
    
    if suspicious.empty:
        print("No suspicious records found!")
        return
    
    # Merge with fish data for more details
    suspicious_detailed = suspicious.merge(
        db_fish[['event_id', 'sample_id', 'db_year', 'date_year', 'total_score', 
                'comparison_to_reference', 'integrity_class']], 
        on=['event_id', 'sample_id'], 
        how='left'
    )
    
    print(f"Suspicious records by category:")
    for status in suspicious['validation_status'].unique():
        count = len(suspicious[suspicious['validation_status'] == status])
        print(f"  {status}: {count}")
        
        # Show examples
        examples = suspicious_detailed[suspicious_detailed['validation_status'] == status].head(5)
        if not examples.empty:
            print(f"    Examples:")
            for _, ex in examples.iterrows():
                print(f"      {ex['db_site']} | {ex['db_date'].strftime('%Y-%m-%d')} | Sample: {ex['sample_id']}")
    
    # Analyze by year
    print(f"\nSuspicious records by year:")
    year_analysis = suspicious_detailed.groupby('db_year').size().sort_index()
    for year, count in year_analysis.items():
        print(f"  {year}: {count}")
    
    # Analyze sample ID patterns
    print(f"\nSample ID patterns in suspicious records:")
    suspicious_samples = suspicious_detailed['sample_id'].tolist()
    valid_samples = validation_df[validation_df['validation_status'] == 'VALID_MATCH']['sample_id'].tolist()
    
    print(f"  Suspicious sample ID range: {min(suspicious_samples)} - {max(suspicious_samples)}")
    print(f"  Valid sample ID range: {min(valid_samples)} - {max(valid_samples)}")
    
    # Check for overlapping ranges that might indicate mixed data sources
    overlap = set(range(min(suspicious_samples), max(suspicious_samples) + 1)).intersection(
        set(range(min(valid_samples), max(valid_samples) + 1))
    )
    print(f"  Sample ID overlap: {len(overlap)} IDs overlap between suspicious and valid")
    
    return suspicious_detailed

def generate_cleaning_recommendations(validation_df):
    """Generate recommendations for data cleaning"""
    
    print("\n" + "=" * 60)
    print("CLEANING RECOMMENDATIONS")
    print("=" * 60)
    
    total_records = len(validation_df)
    valid_records = len(validation_df[validation_df['validation_status'] == 'VALID_MATCH'])
    
    print(f"SUMMARY:")
    print(f"  Total database records: {total_records}")
    print(f"  Verified Blue Thumb records: {valid_records}")
    print(f"  Records to remove/review: {total_records - valid_records}")
    print(f"  Data retention rate: {(valid_records/total_records)*100:.1f}%")
    
    print(f"\nRECOMMENDATIONS:")
    print(f"1. KEEP: {valid_records} records with validation_status = 'VALID_MATCH'")
    print(f"2. REVIEW: Records with 'DATE_MISMATCH' - may be legitimate with data entry errors")
    print(f"3. REMOVE: Records with 'NO_SITE_MATCH' or 'NO_BT_RECORDS' - likely from other programs")
    
    print(f"\nNEXT STEPS:")
    print(f"1. Export list of valid event_ids for dashboard data")
    print(f"2. Create backup of original data before cleaning")
    print(f"3. Implement cleaning based on validation results")
    print(f"4. Re-run duplicate analysis on cleaned data")
    
    # Save validation results for further analysis
    validation_df.to_csv('data/processed/fish_validation_results.csv', index=False)
    print(f"\nValidation results saved to: data/processed/fish_validation_results.csv")

def main():
    """Run the complete validation analysis"""
    
    print("FISH DATA VALIDATION AGAINST BT FIELD WORK DATES")
    print("Phase 2: Identifying Legitimate Blue Thumb Collections")
    print("=" * 80)
    
    # Load data
    bt_fish = load_and_process_bt_dates()
    if bt_fish.empty:
        print("Could not load BT field work dates. Exiting.")
        return
    
    db_fish = load_database_fish_data()
    if db_fish.empty:
        print("Could not load database fish data. Exiting.")
        return
    
    # Match site names
    site_mapping, exact_matches, fuzzy_matches = find_site_name_matches(
        bt_fish['Site_Clean'], 
        db_fish['site_name_clean']
    )
    
    if not site_mapping:
        print("No site matches found. Check site naming conventions.")
        return
    
    # Validate records
    validation_df = validate_fish_records(bt_fish, db_fish, site_mapping)
    
    # Analyze suspicious records
    suspicious_detailed = analyze_suspicious_records(validation_df, db_fish)
    
    # Generate recommendations
    generate_cleaning_recommendations(validation_df)
    
    print("\n" + "=" * 80)
    print("VALIDATION ANALYSIS COMPLETE")
    print("=" * 80)
    
    return validation_df, site_mapping, suspicious_detailed

if __name__ == "__main__":
    validation_results = main()