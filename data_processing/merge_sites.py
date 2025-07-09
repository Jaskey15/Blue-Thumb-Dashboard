"""
Identifies and merges duplicate sites based on coordinate proximity.

This module analyzes sites with nearly identical coordinates and merges them,
preserving all associated monitoring data by transferring it to a single,
preferred site record.

The preferred site is determined using a priority system:
1. Sites present in the `updated_chemical_data` source file.
2. Sites present in the `chemical_data` source file.
3. The site with the longest name (as a fallback).
"""

import pandas as pd
import os
from data_processing import setup_logging
from data_processing.data_loader import clean_site_name
from database.database import get_connection, close_connection


logger = setup_logging("merge_sites", category="processing")

def load_csv_files():
    """Loads cleaned source CSVs to check for site name existence."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Load cleaned CSVs from the interim directory for reference.
    site_data = pd.read_csv(os.path.join(base_dir, 'data', 'interim', 'cleaned_site_data.csv'))
    updated_chemical = pd.read_csv(os.path.join(base_dir, 'data', 'interim', 'cleaned_updated_chemical_data.csv'))
    chemical_data = pd.read_csv(os.path.join(base_dir, 'data', 'interim', 'cleaned_chemical_data.csv'))
    
    return site_data, updated_chemical, chemical_data

def find_duplicate_coordinate_groups(conn=None):
    """Finds groups of sites with identical coordinates, rounded to 3 decimal places."""
    if conn is None:
        conn = get_connection()
        should_close = True
    else:
        should_close = False
    
    try:
        query = """
        SELECT 
            site_id,
            site_name,
            ROUND(latitude, 3) as rounded_lat,
            ROUND(longitude, 3) as rounded_lon,
            latitude,
            longitude,
            county,
            river_basin,
            ecoregion
        FROM sites 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY rounded_lat, rounded_lon, site_name
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Group by rounded coordinates to identify sites at the same location.
        duplicate_groups = df.groupby(['rounded_lat', 'rounded_lon']).filter(lambda x: len(x) > 1)
        
        return duplicate_groups
    finally:
        if should_close:
            close_connection(conn)

def analyze_coordinate_duplicates():
    """
    Analyzes coordinate duplicates without making database changes.
    
    Returns:
        A dictionary with summary statistics for review.
    """
    logger.info("Analyzing coordinate duplicates...")
    
    try:
        site_data_df, updated_chemical_df, chemical_data_df = load_csv_files()
        
        updated_chemical_sites = set(updated_chemical_df['Site Name'].apply(clean_site_name))
        chemical_data_sites = set(chemical_data_df['SiteName'].apply(clean_site_name))
        
        conn = get_connection()
        duplicate_groups_df = find_duplicate_coordinate_groups(conn)
        close_connection(conn)
        
        if duplicate_groups_df.empty:
            logger.info("No coordinate duplicate sites found")
            return {
                'total_duplicate_sites': 0,
                'duplicate_groups': 0,
                'examples': []
            }
        
        duplicate_groups_summary = []
        total_duplicate_sites = len(duplicate_groups_df)
        group_count = 0
        
        # Process each group to determine which site would be kept.
        for (rounded_lat, rounded_lon), group in duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']):
            group_count += 1
            sites_in_group = list(group['site_name'])
            
            # Apply the same logic as the merge to predict the outcome.
            preferred_site, _, reason = determine_preferred_site(
                group, updated_chemical_sites, chemical_data_sites
            )
            
            group_info = {
                'coordinates': f"({rounded_lat}, {rounded_lon})",
                'site_count': len(group),
                'sites': sites_in_group,
                'would_keep': preferred_site['site_name'],
                'reason': reason
            }
            
            duplicate_groups_summary.append(group_info)
        
        logger.info(f"Found {total_duplicate_sites} duplicate sites in {group_count} coordinate groups")
        if total_duplicate_sites > group_count:
            logger.info(f"Would delete {total_duplicate_sites - group_count} duplicate sites")
        
        return {
            'total_duplicate_sites': total_duplicate_sites,
            'duplicate_groups': group_count,
            'examples': duplicate_groups_summary[:5],  # Provide first 5 for a sample.
            'all_groups': duplicate_groups_summary
        }
        
    except Exception as e:
        logger.error(f"Error analyzing coordinate duplicates: {e}")
        return None

