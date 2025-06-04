import pandas as pd
import re
from difflib import SequenceMatcher
import os

def normalize_for_comparison(name):
    """Normalize a site name for comparison by removing extra whitespace and standardizing case"""
    if pd.isna(name):
        return ""
    return re.sub(r'\s+', ' ', str(name).strip().lower())

def find_similar_names(names, similarity_threshold=0.9):
    """Find groups of similar site names"""
    similar_groups = []
    processed = set()
    
    for i, name1 in enumerate(names):
        if i in processed:
            continue
            
        group = [name1]
        processed.add(i)
        
        for j, name2 in enumerate(names[i+1:], i+1):
            if j in processed:
                continue
                
            # Check similarity ratio
            similarity = SequenceMatcher(None, normalize_for_comparison(name1), 
                                       normalize_for_comparison(name2)).ratio()
            
            if similarity >= similarity_threshold:
                group.append(name2)
                processed.add(j)
        
        if len(group) > 1:
            similar_groups.append(group)
    
    return similar_groups

def analyze_site_names():
    """Analyze site names from all CSV files"""
    
    # Define file paths
    base_dir = "data/raw"  # Adjust if your path is different
    files = {
        'site_data': f'{base_dir}/site_data.csv',
        'chemical_data': f'{base_dir}/chemical_data.csv', 
        'updated_chemical': f'{base_dir}/updated_chemical_data.csv',
        'fish_data': f'{base_dir}/fish_data.csv',
        'macro_data': f'{base_dir}/macro_data.csv',
        'habitat_data': f'{base_dir}/habitat_data.csv'
    }
    
    all_names = {}
    
    # Load site names from each file
    for file_type, file_path in files.items():
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found, skipping...")
            continue
            
        try:
            if file_type == 'updated_chemical':
                df = pd.read_csv(file_path, encoding='cp1252')
                site_col = 'Site Name'
            else:
                df = pd.read_csv(file_path)
                site_col = 'SiteName'
            
            if site_col in df.columns:
                names = df[site_col].dropna().unique()
                all_names[file_type] = list(names)
                print(f"{file_type}: {len(names)} unique site names")
            else:
                print(f"Warning: {site_col} not found in {file_type}")
                
        except Exception as e:
            print(f"Error reading {file_type}: {e}")
    
    return all_names

def check_whitespace_issues(all_names):
    """Check for whitespace-only differences"""
    print("\n" + "="*60)
    print("WHITESPACE ANALYSIS")
    print("="*60)
    
    # Combine all unique names
    all_unique_names = set()
    for names_list in all_names.values():
        all_unique_names.update(names_list)
    
    # Group by normalized names (whitespace cleaned)
    normalized_groups = {}
    for name in all_unique_names:
        normalized = normalize_for_comparison(name)
        if normalized not in normalized_groups:
            normalized_groups[normalized] = []
        normalized_groups[normalized].append(name)
    
    # Find groups with multiple variations
    whitespace_issues = []
    for normalized, variations in normalized_groups.items():
        if len(variations) > 1:
            whitespace_issues.append(variations)
    
    print(f"Found {len(whitespace_issues)} groups of names that differ only by whitespace:")
    for i, group in enumerate(whitespace_issues, 1):
        print(f"\nGroup {i}:")
        for name in group:
            print(f"  '{name}'")
    
    return whitespace_issues

def check_similarity_issues(all_names):
    """Check for similar names with different similarity thresholds"""
    print("\n" + "="*60)
    print("SIMILARITY ANALYSIS")
    print("="*60)
    
    # Combine all unique names
    all_unique_names = list(set().union(*all_names.values()))
    
    # Check different similarity levels
    for threshold in [0.95, 0.9, 0.85]:
        print(f"\nSimilarity threshold {threshold}:")
        similar_groups = find_similar_names(all_unique_names, threshold)
        
        if similar_groups:
            print(f"Found {len(similar_groups)} groups of similar names:")
            for i, group in enumerate(similar_groups[:5], 1):  # Show first 5 groups
                print(f"  Group {i}: {group}")
            if len(similar_groups) > 5:
                print(f"  ... and {len(similar_groups) - 5} more groups")
        else:
            print("No similar name groups found")

def main():
    print("Site Name Analysis Tool")
    print("="*60)
    
    # Load all site names
    all_names = analyze_site_names()
    
    if not all_names:
        print("No data loaded. Please check file paths.")
        return
    
    # Check for whitespace issues (like your Tenmile Creek example)
    whitespace_issues = check_whitespace_issues(all_names)
    
    # Check for other similarity issues
    check_similarity_issues(all_names)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total whitespace-only variations: {len(whitespace_issues)}")
    
    # Show the Tenmile Creek example specifically
    tenmile_variations = []
    for group in whitespace_issues:
        if any('tenmile creek' in name.lower() and 'davis' in name.lower() for name in group):
            tenmile_variations = group
            break
    
    if tenmile_variations:
        print(f"\nTenmile Creek Davis variations found:")
        for name in tenmile_variations:
            print(f"  '{name}' (length: {len(name)})")

if __name__ == "__main__":
    main()