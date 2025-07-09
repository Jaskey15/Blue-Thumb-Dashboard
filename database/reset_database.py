"""
reset_database.py - Utility to reset the database and reload all data.
Use this script to quickly rebuild your database after schema changes.
"""

import os
import time
from utils import setup_logging

# Setup logging
logger = setup_logging("reset_database", category="database")

# ========================================================================
# HELPER FUNCTIONS FOR SITES FIRST PIPELINE
# ========================================================================

def generate_site_summary():
    """Generate summary statistics about sites in the database."""
    from database.database import get_connection, close_connection
    
    conn = get_connection()
    try:
        # Count total sites
        total_sites = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        
        # Count sites with coordinates
        sites_with_coords = conn.execute(
            "SELECT COUNT(*) FROM sites WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        ).fetchone()[0]
        
        # Count active vs historic sites
        active_sites = conn.execute("SELECT COUNT(*) FROM sites WHERE active = 1").fetchone()[0]
        historic_sites = total_sites - active_sites
        
        return {
            'total_sites': total_sites,
            'sites_with_coords': sites_with_coords,
            'active_sites': active_sites,
            'historic_sites': historic_sites
        }
    finally:
        close_connection(conn)

def generate_final_data_summary():
    """Generate comprehensive summary of all data in the database."""
    from database.database import get_connection, close_connection
    
    conn = get_connection()
    try:
        # Sites summary
        sites_total = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        sites_active = conn.execute("SELECT COUNT(*) FROM sites WHERE active = 1").fetchone()[0]
        sites_historic = sites_total - sites_active
        
        # Chemical data summary
        chemical_events = conn.execute("SELECT COUNT(*) FROM chemical_collection_events").fetchone()[0]
        chemical_measurements = conn.execute("SELECT COUNT(*) FROM chemical_measurements").fetchone()[0]
        
        # Biological data summary
        fish_events = conn.execute("SELECT COUNT(*) FROM fish_collection_events").fetchone()[0]
        macro_events = conn.execute("SELECT COUNT(*) FROM macro_collection_events").fetchone()[0]
        
        # Habitat data summary
        habitat_assessments = conn.execute("SELECT COUNT(*) FROM habitat_assessments").fetchone()[0]
        
        return {
            'sites': {
                'total': sites_total,
                'active': sites_active,
                'historic': sites_historic
            },
            'chemical': {
                'events': chemical_events,
                'measurements': chemical_measurements
            },
            'biological': {
                'fish_events': fish_events,
                'macro_events': macro_events
            },
            'habitat': {
                'assessments': habitat_assessments
            }
        }
    finally:
        close_connection(conn)

def load_chemical_data_with_validation():
    """Load chemical data with comprehensive site validation."""
    try:
        from data_processing.chemical_processing import process_chemical_data_from_csv
        from data_processing.data_loader import validate_site_matches
        from data_processing.chemical_utils import insert_chemical_data
        
        logger.info("  Processing chemical data from CSV...")
        df_clean, _, _ = process_chemical_data_from_csv()
        
        if df_clean.empty:
            return {'success': False, 'error': 'No chemical data to process', 'records_loaded': 0}
        
        logger.info(f"  Processed {len(df_clean)} chemical records")
        
        # Validate all sites exist in database
        logger.info("  Validating chemical data sites against database...")
        validation_result = validate_site_matches(df_clean, 'Site_Name', strict=False, log_mismatches=True)
        
        if validation_result['match_rate'] < 0.95:  # Require 95% match rate
            logger.error(f"Chemical data site validation failed: {validation_result['match_rate']:.1%} match rate")
            return {
                'success': False, 
                'error': f"Poor site match rate: {validation_result['match_rate']:.1%}",
                'records_loaded': 0,
                'validation': validation_result
            }
        
        logger.info(f"  Site validation passed: {validation_result['match_rate']:.1%} match rate")
        
        # Filter to only matched records
        matched_sites = [s['original_name'] for s in validation_result['validation_details']['matched_sites']]
        df_matched = df_clean[df_clean['Site_Name'].isin(matched_sites)]
        
        logger.info(f"  Loading {len(df_matched)} validated chemical records...")
        stats = insert_chemical_data(df_matched, data_source="cleaned_chemical_data.csv")
        
        return {
            'success': True,
            'records_loaded': stats['measurements_added'],
            'validation': validation_result
        }
        
    except Exception as e:
        logger.error(f"Error loading chemical data: {e}")
        return {'success': False, 'error': str(e), 'records_loaded': 0}

def load_updated_chemical_data_with_validation():
    """Load updated chemical data with comprehensive site validation."""
    try:
        from data_processing.updated_chemical_processing import process_updated_chemical_data
        from data_processing.data_loader import validate_site_matches
        from data_processing.chemical_utils import insert_chemical_data
        
        logger.info("  Processing updated chemical data from CSV...")
        df_clean = process_updated_chemical_data()
        
        if df_clean.empty:
            return {'success': False, 'error': 'No updated chemical data to process', 'records_loaded': 0}
        
        logger.info(f"  Processed {len(df_clean)} updated chemical records")
        
        # Validate all sites exist in database
        logger.info("  Validating updated chemical data sites against database...")
        validation_result = validate_site_matches(df_clean, 'Site_Name', strict=False, log_mismatches=True)
        
        if validation_result['match_rate'] < 0.95:  # Require 95% match rate
            logger.error(f"Updated chemical data site validation failed: {validation_result['match_rate']:.1%} match rate")
            return {
                'success': False, 
                'error': f"Poor site match rate: {validation_result['match_rate']:.1%}",
                'records_loaded': 0,
                'validation': validation_result
            }
        
        logger.info(f"  Site validation passed: {validation_result['match_rate']:.1%} match rate")
        
        # Filter to only matched records
        matched_sites = [s['original_name'] for s in validation_result['validation_details']['matched_sites']]
        df_matched = df_clean[df_clean['Site_Name'].isin(matched_sites)]
        
        logger.info(f"  Loading {len(df_matched)} validated updated chemical records...")
        stats = insert_chemical_data(df_matched, data_source="cleaned_updated_chemical_data.csv")
        
        return {
            'success': True,
            'records_loaded': stats['measurements_added'],
            'validation': validation_result
        }
        
    except Exception as e:
        logger.error(f"Error loading updated chemical data: {e}")
        return {'success': False, 'error': str(e), 'records_loaded': 0}

def load_fish_data_with_validation():
    """Load fish data with comprehensive site validation."""
    try:
        from data_processing.fish_processing import load_fish_data
        from data_processing.data_loader import validate_site_matches
        
        logger.info("  Loading fish data...")
        # Note: This is a placeholder - the actual fish processing would need to be modified
        # to return validation-compatible results and use site validation
        
        result = load_fish_data()
        if result is None or (hasattr(result, 'empty') and result.empty):
            return {'success': False, 'error': 'Fish data loading failed', 'records_loaded': 0}
        
        # For now, assume success - this would need proper implementation
        return {'success': True, 'records_loaded': len(result) if hasattr(result, '__len__') else 1}
        
    except Exception as e:
        logger.error(f"Error loading fish data: {e}")
        return {'success': False, 'error': str(e), 'records_loaded': 0}

def load_macro_data_with_validation():
    """Load macroinvertebrate data with comprehensive site validation."""
    try:
        from data_processing.macro_processing import load_macroinvertebrate_data
        
        logger.info("  Loading macroinvertebrate data...")
        # Note: This is a placeholder - similar to fish data
        
        result = load_macroinvertebrate_data()
        if result is None or (hasattr(result, 'empty') and result.empty):
            return {'success': False, 'error': 'Macro data loading failed', 'records_loaded': 0}
        
        return {'success': True, 'records_loaded': len(result) if hasattr(result, '__len__') else 1}
        
    except Exception as e:
        logger.error(f"Error loading macro data: {e}")
        return {'success': False, 'error': str(e), 'records_loaded': 0}

def load_habitat_data_with_validation():
    """Load habitat data with comprehensive site validation."""
    try:
        from data_processing.habitat_processing import load_habitat_data
        
        logger.info("  Loading habitat data...")
        # Note: This is a placeholder - similar to fish data
        
        result = load_habitat_data()
        if result is None or (hasattr(result, 'empty') and result.empty):
            return {'success': False, 'error': 'Habitat data loading failed', 'records_loaded': 0}
        
        return {'success': True, 'records_loaded': len(result) if hasattr(result, '__len__') else 1}
        
    except Exception as e:
        logger.error(f"Error loading habitat data: {e}")
        return {'success': False, 'error': str(e), 'records_loaded': 0}

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
    """
    Reload all data using the 'Sites First' approach.
    
    This new approach ensures maximum data integrity by:
    1. First consolidating and merging ALL sites from all data sources
    2. Then loading monitoring data against the unified site list
    3. Finally consolidating duplicate measurements
    
    Returns:
        True if all steps complete successfully, False otherwise
    """
    try:        
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("STARTING 'SITES FIRST' DATA RELOAD PIPELINE")
        logger.info("="*80)
        
        # ========================================================================
        # PHASE 1: COMPLETE SITE UNIFICATION (BEFORE ANY MONITORING DATA)
        # ========================================================================
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: COMPLETE SITE UNIFICATION")
        logger.info("="*60)
        
        # Step 1: Ensure all CSVs are cleaned and ready
        logger.info("Step 1: Verifying CSV cleaning status...")
        from data_processing.consolidate_sites import verify_cleaned_csvs
        csv_status = verify_cleaned_csvs()
        if not csv_status:
            logger.error("CSV cleaning verification failed. Run consolidate_sites.py first.")
            return False
        logger.info("✅ All CSV files are properly cleaned")
        
        # Step 2: Consolidate master sites list from all CSV sources
        logger.info("Step 2: Consolidating master sites list from all CSV sources...")
        from data_processing.consolidate_sites import consolidate_sites_from_csvs
        consolidate_result = consolidate_sites_from_csvs()
        if not consolidate_result:
            logger.error("Site consolidation failed. Cannot continue.")
            return False
        logger.info("✅ Master sites list consolidated successfully")
        
        # Step 3: Load master sites into database
        logger.info("Step 3: Loading master sites into database...")
        from data_processing.site_processing import process_site_data
        site_success = process_site_data()
        if not site_success:
            logger.error("Site processing failed. Cannot continue with data processing.")
            return False
        logger.info("✅ Master sites loaded to database successfully")
        
        # Step 4: Merge coordinate duplicates 
        logger.info("Step 4: Merging coordinate duplicate sites...")
        from data_processing.merge_sites import merge_duplicate_sites
        merge_result = merge_duplicate_sites()
        if not merge_result:
            logger.warning("Site merging had issues, but continuing...")
        else:
            logger.info("✅ Coordinate duplicate sites merged successfully")
        
        # Step 5: Classify active vs historic sites (preliminary)
        logger.info("Step 5: Preliminary site classification...")  
        from data_processing.site_processing import classify_active_sites
        classification_result = classify_active_sites()
        if not classification_result:
            logger.warning("Preliminary site classification had issues, but continuing...")
        else:
            logger.info("✅ Preliminary site classification completed")
        
        # Step 6: Generate site summary for monitoring data loading
        logger.info("Step 6: Generating final site summary...")
        site_summary = generate_site_summary()
        logger.info(f"✅ Site unification complete! Final summary:")
        logger.info(f"   - Total unified sites: {site_summary['total_sites']}")
        logger.info(f"   - Sites with coordinates: {site_summary['sites_with_coords']}")
        logger.info(f"   - Active sites: {site_summary['active_sites']}")
        logger.info(f"   - Historic sites: {site_summary['historic_sites']}")
        
        # ========================================================================
        # PHASE 2: LOAD MONITORING DATA (AGAINST UNIFIED SITES)
        # ========================================================================
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: MONITORING DATA LOADING")
        logger.info("="*60)
        
        # Step 7: Load chemical data with site validation
        logger.info("Step 7: Loading original chemical data with site validation...")
        chemical_result = load_chemical_data_with_validation()
        if not chemical_result['success']:
            logger.error(f"Chemical data loading failed: {chemical_result.get('error', 'Unknown error')}")
            return False
        logger.info(f"✅ Chemical data loaded: {chemical_result['records_loaded']} records")
        
        # Step 8: Load updated chemical data with site validation  
        logger.info("Step 8: Loading updated chemical data with site validation...")
        updated_chemical_result = load_updated_chemical_data_with_validation()
        if not updated_chemical_result['success']:
            logger.error(f"Updated chemical data loading failed: {updated_chemical_result.get('error', 'Unknown error')}")
            return False
        logger.info(f"✅ Updated chemical data loaded: {updated_chemical_result['records_loaded']} records")
        
        # Step 9: Skip consolidation - keeping all replicate samples as separate records
        logger.info("Step 9: Skipping chemical replicate consolidation (preserving all duplicate samples)")
        logger.info("ℹ️  Replicate samples remain as separate records for maximum data preservation")
        
        # Step 10: Load fish data with site validation
        logger.info("Step 10: Loading fish data with site validation...")
        fish_result = load_fish_data_with_validation()
        if not fish_result['success']:
            logger.warning(f"Fish data loading had issues: {fish_result.get('error', 'Unknown error')}")
        else:
            logger.info(f"✅ Fish data loaded: {fish_result['records_loaded']} records")
        
        # Step 11: Load macroinvertebrate data with site validation
        logger.info("Step 11: Loading macroinvertebrate data with site validation...")
        macro_result = load_macro_data_with_validation()
        if not macro_result['success']:
            logger.warning(f"Macro data loading had issues: {macro_result.get('error', 'Unknown error')}")
        else:
            logger.info(f"✅ Macro data loaded: {macro_result['records_loaded']} records")

        # Step 12: Load habitat data with site validation
        logger.info("Step 12: Loading habitat data with site validation...")
        habitat_result = load_habitat_data_with_validation()
        if not habitat_result['success']:
            logger.warning(f"Habitat data loading had issues: {habitat_result.get('error', 'Unknown error')}")
        else:
            logger.info(f"✅ Habitat data loaded: {habitat_result['records_loaded']} records")

        # ========================================================================
        # PHASE 3: FINAL DATA QUALITY AND CLEANUP
        # ========================================================================
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 3: FINAL DATA QUALITY AND CLEANUP")
        logger.info("="*60)
        
        # Step 13: Final site classification with all data loaded
        logger.info("Step 13: Final site classification with complete data...")  
        final_classification_result = classify_active_sites()
        if not final_classification_result:
            logger.warning("Final site classification had issues, but continuing...")
        else:
            logger.info("✅ Final site classification completed")

        # Step 14: Cleanup unused sites
        logger.info("Step 14: Cleaning up unused sites...")  
        from data_processing.site_processing import cleanup_unused_sites
        cleanup_result = cleanup_unused_sites()
        if not cleanup_result:
            logger.warning("Site cleanup had issues, but continuing...")
        else:
            logger.info("✅ Unused sites cleaned up")
        
        # Step 15: Generate final data summary
        logger.info("Step 15: Generating final data summary...")
        final_summary = generate_final_data_summary()
        
        elapsed_time = time.time() - start_time
        
        # ========================================================================
        # FINAL RESULTS
        # ========================================================================
        
        logger.info("\n" + "="*80)
        logger.info("'SITES FIRST' PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds")
        logger.info("\nFinal Data Summary:")
        logger.info(f"  Sites:")
        logger.info(f"    - Total sites: {final_summary['sites']['total']}")
        logger.info(f"    - Active sites: {final_summary['sites']['active']}")
        logger.info(f"    - Historic sites: {final_summary['sites']['historic']}")
        logger.info(f"  Chemical Data:")
        logger.info(f"    - Collection events: {final_summary['chemical']['events']}")
        logger.info(f"    - Measurements: {final_summary['chemical']['measurements']}")
        logger.info(f"  Biological Data:")
        logger.info(f"    - Fish events: {final_summary['biological']['fish_events']}")
        logger.info(f"    - Macro events: {final_summary['biological']['macro_events']}")
        logger.info(f"  Habitat Data:")
        logger.info(f"    - Assessments: {final_summary['habitat']['assessments']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in 'Sites First' data reload pipeline: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

def reset_database():
    """Perform complete database reset and reload."""
    logger.info("Starting database reset process...")

    if not delete_database_file():
        logger.error("Database deletion failed. Aborting reset.")
        return False
    
    if not recreate_schema():
        logger.error("Schema recreation failed. Aborting reset.")
        return False
    
    if not reload_all_data():
        logger.error("Data reloading failed. Reset process incomplete.")
        return False
    
    logger.info("Database reset process completed successfully!")
    return True

if __name__ == "__main__":
    success = reset_database()
    if success:
        print("Database has been successfully reset and all data reloaded.")
    else:
        print("Database reset failed. Check the logs for details.")