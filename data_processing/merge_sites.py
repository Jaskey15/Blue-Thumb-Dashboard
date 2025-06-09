import pandas as pd
import os
from utils import setup_logging
from data_processing.data_loader import clean_site_name
from database.database import get_connection, close_connection


# Set up logging
logger = setup_logging("merge_sites", category="processing")

def load_csv_files():
    """Load the relevant cleaned CSV files for site name checking."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Load CLEANED CSV files from processed directory
    site_data = pd.read_csv(os.path.join(base_dir, 'data', 'processed', 'cleaned_site_data.csv'))
    updated_chemical = pd.read_csv(os.path.join(base_dir, 'data', 'processed', 'cleaned_updated_chemical_data.csv'))
    chemical_data = pd.read_csv(os.path.join(base_dir, 'data', 'processed', 'cleaned_chemical_data.csv'))
    
    return site_data, updated_chemical, chemical_data

def find_duplicate_coordinate_groups():
    """Find groups of sites with the same coordinates (rounded to 3 decimal places)."""
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
    
    # Group by rounded coordinates and filter for duplicates
    duplicate_groups = df.groupby(['rounded_lat', 'rounded_lon']).filter(lambda x: len(x) > 1)
    
    return duplicate_groups

def analyze_coordinate_duplicates():
    """
    Analyze coordinate duplicates without making any changes.
    Returns summary statistics for review.
    """
    logger.info("Analyzing coordinate duplicates...")
    
    try:
        # Load CSV data for reference
        site_data_df, updated_chemical_df, chemical_data_df = load_csv_files()
        
        # Create sets of site names for fast lookup
        updated_chemical_sites = set(updated_chemical_df['Site Name'].apply(clean_site_name))
        chemical_data_sites = set(chemical_data_df['SiteName'].apply(clean_site_name))
        
        # Find duplicate groups
        duplicate_groups_df = find_duplicate_coordinate_groups()
        
        if duplicate_groups_df.empty:
            logger.info("No coordinate duplicate sites found")
            return {
                'total_duplicate_sites': 0,
                'duplicate_groups': 0,
                'examples': []
            }
        
        # Analyze the duplicates
        duplicate_groups_summary = []
        total_duplicate_sites = len(duplicate_groups_df)
        group_count = 0
        
        # Process each duplicate group for analysis
        for (rounded_lat, rounded_lon), group in duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']):
            group_count += 1
            sites_in_group = list(group['site_name'])
            
            # Determine preferred site using same logic as merge
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
            'examples': duplicate_groups_summary[:5],  # First 5 examples for display
            'all_groups': duplicate_groups_summary
        }
        
    except Exception as e:
        logger.error(f"Error analyzing coordinate duplicates: {e}")
        return None

def determine_preferred_site(group, updated_chemical_sites, chemical_data_sites):
    """
    Determine which site to keep and which to merge/delete for a duplicate group.
    
    Returns: (preferred_site_row, sites_to_merge_list, reason)
    """
    if group.empty:
        return None, [], "Empty group"
    
    sites_in_updated = group[group['site_name'].isin(updated_chemical_sites)]
    sites_in_chemical = group[group['site_name'].isin(chemical_data_sites)]
    
    # Case 1: Multiple sites in updated_chemical_data (merge case)
    if len(sites_in_updated) > 1:
        preferred_site = sites_in_updated.loc[sites_in_updated['site_name'].str.len().idxmax()]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Multiple in updated_chemical - keeping longer name"
    
    # Case 2: One site in updated_chemical_data
    elif len(sites_in_updated) == 1:
        preferred_site = sites_in_updated.iloc[0]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Found in updated_chemical"
    
    # Case 3: No sites in updated_chemical, check chemical_data
    elif len(sites_in_chemical) > 0:
        if len(sites_in_chemical) > 1:
            preferred_site = sites_in_chemical.loc[sites_in_chemical['site_name'].str.len().idxmax()]
        else:
            preferred_site = sites_in_chemical.iloc[0]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Found in chemical_data"
    
    # Case 4: Not found in either CSV - pick longest name arbitrarily
    else:
        preferred_site = group.loc[group['site_name'].str.len().idxmax()]
        sites_to_merge = group[group['site_id'] != preferred_site['site_id']].to_dict('records')
        return preferred_site, sites_to_merge, "Arbitrary choice - longest name"

def transfer_site_data(cursor, from_site_id, to_site_id):
    """
    Transfer all data from one site to another across all tables.
    
    Returns: Dictionary with counts of records transferred per table
    """
    transfer_counts = {}
    
    # Define the tables and their site_id column names
    tables_to_update = [
        ('chemical_collection_events', 'site_id'),
        ('fish_collection_events', 'site_id'),
        ('macro_collection_events', 'site_id'),
        ('habitat_assessments', 'site_id')
    ]
    
    for table_name, site_column in tables_to_update:
        try:
            # Count records to transfer
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {site_column} = ?", (from_site_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Transfer the records
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET {site_column} = ? 
                    WHERE {site_column} = ?
                """, (to_site_id, from_site_id))
                
                transfer_counts[table_name] = count
            else:
                transfer_counts[table_name] = 0
                
        except Exception as e:
            logger.error(f"Error transferring data from {table_name}: {e}")
            raise
    
    return transfer_counts

