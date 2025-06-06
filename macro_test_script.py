"""
Final Macro Data Integrity Check
Check for macro samples that have the same site name and collection date
(regardless of habitat type - this checks for true duplicates)
"""

import sqlite3
import pandas as pd
from database.database import get_connection, close_connection

def check_macro_same_date_duplicates():
    """
    Check for macro samples that have the same site name and collection date.
    This identifies potential data entry errors or unintentional duplicates.
    Multiple habitats on the same date are expected and normal.
    """
    
    print("=" * 60)
    print("MACRO SAME DATE/SITE CHECK")
    print("=" * 60)
    
    conn = get_connection()
    
    try:
        # Query to find samples with same site and date (regardless of habitat)
        same_date_query = """
        SELECT 
            s.site_name,
            m.collection_date,
            m.year,
            m.season,
            COUNT(*) as sample_count,
            GROUP_CONCAT(m.habitat) as habitats,
            GROUP_CONCAT(m.event_id) as event_ids,
            GROUP_CONCAT(m.sample_id) as sample_ids
        FROM macro_collection_events m
        JOIN sites s ON m.site_id = s.site_id
        GROUP BY s.site_name, m.collection_date
        ORDER BY sample_count DESC, s.site_name, m.collection_date
        """
        
        same_date_df = pd.read_sql_query(same_date_query, conn)
        
        if same_date_df.empty:
            print("❌ NO MACRO DATA FOUND")
            return pd.DataFrame()
        
        # Separate into different categories
        multiple_samples = same_date_df[same_date_df['sample_count'] > 1]
        single_samples = same_date_df[same_date_df['sample_count'] == 1]
        
        print(f"📊 MACRO COLLECTION SUMMARY:")
        print(f"  Total unique site/date combinations: {len(same_date_df)}")
        print(f"  Site/dates with single sample: {len(single_samples)}")
        print(f"  Site/dates with multiple samples: {len(multiple_samples)}")
        
        if len(multiple_samples) > 0:
            print(f"\n🔍 MULTIPLE SAMPLES ON SAME DATE:")
            print("-" * 60)
            
            for _, row in multiple_samples.iterrows():
                habitats = row['habitats'].split(',')
                unique_habitats = set(habitats)
                
                print(f"Site: {row['site_name']}")
                print(f"Date: {row['collection_date']}")
                print(f"Season: {row['season']} {row['year']}")
                print(f"Number of samples: {row['sample_count']}")
                print(f"Habitats: {', '.join(habitats)}")
                print(f"Unique habitats: {len(unique_habitats)} ({', '.join(unique_habitats)})")
                print(f"Sample IDs: {row['sample_ids']}")
                
                # Check if this is expected (different habitats) or concerning (same habitat)
                if len(unique_habitats) == len(habitats):
                    print("✅ Status: EXPECTED - Different habitats on same date")
                elif len(unique_habitats) < len(habitats):
                    print("⚠️  Status: POTENTIAL DUPLICATE - Same habitat sampled multiple times")
                    
                print("-" * 40)
        else:
            print("\n✅ All site/date combinations have single samples")
        
        # Check for true duplicates (same site, same date, same habitat)
        print(f"\n🔍 CHECKING FOR TRUE DUPLICATES (same site/date/habitat):")
        
        true_duplicate_query = """
        SELECT 
            s.site_name,
            m.collection_date,
            m.habitat,
            COUNT(*) as duplicate_count,
            GROUP_CONCAT(m.event_id) as event_ids,
            GROUP_CONCAT(m.sample_id) as sample_ids
        FROM macro_collection_events m
        JOIN sites s ON m.site_id = s.site_id
        GROUP BY s.site_name, m.collection_date, m.habitat
        HAVING COUNT(*) > 1
        ORDER BY s.site_name, m.collection_date, m.habitat
        """
        
        true_duplicates_df = pd.read_sql_query(true_duplicate_query, conn)
        
        if true_duplicates_df.empty:
            print("✅ NO TRUE DUPLICATES FOUND")
            print("All site/date/habitat combinations are unique")
        else:
            print(f"⚠️  FOUND {len(true_duplicates_df)} TRUE DUPLICATE GROUPS")
            print("These need investigation:")
            print("-" * 40)
            
            for _, row in true_duplicates_df.iterrows():
                print(f"Site: {row['site_name']}")
                print(f"Date: {row['collection_date']}")
                print(f"Habitat: {row['habitat']}")
                print(f"Number of duplicates: {row['duplicate_count']}")
                print(f"Sample IDs: {row['sample_ids']}")
                print("-" * 30)
        
        # Summary statistics
        print(f"\n📈 COLLECTION PATTERNS:")
        
        # Habitat distribution per site/date
        habitat_stats_query = """
        SELECT 
            sample_count,
            COUNT(*) as frequency
        FROM (
            SELECT 
                s.site_name,
                m.collection_date,
                COUNT(DISTINCT m.habitat) as sample_count
            FROM macro_collection_events m
            JOIN sites s ON m.site_id = s.site_id
            GROUP BY s.site_name, m.collection_date
        ) habitat_counts
        GROUP BY sample_count
        ORDER BY sample_count
        """
        
        habitat_stats_df = pd.read_sql_query(habitat_stats_query, conn)
        
        for _, row in habitat_stats_df.iterrows():
            habitats = "habitat" if row['sample_count'] == 1 else "habitats"
            print(f"  {row['frequency']} site/dates with {row['sample_count']} {habitats}")
        
        return multiple_samples, true_duplicates_df
        
    except Exception as e:
        print(f"Error checking macro same-date duplicates: {e}")
        return pd.DataFrame(), pd.DataFrame()
        
    finally:
        close_connection(conn)

