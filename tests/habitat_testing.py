"""
fish_habitat_cross_reference.py - Cross-reference fish and habitat collection patterns

This script analyzes the correlation between fish replicates and habitat duplicates
by looking at sites that have multiple collections in the same year for both data types.
"""

import os
import sys
import pandas as pd

# Add project root to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from database.database import get_connection, close_connection
from utils import setup_logging

# Set up logging
logger = setup_logging("fish_habitat_cross_reference", category="analysis")

def get_fish_collection_patterns():
    """
    Get fish collection patterns from the database (processed data with corrected dates).
    
    Returns:
        DataFrame with fish collection patterns by site and year
    """
    conn = get_connection()
    try:
        fish_query = """
        SELECT 
            s.site_name,
            e.year,
            COUNT(*) as fish_collections,
            GROUP_CONCAT(e.collection_date) as fish_dates,
            GROUP_CONCAT(e.sample_id) as fish_sample_ids
        FROM fish_collection_events e
        JOIN sites s ON e.site_id = s.site_id
        GROUP BY s.site_name, e.year
        ORDER BY s.site_name, e.year
        """
        
        fish_df = pd.read_sql_query(fish_query, conn)
        logger.info(f"Retrieved fish collection patterns for {len(fish_df)} site/year combinations")
        
        return fish_df
        
    except Exception as e:
        logger.error(f"Error getting fish collection patterns: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)

def get_habitat_collection_patterns():
    """
    Get habitat collection patterns from the database.
    
    Returns:
        DataFrame with habitat collection patterns by site and year
    """
    conn = get_connection()
    try:
        habitat_query = """
        SELECT 
            s.site_name,
            h.year,
            COUNT(*) as habitat_assessments,
            GROUP_CONCAT(h.assessment_date) as habitat_dates,
            GROUP_CONCAT(h.assessment_id) as habitat_assessment_ids
        FROM habitat_assessments h
        JOIN sites s ON h.site_id = s.site_id
        GROUP BY s.site_name, h.year
        ORDER BY s.site_name, h.year
        """
        
        habitat_df = pd.read_sql_query(habitat_query, conn)
        logger.info(f"Retrieved habitat collection patterns for {len(habitat_df)} site/year combinations")
        
        return habitat_df
        
    except Exception as e:
        logger.error(f"Error getting habitat collection patterns: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)

def analyze_multiple_collections(df, data_type):
    """
    Identify sites/years with multiple collections.
    
    Args:
        df: DataFrame with collection patterns
        data_type: 'fish' or 'habitat'
        
    Returns:
        DataFrame with only multiple collection cases
    """
    count_column = f'{data_type}_collections' if data_type == 'fish' else f'{data_type}_assessments'
    multiple_collections = df[df[count_column] > 1].copy()
    
    logger.info(f"Found {len(multiple_collections)} site/year combinations with multiple {data_type} collections")
    
    return multiple_collections

def cross_reference_patterns(fish_df, habitat_df):
    """
    Cross-reference fish and habitat collection patterns to find correlations.
    
    Args:
        fish_df: DataFrame with fish collection patterns
        habitat_df: DataFrame with habitat collection patterns
        
    Returns:
        Dict with cross-reference analysis results
    """
    # Get multiple collections for each data type
    fish_multiple = analyze_multiple_collections(fish_df, 'fish')
    habitat_multiple = analyze_multiple_collections(habitat_df, 'habitat')
    
    # Merge on site_name and year to find correlations
    correlation_df = pd.merge(
        fish_multiple[['site_name', 'year', 'fish_collections', 'fish_dates', 'fish_sample_ids']],
        habitat_multiple[['site_name', 'year', 'habitat_assessments', 'habitat_dates', 'habitat_assessment_ids']],
        on=['site_name', 'year'],
        how='outer',
        indicator=True
    )
    
    # Categorize the correlations
    both_have_multiples = correlation_df[correlation_df['_merge'] == 'both'].copy()
    only_fish_multiples = correlation_df[correlation_df['_merge'] == 'left_only'].copy()
    only_habitat_multiples = correlation_df[correlation_df['_merge'] == 'right_only'].copy()
    
    # Get sites that appear in both datasets (regardless of multiple collections)
    all_fish_sites = set(fish_df['site_name'].unique())
    all_habitat_sites = set(habitat_df['site_name'].unique())
    sites_with_both_data_types = all_fish_sites.intersection(all_habitat_sites)
    
    return {
        'fish_multiple': fish_multiple,
        'habitat_multiple': habitat_multiple,
        'both_have_multiples': both_have_multiples,
        'only_fish_multiples': only_fish_multiples,
        'only_habitat_multiples': only_habitat_multiples,
        'sites_with_both_data_types': sites_with_both_data_types,
        'correlation_df': correlation_df
    }

def analyze_year_patterns(results):
    """
    Analyze patterns by year to see if certain years had more replicates.
    
    Args:
        results: Results dictionary from cross_reference_patterns
        
    Returns:
        DataFrame with year-based analysis
    """
    both_multiples = results['both_have_multiples']
    
    if both_multiples.empty:
        return pd.DataFrame()
    
    year_analysis = both_multiples.groupby('year').agg({
        'site_name': 'count',
        'fish_collections': 'sum',
        'habitat_assessments': 'sum'
    }).rename(columns={'site_name': 'sites_with_both_multiples'})
    
    return year_analysis

def print_cross_reference_results(results):
    """
    Print comprehensive cross-reference analysis results.
    """
    print("\n" + "="*80)
    print("FISH-HABITAT COLLECTION PATTERN CROSS-REFERENCE ANALYSIS")
    print("="*80)
    
    fish_multiple = results['fish_multiple']
    habitat_multiple = results['habitat_multiple']
    both_have_multiples = results['both_have_multiples']
    only_fish_multiples = results['only_fish_multiples']
    only_habitat_multiples = results['only_habitat_multiples']
    sites_with_both_data_types = results['sites_with_both_data_types']
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"Sites with both fish and habitat data: {len(sites_with_both_data_types)}")
    print(f"Site/year combinations with multiple fish collections: {len(fish_multiple)}")
    print(f"Site/year combinations with multiple habitat assessments: {len(habitat_multiple)}")
    
    print(f"\n🔗 CORRELATION ANALYSIS:")
    print(f"Site/years with BOTH multiple fish AND multiple habitat: {len(both_have_multiples)}")
    print(f"Site/years with ONLY multiple fish: {len(only_fish_multiples)}")
    print(f"Site/years with ONLY multiple habitat: {len(only_habitat_multiples)}")
    
    if len(both_have_multiples) > 0:
        correlation_rate = len(both_have_multiples) / max(len(fish_multiple), len(habitat_multiple)) * 100
        print(f"Correlation rate: {correlation_rate:.1f}%")
    
    # Show detailed examples
    if not both_have_multiples.empty:
        print(f"\n📝 SITES WITH BOTH MULTIPLE FISH AND HABITAT COLLECTIONS:")
        for _, row in both_have_multiples.iterrows():
            print(f"- {row['site_name']} ({row['year']})")
            print(f"  Fish: {row['fish_collections']} collections on {row['fish_dates']}")
            print(f"  Habitat: {row['habitat_assessments']} assessments on {row['habitat_dates']}")
            print()
    
    if not only_fish_multiples.empty:
        print(f"\n🐟 SITES WITH ONLY MULTIPLE FISH COLLECTIONS:")
        for _, row in only_fish_multiples.head(5).iterrows():
            print(f"- {row['site_name']} ({row['year']}): {row['fish_collections']} fish collections")
        if len(only_fish_multiples) > 5:
            print(f"  ... and {len(only_fish_multiples) - 5} more")
    
    if not only_habitat_multiples.empty:
        print(f"\n🏞️ SITES WITH ONLY MULTIPLE HABITAT ASSESSMENTS:")
        for _, row in only_habitat_multiples.head(5).iterrows():
            print(f"- {row['site_name']} ({row['year']}): {row['habitat_assessments']} habitat assessments")
        if len(only_habitat_multiples) > 5:
            print(f"  ... and {len(only_habitat_multiples) - 5} more")
    
    # Year pattern analysis
    year_analysis = analyze_year_patterns(results)
    if not year_analysis.empty:
        print(f"\n📅 YEAR PATTERN ANALYSIS:")
        print("Years with most correlated replicates:")
        for year, row in year_analysis.sort_values('sites_with_both_multiples', ascending=False).head(5).iterrows():
            print(f"- {year}: {row['sites_with_both_multiples']} sites with both types of multiples")

def provide_recommendations(results):
    """
    Provide recommendations based on the cross-reference analysis.
    """
    both_have_multiples = results['both_have_multiples']
    only_habitat_multiples = results['only_habitat_multiples']
    fish_multiple = results['fish_multiple']
    habitat_multiple = results['habitat_multiple']
    
    print(f"\n🔧 RECOMMENDATIONS:")
    print("-" * 50)
    
    if len(both_have_multiples) > 0:
        correlation_rate = len(both_have_multiples) / len(habitat_multiple) * 100 if len(habitat_multiple) > 0 else 0
        
        print(f"✅ STRONG CORRELATION FOUND ({correlation_rate:.1f}% of habitat duplicates correlate with fish replicates)")
        print(f"\nRecommended approach:")
        print(f"1. For sites with both fish and habitat multiples in the same year:")
        print(f"   - Use fish collection dates to assign habitat assessment dates")
        print(f"   - Apply the same Original/REP logic from fish processing")
        print(f"   - Keep habitat assessments separate (don't average)")
        
        if len(only_habitat_multiples) > 0:
            print(f"\n2. For {len(only_habitat_multiples)} sites with only habitat multiples:")
            print(f"   - Consider averaging these since no fish correlation exists")
            print(f"   - Or investigate further for site-specific reasons")
    else:
        print(f"❌ NO CORRELATION FOUND")
        print(f"Habitat duplicates don't correlate with fish replicates")
        print(f"Consider averaging all habitat duplicates or investigate other causes")
    
    print(f"\n📋 IMPLEMENTATION STEPS:")
    print(f"1. Create habitat duplicate resolution function")
    print(f"2. For correlated sites: assign dates based on fish collection patterns")
    print(f"3. For non-correlated sites: average assessments or keep separate")
    print(f"4. Update habitat_processing.py with the new logic")

def main():
    """
    Main analysis function.
    """
    logger.info("Starting fish-habitat collection pattern cross-reference analysis...")
    
    # Get collection patterns from database
    print("Loading fish collection patterns from database...")
    fish_df = get_fish_collection_patterns()
    
    print("Loading habitat collection patterns from database...")
    habitat_df = get_habitat_collection_patterns()
    
    if fish_df.empty or habitat_df.empty:
        print("❌ Could not load collection patterns from database")
        print("Make sure fish and habitat data have been processed and loaded")
        return
    
    # Perform cross-reference analysis
    print("Analyzing collection pattern correlations...")
    results = cross_reference_patterns(fish_df, habitat_df)
    
    # Print comprehensive results
    print_cross_reference_results(results)
    
    # Provide recommendations
    provide_recommendations(results)
    
    print(f"\n" + "="*80)
    logger.info("Fish-habitat cross-reference analysis complete")

if __name__ == "__main__":
    main()