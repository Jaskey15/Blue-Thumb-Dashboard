import pandas as pd
import sqlite3
import os

def load_csv_files():
    """Load the relevant CSV files."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Load site_data.csv for metadata
    site_data = pd.read_csv(os.path.join(base_dir, 'data', 'raw', 'site_data.csv'))
    
    # Load updated_chemical_data.csv for preferred names (use cp1252 encoding)
    updated_chemical = pd.read_csv(
        os.path.join(base_dir, 'data', 'raw', 'updated_chemical_data.csv'), 
        encoding='cp1252'
    )
    
    return site_data, updated_chemical

def get_duplicate_groups():
    """Find groups of sites with the same coordinates (rounded to 3 decimal places)."""
    conn = sqlite3.connect('database/tenmile_biology.db')
    
    query = """
    SELECT 
        ROUND(latitude, 3) as rounded_lat,
        ROUND(longitude, 3) as rounded_lon,
        site_name,
        latitude,
        longitude,
        county,
        river_basin,
        ecoregion,
        active
    FROM sites 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY rounded_lat, rounded_lon, site_name
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Group by rounded coordinates and filter for duplicates
    duplicate_groups = df.groupby(['rounded_lat', 'rounded_lon']).filter(lambda x: len(x) > 1)
    
    return duplicate_groups

def analyze_duplicates():
    """Perform dry-run analysis of duplicate cleanup."""
    print("Loading CSV files...")
    site_data, updated_chemical = load_csv_files()
    
    print("Finding duplicate site groups...")
    duplicate_groups = get_duplicate_groups()
    
    if duplicate_groups.empty:
        print("No duplicate sites found!")
        return
    
    # Clean site names for comparison
    updated_chemical_sites = set(updated_chemical['Site Name'].str.strip())
    site_data_sites = set(site_data['SiteName'].str.strip())
    
    print(f"\nFound {len(duplicate_groups)} sites in duplicate groups")
    print("="*80)
    
    actions = []
    warnings = []
    
    # Analyze each duplicate group
    for (rounded_lat, rounded_lon), group in duplicate_groups.groupby(['rounded_lat', 'rounded_lon']):
        print(f"\nDuplicate Group at ({rounded_lat}, {rounded_lon}):")
        print(f"Sites in group: {len(group)}")
        
        # Check which sites are in updated_chemical_data
        sites_in_updated = []
        sites_not_in_updated = []
        
        for _, site in group.iterrows():
            site_name = site['site_name'].strip()
            if site_name in updated_chemical_sites:
                sites_in_updated.append(site)
                print(f"  ✓ KEEP: {site_name} (found in updated_chemical_data)")
            else:
                sites_not_in_updated.append(site)
                print(f"  ✗ DELETE: {site_name} (not in updated_chemical_data)")
        
        # Check for issues
        if len(sites_in_updated) == 0:
            warnings.append(f"No sites in group at ({rounded_lat}, {rounded_lon}) found in updated_chemical_data")
            print(f"  ⚠️  WARNING: No sites in this group found in updated_chemical_data")
        elif len(sites_in_updated) > 1:
            warnings.append(f"Multiple sites at ({rounded_lat}, {rounded_lon}) found in updated_chemical_data: {[s['site_name'] for s in sites_in_updated]}")
            print(f"  ⚠️  WARNING: Multiple sites in this group found in updated_chemical_data")
        
        # Plan actions
        if len(sites_in_updated) == 1:
            keep_site = sites_in_updated[0]
            delete_sites = [s['site_name'] for s in sites_not_in_updated]
            
            # Check if we can get metadata from site_data
            metadata_source = None
            for _, site_data_row in site_data.iterrows():
                if site_data_row['SiteName'].strip() == keep_site['site_name']:
                    metadata_source = "site_data.csv"
                    break
            
            if not metadata_source:
                # Check if any of the sites to be deleted have metadata in site_data
                for delete_site_name in delete_sites:
                    for _, site_data_row in site_data.iterrows():
                        if site_data_row['SiteName'].strip() == delete_site_name:
                            metadata_source = f"site_data.csv (via {delete_site_name})"
                            break
                    if metadata_source:
                        break
            
            action = {
                'coordinates': (rounded_lat, rounded_lon),
                'keep_site': keep_site['site_name'],
                'delete_sites': delete_sites,
                'metadata_source': metadata_source or "No metadata found in site_data.csv"
            }
            actions.append(action)
            
            print(f"  📋 ACTION: Keep '{keep_site['site_name']}', delete {len(delete_sites)} others")
            print(f"  📊 METADATA: {metadata_source or 'No metadata available'}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total duplicate groups: {len(duplicate_groups.groupby(['rounded_lat', 'rounded_lon']))}")
    print(f"Sites that would be kept: {len(actions)}")
    print(f"Sites that would be deleted: {sum(len(action['delete_sites']) for action in actions)}")
    
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    
    print(f"\nREADY TO PROCEED? This analysis shows what would happen.")
    print("Next step: Write the actual cleanup script if this looks correct.")

if __name__ == "__main__":
    analyze_duplicates()