def check_macro_data_completeness():
    """
    Check completeness of macro data - ensure all events have summary scores.
    """
    
    print(f"\n" + "=" * 60)
    print("MACRO DATA COMPLETENESS CHECK")
    print("=" * 60)
    
    conn = get_connection()
    
    try:
        # Check for events without summary scores
        completeness_query = """
        SELECT 
            COUNT(m.event_id) as total_events,
            COUNT(ms.event_id) as events_with_scores,
            COUNT(m.event_id) - COUNT(ms.event_id) as missing_scores
        FROM macro_collection_events m
        LEFT JOIN macro_summary_scores ms ON m.event_id = ms.event_id
        """
        
        completeness = pd.read_sql_query(completeness_query, conn).iloc[0]
        
        print(f"Total macro collection events: {completeness['total_events']}")
        print(f"Events with summary scores: {completeness['events_with_scores']}")
        print(f"Events missing scores: {completeness['missing_scores']}")
        
        if completeness['missing_scores'] == 0:
            print("✅ ALL EVENTS HAVE SUMMARY SCORES")
        else:
            print(f"⚠️  {completeness['missing_scores']} EVENTS MISSING SCORES")
            
            # Show which events are missing scores
            missing_query = """
            SELECT 
                s.site_name,
                m.collection_date,
                m.habitat,
                m.event_id
            FROM macro_collection_events m
            JOIN sites s ON m.site_id = s.site_id
            LEFT JOIN macro_summary_scores ms ON m.event_id = ms.event_id
            WHERE ms.event_id IS NULL
            ORDER BY s.site_name, m.collection_date
            """
            
            missing_df = pd.read_sql_query(missing_query, conn)
            print("\nEvents missing summary scores:")
            for _, row in missing_df.iterrows():
                print(f"  {row['site_name']} - {row['collection_date']} - {row['habitat']}")
        
        return completeness['missing_scores'] == 0
        
    except Exception as e:
        print(f"Error checking macro data completeness: {e}")
        return False
        
    finally:
        close_connection(conn)

if __name__ == "__main__":
    print("Starting final macro data integrity checks...")
    
    # Check for same date samples
    multiple_samples, true_duplicates = check_macro_same_date_duplicates()
    
    # Check data completeness
    completeness_ok = check_macro_data_completeness()
    
    print(f"\n" + "=" * 60)
    print("FINAL MACRO INTEGRITY CHECK COMPLETE")
    print("=" * 60)
    
    if true_duplicates.empty and completeness_ok:
        print("✅ All macro data integrity checks passed!")
        print("✅ Multiple samples per site/date are legitimate (different habitats)")
        print("✅ No true duplicates found")
        print("✅ All events have complete data")
    else:
        if not true_duplicates.empty:
            print("⚠️  Action needed: Investigate true duplicates")
        if not completeness_ok:
            print("⚠️  Action needed: Add missing summary scores")
    
    if not multiple_samples.empty:
        print(f"\nℹ️  Found {len(multiple_samples)} site/dates with multiple samples")
        print("   This is normal when different habitats are sampled on the same date")