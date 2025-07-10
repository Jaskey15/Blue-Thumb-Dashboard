"""
Manages the processing and loading of site information into the database.

This module handles loading consolidated site data from `master_sites.csv`,
inserting it into the database, classifying sites as active or historic,
and removing sites that have no associated monitoring data.
"""

import os
from datetime import datetime, timedelta

import pandas as pd

from data_processing import setup_logging
from data_processing.data_loader import PROCESSED_DATA_DIR
from database.database import close_connection, get_connection

logger = setup_logging("site_processing", category="processing")

def load_site_data():
    """
    Loads and prepares site information from the master_sites.csv file.
    
    Returns:
        A DataFrame with site information ready for database insertion.
    """
    try:
        master_sites_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'processed', 'master_sites.csv'
        )
        
        if not os.path.exists(master_sites_path):
            logger.error("master_sites.csv not found. Run site consolidation first.")
            return pd.DataFrame()
        
        site_df = pd.read_csv(master_sites_path)
        
        # Filter the DataFrame to include only columns that exist in the database schema.
        database_columns = ['site_name', 'latitude', 'longitude', 'county', 'river_basin', 'ecoregion']
        
        available_columns = [col for col in database_columns if col in site_df.columns]
        missing_columns = [col for col in database_columns if col not in site_df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns in master_sites.csv: {missing_columns}")
        
        if 'site_name' not in available_columns:
            logger.error("Required site_name column missing from master_sites.csv")
            return pd.DataFrame()
        
        sites_df = site_df[available_columns].copy()
        
        if 'latitude' in sites_df.columns:
            sites_df['latitude'] = pd.to_numeric(sites_df['latitude'], errors='coerce')
        if 'longitude' in sites_df.columns:
            sites_df['longitude'] = pd.to_numeric(sites_df['longitude'], errors='coerce')
        
        # Ensure site names are unique as a final safety check.
        sites_df = sites_df.drop_duplicates(subset=['site_name']).copy()
        
        logger.info(f"Processed {len(sites_df)} unique sites for database")
        
        # Save the database-ready data for auditing and review.
        sites_for_db_path = os.path.join(PROCESSED_DATA_DIR, 'sites_for_db.csv')
        sites_df.to_csv(sites_for_db_path, index=False)
        
        return sites_df
    
    except Exception as e:
        logger.error(f"Error loading site data: {e}")
        return pd.DataFrame()

def insert_sites_into_db(sites_df):
    """
    Inserts or updates site data in the database.
    
    Uses INSERT OR IGNORE followed by UPDATE to avoid foreign key constraint 
    issues when sites already exist with child records.
    
    Args:
        sites_df: A DataFrame containing the site information to load.
    
    Returns:
        The number of sites inserted or updated.
    """
    if sites_df.empty:
        logger.warning("No site data to insert into database")
        return 0
    
    conn = get_connection()
    
    try:
        if 'site_name' not in sites_df.columns:
            logger.error("Missing required column 'site_name' in site data")
            return 0
        
        sites_df['site_name'] = sites_df['site_name'].astype(str)
        
        columns = sites_df.columns.tolist()
        
        cursor = conn.cursor()
        sites_inserted = 0
        sites_updated = 0
        
        for _, row in sites_df.iterrows():
            site_name = row['site_name']
            
            # Check if site already exists
            cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
            existing_site = cursor.fetchone()
            
            if existing_site:
                # Site exists - UPDATE it (avoids foreign key constraint issues)
                site_id = existing_site[0]
                
                # Build UPDATE statement for non-site_name columns
                update_columns = [col for col in columns if col != 'site_name']
                if update_columns:
                    set_clause = ', '.join([f"{col} = ?" for col in update_columns])
                    update_sql = f"UPDATE sites SET {set_clause} WHERE site_id = ?"
                    update_values = [row[col] for col in update_columns] + [site_id]
                    
                    cursor.execute(update_sql, update_values)
                    sites_updated += 1
                
            else:
                # Site doesn't exist - INSERT it
                placeholders = ', '.join(['?' for _ in columns])
                columns_str = ', '.join(columns)
                insert_sql = f"INSERT INTO sites ({columns_str}) VALUES ({placeholders})"
                insert_values = [row[col] for col in columns]
                
                cursor.execute(insert_sql, insert_values)
                sites_inserted += 1
        
        conn.commit()
        
        total_processed = sites_inserted + sites_updated
        logger.info(f"Site database operations: {sites_inserted} inserted, {sites_updated} updated")
        
        return total_processed
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting/updating site data: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 0
    
    finally:
        close_connection(conn)

def process_site_data():
    """
    Executes the full pipeline to load and process site data.
    
    Returns:
        True if the process completes, False otherwise.
    """
    try:
        sites_df = load_site_data()
        
        if sites_df.empty:
            logger.error("Failed to load consolidated site data")
            return False
        
        sites_count = insert_sites_into_db(sites_df)
        
        logger.info(f"Site processing complete: {sites_count} sites processed")
        
        return True
            
    except Exception as e:
        logger.error(f"Error processing site data: {e}")
        return False

def cleanup_unused_sites():
    """
    Removes sites from the database that have no associated monitoring data.
    
    Returns:
        True if successful, False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Identify all sites that have at least one record in any monitoring table.
        cursor.execute('''
            SELECT DISTINCT site_id FROM (
                SELECT site_id FROM chemical_collection_events
                UNION
                SELECT site_id FROM fish_collection_events  
                UNION
                SELECT site_id FROM macro_collection_events
                UNION  
                SELECT site_id FROM habitat_assessments
            )
        ''')
        
        sites_with_data = {row[0] for row in cursor.fetchall()}
        
        cursor.execute('SELECT site_id FROM sites')
        all_sites = {row[0] for row in cursor.fetchall()}
        
        # Determine which sites have no data by finding the difference.
        unused_sites = all_sites - sites_with_data
        
        if unused_sites:
            placeholders = ','.join(['?' for _ in unused_sites])
            cursor.execute(f'DELETE FROM sites WHERE site_id IN ({placeholders})', list(unused_sites))
            conn.commit()
            
            logger.info(f"Removed {len(unused_sites)} unused sites")
        else:
            logger.info("No unused sites found")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning up unused sites: {e}")
        return False
    finally:
        close_connection(conn)

def classify_active_sites():
    """
    Classifies sites as active or historic based on recent chemical data.
    
    A site is "active" if it has a chemical reading within one year of the
    most recent reading date across all sites. Otherwise, it is "historic".
    
    Returns:
        True if classification was successful, False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Step 1: Find the most recent chemical reading date across all sites
        cursor.execute("""
            SELECT MAX(collection_date) 
            FROM chemical_collection_events
        """)
        
        result = cursor.fetchone()
        if not result or not result[0]:
            logger.warning("No chemical data found - cannot classify active sites")
            return False
            
        most_recent_date = result[0]
        
        # Step 2: Calculate cutoff date (1 year before most recent reading)
        most_recent_dt = datetime.strptime(most_recent_date, '%Y-%m-%d')
        cutoff_date = most_recent_dt - timedelta(days=365)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Step 3: Get the most recent chemical reading date for each site
        cursor.execute("""
            SELECT s.site_id, s.site_name, MAX(c.collection_date) as last_reading
            FROM sites s
            LEFT JOIN chemical_collection_events c ON s.site_id = c.site_id
            GROUP BY s.site_id, s.site_name
        """)
        
        sites_data = cursor.fetchall()
        active_count = 0
        historic_count = 0
        
        # Step 4: Update each site's active status
        for site_id, site_name, last_reading in sites_data:
            if last_reading and last_reading >= cutoff_date_str:
                cursor.execute("""
                    UPDATE sites 
                    SET active = 1, last_chemical_reading_date = ?
                    WHERE site_id = ?
                """, (last_reading, site_id))
                active_count += 1
            else:
                cursor.execute("""
                    UPDATE sites 
                    SET active = 0, last_chemical_reading_date = ?
                    WHERE site_id = ?
                """, (last_reading, site_id))
                historic_count += 1
        
        conn.commit()
        
        logger.info(f"Site classification complete: {active_count} active, {historic_count} historic")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error classifying active sites: {e}")
        return False
    finally:
        close_connection(conn)

if __name__ == "__main__":
    success = process_site_data()
    if success:
        print("Site processing completed successfully!")
        # Display total site count after processing.
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sites")
            site_count = cursor.fetchone()[0]
            print(f"Total sites: {site_count}")
        except Exception as e:
            print(f"Could not retrieve site count: {e}")
        finally:
            close_connection(conn)
    else:
        print("Site processing failed. Check the log for details.")