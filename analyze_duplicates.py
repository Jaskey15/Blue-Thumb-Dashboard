import pandas as pd
from collections import Counter

def analyze_duplicates():
    """
    Analyze how many samples have the same site name AND collection date
    in both cleaned_chemical_data.csv and cleaned_updated_chemical_data.csv
    """
    
    # Read the CSV files
    print("Reading CSV files...")
    
    # For cleaned_chemical_data.csv
    df1 = pd.read_csv('data/processed/cleaned_chemical_data.csv')
    print(f"cleaned_chemical_data.csv: {len(df1)} total rows")
    
    # For cleaned_updated_chemical_data.csv  
    df2 = pd.read_csv('data/processed/cleaned_updated_chemical_data.csv')
    print(f"cleaned_updated_chemical_data.csv: {len(df2)} total rows")
    
    # Analyze cleaned_chemical_data.csv
    print("\n" + "="*60)
    print("ANALYSIS OF cleaned_chemical_data.csv")
    print("="*60)
    
    # Create site-date combinations
    df1['site_date'] = df1['SiteName'].astype(str) + ' | ' + df1['Date'].astype(str)
    site_date_counts1 = df1['site_date'].value_counts()
    
    # Count how many site-date combinations have duplicates
    duplicates1 = site_date_counts1[site_date_counts1 > 1]
    
    print(f"Total unique site-date combinations: {len(site_date_counts1)}")
    print(f"Site-date combinations with duplicates: {len(duplicates1)}")
    print(f"Total duplicate rows: {duplicates1.sum() - len(duplicates1)}")
    
    if len(duplicates1) > 0:
        print(f"\nTop 10 most duplicated site-date combinations:")
        for i, (site_date, count) in enumerate(duplicates1.head(10).items(), 1):
            site, date = site_date.split(' | ')
            print(f"{i:2d}. {site} on {date}: {count} samples")
        
        print(f"\nDistribution of duplicate counts:")
        duplicate_distribution1 = Counter(duplicates1.values)
        for count, frequency in sorted(duplicate_distribution1.items()):
            print(f"  {frequency} site-date combinations have {count} samples each")
    
    # Analyze cleaned_updated_chemical_data.csv
    print("\n" + "="*60)
    print("ANALYSIS OF cleaned_updated_chemical_data.csv")
    print("="*60)
    
    # Create site-date combinations using the correct column names
    # From the file inspection, it looks like the columns are 'Site Name' and 'Sampling Date'
    df2['site_date'] = df2['Site Name'].astype(str) + ' | ' + df2['Sampling Date'].astype(str)
    site_date_counts2 = df2['site_date'].value_counts()
    
    # Count how many site-date combinations have duplicates
    duplicates2 = site_date_counts2[site_date_counts2 > 1]
    
    print(f"Total unique site-date combinations: {len(site_date_counts2)}")
    print(f"Site-date combinations with duplicates: {len(duplicates2)}")
    print(f"Total duplicate rows: {duplicates2.sum() - len(duplicates2)}")
    
    if len(duplicates2) > 0:
        print(f"\nTop 10 most duplicated site-date combinations:")
        for i, (site_date, count) in enumerate(duplicates2.head(10).items(), 1):
            site, date = site_date.split(' | ')
            print(f"{i:2d}. {site} on {date}: {count} samples")
        
        print(f"\nDistribution of duplicate counts:")
        duplicate_distribution2 = Counter(duplicates2.values)
        for count, frequency in sorted(duplicate_distribution2.items()):
            print(f"  {frequency} site-date combinations have {count} samples each")
    
    # Summary comparison
    print("\n" + "="*60)
    print("SUMMARY COMPARISON")
    print("="*60)
    
    print(f"cleaned_chemical_data.csv:")
    print(f"  - Total rows: {len(df1)}")
    print(f"  - Unique site-date combinations: {len(site_date_counts1)}")
    print(f"  - Site-date combinations with duplicates: {len(duplicates1)}")
    print(f"  - Total duplicate rows: {duplicates1.sum() - len(duplicates1) if len(duplicates1) > 0 else 0}")
    
    print(f"\ncleaned_updated_chemical_data.csv:")
    print(f"  - Total rows: {len(df2)}")
    print(f"  - Unique site-date combinations: {len(site_date_counts2)}")
    print(f"  - Site-date combinations with duplicates: {len(duplicates2)}")
    print(f"  - Total duplicate rows: {duplicates2.sum() - len(duplicates2) if len(duplicates2) > 0 else 0}")
    
    # Return the duplicate DataFrames for further analysis if needed
    return duplicates1, duplicates2, df1, df2

if __name__ == "__main__":
    duplicates1, duplicates2, df1, df2 = analyze_duplicates()
    
    # Additional detailed analysis for cleaned_updated_chemical_data.csv if it has duplicates
    if len(duplicates2) > 0:
        print("\n" + "="*60)
        print("DETAILED ANALYSIS OF DUPLICATES IN cleaned_updated_chemical_data.csv")
        print("="*60)
        
        # Show examples of duplicate rows
        print("\nExample duplicate entries (first 3 site-date combinations):")
        for i, (site_date, count) in enumerate(duplicates2.head(3).items()):
            site, date = site_date.split(' | ')
            print(f"\n{i+1}. {site} on {date} ({count} samples):")
            
            # Find rows for this site-date combination
            mask = (df2['Site Name'] == site) & (df2['Sampling Date'] == date)
            duplicate_rows = df2[mask]
            
            # Show key columns that might differ between duplicates
            key_cols = ['Samplers', 'Sampling Time', 'Water Temperature ( ?C )', 
                       'mg/L DO High #1', 'pH #1', 'mg/L NO3-N']
            
            for col in key_cols:
                if col in duplicate_rows.columns:
                    values = duplicate_rows[col].values
                    if len(set(str(v) for v in values)) > 1:  # If values differ
                        print(f"    {col}: {list(values)}")