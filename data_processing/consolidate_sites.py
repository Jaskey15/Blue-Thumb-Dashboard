"""
consolidate_sites.py - Site Consolidation Pipeline

This script consolidates sites from all cleaned CSV files using name-based consolidation.
Creates a master sites table with best available metadata from priority sources.
"""

import os
import sys
import pandas as pd

# Add the parent directory to Python path so we can import utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from utils import setup_logging

# Set up logging
logger = setup_logging("consolidate_sites", category="preprocessing")

# Define directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')

# CSV file configurations in priority order (highest to lowest priority)
CSV_CONFIGS = [
    {
        'file': 'cleaned_site_data.csv',
        'site_column': 'SiteName',
        'lat_column': 'Latitude',
        'lon_column': 'Longitude',
        'county_column': 'County',
        'basin_column': 'RiverBasin',
        'ecoregion_column': 'Mod_Ecoregion',
        'description': 'Master site data'
    },
    {
        'file': 'cleaned_chemical_data.csv',
        'site_column': 'SiteName',
        'lat_column': 'Latitude',
        'lon_column': 'Longitude',
        'county_column': 'County',
        'basin_column': 'RiverBasin',
        'ecoregion_column': None,  # Not available in chemical data
        'description': 'Original chemical data'
    },
    {
        'file': 'cleaned_fish_data.csv',
        'site_column': 'SiteName',
        'lat_column': 'Latitude',
        'lon_column': 'Longitude',
        'county_column': None,  # Not readily available
        'basin_column': 'RiverBasin',
        'ecoregion_column': 'Mod_Ecoregion',
        'description': 'Fish community data'
    },
    {
        'file': 'cleaned_updated_chemical_data.csv',
        'site_column': 'Site Name',
        'lat_column': 'lat', 
        'lon_column': 'lon', 
        'county_column': 'CountyName',
        'basin_column': None, # Not available in this file
        'ecoregion_column': None, # Not available in this file
        'description': 'Updated chemical data'
    },
    {
        'file': 'cleaned_macro_data.csv',
        'site_column': 'SiteName',
        'lat_column': 'Latitude',
        'lon_column': 'Longitude',
        'county_column': None,  # Not available
        'basin_column': None,  # Not available
        'ecoregion_column': 'Mod_Ecoregion',
        'description': 'Macroinvertebrate data'
    },
    {
        'file': 'cleaned_habitat_data.csv',
        'site_column': 'SiteName',
        'lat_column': None,  # Not available in habitat data
        'lon_column': None,  # Not available in habitat data
        'county_column': None,
        'basin_column': 'RiverBasin',
        'ecoregion_column': None,
        'description': 'Habitat assessment data'
    }
]

def extract_sites_from_csv(config):
    """
    Extract unique sites and their metadata from a single CSV file.
    
    Args:
        config: Configuration dictionary for the CSV file
        
    Returns:
        DataFrame with unique sites and their metadata
    """
    file_path = os.path.join(PROCESSED_DATA_DIR, config['file'])
    
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {config['file']}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path, low_memory=False)
        logger.info(f"Loaded {len(df)} rows from {config['file']}")
        
        # Check if site column exists
        if config['site_column'] not in df.columns:
            logger.error(f"Site column '{config['site_column']}' not found in {config['file']}")
            return pd.DataFrame()
        
        # Extract unique sites
        unique_sites = df.drop_duplicates(subset=[config['site_column']])
        
        # Build the site metadata DataFrame
        site_data = pd.DataFrame()
        site_data['site_name'] = unique_sites[config['site_column']].str.strip()
        
        # Extract metadata columns if they exist
        for metadata_field, column_name in [
            ('latitude', config['lat_column']),
            ('longitude', config['lon_column']),
            ('county', config['county_column']),
            ('river_basin', config['basin_column']),
            ('ecoregion', config['ecoregion_column'])
        ]:
            if column_name and column_name in df.columns:
                site_data[metadata_field] = unique_sites[column_name]
            else:
                site_data[metadata_field] = None
        
        # Add source tracking
        site_data['source_file'] = config['file']
        site_data['source_description'] = config['description']
        
        # Remove any sites with null/empty names
        site_data = site_data[site_data['site_name'].notna() & (site_data['site_name'] != '')]
        
        logger.info(f"Extracted {len(site_data)} unique sites from {config['file']}")
        return site_data
        
    except Exception as e:
        logger.error(f"Error processing {config['file']}: {e}")
        return pd.DataFrame()

def detect_conflicts(site_name, existing_site, new_site):
    """
    Check if two site records have conflicting metadata.
    
    Args:
        site_name: Name of the site being compared
        existing_site: Series with existing site data
        new_site: Series with new site data
        
    Returns:
        List of conflict descriptions, empty if no conflicts
    """
    conflicts = []
    
    # Check each metadata field for conflicts
    for field in ['latitude', 'longitude', 'county', 'river_basin', 'ecoregion']:
        existing_val = existing_site.get(field)
        new_val = new_site.get(field)
        
        # Only flag as conflict if both values exist and are different
        if (pd.notna(existing_val) and pd.notna(new_val) and 
            existing_val != new_val):
            conflicts.append(f"{field}: '{existing_val}' vs '{new_val}'")
    
    return conflicts

