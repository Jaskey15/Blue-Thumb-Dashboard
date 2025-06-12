"""
habitat_processing.py - Habitat Assessment Data Processing

This module processes habitat assessment data from cleaned CSV files and loads it into the database.
Handles habitat metric validation, duplicate resolution through averaging, and calculates 
habitat grades based on total scores for Blue Thumb stream assessments.

Key Functions:
- load_habitat_data(): Main pipeline to process and load habitat data
- process_habitat_csv_data(): Process habitat data from cleaned CSV
- insert_habitat_assessments(): Insert assessment records into database
- insert_metrics_data(): Insert individual metrics and summary scores

Helper Functions:
- resolve_habitat_duplicates(): Average duplicate assessments for same site/date
- calculate_habitat_grade(): Convert total scores to letter grades (A-F)

Habitat Metrics:
- 11 habitat parameters scored 1-20 each (total 0-200 scale, converted to 0-100)
- Grades: A (90+), B (80-89), C (70-79), D (60-69), F (<60)

Usage:
- Run directly to test habitat data processing
- Import functions for use in the main data pipeline

Note: Query functions (get_habitat_dataframe, get_habitat_metrics_data_for_table) 
are available in data_processing.data_queries module.
"""

import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from data_processing import setup_logging

# Set up component-specific logging
logger = setup_logging("habitat_processing", category="processing")

# =============================================================================
# Helper Functions
# =============================================================================

def resolve_habitat_duplicates(habitat_df):
    """
    Resolve habitat duplicate assessments by averaging all numeric metrics and scores.
    
    Args:
        habitat_df: DataFrame with habitat data (after column mapping)
        
    Returns:
        DataFrame with duplicates resolved through averaging
    """
    try:
        # Define columns to average (after column mapping)
        metric_columns = [
            'instream_cover',
            'pool_bottom_substrate', 
            'pool_variability',
            'canopy_cover',
            'rocky_runs_riffles',
            'flow',
            'channel_alteration',
            'channel_sinuosity',
            'bank_stability',
            'bank_vegetation_stability',
            'streamside_cover'
        ]
        
        # Filter to only columns that exist in the DataFrame
        existing_metric_columns = [col for col in metric_columns if col in habitat_df.columns]
        
        if not existing_metric_columns and 'total_score' not in habitat_df.columns:
            logger.warning("No habitat metric columns found for averaging")
            return habitat_df
        
        # Group by site and date to find duplicates
        grouped = habitat_df.groupby(['site_name', 'assessment_date'])
        
        # Separate duplicates from unique records
        duplicate_groups = []
        unique_records = []
        
        for (site_name, date_str), group in grouped:
            if len(group) > 1:
                duplicate_groups.append((site_name, date_str, group))
            else:
                unique_records.append(group)
        
        if not duplicate_groups:
            return habitat_df
        
        # Process each duplicate group
        averaged_records = []
        
        for site_name, date_str, group in duplicate_groups:
            # Calculate averages for specified columns
            averaged_record = group.iloc[0].copy()  # Start with first record as template
            
            # Average individual metrics (round to 1 decimal place)
            for col in existing_metric_columns:
                values = group[col].dropna()
                
                if len(values) > 0:
                    avg_value = values.mean()
                    averaged_record[col] = round(avg_value, 1)
                else:
                    averaged_record[col] = None
            
            # Average total score (round to nearest integer)
            if 'total_score' in habitat_df.columns:
                total_values = group['total_score'].dropna()
                
                if len(total_values) > 0:
                    avg_total = total_values.mean()
                    averaged_record['total_score'] = round(avg_total)
                else:
                    averaged_record['total_score'] = None
            
            # Calculate new habitat grade based on averaged total score (1-100 scale)
            if pd.notna(averaged_record['total_score']):
                averaged_record['habitat_grade'] = calculate_habitat_grade(averaged_record['total_score'])
            else:
                averaged_record['habitat_grade'] = "Unknown"
            
            averaged_records.append(averaged_record)
        
        # Combine unique records with averaged records
        if unique_records:
            unique_df = pd.concat(unique_records, ignore_index=True)
        else:
            unique_df = pd.DataFrame()
        
        if averaged_records:
            averaged_df = pd.DataFrame(averaged_records)
            if not unique_df.empty:
                result_df = pd.concat([unique_df, averaged_df], ignore_index=True)
            else:
                result_df = averaged_df
        else:
            result_df = unique_df
        
        # Log concise summary
        original_count = len(habitat_df)
        final_count = len(result_df)
        duplicates_resolved = original_count - final_count
        
        logger.info(f"Habitat duplicate resolution: {duplicates_resolved} duplicates resolved from {original_count} records")
        
        return result_df
        
    except Exception as e:
        logger.error(f"Error resolving habitat duplicates: {e}")
        return habitat_df

def calculate_habitat_grade(total_score):
    """
    Calculate habitat grade based on total score (1-100 scale).
    
    Args:
        total_score: Numeric total score (1-100 scale)
        
    Returns:
        str: Letter grade (A, B, C, D, F)
    """
    if pd.isna(total_score):
        return "Unknown"
    
    if total_score >= 90:
        return "A"
    elif total_score >= 80:
        return "B"
    elif total_score >= 70:
        return "C"
    elif total_score >= 60:
        return "D"
    else:
        return "F"

