"""
Fish Data Investigation Script - Phase 5: REP Collections Analysis
================================================================

This script analyzes REP (repeat) collections in the BT fish collection dates
to understand patterns, timing, and score differences between original and repeat samples.

Focus areas:
1. Identify original-REP collection pairs
2. Analyze timing patterns between collections
3. Compare scores between original and REP samples
4. Identify patterns and recommend processing strategy

Author: Jacob Askey
Purpose: Investigate REP collection patterns for data quality improvement
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Database connection
def get_connection():
    """Get database connection"""
    db_path = 'database/tenmile_biology.db'
    return sqlite3.connect(db_path)

def load_bt_fish_collection_dates():
    """Load BT fish collection dates including REP collections"""
    
    print("=" * 60)
    print("LOADING BT FISH COLLECTION DATES (INCLUDING REP)")
    print("=" * 60)
    
    try:
        # Load the CSV - now should include all fish collections
        csv_path = 'data/raw/BT_fish_collection_dates.csv'
        bt_dates = pd.read_csv(csv_path)
        
        print(f"Loaded {len(bt_dates)} BT fish collection records")
        print(f"Columns: {list(bt_dates.columns)}")
        
        # Clean and standardize dates
        bt_dates['Date_Clean'] = pd.to_datetime(bt_dates['Date'], errors='coerce')
        bt_dates = bt_dates.dropna(subset=['Date_Clean'])
        
        # Clean site names
        bt_dates['Site_Clean'] = bt_dates['Name'].str.strip()
        
        # Add year for easier comparison
        bt_dates['Year'] = bt_dates['Date_Clean'].dt.year
        
        # Categorize collection types
        bt_dates['Collection_Type'] = bt_dates['M/F/H'].apply(categorize_collection_type)
        
        print(f"After date cleaning: {len(bt_dates)} valid fish records")
        print(f"Date range: {bt_dates['Date_Clean'].min()} to {bt_dates['Date_Clean'].max()}")
        print(f"Year range: {bt_dates['Year'].min()} to {bt_dates['Year'].max()}")
        print(f"Unique sites: {bt_dates['Site_Clean'].nunique()}")
        
        # Show collection type distribution
        print(f"\nCollection type distribution:")
        type_counts = bt_dates['Collection_Type'].value_counts()
        for col_type, count in type_counts.items():
            print(f"  {col_type}: {count}")
        
        return bt_dates
        
    except Exception as e:
        print(f"Error loading BT fish collection dates: {e}")
        return pd.DataFrame()

def categorize_collection_type(m_f_h_value):
    """Categorize collection types from M/F/H column"""
    
    if pd.isna(m_f_h_value):
        return 'Unknown'
    
    value_lower = str(m_f_h_value).lower()
    
    if 'rep' in value_lower:
        return 'REP'
    elif 'boat' in value_lower:
        return 'Boat'
    elif value_lower == 'fish':
        return 'Standard'
    else:
        return 'Other'

def identify_rep_collection_pairs(bt_dates):
    """Identify original-REP collection pairs"""
    
    print("\n" + "=" * 60)
    print("IDENTIFYING ORIGINAL-REP COLLECTION PAIRS")
    print("=" * 60)
    
    rep_pairs = []
    
    # Get REP collections
    rep_collections = bt_dates[bt_dates['Collection_Type'] == 'REP'].copy()
    standard_collections = bt_dates[bt_dates['Collection_Type'] == 'Standard'].copy()
    
    print(f"REP collections found: {len(rep_collections)}")
    print(f"Standard collections found: {len(standard_collections)}")
    
    for _, rep_record in rep_collections.iterrows():
        rep_site = rep_record['Site_Clean']
        rep_date = rep_record['Date_Clean']
        rep_year = rep_record['Year']
        
        # Find potential original collections for this site
        # Look for standard collections at same site in same year, before REP date
        potential_originals = standard_collections[
            (standard_collections['Site_Clean'] == rep_site) &
            (standard_collections['Year'] == rep_year) &
            (standard_collections['Date_Clean'] < rep_date)
        ].copy()
        
        if not potential_originals.empty:
            # Find the closest original collection before the REP
            potential_originals['Days_Before_REP'] = (rep_date - potential_originals['Date_Clean']).dt.days
            closest_original = potential_originals.loc[potential_originals['Days_Before_REP'].idxmin()]
            
            days_between = closest_original['Days_Before_REP']
            
            rep_pairs.append({
                'Site': rep_site,
                'Year': rep_year,
                'Original_Date': closest_original['Date_Clean'],
                'REP_Date': rep_date,
                'Days_Between': days_between,
                'Original_COC': closest_original.get('COC', ''),
                'REP_COC': rep_record.get('COC', ''),
                'Original_M_F_H': closest_original['M/F/H'],
                'REP_M_F_H': rep_record['M/F/H']
            })
        else:
            # REP without clear original
            rep_pairs.append({
                'Site': rep_site,
                'Year': rep_year,
                'Original_Date': None,
                'REP_Date': rep_date,
                'Days_Between': None,
                'Original_COC': '',
                'REP_COC': rep_record.get('COC', ''),
                'Original_M_F_H': '',
                'REP_M_F_H': rep_record['M/F/H']
            })
    
    rep_pairs_df = pd.DataFrame(rep_pairs)
    
    # Analysis of pairs
    if not rep_pairs_df.empty:
        pairs_with_original = rep_pairs_df[rep_pairs_df['Original_Date'].notna()]
        orphan_reps = rep_pairs_df[rep_pairs_df['Original_Date'].isna()]
        
        print(f"\nREP PAIRING ANALYSIS:")
        print(f"  REP collections with identified original: {len(pairs_with_original)}")
        print(f"  REP collections without clear original: {len(orphan_reps)}")
        
        if len(pairs_with_original) > 0:
            print(f"\nTIMING ANALYSIS:")
            print(f"  Average days between original and REP: {pairs_with_original['Days_Between'].mean():.1f}")
            print(f"  Median days between original and REP: {pairs_with_original['Days_Between'].median():.1f}")
            print(f"  Min days between: {pairs_with_original['Days_Between'].min()}")
            print(f"  Max days between: {pairs_with_original['Days_Between'].max()}")
            
            # Show distribution of days between
            print(f"\nDAYS BETWEEN DISTRIBUTION:")
            days_bins = [0, 7, 14, 30, 60, 365]
            days_labels = ['0-7 days', '8-14 days', '15-30 days', '31-60 days', '60+ days']
            pairs_with_original['Days_Category'] = pd.cut(pairs_with_original['Days_Between'], 
                                                         bins=days_bins, labels=days_labels, include_lowest=True)
            
            for category in days_labels:
                count = len(pairs_with_original[pairs_with_original['Days_Category'] == category])
                if count > 0:
                    print(f"  {category}: {count}")
        
        # Show examples
        print(f"\nEXAMPLE REP PAIRS:")
        examples = pairs_with_original.head(10) if len(pairs_with_original) > 0 else rep_pairs_df.head(5)
        for _, pair in examples.iterrows():
            if pd.notna(pair['Original_Date']):
                print(f"  {pair['Site']} ({pair['Year']}):")
                print(f"    Original: {pair['Original_Date'].strftime('%Y-%m-%d')} ({pair['Original_M_F_H']})")
                print(f"    REP: {pair['REP_Date'].strftime('%Y-%m-%d')} ({pair['REP_M_F_H']})")
                print(f"    Days between: {pair['Days_Between']}")
            else:
                print(f"  {pair['Site']} ({pair['Year']}): REP without clear original")
            print()
    
    return rep_pairs_df

def load_database_fish_scores():
    """Load fish scores from database for comparison"""
    
    print("\n" + "=" * 60)
    print("LOADING DATABASE FISH SCORES")
    print("=" * 60)
    
    conn = get_connection()
    
    # Simplified query focusing on summary scores only
    query = """
    SELECT 
        f.event_id,
        f.sample_id,
        s.site_name,
        f.collection_date,
        f.year as db_year,
        fs.total_score,
        fs.comparison_to_reference,
        fs.integrity_class
    FROM fish_collection_events f
    JOIN sites s ON f.site_id = s.site_id
    LEFT JOIN fish_summary_scores fs ON f.event_id = fs.event_id
    ORDER BY s.site_name, f.collection_date
    """
    
    db_fish = pd.read_sql_query(query, conn)
    conn.close()
    
    # Process database data
    db_fish['collection_date_clean'] = pd.to_datetime(db_fish['collection_date'])
    db_fish['site_name_clean'] = db_fish['site_name'].str.strip()
    
    # Convert numeric columns to proper types
    db_fish['total_score'] = pd.to_numeric(db_fish['total_score'], errors='coerce')
    db_fish['comparison_to_reference'] = pd.to_numeric(db_fish['comparison_to_reference'], errors='coerce')
    
    print(f"Database fish records with scores: {len(db_fish)}")
    print(f"Records with comparison_to_reference: {db_fish['comparison_to_reference'].notna().sum()}")
    
    return db_fish

def match_rep_pairs_with_scores(rep_pairs_df, db_fish):
    """Match REP pairs with database scores for comparison"""
    
    print("\n" + "=" * 60)
    print("MATCHING REP PAIRS WITH DATABASE SCORES")
    print("=" * 60)
    
    score_comparisons = []
    
    # Only process pairs with both original and REP dates
    valid_pairs = rep_pairs_df[rep_pairs_df['Original_Date'].notna()].copy()
    
    print(f"Processing {len(valid_pairs)} REP pairs with identified originals")
    
    for _, pair in valid_pairs.iterrows():
        site = pair['Site']
        original_date = pair['Original_Date']
        rep_date = pair['REP_Date']
        year = pair['Year']
        
        # Find database records that match these dates (within tolerance)
        site_records = db_fish[db_fish['site_name_clean'] == site].copy()
        
        if site_records.empty:
            continue
        
        # Find original record (within 7 days of BT original date)
        original_tolerance = timedelta(days=7)
        original_matches = site_records[
            abs(site_records['collection_date_clean'] - original_date) <= original_tolerance
        ]
        
        # Find REP record (within 7 days of BT REP date)
        rep_matches = site_records[
            abs(site_records['collection_date_clean'] - rep_date) <= original_tolerance
        ]
        
        # If we found both records, compare them
        if not original_matches.empty and not rep_matches.empty:
            # Use the closest matches
            original_match = original_matches.loc[
                abs(original_matches['collection_date_clean'] - original_date).idxmin()
            ]
            rep_match = rep_matches.loc[
                abs(rep_matches['collection_date_clean'] - rep_date).idxmin()
            ]
            
            comparison = {
                'Site': site,
                'Year': year,
                'Days_Between': pair['Days_Between'],
                
                # BT dates
                'BT_Original_Date': original_date,
                'BT_REP_Date': rep_date,
                
                # DB dates and scores - Original
                'DB_Original_Date': original_match['collection_date_clean'],
                'DB_Original_Total_Score': original_match['total_score'],
                'DB_Original_Comparison': original_match['comparison_to_reference'],
                'DB_Original_Integrity': original_match['integrity_class'],
                
                # DB dates and scores - REP
                'DB_REP_Date': rep_match['collection_date_clean'],
                'DB_REP_Total_Score': rep_match['total_score'],
                'DB_REP_Comparison': rep_match['comparison_to_reference'],
                'DB_REP_Integrity': rep_match['integrity_class'],
                
                # Calculate differences
                'Total_Score_Diff': None,
                'Comparison_Diff': None,
                'Integrity_Changed': None
            }
            
            # Calculate differences if both scores exist
            if (pd.notna(original_match['total_score']) and pd.notna(rep_match['total_score'])):
                try:
                    # Convert to numeric if needed
                    orig_total = pd.to_numeric(original_match['total_score'], errors='coerce')
                    rep_total = pd.to_numeric(rep_match['total_score'], errors='coerce')
                    if pd.notna(orig_total) and pd.notna(rep_total):
                        comparison['Total_Score_Diff'] = rep_total - orig_total
                except:
                    comparison['Total_Score_Diff'] = None
            
            if (pd.notna(original_match['comparison_to_reference']) and pd.notna(rep_match['comparison_to_reference'])):
                try:
                    # Convert to numeric if needed
                    orig_comp = pd.to_numeric(original_match['comparison_to_reference'], errors='coerce')
                    rep_comp = pd.to_numeric(rep_match['comparison_to_reference'], errors='coerce')
                    if pd.notna(orig_comp) and pd.notna(rep_comp):
                        comparison['Comparison_Diff'] = rep_comp - orig_comp
                except:
                    comparison['Comparison_Diff'] = None
            
            if (pd.notna(original_match['integrity_class']) and pd.notna(rep_match['integrity_class'])):
                comparison['Integrity_Changed'] = original_match['integrity_class'] != rep_match['integrity_class']
            
            score_comparisons.append(comparison)
        
        elif not original_matches.empty:
            # Only found original, not REP
            original_match = original_matches.iloc[0]
            comparison = {
                'Site': site,
                'Year': year,
                'Days_Between': pair['Days_Between'],
                'BT_Original_Date': original_date,
                'BT_REP_Date': rep_date,
                'DB_Original_Date': original_match['collection_date_clean'],
                'DB_Original_Total_Score': original_match['total_score'],
                'DB_Original_Comparison': original_match['comparison_to_reference'],
                'DB_Original_Integrity': original_match['integrity_class'],
                'DB_REP_Date': None,
                'DB_REP_Total_Score': None,
                'DB_REP_Comparison': None,
                'DB_REP_Integrity': None,
                'Total_Score_Diff': None,
                'Comparison_Diff': None,
                'Integrity_Changed': None
            }
            score_comparisons.append(comparison)
        
        elif not rep_matches.empty:
            # Only found REP, not original
            rep_match = rep_matches.iloc[0]
            comparison = {
                'Site': site,
                'Year': year,
                'Days_Between': pair['Days_Between'],
                'BT_Original_Date': original_date,
                'BT_REP_Date': rep_date,
                'DB_Original_Date': None,
                'DB_Original_Total_Score': None,
                'DB_Original_Comparison': None,
                'DB_Original_Integrity': None,
                'DB_REP_Date': rep_match['collection_date_clean'],
                'DB_REP_Total_Score': rep_match['total_score'],
                'DB_REP_Comparison': rep_match['comparison_to_reference'],
                'DB_REP_Integrity': rep_match['integrity_class'],
                'Total_Score_Diff': None,
                'Comparison_Diff': None,
                'Integrity_Changed': None
            }
            score_comparisons.append(comparison)
    
    score_comparisons_df = pd.DataFrame(score_comparisons)
    
    if not score_comparisons_df.empty:
        # Analysis of matches
        both_found = score_comparisons_df[
            score_comparisons_df['DB_Original_Date'].notna() & 
            score_comparisons_df['DB_REP_Date'].notna()
        ]
        only_original = score_comparisons_df[
            score_comparisons_df['DB_Original_Date'].notna() & 
            score_comparisons_df['DB_REP_Date'].isna()
        ]
        only_rep = score_comparisons_df[
            score_comparisons_df['DB_Original_Date'].isna() & 
            score_comparisons_df['DB_REP_Date'].notna()
        ]
        
        print(f"SCORE MATCHING RESULTS:")
        print(f"  Pairs with both original and REP scores: {len(both_found)}")
        print(f"  Pairs with only original scores: {len(only_original)}")
        print(f"  Pairs with only REP scores: {len(only_rep)}")
        print(f"  Total pairs matched to database: {len(score_comparisons_df)}")
    
    return score_comparisons_df

def analyze_score_differences(score_comparisons_df):
    """Analyze differences between original and REP scores"""
    
    print("\n" + "=" * 60)
    print("ANALYZING SCORE DIFFERENCES")
    print("=" * 60)
    
    # Focus on pairs with both scores
    both_scores = score_comparisons_df[
        score_comparisons_df['Comparison_Diff'].notna()
    ].copy()
    
    if both_scores.empty:
        print("No pairs with both original and REP scores found.")
        return
    
    print(f"Analyzing {len(both_scores)} pairs with both original and REP scores")
    
    # Summary statistics
    print(f"\nCOMPARISON TO REFERENCE DIFFERENCES:")
    print(f"  Mean difference (REP - Original): {both_scores['Comparison_Diff'].mean():.4f}")
    print(f"  Median difference: {both_scores['Comparison_Diff'].median():.4f}")
    print(f"  Standard deviation: {both_scores['Comparison_Diff'].std():.4f}")
    print(f"  Min difference: {both_scores['Comparison_Diff'].min():.4f}")
    print(f"  Max difference: {both_scores['Comparison_Diff'].max():.4f}")
    
    # Categorize differences
    both_scores['Diff_Category'] = pd.cut(
        both_scores['Comparison_Diff'],
        bins=[-1, -0.1, -0.05, 0.05, 0.1, 1],
        labels=['Large Decrease', 'Small Decrease', 'No Change', 'Small Increase', 'Large Increase'],
        include_lowest=True
    )
    
    print(f"\nDIFFERENCE CATEGORIES:")
    diff_counts = both_scores['Diff_Category'].value_counts()
    for category, count in diff_counts.items():
        percentage = (count / len(both_scores)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")
    
    # Integrity class changes
    integrity_changes = both_scores[both_scores['Integrity_Changed'] == True]
    print(f"\nINTEGRITY CLASS CHANGES:")
    print(f"  Pairs where integrity class changed: {len(integrity_changes)}")
    
    if len(integrity_changes) > 0:
        print(f"  Examples of integrity class changes:")
        for _, row in integrity_changes.head(5).iterrows():
            print(f"    {row['Site']} ({row['Year']}): {row['DB_Original_Integrity']} → {row['DB_REP_Integrity']}")
    
    # Show examples of large differences
    large_diffs = both_scores[abs(both_scores['Comparison_Diff']) > 0.1]
    if len(large_diffs) > 0:
        print(f"\nLARGE SCORE DIFFERENCES (>0.1):")
        for _, row in large_diffs.iterrows():
            print(f"  {row['Site']} ({row['Year']}):")
            print(f"    Original: {row['DB_Original_Comparison']:.3f}")
            print(f"    REP: {row['DB_REP_Comparison']:.3f}")
            print(f"    Difference: {row['Comparison_Diff']:.3f}")
            print(f"    Days between: {row['Days_Between']}")
            print()
    
    # Time pattern analysis
    print(f"\nTIME PATTERN ANALYSIS:")
    time_bins = [0, 14, 30, 60, 365]
    time_labels = ['0-14 days', '15-30 days', '31-60 days', '60+ days']
    both_scores['Time_Category'] = pd.cut(both_scores['Days_Between'], 
                                         bins=time_bins, labels=time_labels, include_lowest=True)
    
    for time_cat in time_labels:
        time_subset = both_scores[both_scores['Time_Category'] == time_cat]
        if len(time_subset) > 0:
            mean_diff = time_subset['Comparison_Diff'].mean()
            print(f"  {time_cat}: {len(time_subset)} pairs, mean diff = {mean_diff:.4f}")

def generate_rep_processing_recommendations(score_comparisons_df, rep_pairs_df):
    """Generate recommendations for processing REP collections"""
    
    print("\n" + "=" * 60)
    print("REP PROCESSING RECOMMENDATIONS")
    print("=" * 60)
    
    both_scores = score_comparisons_df[score_comparisons_df['Comparison_Diff'].notna()]
    
    if not both_scores.empty:
        # Calculate key metrics
        rep_better_count = len(both_scores[both_scores['Comparison_Diff'] > 0])
        original_better_count = len(both_scores[both_scores['Comparison_Diff'] < 0])
        similar_count = len(both_scores[abs(both_scores['Comparison_Diff']) <= 0.05])
        
        rep_better_pct = (rep_better_count / len(both_scores)) * 100
        original_better_pct = (original_better_count / len(both_scores)) * 100
        similar_pct = (similar_count / len(both_scores)) * 100
        
        print(f"SCORE COMPARISON SUMMARY:")
        print(f"  REP scores higher: {rep_better_count} ({rep_better_pct:.1f}%)")
        print(f"  Original scores higher: {original_better_count} ({original_better_pct:.1f}%)")
        print(f"  Scores similar (±0.05): {similar_count} ({similar_pct:.1f}%)")
        
        # Generate recommendations
        print(f"\nRECOMMENDATIONS:")
        
        if rep_better_pct > 60:
            print(f"✅ PREFER REP: REP collections show consistently higher scores")
            print(f"   → Use REP dates and scores when available")
            
        elif original_better_pct > 60:
            print(f"⚠️  PREFER ORIGINAL: Original collections show higher scores")
            print(f"   → Use original dates and scores, treat REP as quality check")
            
        elif similar_pct > 60:
            print(f"📊 AVERAGE OR USE LATEST: Scores are similar between original and REP")
            print(f"   → Consider averaging scores or using the later (REP) collection")
            
        else:
            print(f"🤔 MIXED RESULTS: No clear pattern in score differences")
            print(f"   → Manual review recommended for each pair")
        
        # Additional considerations
        large_diff_count = len(both_scores[abs(both_scores['Comparison_Diff']) > 0.1])
        if large_diff_count > 0:
            large_diff_pct = (large_diff_count / len(both_scores)) * 100
            print(f"\n⚠️  QUALITY CONCERN: {large_diff_count} pairs ({large_diff_pct:.1f}%) show large differences (>0.1)")
            print(f"   → These may indicate field methodology issues or environmental changes")
    
    # Overall processing strategy
    total_reps = len(rep_pairs_df)
    matched_reps = len(score_comparisons_df)
    
    print(f"\nOVERALL PROCESSING STRATEGY:")
    print(f"  Total REP collections: {total_reps}")
    print(f"  REP collections matched to database: {matched_reps}")
    print(f"  Processing approach options:")
    print(f"    1. Use REP dates as authoritative (if REP scores consistently better)")
    print(f"    2. Average original and REP scores (if scores similar)")
    print(f"    3. Flag for manual review (if large differences)")
    print(f"    4. Prefer latest collection date (chronological approach)")

def save_analysis_results(rep_pairs_df, score_comparisons_df):
    """Save analysis results to CSV files"""
    
    print("\n" + "=" * 60)
    print("SAVING ANALYSIS RESULTS")
    print("=" * 60)
    
    # Create output directory if it doesn't exist
    os.makedirs('data/processed', exist_ok=True)
    
    # Save REP pairs analysis
    rep_pairs_df.to_csv('data/processed/rep_collection_pairs.csv', index=False)
    print(f"REP collection pairs saved to: data/processed/rep_collection_pairs.csv")
    
    # Save score comparisons
    if not score_comparisons_df.empty:
        score_comparisons_df.to_csv('data/processed/rep_score_comparisons.csv', index=False)
        print(f"Score comparisons saved to: data/processed/rep_score_comparisons.csv")
    
    print(f"\nFiles saved for further analysis and decision making")

def main():
    """Run REP collections investigation"""
    
    print("REP COLLECTIONS INVESTIGATION")
    print("Phase 5: Understanding Repeat Sample Patterns")
    print("=" * 80)
    
    # Load BT fish collection dates
    bt_dates = load_bt_fish_collection_dates()
    if bt_dates.empty:
        print("Could not load BT fish collection dates. Exiting.")
        return
    
    # Identify REP collection pairs
    rep_pairs_df = identify_rep_collection_pairs(bt_dates)
    
    # Load database fish scores
    db_fish = load_database_fish_scores()
    if db_fish.empty:
        print("Could not load database fish scores. Exiting.")
        return
    
    # Match REP pairs with database scores
    score_comparisons_df = match_rep_pairs_with_scores(rep_pairs_df, db_fish)
    
    # Analyze score differences
    if not score_comparisons_df.empty:
        analyze_score_differences(score_comparisons_df)
        generate_rep_processing_recommendations(score_comparisons_df, rep_pairs_df)
    
    # Save results
    save_analysis_results(rep_pairs_df, score_comparisons_df)
    
    print("\n" + "=" * 80)
    print("REP COLLECTIONS INVESTIGATION COMPLETE")
    print("=" * 80)
    print("\nKEY OUTPUTS:")
    print("1. rep_collection_pairs.csv - All REP pairs identified")
    print("2. rep_score_comparisons.csv - Score comparisons between original and REP")
    print("\nNEXT STEPS:")
    print("1. Review score comparison patterns")
    print("2. Decide on REP processing strategy")
    print("3. Update fish processing pipeline to handle REP collections")
    print("4. Consider quality control implications")
    
    return bt_dates, rep_pairs_df, score_comparisons_df

if __name__ == "__main__":
    results = main()