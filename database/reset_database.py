"""
reset_database.py - Utility to reset the database and reload all data.
Use this script to quickly rebuild your database after schema changes.
"""

import os
import logging
import time
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reset_database")

def delete_database_file():
    """Delete the SQLite database file if it exists."""
    try:
        # Determine database path based on database.py module
        from database.database import get_connection
        conn = get_connection()
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]  # Get the path from SQLite
        conn.close()
        
        # Delete the file
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Successfully deleted database file: {db_path}")
            return True
        else:
            logger.info("No database file found to delete")
            return True
    except Exception as e:
        logger.error(f"Error deleting database file: {e}")
        return False

def recreate_schema():
    """Recreate the database schema."""
    try:
        from database.db_schema import create_tables
        create_tables()
        logger.info("Successfully recreated database schema")
        return True
    except Exception as e:
        logger.error(f"Error recreating database schema: {e}")
        return False

def reload_all_data():
    """Reload all data from CSV files into the database."""
    try:
        # Import all processing modules
        from data_processing.site_processing import process_site_data
        from data_processing.chemical_processing import run_initial_db_setup as load_chemical_data
        from data_processing.fish_processing import load_fish_data
        from data_processing.macro_processing import load_macroinvertebrate_data
        
        # Process each data type
        start_time = time.time()
        
        logger.info("Loading chemical data...")
        chemical_success = load_chemical_data()
        
        logger.info("Loading fish data...")
        fish_success = load_fish_data()
        
        logger.info("Loading macroinvertebrate data...")
        macro_success = load_macroinvertebrate_data()
        
        elapsed_time = time.time() - start_time
        
        if chemical_success and fish_success and macro_success:
            logger.info(f"Successfully reloaded all data in {elapsed_time:.2f} seconds")
            return True
        else:
            logger.error("Some data loading failed. See above errors for details.")
            return False
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        return False

def reset_database():
    """Perform complete database reset and reload."""
    logger.info("Starting database reset process...")
    
    # Delete existing database
    if not delete_database_file():
        logger.error("Database deletion failed. Aborting reset.")
        return False
    
    # Recreate schema
    if not recreate_schema():
        logger.error("Schema recreation failed. Aborting reset.")
        return False
    
    # Reload all data
    if not reload_all_data():
        logger.error("Data reloading failed. Reset process incomplete.")
        return False
    
    logger.info("Database reset process completed successfully!")
    return True

if __name__ == "__main__":
    # If run directly, perform reset
    success = reset_database()
    if success:
        print("Database has been successfully reset and all data reloaded.")
    else:
        print("Database reset failed. Check the logs for details.")