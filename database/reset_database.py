"""
reset_database.py - Utility to reset the database and reload all data.
Use this script to quickly rebuild your database after schema changes.
"""

import os
import time
from utils import setup_logging

# Setup logging
logger = setup_logging("reset_database", category="database")

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
        from data_processing.habitat_processing import load_habitat_data
        
        start_time = time.time()
        
        # CRITICAL: Site processing must run first and complete successfully
        logger.info("Step 1: Loading site data...")
        site_success = process_site_data()
        
        if not site_success:
            logger.error("Site processing failed. Cannot continue with other data processing.")
            return False
        
        # Only proceed with other data processing if sites were loaded successfully
        logger.info("Step 2: Loading chemical data...")
        chemical_result = load_chemical_data()
        chemical_success = chemical_result is not False and chemical_result is not None
        
        logger.info("Step 3: Loading fish data...")
        fish_result = load_fish_data()
        fish_success = not (hasattr(fish_result, 'empty') and fish_result.empty) if fish_result is not None else False
        
        logger.info("Step 4: Loading macroinvertebrate data...")
        macro_result = load_macroinvertebrate_data()
        macro_success = not (hasattr(macro_result, 'empty') and macro_result.empty) if macro_result is not None else False

        logger.info("Step 5: Loading habitat data...")
        habitat_result = load_habitat_data()
        habitat_success = not (hasattr(habitat_result, 'empty') and habitat_result.empty) if habitat_result is not None else False

        logger.info("Step 6: Cleaning up unused sites...")
        from data_processing.site_processing import cleanup_unused_sites
        cleanup_result = cleanup_unused_sites()
        cleanup_success = cleanup_result is not False and cleanup_result is not None
        
        elapsed_time = time.time() - start_time
        
        if chemical_success and fish_success and macro_success and habitat_success and cleanup_success:
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