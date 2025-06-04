"""
quick_validation.py - Validate cleaned files before database loading

Run this to check your cleaned files and get baseline metrics.
"""

import os
import pandas as pd
from datetime import datetime

def validate_cleaned_files():
    """
    Validate all cleaned files and report key metrics.
    """
    print("=" * 60)
    print("CLEANED FILES VALIDATION")
    print("=" * 60)
    
    # Define file paths
    processed_dir = os.path.join(os.path.dirname(__file__), 'data', 'processed')
    
    files_to_check = {
        'Master Sites': 'master_sites.csv',
        'Cleaned Chemical': 'cleaned_chemical_data.csv', 
        'Cleaned Updated Chemical': 'cleaned_updated_chemical_data.csv',
        'Cleaned Fish': 'cleaned_fish_data.csv',
        'Cleaned Macro': 'cleaned_macro_data.csv',
        'Cleaned Habitat': 'cleaned_habitat_data.csv'
    }
    
    results = {}
    
    # Check each file
    for file_desc, filename in files_to_check.items():
        file_path = os.path.join(processed_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"❌ {file_desc}: FILE NOT FOUND - {filename}")
            results[file_desc] = None
            continue
            
        try:
            df = pd.read_csv(file_path, low_memory=False)
            
            # Get basic info
            rows = len(df)
            cols = len(df.columns)
            
            # Find site column
            site_col = None
            for col in df.columns:
                if 'site' in col.lower() and 'name' in col.lower():
                    site_col = col
                    break
            
            if not site_col:
                # Try other common patterns
                for col in ['SiteName', 'Site Name', 'site_name']:
                    if col in df.columns:
                        site_col = col
                        break
            
            unique_sites = df[site_col].nunique() if site_col else "Unknown"
            
            # Get date info if available
            date_info = "No dates"
            for date_col in ['Date', 'date', 'collection_date', 'Sampling Date']:
                if date_col in df.columns:
                    try:
                        dates = pd.to_datetime(df[date_col], errors='coerce')
                        min_date = dates.min()
                        max_date = dates.max()
                        date_info = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
                        break
                    except:
                        continue
            
            print(f"✅ {file_desc}:")
            print(f"   📊 {rows:,} rows, {cols} columns")
            print(f"   🏠 {unique_sites} unique sites")
            print(f"   📅 {date_info}")
            
            results[file_desc] = {
                'rows': rows,
                'cols': cols, 
                'sites': unique_sites,
                'dates': date_info,
                'site_column': site_col
            }
            
        except Exception as e:
            print(f"❌ {file_desc}: ERROR - {e}")
            results[file_desc] = None
    
    return results

def check_site_overlap():
    """
    Check which sites appear in which data files.
    """
    print("\n" + "=" * 60)
    print("SITE OVERLAP ANALYSIS")
    print("=" * 60)
    
    processed_dir = os.path.join(os.path.dirname(__file__), 'data', 'processed')
    
    # Load all site lists
    site_sets = {}
    
    # Master sites
    master_path = os.path.join(processed_dir, 'master_sites.csv')
    if os.path.exists(master_path):
        master_df = pd.read_csv(master_path)
        site_sets['Master'] = set(master_df['site_name'].dropna())
        print(f"📋 Master Sites: {len(site_sets['Master'])} sites")
    
    # Chemical data sites
    chemical_files = {
        'Original Chemical': ('cleaned_chemical_data.csv', 'SiteName'),
        'Updated Chemical': ('cleaned_updated_chemical_data.csv', 'Site Name')
    }
    
    for name, (filename, site_col) in chemical_files.items():
        file_path = os.path.join(processed_dir, filename)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            site_sets[name] = set(df[site_col].dropna())
            print(f"🧪 {name}: {len(site_sets[name])} sites")
    
    # Check overlaps
    if len(site_sets) >= 2:
        print(f"\n📊 Site Coverage Analysis:")
        
        if 'Master' in site_sets and 'Original Chemical' in site_sets:
            overlap = site_sets['Master'] & site_sets['Original Chemical']
            print(f"   Master ∩ Original Chemical: {len(overlap)} sites")
        
        if 'Master' in site_sets and 'Updated Chemical' in site_sets:
            overlap = site_sets['Master'] & site_sets['Updated Chemical']
            print(f"   Master ∩ Updated Chemical: {len(overlap)} sites")
        
        if 'Original Chemical' in site_sets and 'Updated Chemical' in site_sets:
            overlap = site_sets['Original Chemical'] & site_sets['Updated Chemical']
            print(f"   Original ∩ Updated Chemical: {len(overlap)} sites")
            
            # Sites only in updated
            only_updated = site_sets['Updated Chemical'] - site_sets['Original Chemical']
            if only_updated:
                print(f"   📈 Only in Updated Chemical: {len(only_updated)} sites")
                print(f"      Examples: {', '.join(list(only_updated)[:3])}")

def main():
    """
    Run all validation checks.
    """
    print(f"🔍 Starting validation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if we're in the right directory
    if not os.path.exists('data'):
        print("❌ ERROR: 'data' directory not found. Run this from your project root.")
        return False
    
    # Run validations
    results = validate_cleaned_files()
    check_site_overlap()
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results.values() if r is not None)
    total_count = len(results)
    
    print(f"✅ {success_count}/{total_count} files validated successfully")
    
    if success_count == total_count:
        print("🎉 All files ready for database loading!")
        return True
    else:
        print("⚠️  Some files missing or have issues. Check above for details.")
        return False

if __name__ == "__main__":
    success = main()