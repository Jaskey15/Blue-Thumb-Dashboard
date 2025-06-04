import pandas as pd
import sqlite3
import os
from utils import setup_logging
from database.database import get_connection, close_connection

# Set up logging
logger = setup_logging("merge_sites", category="processing")

def load_csv_files():
    """Load the relevant CSV files for site name checking."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Load site_data.csv for metadata and names
    site_data = pd.read_csv(os.path.join(base_dir, 'data', 'raw', 'site_data.csv'))
    
    # Load updated_chemical_data.csv for preferred names
    updated_chemical = pd.read_csv(
        os.path.join(base_dir, 'data', 'raw', 'updated_chemical_data.csv'), 
        encoding='cp1252'
    )
    
    # Load chemical_data.csv for fallback names
    chemical_data = pd.read_csv(os.path.join(base_dir, 'data', 'raw', 'chemical_data.csv'))
    
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
        ecoregion,
        active
    FROM sites 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY rounded_lat, rounded_lon, site_name
    """
    
    df = pd.read_sql_query(query, conn)
    close_connection(conn)
    
    # Group by rounded coordinates and filter for duplicates
    duplicate_groups = df.groupby(['rounded_lat', 'rounded_lon']).filter(lambda x: len(x) > 1)
    
    return duplicate_groups

def determine_preferred_site(group, updated_chemical_sites, chemical_data_sites):
    """
    Determine which site to keep and which to merge/delete for a duplicate group.
    
    Returns: (preferred_site_row, sites_to_merge_list, reason)
    """
    sites_in_updated = group[group['site_name'].isin(updated_chemical_sites)]
    sites_in_chemical = group[group['site_name'].isin(chemical_data_sites)]
    
    # Case 1: Multiple sites in updated_chemical_data (merge case)
    if len(sites_in_updated) > 1:
        # Keep the site with the longer name
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
        # If multiple in chemical_data, pick the longer name
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
                logger.info(f"Transferred {count} records from {table_name}")
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
        
        logger.info(f"Updated metadata for site {preferred_name}")
        return True
    else:
        logger.warning(f"No metadata found in site_data.csv for {preferred_name}")
        return False

def delete_duplicate_site(cursor, site_id, site_name):
    """Delete a duplicate site record."""
    cursor.execute("DELETE FROM sites WHERE site_id = ?", (site_id,))
    logger.info(f"Deleted duplicate site: {site_name} (ID: {site_id})")

def merge_duplicate_sites():
    """
    Main function to merge sites with the same coordinates and clean up site names.
    """
    logger.info("Starting site merge and cleanup process...")
    
    try:
        # Load CSV data for reference
        site_data_df, updated_chemical_df, chemical_data_df = load_csv_files()
        
        # Create sets of site names for fast lookup
        updated_chemical_sites = set(updated_chemical_df['Site Name'].str.strip())
        chemical_data_sites = set(chemical_data_df['SiteName'].str.strip())
        
        # Find duplicate groups
        duplicate_groups_df = find_duplicate_coordinate_groups()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Track statistics
        groups_processed = 0
        sites_merged = 0
        sites_deleted = 0
        
        try:
            # Only process coordinate duplicates if they exist
            if not duplicate_groups_df.empty:
                logger.info(f"Found {len(duplicate_groups_df)} sites in coordinate duplicate groups")
                
                # Process each duplicate group
                for (rounded_lat, rounded_lon), group in duplicate_groups_df.groupby(['rounded_lat', 'rounded_lon']):
                    logger.info(f"Processing duplicate group at ({rounded_lat}, {rounded_lon})")
                    logger.info(f"Sites in group: {list(group['site_name'])}")
                    
                    # Determine preferred site
                    preferred_site, sites_to_merge, reason = determine_preferred_site(
                        group, updated_chemical_sites, chemical_data_sites
                    )
                    
                    logger.info(f"Keeping: {preferred_site['site_name']} - {reason}")
                    
                    # Transfer data from each site to be merged
                    for site_to_merge in sites_to_merge:
                        logger.info(f"Merging data from: {site_to_merge['site_name']}")
                        
                        # Transfer all data
                        transfer_counts = transfer_site_data(
                            cursor, 
                            site_to_merge['site_id'], 
                            preferred_site['site_id']
                        )
                        
                        # Log transfer details
                        total_transferred = sum(transfer_counts.values())
                        logger.info(f"Total records transferred: {total_transferred}")
                        
                        # Delete the duplicate site
                        delete_duplicate_site(cursor, site_to_merge['site_id'], site_to_merge['site_name'])
                        sites_deleted += 1
                    
                    # Update metadata for the preferred site
                    update_site_metadata(cursor, preferred_site['site_id'], site_data_df, preferred_site['site_name'])
                    
                    groups_processed += 1
                    sites_merged += len(sites_to_merge)
            else:
                logger.info("No coordinate duplicate sites found!")
            
            # Always run site name cleanup
            logger.info("Running site name cleanup...")
            cleanup_success = cleanup_site_names()
            
            if cleanup_success:
                logger.info("Site name cleanup completed successfully")
            else:
                logger.warning("Site name cleanup had some issues but continued")
            
            # Commit all changes
            conn.commit()
            
            logger.info(f"Process complete!")
            logger.info(f"Coordinate duplicate groups processed: {groups_processed}")
            logger.info(f"Sites merged: {sites_merged}")
            logger.info(f"Sites deleted: {sites_deleted}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during merge and cleanup, rolling back: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error in site merge: {e}")
        return False
        
    finally:
        if conn:
            close_connection(conn)

if __name__ == "__main__":
    success = merge_duplicate_sites()
    if success:
        print("Site merge completed successfully!")
    else:
        print("Site merge failed. Check logs for details.")