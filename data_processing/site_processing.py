"""
site_processing.py - Site Information Processing and Database Management

This module manages site information processing for the Blue Thumb Water Quality Dashboard.
Loads consolidated site data from master_sites.csv and manages the sites table in the database.
Handles site metadata extraction, database operations, and site classification.

Key Functions:
- process_site_data(): Main pipeline to load sites from master_sites.csv into database
- create_sites_table(): Create the sites table schema
- insert_sites_into_db(): Insert site records into database
- get_site_by_name(), get_site_id(): Query functions for site data
- cleanup_unused_sites(): Remove sites with no monitoring data
- classify_active_sites(): Mark sites as active/historic based on recent data

Usage:
- Run directly to process site data from master_sites.csv
- Import functions for site database operations in other modules
"""

import os
import pandas as pd
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data, clean_site_name
from database.database import get_connection, close_connection
from data_processing import setup_logging

# Initialize logger
logger = setup_logging("site_processing", category="processing")

def create_sites_table():
    """Create the sites table in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sites (
        site_id INTEGER PRIMARY KEY,
        site_name TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        county TEXT,
        river_basin TEXT,
        ecoregion TEXT,
        UNIQUE(site_name)
    )
    ''')
    
    conn.commit()
    logger.info("Sites table created successfully")
    close_connection(conn)

def load_site_data():
    """
    Load site information from MASTER_SITES.CSV file (consolidated data).
    Returns a DataFrame with essential site information.
    """
    try:
        # Load from master_sites.csv
        master_sites_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'processed', 'master_sites.csv'
        )
        
        if not os.path.exists(master_sites_path):
            logger.error("master_sites.csv not found. Run site consolidation first.")
            return pd.DataFrame()
        
        site_df = pd.read_csv(master_sites_path)
        logger.info(f"Loaded {len(site_df)} sites from master_sites.csv")
        
        # FILTER TO ONLY DATABASE SCHEMA COLUMNS
        database_columns = ['site_name', 'latitude', 'longitude', 'county', 'river_basin', 'ecoregion']
        
        # Check which columns exist
        available_columns = [col for col in database_columns if col in site_df.columns]
        missing_columns = [col for col in database_columns if col not in site_df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns in master_sites.csv: {missing_columns}")
        
        if 'site_name' not in available_columns:
            logger.error("Required site_name column missing from master_sites.csv")
            return pd.DataFrame()
        
        # Select only the columns that match the database schema
        sites_df = site_df[available_columns].copy()
        
        # Convert latitude and longitude to numeric types
        if 'latitude' in sites_df.columns:
            sites_df['latitude'] = pd.to_numeric(sites_df['latitude'], errors='coerce')
        if 'longitude' in sites_df.columns:
            sites_df['longitude'] = pd.to_numeric(sites_df['longitude'], errors='coerce')
        
        # Drop duplicates (should already be unique, but safety check)
        sites_df = sites_df.drop_duplicates(subset=['site_name']).copy()
        
        logger.info(f"Processed {len(sites_df)} unique sites with database schema columns")
        logger.info(f"Using columns: {list(sites_df.columns)}")
        
        # Save the processed data
        save_processed_data(sites_df, 'consolidated_sites_for_db')
        
        return sites_df
    
    except Exception as e:
        logger.error(f"Error loading site data: {e}")
        return pd.DataFrame()

def extract_site_metadata_from_csv(file_path, data_type):
    """
    Extract site metadata from a CSV file for sites not in the main sites table.
    Now uses enhanced data loading with automatic site name cleaning.
    
    Args:
        file_path: Path to the CSV file (not used when using load_csv_data)
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat', 'updated_chemical')
    
    Returns:
        DataFrame with unique sites and their metadata
    """
    try:
        # Use enhanced data_loader for consistent loading and site name cleaning
        if data_type == 'updated_chemical':
            df = load_csv_data('updated_chemical', encoding='cp1252', clean_site_names=True)
        elif data_type in ['chemical', 'fish', 'macro', 'habitat']:
            df = load_csv_data(data_type, clean_site_names=True)
        else:
            logger.error(f"Unknown data type: {data_type}")
            return pd.DataFrame()
        
        if df.empty:
            logger.warning(f"No data loaded for {data_type}")
            return pd.DataFrame()
        
        # Clean column names
        df = clean_column_names(df)
        
        # DEBUG: Print columns after cleaning (before mapping)
        print(f"DEBUG - {data_type}: Cleaned columns: {list(df.columns)}")
        
        # Define column mappings for each data type
        column_mappings = {
            'chemical': {
                'site_col': 'sitename',
                'lat_col': 'latitude',
                'lon_col': 'longitude',
                'county_col': 'county',
                'basin_col': 'riverbasin',
                'ecoregion_col': None  # Not available in chemical data
            },
            'updated_chemical': { 
                'site_col': 'site_name',  
                'lat_col': 'lat',         
                'lon_col': 'lon',         
                'county_col': 'countyname', 
                'basin_col': None,        # Not available in this file
                'ecoregion_col': None     # Not available in this file
            },
            'fish': {
                'site_col': 'sitename',
                'lat_col': 'latitude', 
                'lon_col': 'longitude',
                'county_col': None,  # Not readily available
                'basin_col': 'riverbasin',
                'ecoregion_col': 'mod_ecoregion'
            },
            'habitat': {
                'site_col': 'sitename',
                'lat_col': None,  # Not available in habitat data
                'lon_col': None,  # Not available in habitat data
                'county_col': None,
                'basin_col': 'riverbasin',
                'ecoregion_col': None
            },
            'macro': {
                'site_col': 'sitename',
                'lat_col': 'latitude',
                'lon_col': 'longitude', 
                'county_col': None,
                'basin_col': None,  # Not available in macro data
                'ecoregion_col': 'mod_ecoregion'
            }
        }
        
        if data_type not in column_mappings:
            logger.error(f"Unknown data type: {data_type}")
            return pd.DataFrame()
            
        mapping = column_mappings[data_type]
        
        # DEBUG: Print mapping and column check (after mapping is defined)
        print(f"DEBUG - {data_type}: Looking for site column: '{mapping['site_col']}'")
        print(f"DEBUG - {data_type}: Site column found: {mapping['site_col'] in df.columns}")
        if mapping['site_col'] not in df.columns:
            print(f"DEBUG - {data_type}: Available columns: {list(df.columns)}")
        
        # Check if site name column exists
        if mapping['site_col'] not in df.columns:
            logger.error(f"Site name column '{mapping['site_col']}' not found in {data_type} data")
            return pd.DataFrame()
        
        # Get unique sites (site names are already cleaned by load_csv_data)
        unique_sites = df.drop_duplicates(subset=[mapping['site_col']])
        
        # DEBUG: Print site extraction results
        print(f"DEBUG - {data_type}: Found {len(unique_sites)} unique sites")
        
        # Build the result DataFrame
        result_data = {
            'site_name': unique_sites[mapping['site_col']]  # No need to strip - already cleaned
        }
        
        # Add available metadata columns
        for meta_type, col_name in [
            ('latitude', mapping['lat_col']),
            ('longitude', mapping['lon_col']),
            ('county', mapping['county_col']),
            ('river_basin', mapping['basin_col']),
            ('ecoregion', mapping['ecoregion_col'])
        ]:
            if col_name and col_name in df.columns:
                result_data[meta_type] = unique_sites[col_name]
                print(f"DEBUG - {data_type}: Found metadata column '{col_name}' for {meta_type}")
            else:
                result_data[meta_type] = None
                if col_name:  # Only log if we were expecting the column
                    print(f"DEBUG - {data_type}: Missing expected column '{col_name}' for {meta_type}")
        
        result_df = pd.DataFrame(result_data)
        
        # Convert lat/lon to numeric if they exist
        for coord_col in ['latitude', 'longitude']:
            if coord_col in result_df.columns and result_df[coord_col].notna().any():
                result_df[coord_col] = pd.to_numeric(result_df[coord_col], errors='coerce')
        
        logger.info(f"Extracted metadata for {len(result_df)} sites from {data_type} data")
        return result_df
        
    except Exception as e:
        logger.error(f"Error extracting site metadata from {data_type}: {e}")
        import traceback
        print(f"DEBUG - {data_type}: Full traceback: {traceback.format_exc()}")
        return pd.DataFrame()

def find_missing_sites(sites_df):
    """
    Find sites that exist in the DataFrame but not in the database.
    
    Args:
        sites_df: DataFrame with site information
    
    Returns:
        DataFrame with sites that don't exist in the database
    """
    if sites_df.empty:
        return pd.DataFrame()
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get existing site names from database
        cursor.execute("SELECT site_name FROM sites")
        existing_sites = {clean_site_name(row[0]).lower() for row in cursor.fetchall()}
        
        # Find sites that don't exist in database
        mask = ~sites_df['site_name'].apply(clean_site_name).str.lower().isin(existing_sites)
        missing_sites = sites_df[mask].copy()
        
        return missing_sites
        
    except Exception as e:
        logger.error(f"Error finding missing sites: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)

def insert_sites_into_db(sites_df):
    """
    Insert site data into the SQLite database.
    
    Args:
        sites_df: DataFrame containing site information
    
    Returns:
        int: Number of sites inserted
    """
    if sites_df.empty:
        logger.warning("No site data to insert into database")
        return 0
    
    conn = get_connection()
    
    try:
        # Ensure we have the required site_name column
        if 'site_name' not in sites_df.columns:
            logger.error("Missing required column 'site_name' in site data")
            return 0
        
        # Make sure site_name is a string
        sites_df['site_name'] = sites_df['site_name'].astype(str)
        
        # Get columns that exist in the dataframe
        columns = sites_df.columns.tolist()
        
        # Debug logging
        logger.info(f"Inserting sites with columns: {columns}")
        if not sites_df.empty:
            sample_row = sites_df.iloc[0].to_dict()
            logger.info(f"Sample row: {sample_row}")
        
        # Prepare SQL statement
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        sql = f"INSERT OR REPLACE INTO sites ({columns_str}) VALUES ({placeholders})"
        
        # Prepare data for insertion
        site_data = []
        for _, row in sites_df.iterrows():
            site_data.append(tuple(row[col] for col in columns))
        
        # Execute insertion
        cursor = conn.cursor()
        cursor.executemany(sql, site_data)
        conn.commit()
        
        # Log the results
        sites_count = len(site_data)
        logger.info(f"Successfully inserted/updated {sites_count} sites in the database")
        return sites_count
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting site data into database: {e}")
        return 0
    
    finally:
        close_connection(conn)

def get_all_sites():
    """
    Retrieve all sites from the database.
    
    Returns:
        DataFrame containing all site data
    """
    conn = get_connection()
    try:
        query = "SELECT * FROM sites ORDER BY site_name"
        sites_df = pd.read_sql_query(query, conn)
        logger.debug(f"Retrieved {len(sites_df)} sites from database")
        return sites_df
    except Exception as e:
        logger.error(f"Error retrieving sites from database: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)

def get_site_by_name(site_name):
    """
    Retrieve a specific site from the database by name.
    
    Args:
        site_name: Name of the site to retrieve
    
    Returns:
        DataFrame row containing site data or None if not found
    """
    conn = get_connection()
    try:
        query = "SELECT * FROM sites WHERE site_name = ?"
        site_df = pd.read_sql_query(query, conn, params=(site_name,))
        
        if len(site_df) == 0:
            logger.warning(f"Site not found: {site_name}")
            return None
        
        logger.debug(f"Retrieved site data for: {site_name}")
        return site_df.iloc[0]
    except Exception as e:
        logger.error(f"Error retrieving site data for {site_name}: {e}")
        return None
    finally:
        close_connection(conn)

def get_site_id(site_name):
    """
    Get the database ID for a given site name.
    
    Args:
        site_name: Name of the site
    
    Returns:
        int: Site ID or None if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (site_name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            logger.warning(f"No site_id found for site: {site_name}")
            return None
    except Exception as e:
        logger.error(f"Error getting site_id for {site_name}: {e}")
        return None
    finally:
        close_connection(conn)

def process_site_data():
    try:
        # Create sites table
        create_sites_table()
        
        # Load consolidated site data
        logger.info("Loading consolidated site data from master_sites.csv")
        sites_df = load_site_data()
        
        if sites_df.empty:
            logger.error("Failed to load consolidated site data")
            return False
        
        # Insert all sites into database
        sites_count = insert_sites_into_db(sites_df)
        
        logger.info(f"Site processing complete!")
        logger.info(f"Total sites in database: {sites_count}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error processing site data: {e}")
        return False

def cleanup_unused_sites():
    """
    Remove sites from the database that have no data in any monitoring tables.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get all sites that DO have data in any monitoring table
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
        
        # Get all sites in the sites table
        cursor.execute('SELECT site_id FROM sites')
        all_sites = {row[0] for row in cursor.fetchall()}
        
        # Find sites with no data
        unused_sites = all_sites - sites_with_data
        
        if unused_sites:
            # Remove unused sites
            placeholders = ','.join(['?' for _ in unused_sites])
            cursor.execute(f'DELETE FROM sites WHERE site_id IN ({placeholders})', list(unused_sites))
            conn.commit()
            
            logger.info(f"Removed {len(unused_sites)} unused sites from database")
        else:
            logger.info("No unused sites found - all sites have monitoring data")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning up unused sites: {e}")
        return False
    finally:
        close_connection(conn)

def classify_active_sites():
    """
    Classify sites as active or historic based on recent chemical data.
    Active sites have chemical readings within 2 years of the most recent reading date.
    
    Returns:
        bool: True if classification was successful, False otherwise
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
        logger.info(f"Most recent chemical reading date: {most_recent_date}")
        
        # Step 2: Calculate cutoff date (2 years before most recent reading)
        from datetime import datetime, timedelta
        most_recent_dt = datetime.strptime(most_recent_date, '%Y-%m-%d')
        cutoff_date = most_recent_dt - timedelta(days=365)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
        
        logger.info(f"Active site cutoff date: {cutoff_date_str}")
        
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
                # Active site
                cursor.execute("""
                    UPDATE sites 
                    SET active = 1, last_chemical_reading_date = ?
                    WHERE site_id = ?
                """, (last_reading, site_id))
                active_count += 1
                logger.debug(f"Active site: {site_name} (last reading: {last_reading})")
            else:
                # Historic site
                cursor.execute("""
                    UPDATE sites 
                    SET active = 0, last_chemical_reading_date = ?
                    WHERE site_id = ?
                """, (last_reading, site_id))
                historic_count += 1
                logger.debug(f"Historic site: {site_name} (last reading: {last_reading or 'never'})")
        
        conn.commit()
        
        logger.info(f"Site classification complete:")
        logger.info(f"  - Active sites: {active_count}")
        logger.info(f"  - Historic sites: {historic_count}")
        logger.info(f"  - Total sites: {active_count + historic_count}")
        
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
        # Display some sample site data
        all_sites = get_all_sites()
        if not all_sites.empty:
            print(f"Total sites: {len(all_sites)}")
            print("\nSample sites:")
            print(all_sites[['site_name', 'county', 'river_basin']].head())
    else:
        print("Site processing failed. Check the log for details.")