def determine_preferred_site(group, updated_chemical_sites, chemical_data_sites):
    """
    Determines which site to keep from a group of duplicates.

    Returns:
        A tuple containing (preferred_site_row, sites_to_merge_list, reason).
    """
    if group.empty:
        return None, [], "Empty group"
    
    sites_in_updated = group[group['site_name'].isin(updated_chemical_sites)]
    sites_in_chemical = group[group['site_name'].isin(chemical_data_sites)]
    
    # Priority 1: Site exists in the `updated_chemical` source file.
    if len(sites_in_updated) > 1:
        # If multiple, prefer the one with the longest name.
        max_idx = sites_in_updated['site_name'].str.len().idxmax()
        preferred_site = sites_in_updated.loc[max_idx]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Multiple in updated_chemical - keeping longer name"
    
    elif len(sites_in_updated) == 1:
        preferred_site = sites_in_updated.iloc[0]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Found in updated_chemical"
    
    # Priority 2: Site exists in the `chemical_data` source file.
    elif len(sites_in_chemical) > 0:
        if len(sites_in_chemical) > 1:
            max_idx = sites_in_chemical['site_name'].str.len().idxmax()
            preferred_site = sites_in_chemical.loc[max_idx]
        else:
            preferred_site = sites_in_chemical.iloc[0]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Found in chemical_data"
    
    # Fallback: No source file matches, so pick the longest name.
    else:
        max_idx = group['site_name'].str.len().idxmax()
        preferred_site = group.loc[max_idx]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Arbitrary choice - longest name"

def transfer_site_data(cursor, from_site_id, to_site_id):
    """
    Transfers all monitoring data from a duplicate site to the preferred site.
    
    Returns: 
        A dictionary with counts of records transferred per table.
    """
    transfer_counts = {}
    
    # Convert numpy types to Python native types for SQLite compatibility
    from_site_id = int(from_site_id)
    to_site_id = int(to_site_id)
    
    # Verify both sites exist before attempting transfer
    cursor.execute("SELECT site_name FROM sites WHERE site_id = ?", (from_site_id,))
    from_site_result = cursor.fetchone()
    cursor.execute("SELECT site_name FROM sites WHERE site_id = ?", (to_site_id,))
    to_site_result = cursor.fetchone()
    
    if not from_site_result:
        logger.error(f"Source site_id {from_site_id} not found in database")
        raise Exception(f"Source site_id {from_site_id} not found")
    
    if not to_site_result:
        logger.error(f"Destination site_id {to_site_id} not found in database")
        raise Exception(f"Destination site_id {to_site_id} not found")
    
    tables_to_update = [
        ('chemical_collection_events', 'site_id'),
        ('fish_collection_events', 'site_id'),
        ('macro_collection_events', 'site_id'),
        ('habitat_assessments', 'site_id')
    ]
    
    for table_name, site_column in tables_to_update:
        try:
            # Check if there is data to transfer.
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {site_column} = ?", (from_site_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Perform the reassignment
                try:
                    cursor.execute(f"""
                        UPDATE {table_name} 
                        SET {site_column} = ? 
                        WHERE {site_column} = ?
                    """, (to_site_id, from_site_id))
                    
                    rows_affected = cursor.rowcount
                    
                    if rows_affected != count:
                        logger.warning(f"Expected to update {count} rows but updated {rows_affected} in {table_name}")
                    
                    transfer_counts[table_name] = rows_affected
                    
                except Exception as update_error:
                    logger.error(f"Failed to update {table_name}: {update_error}")
                    raise Exception(f"Failed to transfer data from {table_name}: {update_error}")
                    
            else:
                transfer_counts[table_name] = 0
                
        except Exception as e:
            logger.error(f"Error transferring data from {table_name}: {e}")
            raise
    
    return transfer_counts

def update_site_metadata(cursor, site_id, site_data_df, preferred_name):
    """Updates site metadata from site_data.csv if available."""
    # Convert numpy types to Python native types for SQLite compatibility
    site_id = int(site_id)
    
    metadata_row = site_data_df[site_data_df['SiteName'].str.strip() == preferred_name.strip()]
    
    if not metadata_row.empty:
        metadata = metadata_row.iloc[0]
        
        cursor.execute("""
            UPDATE sites 
            SET county = ?, river_basin = ?, ecoregion = ?
            WHERE site_id = ?
        """, (
            metadata.get('County'),
            metadata.get('RiverBasin'), 
            metadata.get('Mod_Ecoregion'),
            site_id
        ))
        
        return True
    else:
        return False

def update_csv_files_with_mapping(site_mapping):
    """
    Updates the cleaned CSV files to use preferred site names instead of deleted ones.
    
    Args:
        site_mapping: Dictionary mapping old site names to new site names
    """
    if not site_mapping:
        logger.info("No site mappings to apply to CSV files")
        return
    
    logger.info(f"Applying {len(site_mapping)} site name mappings to CSV files...")
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    interim_dir = os.path.join(base_dir, 'data', 'interim')
    
    # Define CSV files and their site name columns
    csv_configs = [
        {'file': 'cleaned_chemical_data.csv', 'site_column': 'SiteName'},
        {'file': 'cleaned_updated_chemical_data.csv', 'site_column': 'Site Name'},
        {'file': 'cleaned_fish_data.csv', 'site_column': 'SiteName'},
        {'file': 'cleaned_macro_data.csv', 'site_column': 'SiteName'},
        {'file': 'cleaned_habitat_data.csv', 'site_column': 'SiteName'},
    ]
    
    total_updates = 0
    files_updated = 0
    
    for config in csv_configs:
        file_path = os.path.join(interim_dir, config['file'])
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {config['file']}")
            continue
            
        try:
            # Load CSV
            df = pd.read_csv(file_path)
            
            if config['site_column'] not in df.columns:
                logger.warning(f"Site column '{config['site_column']}' not found in {config['file']}")
                continue
            
            # Apply site name mappings
            updates_in_file = 0
            
            for old_name, new_name in site_mapping.items():
                mask = df[config['site_column']] == old_name
                update_count = mask.sum()
                
                if update_count > 0:
                    df.loc[mask, config['site_column']] = new_name
                    updates_in_file += update_count
            
            # Save updated CSV if changes were made
            if updates_in_file > 0:
                df.to_csv(file_path, index=False)
                logger.info(f"Updated {config['file']}: {updates_in_file} records redirected")
                total_updates += updates_in_file
                files_updated += 1
                
        except Exception as e:
            logger.error(f"Error updating {config['file']}: {e}")
    
    if total_updates > 0:
        logger.info(f"CSV mapping complete: {total_updates} records updated across {files_updated} files")
    else:
        logger.info("No CSV updates needed - site names already current")

