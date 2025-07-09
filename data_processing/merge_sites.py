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

def find_duplicate_coordinate_groups():
    """Finds groups of sites with identical coordinates, rounded to 3 decimal places."""
    conn = get_connection()
    
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
    close_connection(conn)
    
    # Group by rounded coordinates to identify sites at the same location.
    duplicate_groups = df.groupby(['rounded_lat', 'rounded_lon']).filter(lambda x: len(x) > 1)
    
    return duplicate_groups

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
        
        duplicate_groups_df = find_duplicate_coordinate_groups()
        
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
        
        logger.info(f"Found {total_duplicate_sites} sites in {group_count} coordinate duplicate groups")
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
        preferred_site = sites_in_updated.loc[sites_in_updated['site_name'].str.len().idxmax()]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Multiple in updated_chemical - keeping longer name"
    
    elif len(sites_in_updated) == 1:
        preferred_site = sites_in_updated.iloc[0]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Found in updated_chemical"
    
    # Priority 2: Site exists in the `chemical_data` source file.
    elif len(sites_in_chemical) > 0:
        if len(sites_in_chemical) > 1:
            preferred_site = sites_in_chemical.loc[sites_in_chemical['site_name'].str.len().idxmax()]
        else:
            preferred_site = sites_in_chemical.iloc[0]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Found in chemical_data"
    
    # Fallback: No source file matches, so pick the longest name.
    else:
        preferred_site = group.loc[group['site_name'].str.len().idxmax()]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Arbitrary choice - longest name"

def transfer_site_data(cursor, from_site_id, to_site_id):
    """
    Transfers all monitoring data from a duplicate site to the preferred site.
    
    Returns: 
        A dictionary with counts of records transferred per table.
    """
    transfer_counts = {}
    
    logger.info(f"    Transferring data from site_id {from_site_id} to site_id {to_site_id}")
    
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
    
    logger.debug(f"    Source site: {from_site_result[0]}")
    logger.debug(f"    Destination site: {to_site_result[0]}")
    
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
            
            logger.debug(f"    {table_name}: {count} records to transfer")
            
            if count > 0:
                # Log a sample of what we're about to update
                cursor.execute(f"SELECT * FROM {table_name} WHERE {site_column} = ? LIMIT 3", (from_site_id,))
                sample_records = cursor.fetchall()
                logger.debug(f"    Sample records from {table_name}: {sample_records}")
                
                # Check for potential conflicts at the destination
                if table_name == 'chemical_collection_events':
                    cursor.execute('''
                        SELECT COUNT(*) FROM chemical_collection_events c1
                        JOIN chemical_collection_events c2 ON 
                            c1.sample_id = c2.sample_id AND 
                            c1.collection_date = c2.collection_date
                        WHERE c1.site_id = ? AND c2.site_id = ?
                    ''', (from_site_id, to_site_id))
                    conflicts = cursor.fetchone()[0]
                    if conflicts > 0:
                        logger.warning(f"    Potential UNIQUE constraint conflicts in {table_name}: {conflicts}")
                
                # Perform the reassignment with extensive error handling
                try:
                    logger.debug(f"    Executing UPDATE {table_name} SET {site_column} = {to_site_id} WHERE {site_column} = {from_site_id}")
                    
                    cursor.execute(f"""
                        UPDATE {table_name} 
                        SET {site_column} = ? 
                        WHERE {site_column} = ?
                    """, (to_site_id, from_site_id))
                    
                    rows_affected = cursor.rowcount
                    logger.debug(f"    Successfully updated {rows_affected} rows in {table_name}")
                    
                    if rows_affected != count:
                        logger.warning(f"    Expected to update {count} rows but actually updated {rows_affected} rows")
                    
                    transfer_counts[table_name] = rows_affected
                    
                except Exception as update_error:
                    logger.error(f"    Failed to update {table_name}: {update_error}")
                    logger.error(f"    Update query: UPDATE {table_name} SET {site_column} = {to_site_id} WHERE {site_column} = {from_site_id}")
                    
                    # Additional debugging - check the current state
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {site_column} = ?", (from_site_id,))
                    current_count = cursor.fetchone()[0]
                    logger.error(f"    Records still at source site after failed update: {current_count}")
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {site_column} = ?", (to_site_id,))
                    dest_count = cursor.fetchone()[0]
                    logger.error(f"    Records at destination site: {dest_count}")
                    
                    # Re-raise the error with more context
                    raise Exception(f"Failed to transfer data from {table_name}: {update_error}")
                    
            else:
                transfer_counts[table_name] = 0
                
        except Exception as e:
            logger.error(f"Error transferring data from {table_name}: {e}")
            raise
    
    logger.info(f"    Transfer completed. Total records transferred: {sum(transfer_counts.values())}")
    return transfer_counts

def update_site_metadata(cursor, site_id, site_data_df, preferred_name):
    """Updates site metadata from site_data.csv if available."""
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
        logger.debug(f"No metadata found in site_data.csv for {preferred_name}")
        return False

def merge_duplicate_sites():
    """Executes the merge process for all sites with the same coordinates."""
    logger.info("Starting coordinate-based site merge process...")
    
    try:
        site_data_df, updated_chemical_df, chemical_data_df = load_csv_files()
        
        updated_chemical_sites = set(updated_chemical_df['Site Name'].str.strip())
        chemical_data_sites = set(chemical_data_df['SiteName'].str.strip())
        
        duplicate_groups_df = find_duplicate_coordinate_groups()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        groups_processed = 0
        sites_deleted = 0
        total_records_transferred = 0
        
        try:
            if not duplicate_groups_df.empty:
                logger.info(f"Processing {len(duplicate_groups_df)} sites in coordinate duplicate groups")
                
                for (rounded_lat, rounded_lon), group in duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']):
                    preferred_site, sites_to_merge, reason = determine_preferred_site(
                        group, updated_chemical_sites, chemical_data_sites
                    )
                    
                    for site_to_merge in sites_to_merge:
                        transfer_counts = transfer_site_data(
                            cursor, 
                            site_to_merge['site_id'], 
                            preferred_site['site_id']
                        )
                        
                        total_records_transferred += sum(transfer_counts.values())
                        
                        cursor.execute("DELETE FROM sites WHERE site_id = ?", (site_to_merge['site_id'],))
                        sites_deleted += 1
                    
                    update_site_metadata(cursor, preferred_site['site_id'], site_data_df, preferred_site['site_name'])
                    
                    groups_processed += 1
                    
                    if groups_processed % 10 == 0:
                        logger.info(f"Processed {groups_processed} duplicate groups...")
            else:
                logger.info("No coordinate duplicate sites found")
            
            conn.commit()
            
            logger.info(f"Coordinate-based merge complete!")
            logger.info(f"Groups processed: {groups_processed}")
            logger.info(f"Sites deleted: {sites_deleted}")
            logger.info(f"Records transferred: {total_records_transferred}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during coordinate merge, rolling back: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error in coordinate-based site merge: {e}")
        return False
        
    finally:
        if conn:
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