# =============================================================================
# Main Processing Functions
# =============================================================================

def load_habitat_data(site_name=None):
    """
    Load habitat data from CSV into the database.
    
    Args:
        site_name: Optional site name to filter data for (default: None, loads all sites)
    
    Returns:
        DataFrame with processed habitat data
    """
    conn = get_connection()
    cursor = conn.cursor()
  
    try: 
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM habitat_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Load habitat data from CSV
            habitat_df = process_habitat_csv_data(site_name)
            
            if habitat_df.empty:
                logger.warning(f"No habitat data found for processing.")
                return pd.DataFrame()
                
            # Insert assessments and get mapping
            assessment_id_map = insert_habitat_assessments(cursor, habitat_df)
            
            # Insert metrics and summary scores
            insert_metrics_data(cursor, habitat_df, assessment_id_map)
            
            conn.commit()
            logger.info("Habitat data loaded successfully")
        else:
            logger.info("Habitat data already exists in the database - skipping processing")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"SQLite error: {e}")
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading habitat data: {e}")
        raise
    finally:
        close_connection(conn)

    # Always return current data state
    from data_processing.data_queries import get_habitat_dataframe
    if site_name:
        return get_habitat_dataframe(site_name)
    else:
        return get_habitat_dataframe()

def process_habitat_csv_data(site_name=None):
    """
    Process habitat data from cleaned CSV file.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with processed habitat data
    """
    try:
        # Load raw habitat data from CLEANED CSV
        habitat_df = load_csv_data('habitat')
        
        if habitat_df.empty:
            logger.error("Failed to load habitat data from cleaned CSV.")
            return pd.DataFrame()
        
        # Clean column names 
        habitat_df = clean_column_names(habitat_df)
        
        # Map to standardized column names 
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'date': 'assessment_date',
            'instreamhabitat': 'instream_cover',
            'poolbottomsubstrate': 'pool_bottom_substrate',
            'poolvariability': 'pool_variability',
            'canopycover': 'canopy_cover',
            'presenceofrockyruns': 'rocky_runs_riffles',
            'presenceofrockyrunsandriffles': 'rocky_runs_riffles',
            'flowlowflow': 'flow',
            'channelalteration': 'channel_alteration',
            'channelsinuosity': 'channel_sinuosity',
            'bankstability': 'bank_stability',
            'bankvegetationstability': 'bank_vegetation_stability',
            'streamsidecover': 'streamside_cover',
            'total': 'total_score',
            'habitatgrade': 'habitat_grade'
        }
        
        # Create a mapping with only columns that exist in the dataframe
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in habitat_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        habitat_df = habitat_df.rename(columns=valid_mapping)
        
        # RESOLVE DUPLICATES
        habitat_df = resolve_habitat_duplicates(habitat_df)
        
        # Filter by site name if provided
        if site_name:
            habitat_df = habitat_df[habitat_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(habitat_df)} rows for site: {site_name}")
        
        # Handle date formatting 
        if 'assessment_date' in habitat_df.columns:
            try:
                habitat_df['assessment_date'] = pd.to_datetime(habitat_df['assessment_date'])
                habitat_df['assessment_date_str'] = habitat_df['assessment_date'].dt.strftime('%Y-%m-%d')
                habitat_df['year'] = habitat_df['assessment_date'].dt.year
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        elif 'year' not in habitat_df.columns:
            # If no date or year column, add a placeholder year
            logger.warning("No assessment_date or year column found, using current year as placeholder")
            from datetime import datetime
            habitat_df['year'] = datetime.now().year
        
        save_processed_data(habitat_df, 'habitat_data')
        
        return habitat_df
        
    except Exception as e:
        logger.error(f"Error processing habitat CSV data: {e}")
        return pd.DataFrame()

def insert_habitat_assessments(cursor, habitat_df):
    """
    Insert habitat assessments into the database.
    
    Args:
        cursor: Database cursor
        habitat_df: DataFrame with habitat data
    
    Returns:
        dict: Dictionary mapping sample_ids to assessment_ids
    """
    try:
        assessment_id_map = {}  # Map sample_id to assessment_id
        
        # Check for required columns
        if 'site_name' not in habitat_df.columns or 'sample_id' not in habitat_df.columns:
            logger.error("Missing required columns site_name or sample_id")
            return assessment_id_map
            
        # Get unique assessments by site_name and sample_id
        unique_assessments = habitat_df.drop_duplicates(subset=['site_name', 'sample_id']).copy()
        
        for _, assessment in unique_assessments.iterrows():
            # Get site_id (assumes site already exists)
            cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (assessment['site_name'],))
            site_result = cursor.fetchone()

            if site_result:
                site_id = site_result[0]
            else:
                logger.error(f"Site '{assessment['site_name']}' not found in database. Run site processing first.")
                continue  # Skip this assessment
            
            # Format date if available
            assessment_date = assessment.get('assessment_date_str', None)
            if assessment_date is None and 'assessment_date' in assessment:
                try:
                    assessment_date = pd.to_datetime(assessment['assessment_date']).strftime('%Y-%m-%d')
                except:
                    assessment_date = None
            
            # Get year
            year = assessment.get('year')
            
            # Insert habitat assessment
            cursor.execute('''
                INSERT INTO habitat_assessments 
                (site_id, assessment_date, year)
                VALUES (?, ?, ?)
            ''', (
                site_id, 
                assessment_date, 
                year
            ))
            
            assessment_id = cursor.lastrowid
            
            # Store mapping using sample_id
            assessment_id_map[assessment['sample_id']] = assessment_id
        
        logger.info(f"Inserted {len(assessment_id_map)} habitat assessments")
        return assessment_id_map
        
    except Exception as e:
        logger.error(f"Error inserting habitat assessments: {e}")
        return {}