def merge_duplicate_sites():
    """Executes the merge process for all sites with the same coordinates."""
    logger.info("Starting coordinate-based site merge process...")
    
    try:
        site_data_df, updated_chemical_df, chemical_data_df = load_csv_files()
        
        updated_chemical_sites = set(updated_chemical_df['Site Name'].apply(clean_site_name))
        chemical_data_sites = set(chemical_data_df['SiteName'].apply(clean_site_name))
        
        conn = get_connection()
        cursor = conn.cursor()
        
        duplicate_groups_df = find_duplicate_coordinate_groups(conn)
        
        groups_processed = 0
        sites_deleted = 0
        total_records_transferred = 0
        site_mapping = {}  # Track mapping from deleted sites to preferred sites
        
        try:
            if not duplicate_groups_df.empty:
                logger.info(f"Found {len(duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']))} coordinate groups with duplicates")
                
                for (rounded_lat, rounded_lon), group in duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']):
                    preferred_site, sites_to_merge, reason = determine_preferred_site(
                        group, updated_chemical_sites, chemical_data_sites
                    )
                    
                    if not preferred_site is None and sites_to_merge:
                        # Verify preferred site exists before proceeding  
                        # Convert numpy types to Python native types for SQLite compatibility
                        preferred_site_id = int(preferred_site['site_id'])
                        
                        cursor.execute("SELECT site_name FROM sites WHERE site_id = ?", (preferred_site_id,))
                        preferred_site_check = cursor.fetchone()
                        
                        if not preferred_site_check:
                            logger.error(f"CRITICAL: Preferred site_id {preferred_site_id} ('{preferred_site['site_name']}') not found in database!")
                            raise Exception(f"Preferred site_id {preferred_site_id} not found in database")
                        
                        # Process all sites to merge in this group
                        for site_to_merge in sites_to_merge:
                            from_site_id = int(site_to_merge['site_id'])
                            
                            transfer_counts = transfer_site_data(cursor, from_site_id, preferred_site_id)
                            total_records_transferred += sum(transfer_counts.values())
                            
                            cursor.execute("DELETE FROM sites WHERE site_id = ?", (from_site_id,))
                            sites_deleted += 1
                            
                            # Add to site mapping
                            old_site_name = site_to_merge['site_name']
                            new_site_name = preferred_site['site_name']
                            site_mapping[old_site_name] = new_site_name
                        
                        update_site_metadata(cursor, preferred_site_id, site_data_df, preferred_site['site_name'])
                        
                        groups_processed += 1
            
            conn.commit()
            logger.info(f"Site merge complete: {groups_processed} groups processed, {sites_deleted} sites deleted, {total_records_transferred} records transferred")
            
            # Apply site name mapping to CSV files
            if site_mapping:
                update_csv_files_with_mapping(site_mapping)
            
            return {
                'groups_processed': groups_processed,
                'sites_deleted': sites_deleted,
                'records_transferred': total_records_transferred
            }
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during site merge: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Error in coordinate merge process: {e}")
        raise
    finally:
        if 'conn' in locals():
            close_connection(conn)

if __name__ == "__main__":
    # When run directly, analyze duplicates without merging.
    print("🔍 Analyzing coordinate duplicates...")
    
    analysis = analyze_coordinate_duplicates()
    
    if analysis:
        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"Total duplicate sites: {analysis['total_duplicate_sites']}")
        print(f"Duplicate groups: {analysis['duplicate_groups']}")
        print(f"Sites that would be deleted: {analysis['total_duplicate_sites'] - analysis['duplicate_groups']}")
        
        if analysis['duplicate_groups'] > 0:
            print(f"\n📝 Sample duplicate groups:")
            for i, group in enumerate(analysis['examples'], 1):
                print(f"{i}. {group['coordinates']}: {group['sites']} → Keep: {group['would_keep']}")
        
        print("\nTo execute the merge, call merge_duplicate_sites() function")
    else:
        print("❌ Analysis failed. Check logs for details.")