def consolidate_sites():
    """
    Main function to consolidate sites from all cleaned CSV files.
    
    Returns:
        Tuple of (consolidated_sites_df, conflicts_df)
    """
    logger.info("Starting site consolidation process...")
    
    consolidated_sites = pd.DataFrame()
    conflicts_list = []
    
    # Process each CSV file in priority order
    for i, config in enumerate(CSV_CONFIGS):
        logger.info(f"\nProcessing priority {i+1}: {config['description']}")
        
        # Extract sites from this CSV
        csv_sites = extract_sites_from_csv(config)
        
        if csv_sites.empty:
            logger.warning(f"No sites extracted from {config['file']}")
            continue
        
        sites_added = 0
        sites_updated = 0
        conflicts_found = 0
        
        # Process each site from this CSV
        for _, new_site in csv_sites.iterrows():
            site_name = new_site['site_name']
            
            # Check if site already exists in consolidated data
            if not consolidated_sites.empty and site_name in consolidated_sites['site_name'].values:
                # Site exists - check for conflicts and update missing metadata
                existing_idx = consolidated_sites[consolidated_sites['site_name'] == site_name].index[0]
                existing_site = consolidated_sites.loc[existing_idx]
                
                # Check for conflicts
                conflicts = detect_conflicts(site_name, existing_site, new_site)
                
                if conflicts:
                    # Record conflict for manual review
                    conflict_record = {
                        'site_name': site_name,
                        'conflicts': conflicts,
                        'existing_source': existing_site['source_file'],
                        'new_source': new_site['source_file'],
                        'existing_data': existing_site.to_dict(),
                        'new_data': new_site.to_dict()
                    }
                    conflicts_list.append(conflict_record)
                    conflicts_found += 1
                    logger.warning(f"Conflict detected for '{site_name}': {', '.join(conflicts)}")
                else:
                    # No conflicts - update missing metadata from lower priority source
                    updated = False
                    for field in ['latitude', 'longitude', 'county', 'river_basin', 'ecoregion']:
                        if (pd.isna(existing_site[field]) and pd.notna(new_site[field])):
                            consolidated_sites.loc[existing_idx, field] = new_site[field]
                            consolidated_sites.loc[existing_idx, f'{field}_source'] = new_site['source_file']
                            updated = True
                    
                    if updated:
                        sites_updated += 1
            else:
                # New site - add to consolidated data
                new_record = new_site.copy()
                
                # Add source tracking for each field
                for field in ['latitude', 'longitude', 'county', 'river_basin', 'ecoregion']:
                    if pd.notna(new_site[field]):
                        new_record[f'{field}_source'] = new_site['source_file']
                    else:
                        new_record[f'{field}_source'] = None
                
                consolidated_sites = pd.concat([consolidated_sites, new_record.to_frame().T], ignore_index=True)
                sites_added += 1
        
        logger.info(f"  Added: {sites_added} new sites")
        logger.info(f"  Updated: {sites_updated} existing sites")
        if conflicts_found > 0:
            logger.warning(f"  Conflicts: {conflicts_found} sites flagged for review")
    
    # Create conflicts DataFrame
    conflicts_df = pd.DataFrame(conflicts_list) if conflicts_list else pd.DataFrame()
    
    logger.info(f"\nConsolidation complete!")
    logger.info(f"Total consolidated sites: {len(consolidated_sites)}")
    logger.info(f"Total conflicts for review: {len(conflicts_df)}")
    
    return consolidated_sites, conflicts_df

def save_consolidated_data(consolidated_sites, conflicts_df):
    """
    Save the consolidated sites and conflicts to CSV files.
    
    Args:
        consolidated_sites: DataFrame with consolidated site data
        conflicts_df: DataFrame with conflicts that need manual review
    """
    # Save consolidated sites
    consolidated_path = os.path.join(PROCESSED_DATA_DIR, 'master_sites.csv')
    consolidated_sites.to_csv(consolidated_path, index=False, encoding='utf-8')
    logger.info(f"Saved consolidated sites to: master_sites.csv")
    
    # Save conflicts if any exist
    if not conflicts_df.empty:
        conflicts_path = os.path.join(PROCESSED_DATA_DIR, 'site_conflicts_for_review.csv')
        conflicts_df.to_csv(conflicts_path, index=False, encoding='utf-8')
        logger.warning(f"Saved {len(conflicts_df)} conflicts to: site_conflicts_for_review.csv")
        logger.warning("⚠️  Manual review required for conflicting sites!")
    else:
        logger.info("✓ No conflicts detected - all sites consolidated cleanly")

def main():
    """
    Main execution function.
    """
    logger.info("=" * 60)
    logger.info("SITE CONSOLIDATION - PHASE 2A")
    logger.info("=" * 60)
    
    # Run consolidation
    consolidated_sites, conflicts_df = consolidate_sites()
    
    if consolidated_sites.empty:
        logger.error("No sites were consolidated. Check input files.")
        return False
    
    # Save results
    save_consolidated_data(consolidated_sites, conflicts_df)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("CONSOLIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✓ Consolidated {len(consolidated_sites)} unique sites")
    logger.info(f"✓ Created master_sites.csv")
    
    if not conflicts_df.empty:
        logger.warning(f"⚠️  {len(conflicts_df)} conflicts need manual review")
        logger.warning("⚠️  See site_conflicts_for_review.csv")
    
    logger.info("\nNext steps:")
    logger.info("1. Review any conflicts flagged above")
    logger.info("2. Load master_sites.csv into database")
    logger.info("3. Update processors to use cleaned CSVs")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)