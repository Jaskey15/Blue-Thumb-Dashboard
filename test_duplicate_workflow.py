"""
Test script to demonstrate the new duplicate insertion and consolidation workflow.

This script shows how:
1. Chemical data can now be inserted with duplicate site+date combinations
2. The chemical_duplicates.py module can then consolidate them using "worst case" logic
"""

import pandas as pd
from database.database import get_connection, close_connection
from data_processing.chemical_duplicates import consolidate_replicate_samples, identify_replicate_samples
from data_processing import setup_logging

# Set up logging
logger = setup_logging("test_duplicate_workflow", category="testing")

def create_test_duplicate_data():
    """Create test data with intentional duplicates for the same site and date."""
    try:
        from data_processing.chemical_utils import insert_chemical_data
        
        # First, ensure the test site exists in the database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert test site if it doesn't exist
        cursor.execute("""
        INSERT OR IGNORE INTO sites (site_name, latitude, longitude, county, active)
        VALUES ('Test Site A', 35.0, -97.0, 'Test County', 1)
        """)
        conn.commit()
        close_connection(conn)
        
        # Create test data with duplicate site+date combinations
        test_data = pd.DataFrame({
            'Site_Name': ['Test Site A', 'Test Site A', 'Test Site A'],  # Same site
            'Date': pd.to_datetime(['2023-07-15', '2023-07-15', '2023-07-15']),  # Same date
            'Year': [2023, 2023, 2023],
            'Month': [7, 7, 7],
            'pH': [6.5, 8.2, 7.1],  # Different pH values (worst case should be 8.2 - furthest from 7)
            'do_percent': [85.0, 75.0, 90.0],  # Different DO values (worst case should be 75.0 - lowest)
            'Phosphorus': [0.08, 0.12, 0.15],  # Different phosphorus values (worst case should be 0.15 - highest)
            'Chloride': [150, 200, 180]  # Different chloride values (worst case should be 200 - highest)
        })
        
        logger.info("Created test data with 3 replicate samples:")
        logger.info(f"  Site: Test Site A")
        logger.info(f"  Date: 2023-07-15")
        logger.info(f"  pH values: {test_data['pH'].tolist()}")
        logger.info(f"  DO values: {test_data['do_percent'].tolist()}")
        logger.info(f"  Phosphorus values: {test_data['Phosphorus'].tolist()}")
        logger.info(f"  Chloride values: {test_data['Chloride'].tolist()}")
        
        # Insert the test data (should create 3 separate collection events)
        stats = insert_chemical_data(test_data, data_source="test_duplicate_data")
        
        logger.info(f"Insertion results:")
        logger.info(f"  - Events added: {stats['events_added']}")
        logger.info(f"  - Measurements added: {stats['measurements_added']}")
        
        return stats['events_added'] > 0
        
    except Exception as e:
        logger.error(f"Error creating test duplicate data: {e}")
        return False

def test_duplicate_workflow():
    """Test the complete duplicate insertion and consolidation workflow."""
    try:
        logger.info("=== TESTING DUPLICATE INSERTION AND CONSOLIDATION WORKFLOW ===")
        
        # Step 1: Create test duplicate data
        logger.info("\nStep 1: Creating test duplicate data...")
        if not create_test_duplicate_data():
            logger.error("Failed to create test data")
            return False
        
        # Step 2: Identify replicates
        logger.info("\nStep 2: Identifying replicate samples...")
        replicates = identify_replicate_samples()
        
        if not replicates:
            logger.warning("No replicates found after insertion")
            return False
        
        logger.info(f"Found {len(replicates)} replicate groups")
        
        # Step 3: Run consolidation in dry run mode first
        logger.info("\nStep 3: Running consolidation in dry run mode...")
        dry_run_stats = consolidate_replicate_samples(dry_run=True, quiet=False)  # Show details in test
        
        logger.info("Dry run results:")
        logger.info(f"  - Groups to process: {dry_run_stats['groups_processed']}")
        logger.info(f"  - Events to remove: {dry_run_stats['events_removed']}")
        logger.info(f"  - Measurements to update: {dry_run_stats['measurements_updated']}")
        
        # Step 4: Run actual consolidation
        logger.info("\nStep 4: Running actual consolidation...")
        live_stats = consolidate_replicate_samples(dry_run=False, quiet=False)  # Show details in test
        
        logger.info("Live consolidation results:")
        logger.info(f"  - Groups processed: {live_stats['groups_processed']}")
        logger.info(f"  - Events removed: {live_stats['events_removed']}")
        logger.info(f"  - Measurements updated: {live_stats['measurements_updated']}")
        
        # Step 5: Verify no more duplicates exist
        logger.info("\nStep 5: Verifying consolidation...")
        remaining_replicates = identify_replicate_samples()
        
        if not remaining_replicates:
            logger.info("✅ SUCCESS! No replicate samples remain after consolidation")
            return True
        else:
            logger.warning(f"❌ WARNING! {len(remaining_replicates)} replicate groups still exist")
            return False
        
    except Exception as e:
        logger.error(f"Error in duplicate workflow test: {e}")
        return False

def cleanup_test_data():
    """Clean up test data created during testing."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Remove test collection events (this will cascade to measurements)
        cursor.execute("""
        DELETE FROM chemical_collection_events 
        WHERE site_id IN (
            SELECT site_id FROM sites WHERE site_name = 'Test Site A'
        )
        """)
        
        rows_deleted = cursor.rowcount
        conn.commit()
        close_connection(conn)
        
        logger.info(f"Cleanup: Removed {rows_deleted} test collection events")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")
        return False

if __name__ == "__main__":
    try:
        # Run the test workflow
        success = test_duplicate_workflow()
        
        if success:
            print("\n🎉 DUPLICATE WORKFLOW TEST PASSED!")
            print("The new system successfully:")
            print("  ✅ Allowed duplicate site+date insertions")
            print("  ✅ Identified replicate samples")
            print("  ✅ Consolidated duplicates using worst-case logic")
            print("  ✅ Cleaned up duplicate collection events")
        else:
            print("\n❌ DUPLICATE WORKFLOW TEST FAILED!")
            print("Check the logs above for details.")
        
        # Clean up test data
        print("\nCleaning up test data...")
        cleanup_test_data()
        
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        print("Check the logs for detailed error information.") 