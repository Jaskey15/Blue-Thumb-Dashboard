import os
import pandas as pd
import sqlite3
import logging

def setup_logging():
    """Configure logging to use the logs directory with component-specific log file."""
    # Get the base directory of the project
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Get the module name for the log file
    module_name = os.path.basename(__file__).replace('.py', '')
    log_file = os.path.join(logs_dir, f"{module_name}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

def get_db_connection():
    """Create and return a database connection."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'blue_thumb.db')
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
    Load site information from the blue_thumb_site_data.csv file.
    Returns a DataFrame with essential site information.
    """
    try:
        # Define path to site CSV file
        base_dir = os.path.dirname(os.path.dirname(__file__))
        site_path = os.path.join(base_dir, 'data', 'raw', 'blue_thumb_site_data.csv')
        
        # Check if the file exists
        if not os.path.exists(site_path):
            logger.error(f"Site data file not found: {site_path}")
            return pd.DataFrame()
        
        # Load the site data
        logger.info("Loading site data from CSV file")
        site_df = pd.read_csv(site_path)
        
        # Select only needed columns and rename them
        essential_columns = {
            'SiteName': 'site_name', 
            'Latitude': 'latitude', 
            'Longitude': 'longitude',
            'County': 'county', 
            'RiverBasin': 'river_basin', 
            'L3_Ecoregion': 'ecoregion',  # Using L3_Ecoregion as it's typically the main ecoregion classification
        }
        
        # Check which columns are available
        available_columns = {k: v for k, v in essential_columns.items() if k in site_df.columns}
        
        if 'SiteName' not in available_columns:
            logger.error("Required column 'SiteName' not found in site data file")
            return pd.DataFrame()
        
        # Select and rename columns
        sites_df = site_df[[col for col in available_columns.keys()]].copy()
        sites_df.rename(columns=available_columns, inplace=True)
        
        # Drop duplicates based on site_name
        sites_df.drop_duplicates(subset=['site_name'], inplace=True)
        
        # Fill any missing lat/long with a default value if needed
        if 'latitude' in sites_df.columns and 'longitude' in sites_df.columns:
            sites_df['latitude'].fillna(0, inplace=True)
            sites_df['longitude'].fillna(0, inplace=True)
        
        logger.info(f"Extracted information for {len(sites_df)} unique sites")
        return sites_df
    
    except Exception as e:
        logger.error(f"Error loading site data: {e}")
        return pd.DataFrame()

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
    
    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        # Create sites table
        create_sites_table()
        
        # Load site data
        sites_df = load_site_data()
        
        if sites_df.empty:
            logger.error("Failed to extract site data from CSV file")
            return False
        
        # Insert sites into database
        sites_count = insert_sites_into_db(sites_df)
        
        if sites_count > 0:
            logger.info(f"Successfully processed {sites_count} sites")
            return True
        else:
            logger.error("No sites were inserted into the database")
            return False
            
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