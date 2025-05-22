import pandas as pd
import os

# Define file paths
base_dir = os.path.dirname(os.path.abspath(__file__))
raw_data_dir = os.path.join(base_dir, 'data', 'raw')

files = {
    'sites': os.path.join(raw_data_dir, 'site_data.csv'),
    'chemical': os.path.join(raw_data_dir, 'chemical_data.csv'),
    'fish': os.path.join(raw_data_dir, 'fish_data.csv'),
    'macro': os.path.join(raw_data_dir, 'macro_data.csv'),
    'habitat': os.path.join(raw_data_dir, 'habitat_data.csv')
}

def get_site_names_from_file(file_path, data_type):
    """Extract unique site names from a CSV file."""
    try:
        df = pd.read_csv(file_path)
        
        # Find the site name column (different files might use different column names)
        site_column = None
        for col in df.columns:
            if 'site' in col.lower() and 'name' in col.lower():
                site_column = col
                break
        
        if site_column is None:
            print(f"Warning: Could not find site name column in {data_type} file")
            return set()
        
        # Get unique site names and clean them (strip whitespace)
        sites = set(df[site_column].dropna().str.strip())
        print(f"{data_type.title()}: Found {len(sites)} unique sites")
        return sites
        
    except Exception as e:
        print(f"Error reading {data_type} file: {e}")
        return set()

def main():
    print("Checking site consistency across CSV files...\n")
    
    # Get site names from each file
    all_sites = {}
    for data_type, file_path in files.items():
        if os.path.exists(file_path):
            all_sites[data_type] = get_site_names_from_file(file_path, data_type)
        else:
            print(f"Warning: {data_type} file not found at {file_path}")
            all_sites[data_type] = set()
    
    # Get the master site list
    master_sites = all_sites['sites']
    print(f"\nMaster sites file contains {len(master_sites)} unique sites")
    
    # Check each data file against the master list
    missing_sites = {}
    extra_sites = {}
    
    for data_type in ['chemical', 'fish', 'macro', 'habitat']:
        data_sites = all_sites[data_type]
        
        # Find sites in data that aren't in master
        missing = data_sites - master_sites
        
        # Find sites in master that aren't in this data file
        extra = master_sites - data_sites
        
        if missing:
            missing_sites[data_type] = missing
        if extra:
            extra_sites[data_type] = extra
    
    # Report results
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    if not any(missing_sites.values()):
        print("✅ SUCCESS: All sites in data files exist in the master sites file!")
    else:
        print("❌ ISSUES FOUND:")
        for data_type, missing in missing_sites.items():
            if missing:
                print(f"\n{data_type.upper()} file contains {len(missing)} sites NOT in master sites file:")
                for site in sorted(missing):
                    print(f"  - {site}")
    
    # Optional: Show sites that exist in master but not in specific data files
    print(f"\nINFO: Sites that exist in master but not used in each data type:")
    for data_type, extra in extra_sites.items():
        if extra:
            print(f"{data_type.title()}: {len(extra)} sites not used")
    
    # Summary
    total_unique_across_all = set()
    for sites in all_sites.values():
        total_unique_across_all.update(sites)
    
    print(f"\nSUMMARY:")
    print(f"Total unique sites across ALL files: {len(total_unique_across_all)}")
    print(f"Sites in master file: {len(master_sites)}")
    
    if len(total_unique_across_all) == len(master_sites):
        print("✅ Master sites file appears complete!")
    else:
        print("⚠️  There may be site name inconsistencies to investigate")

if __name__ == "__main__":
    main()