def update_site_metadata(cursor, site_id, site_data_df, preferred_name):
    """
    Update site metadata from site_data.csv if available.
    """
    # Find metadata for this site name in site_data.csv
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

def delete_duplicate_site(cursor, site_id, site_name):
    """Delete a duplicate site record."""
    cursor.execute("DELETE FROM sites WHERE site_id = ?", (site_id,))

def merge_duplicate_sites():
    """
    Main function to merge sites with the same coordinates.
    """
    logger.info("Starting coordinate-based site merge process...")
    
    try:
        # Load cleaned CSV data for reference
        site_data_df, updated_chemical_df, chemical_data_df = load_csv_files()
        
        # Create sets of site names for fast lookup
        updated_chemical_sites = set(updated_chemical_df['Site Name'].str.strip())
        chemical_data_sites = set(chemical_data_df['SiteName'].str.strip())
        
        # Find duplicate groups based on coordinates
        duplicate_groups_df = find_duplicate_coordinate_groups()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Track statistics
        groups_processed = 0
        sites_deleted = 0
        total_records_transferred = 0
        
        try:
            if not duplicate_groups_df.empty:
                logger.info(f"Processing {len(duplicate_groups_df)} sites in coordinate duplicate groups")
                
                # Process each duplicate group
                for (rounded_lat, rounded_lon), group in duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']):
                    # Determine preferred site
                    preferred_site, sites_to_merge, reason = determine_preferred_site(
                        group, updated_chemical_sites, chemical_data_sites
                    )
                    
                    # Transfer data from each site to be merged
                    for site_to_merge in sites_to_merge:
                        # Transfer all data
                        transfer_counts = transfer_site_data(
                            cursor, 
                            site_to_merge['site_id'], 
                            preferred_site['site_id']
                        )
                        
                        # Track total transfers
                        total_records_transferred += sum(transfer_counts.values())
                        
                        # Delete the duplicate site
                        delete_duplicate_site(cursor, site_to_merge['site_id'], site_to_merge['site_name'])
                        sites_deleted += 1
                    
                    # Update metadata for the preferred site
                    update_site_metadata(cursor, preferred_site['site_id'], site_data_df, preferred_site['site_name'])
                    
                    groups_processed += 1
                    
                    # Log progress for larger merges
                    if groups_processed % 10 == 0:
                        logger.info(f"Processed {groups_processed} duplicate groups...")
            else:
                logger.info("No coordinate duplicate sites found")
            
            # Commit all changes
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
    # When run directly, analyze duplicates without merging
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