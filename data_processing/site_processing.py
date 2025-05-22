import os
import pandas as pd
import sqlite3

# Import from data_loader
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from utils import setup_logging

# Initialize logger
logger = setup_logging("site_processing")

def get_db_connection():
    """Create and return a database connection."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tenmile_biology.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    return conn

def close_db_connection(conn):
    """Safely close a database connection."""
    if conn:
        conn.commit()
        conn.close()

def create_sites_table():
    """Create the sites table in the database."""
    conn = get_db_connection()
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
    close_db_connection(conn)

def load_site_data():
    """
    Load site information from site_data.csv file.
    Returns a DataFrame with essential site information.
    """
    try:
        # Use the load_csv_data function from data_loader
        site_df = load_csv_data('site')
        
        if site_df.empty:
            logger.error("Failed to load site data")
            return pd.DataFrame()
        
        # Clean column names using the utility function
        site_df = clean_column_names(site_df)

        # Convert latitude and longitude to numeric types
        if 'latitude' in site_df.columns:
            site_df['latitude'] = pd.to_numeric(site_df['latitude'], errors='coerce')
        if 'longitude' in site_df.columns:
            site_df['longitude'] = pd.to_numeric(site_df['longitude'], errors='coerce')
        
        # Map columns to our desired schema
        column_mapping = {
            'sitename': 'site_name',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'county': 'county',
            'riverbasin': 'river_basin',
            'mod_ecoregion': 'ecoregion'
        }
        
        # Check which columns are available
        available_columns = {k: v for k, v in column_mapping.items() if k in site_df.columns}
        
        if 'sitename' not in available_columns:
            logger.error("Required column 'sitename' not found in site data file")
            return pd.DataFrame()
        
        # Select and rename columns
        sites_df = site_df[[col for col in available_columns.keys()]].copy()
        sites_df.rename(columns=available_columns, inplace=True)
        
        # Drop duplicates based on site_name
        sites_df.drop_duplicates(subset=['site_name'], inplace=True)
        
        # Fill any missing lat/long with a default value if needed
        if 'latitude' in sites_df.columns and 'longitude' in sites_df.columns:
            sites_df = sites_df.fillna({'latitude': 0, 'longitude': 0})
        
        logger.info(f"Extracted information for {len(sites_df)} unique sites")
        
        # Save the processed data using the utility function
        save_processed_data(sites_df, 'site')
        
        return sites_df
    
    except Exception as e:
        logger.error(f"Error loading site data: {e}")
        return pd.DataFrame()

def extract_site_metadata_from_csv(file_path, data_type):
    """
    Extract site metadata from a CSV file for sites not in the main sites table.
    
    Args:
        file_path: Path to the CSV file
        data_type: Type of data ('chemical', 'fish', 'macro', 'habitat')
    
    Returns:
        DataFrame with unique sites and their metadata
    """
    try:
        df = pd.read_csv(file_path)
        
        # Clean column names
        df = clean_column_names(df)
        
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
        
        # Check if site name column exists
        if mapping['site_col'] not in df.columns:
            logger.error(f"Site name column '{mapping['site_col']}' not found in {data_type} data")
            return pd.DataFrame()
        
        # Get unique sites
        unique_sites = df.drop_duplicates(subset=[mapping['site_col']])
        
        # Build the result DataFrame
        result_data = {
            'site_name': unique_sites[mapping['site_col']].str.strip()
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
            else:
                result_data[meta_type] = None
        
        result_df = pd.DataFrame(result_data)
        
        # Convert lat/lon to numeric if they exist
        for coord_col in ['latitude', 'longitude']:
            if coord_col in result_df.columns and result_df[coord_col].notna().any():
                result_df[coord_col] = pd.to_numeric(result_df[coord_col], errors='coerce')
        
        logger.info(f"Extracted metadata for {len(result_df)} sites from {data_type} data")
        return result_df
        
    except Exception as e:
        logger.error(f"Error extracting site metadata from {data_type}: {e}")
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
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get existing site names from database
        cursor.execute("SELECT site_name FROM sites")
        existing_sites = {row[0].strip().lower() for row in cursor.fetchall()}
        
        # Find sites that don't exist in database
        # Use case-insensitive comparison and strip whitespace
        mask = ~sites_df['site_name'].str.strip().str.lower().isin(existing_sites)
        missing_sites = sites_df[mask].copy()
        
        return missing_sites
        
    except Exception as e:
        logger.error(f"Error finding missing sites: {e}")
        return pd.DataFrame()
    finally:
        close_db_connection(conn)

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
    
    conn = get_db_connection()
    
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
        close_db_connection(conn)

def get_all_sites():
    """
    Retrieve all sites from the database.
    
    Returns:
        DataFrame containing all site data
    """
    conn = get_db_connection()
    try:
        query = "SELECT * FROM sites ORDER BY site_name"
        sites_df = pd.read_sql_query(query, conn)
        logger.debug(f"Retrieved {len(sites_df)} sites from database")
        return sites_df
    except Exception as e:
        logger.error(f"Error retrieving sites from database: {e}")
        return pd.DataFrame()
    finally:
        close_db_connection(conn)

def get_site_by_name(site_name):
    """
    Retrieve a specific site from the database by name.
    
    Args:
        site_name: Name of the site to retrieve
    
    Returns:
        DataFrame row containing site data or None if not found
    """
    conn = get_db_connection()
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
        close_db_connection(conn)

def get_site_id(site_name):
    """
    Get the database ID for a given site name.
    
    Args:
        site_name: Name of the site
    
    Returns:
        int: Site ID or None if not found
    """
    conn = get_db_connection()
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
        close_db_connection(conn)

def process_site_data():
    """
    Main function to process site data and store in database.
    This now includes checking all other CSV files for missing sites.
    
    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        # Create sites table
        create_sites_table()
        
        # Step 1: Load primary site data from sites CSV
        logger.info("Step 1: Loading primary site data from sites CSV")
        sites_df = load_site_data()
        
        if sites_df.empty:
            logger.error("Failed to extract site data from CSV file")
            return False
        
        # Insert primary sites into database
        primary_sites_count = insert_sites_into_db(sites_df)
        logger.info(f"Inserted {primary_sites_count} primary sites from sites CSV")
        
        # Step 2: Check other CSV files for missing sites
        logger.info("Step 2: Checking other CSV files for missing sites")
        
        # Define the other data files to check
        base_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
        data_files_to_check = [
            ('chemical', os.path.join(base_data_dir, 'chemical_data.csv')),
            ('fish', os.path.join(base_data_dir, 'fish_data.csv')),
            ('habitat', os.path.join(base_data_dir, 'habitat_data.csv')),
            ('macro', os.path.join(base_data_dir, 'macro_data.csv'))
        ]
        
        total_additional_sites = 0
        
        for data_type, file_path in data_files_to_check:
            if not os.path.exists(file_path):
                logger.warning(f"{data_type} file not found: {file_path}")
                continue
                
            logger.info(f"Checking {data_type} file for missing sites")
            
            # Extract site metadata from this file
            file_sites_df = extract_site_metadata_from_csv(file_path, data_type)
            
            if file_sites_df.empty:
                logger.info(f"No sites found in {data_type} file")
                continue
            
            # Check which sites are missing from our database
            missing_sites = find_missing_sites(file_sites_df)
            
            if not missing_sites.empty:
                logger.info(f"Found {len(missing_sites)} missing sites in {data_type} file")
                
                # Insert missing sites with available metadata
                additional_count = insert_sites_into_db(missing_sites)
                total_additional_sites += additional_count
                
                # Log what metadata was available/missing for these sites
                for _, site in missing_sites.iterrows():
                    available_meta = []
                    missing_meta = []
                    for col in ['latitude', 'longitude', 'county', 'river_basin', 'ecoregion']:
                        if pd.notna(site[col]):
                            available_meta.append(col)
                        else:
                            missing_meta.append(col)
                    
                    logger.info(f"Added site '{site['site_name']}' from {data_type} with: {', '.join(available_meta) if available_meta else 'name only'}")
                    if missing_meta:
                        logger.debug(f"  Missing metadata: {', '.join(missing_meta)}")
            else:
                logger.info(f"No missing sites found in {data_type} file")
        
        # Step 3: Final summary
        total_sites = primary_sites_count + total_additional_sites
        logger.info(f"Site processing complete!")
        logger.info(f"Total sites in database: {total_sites}")
        logger.info(f"  - From primary sites CSV: {primary_sites_count}")
        logger.info(f"  - Added from other files: {total_additional_sites}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error processing site data: {e}")
        return False

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