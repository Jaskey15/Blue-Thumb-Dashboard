#!/usr/bin/env python3
"""
Test script for new date-based replicate detection
"""

import pandas as pd
import difflib

def clean_site_name(site_name):
    """Simple site name cleaning function"""
    if pd.isna(site_name):
        return ""
    return str(site_name).strip()

def find_bt_site_match(db_site_name, bt_sites, threshold=0.9):
    """Find the best matching BT site name for a database site name."""
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
        print(f"Fuzzy match ({best_score:.3f}): '{db_site_name}' → '{best_match}'")
        return best_match
    else:
        return None

def detect_replicates_by_dates(bt_df, site_name, year):
    """
    Detect replicates by finding multiple collection dates for same site/year in BT data,
    regardless of REP labeling.
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
            print(f"Found {len(potential_dates)} dates for {site_name} in {check_year}: date-based replicates")
            return potential_dates.sort_values('Date_Clean')
    
    return None

def load_bt_data():
    """Load and process BT field work dates"""
    try:
        bt_path = 'data/raw/BT_fish_collection_dates.csv'
        bt_df = pd.read_csv(bt_path)
        print(f"Loaded {len(bt_df)} BT field work records")
        
        # Clean and process the data
        bt_df['Date_Clean'] = pd.to_datetime(bt_df['Date'], errors='coerce')
        bt_df = bt_df.dropna(subset=['Date_Clean'])
        
        # Clean site names
        bt_df['Site_Clean'] = bt_df['Name'].apply(clean_site_name)
        
        # Add year for matching
        bt_df['Year'] = bt_df['Date_Clean'].dt.year
        
        print(f"Processed {len(bt_df)} valid BT field work records")
        return bt_df
        
    except Exception as e:
        print(f"Could not load BT field work dates: {e}")
        return pd.DataFrame()

def main():
    # Load BT data
    print('Loading BT data...')
    bt_df = load_bt_data()

    # Test Spring Creek: I-35 for year 2006
    site_name = 'Spring Creek: I-35'
    year = 2006

    print(f'\nTesting date-based replicate detection for {site_name} ({year}):')
    print('='*60)

    # Check what BT data exists for this site
    bt_spring_creek = bt_df[bt_df['Site_Clean'] == site_name]
    print(f'BT records for {site_name}:')
    for _, row in bt_spring_creek.iterrows():
        print(f'  {row["Date"]:<12} ({row["Year"]}) - {row["M/F/H"]}')

    print(f'\nTesting replicate detection:')
    replicate_dates = detect_replicates_by_dates(bt_df, site_name, year)

    if replicate_dates is not None:
        print(f'SUCCESS: Found {len(replicate_dates)} dates for {site_name} in {year}')
        print('Replicate dates found:')
        for i, (_, row) in enumerate(replicate_dates.iterrows()):
            print(f'  {i+1}. {row["Date"]} ({row["Date_Clean"].strftime("%Y-%m-%d")})')
    else:
        print(f'NO REPLICATES: No multiple dates found for {site_name} in {year}')

    # Test a few other known cases
    print(f'\n\nTesting other known cases:')
    print('='*60)

    test_cases = [
        ('Coal Creek: Hwy 11', 2012),  # Should find REP
        ('Guy Sandy Creek', 2020),    # Should find REP  
        ('Cow Creek: Hwy 51', 2015),  # Should find multiple REP entries
    ]

    for test_site, test_year in test_cases:
        print(f'\nTesting {test_site} ({test_year}):')
        
        # Show BT data for this site
        bt_site_data = bt_df[bt_df['Site_Clean'] == test_site]
        if not bt_site_data.empty:
            print(f'BT records for {test_site}:')
            for _, row in bt_site_data.iterrows():
                rep_flag = " (REP)" if 'rep' in str(row['M/F/H']).lower() else ""
                print(f'  {row["Date"]:<12} ({row["Year"]}) - {row["M/F/H"]}{rep_flag}')
        
        result = detect_replicates_by_dates(bt_df, test_site, test_year)
        if result is not None:
            print(f'RESULT: FOUND {len(result)} dates for {test_year}')
            for _, row in result.iterrows():
                print(f'  - {row["Date"]} ({row["M/F/H"]})')
        else:
            print(f'RESULT: No replicates found for {test_year}')

if __name__ == "__main__":
    main() 