def insert_metrics_data(cursor, habitat_df, assessment_id_map):
    """
    Insert habitat metrics and summary scores into the database.
    
    Args:
        cursor: Database cursor
        habitat_df: DataFrame with habitat data
        assessment_id_map: Dictionary mapping sample_id to assessment_id
    
    Returns:
        int: Number of metrics records inserted
    """
    try:
        # Define the metrics we expect to find
        expected_metrics = [
            'instream_cover',
            'pool_bottom_substrate',
            'pool_variability',
            'canopy_cover', 
            'rocky_runs_riffles',
            'flow',
            'channel_alteration',
            'channel_sinuosity',
            'bank_stability',
            'bank_vegetation_stability',
            'streamside_cover'
        ]
        
        # Find which metrics are available in the data
        available_metrics = [col for col in expected_metrics if col in habitat_df.columns]
        
        if not available_metrics:
            logger.error("No habitat metrics columns found in data")
            return 0
            
        # Track counts
        metrics_count = 0
        summary_count = 0
        
        # For each unique sample, insert metrics and summary
        for sample_id, sample_df in habitat_df.groupby('sample_id'):
            # Skip if no sample_id or not in assessment_id_map
            if pd.isna(sample_id) or sample_id not in assessment_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No assessment_id found for sample_id={sample_id}")
                continue
                
            assessment_id = assessment_id_map[sample_id]
            
            # Clear existing data for this assessment (to handle updates)
            cursor.execute('DELETE FROM habitat_metrics WHERE assessment_id = ?', (assessment_id,))
            cursor.execute('DELETE FROM habitat_summary_scores WHERE assessment_id = ?', (assessment_id,))
            
            # Get the data (first row in case of duplicates)
            row = sample_df.iloc[0]
            
            # Insert metrics for this assessment
            for metric_name in available_metrics:
                if pd.notna(row.get(metric_name)):
                    try:
                        # Format metric name for display
                        display_name = metric_name.replace('_', ' ').title()
                        
                        # Round individual metrics to 1 decimal place for database storage
                        metric_value = round(float(row[metric_name]), 1)
                        
                        cursor.execute('''
                            INSERT INTO habitat_metrics 
                            (assessment_id, metric_name, score)
                            VALUES (?, ?, ?)
                        ''', (
                            assessment_id,
                            display_name,
                            metric_value
                        ))
                        metrics_count += 1
                    except Exception as e:
                        logger.error(f"Error inserting metric {metric_name}: {e}")
            
            # Use the habitat grade from our duplicate resolution (which may be newly calculated)
            habitat_grade = row.get('habitat_grade', "Unknown")
            
            # Validate the habitat grade value
            valid_grades = ["A", "B", "C", "D", "F"]
            if habitat_grade not in valid_grades:
                logger.warning(f"Invalid habitat_grade '{habitat_grade}' for sample_id={sample_id}, setting to Unknown")
                habitat_grade = "Unknown"
            
            # Insert summary score
            if 'total_score' in row and pd.notna(row['total_score']) and habitat_grade != "Unknown":
                try:
                    # Round total score to nearest integer for database storage
                    total_score = round(float(row['total_score']))
                    
                    cursor.execute('''
                        INSERT INTO habitat_summary_scores
                        (assessment_id, total_score, habitat_grade)
                        VALUES (?, ?, ?)
                    ''', (
                        assessment_id,
                        total_score,
                        habitat_grade
                    ))
                    summary_count += 1
                except Exception as e:
                    logger.error(f"Error inserting summary score for sample_id={sample_id}: {e}")
            else:
                logger.warning(f"Missing required data for summary scores for sample_id={sample_id}")
        
        logger.info(f"Inserted {metrics_count} habitat metrics and {summary_count} summary records")
        return metrics_count
        
    except Exception as e:
        logger.error(f"Error inserting metrics data: {e}")
        return 0

if __name__ == "__main__":
    habitat_df = load_habitat_data()
    if not habitat_df.empty:
        logger.info("Habitat data summary:")
        logger.info(f"Number of records: {len(habitat_df)}")
    else:
        logger.error("No habitat data loaded. Check database setup.")