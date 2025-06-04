"""
test_chemical_reset.py - Test database reset with just sites and chemical data
Use this to test your consolidated approach before loading all data types.
"""

import os
import time
from utils import setup_logging

# Setup logging
logger = setup_logging("test_chemical_reset", category="database")

def delete_database_file():
    """Delete the SQLite database file if it exists."""
    try:
        from database.database import get_connection
        conn = get_connection()
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        conn.close()
        
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

def test_chemical_loading():
    """Test loading sites and chemical data only."""
    try:        
        from data_processing.site_processing import process_site_data
        from data_processing.chemical_processing import load_chemical_data_to_db
        from data_processing.updated_chemical_processing import load_updated_chemical_data_to_db
        
        start_time = time.time()
        
        # Step 1: Load consolidated sites
        logger.info("Step 1: Loading consolidated site data...")
        site_success = process_site_data()
        
        if not site_success:
            logger.error("Site processing failed. Cannot continue.")
            return False
            
        # Check how many sites were loaded
        from database.database import get_connection, close_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sites")
        site_count = cursor.fetchone()[0]
        close_connection(conn)
        
        logger.info(f"✅ Loaded {site_count} sites into database")
        
        # Step 2: Load original chemical data
        logger.info("Step 2: Loading original chemical data...")
        chemical_success = load_chemical_data_to_db()
        
        if not chemical_success:
            logger.error("Original chemical data loading failed")
            return False
        
        # Step 3: Load updated chemical data
        logger.info("Step 3: Loading updated chemical data...")
        updated_chemical_success = load_updated_chemical_data_to_db()
        
        if not updated_chemical_success:
            logger.error("Updated chemical data loading failed")
            return False
        
        # Validation queries
        logger.info("Step 4: Running validation queries...")
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count chemical collection events
        cursor.execute("SELECT COUNT(*) FROM chemical_collection_events")
        event_count = cursor.fetchone()[0]
        
        # Count chemical measurements
        cursor.execute("SELECT COUNT(*) FROM chemical_measurements")
        measurement_count = cursor.fetchone()[0]
        
        # Count sites with chemical data
        cursor.execute("""
            SELECT COUNT(DISTINCT site_id) 
            FROM chemical_collection_events
        """)
        sites_with_data = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("""
            SELECT MIN(collection_date), MAX(collection_date) 
            FROM chemical_collection_events
        """)
        min_date, max_date = cursor.fetchone()
        
        close_connection(conn)
        
        elapsed_time = time.time() - start_time
        
        # Results summary
        logger.info("=" * 60)
        logger.info("CHEMICAL DATA LOADING TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"✅ Total sites in database: {site_count}")
        logger.info(f"✅ Sites with chemical data: {sites_with_data}")
        logger.info(f"✅ Chemical collection events: {event_count:,}")
        logger.info(f"✅ Chemical measurements: {measurement_count:,}")
        logger.info(f"✅ Date range: {min_date} to {max_date}")
        logger.info(f"✅ Processing time: {elapsed_time:.2f} seconds")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in chemical data test: {e}")
        return False

def test_chemical_reset():
    """Perform chemical-only database reset and test."""
    logger.info("Starting chemical data test...")
    
    # Delete existing database
    if not delete_database_file():
        logger.error("Database deletion failed. Aborting test.")
        return False
    
    # Recreate schema
    if not recreate_schema():
        logger.error("Schema recreation failed. Aborting test.")
        return False
    
    # Test chemical loading
    if not test_chemical_loading():
        logger.error("Chemical data loading test failed.")
        return False
    
    logger.info("🎉 Chemical data test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_chemical_reset()
    if success:
        print("\n🎉 Chemical data test PASSED!")
        print("Ready to update full reset_database.py")
    else:
        print("\n❌ Chemical data test FAILED!")
        print("Check logs for issues before proceeding")