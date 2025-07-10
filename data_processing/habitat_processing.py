"""
Processes and loads habitat assessment data into the database.

This module handles the full pipeline for habitat data, including resolving
duplicate entries by averaging, calculating habitat grades from total scores,
and inserting the final data into the database.
"""

import sqlite3
from datetime import datetime

import pandas as pd

from data_processing import setup_logging
from data_processing.data_loader import (
    clean_column_names,
    load_csv_data,
    save_processed_data,
)
from data_processing.data_queries import get_habitat_dataframe
from database.database import close_connection, get_connection

logger = setup_logging("habitat_processing", category="processing")

# Helper functions

def resolve_habitat_duplicates(habitat_df):
    """
    Resolves duplicate habitat assessments by averaging their numeric metrics and scores.
    
    A duplicate is defined as an assessment for the same site on the same date.
    
    Args:
        habitat_df: A DataFrame containing habitat data, with standardized column names.
        
    Returns:
        A DataFrame with duplicate assessments resolved through averaging.
    """
    try:
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
        
        existing_metric_columns = [col for col in metric_columns if col in habitat_df.columns]
        
        if not existing_metric_columns and 'total_score' not in habitat_df.columns:
            logger.warning("No habitat metric columns found for averaging")
            return habitat_df
        
        grouped = habitat_df.groupby(['site_name', 'assessment_date'])
        
        duplicate_groups = []
        unique_records = []
        
        for (site_name, date_str), group in grouped:
            if len(group) > 1:
                duplicate_groups.append((site_name, date_str, group))
            else:
                unique_records.append(group)
        
        if not duplicate_groups:
            return habitat_df
        
        averaged_records = []
        
        for site_name, date_str, group in duplicate_groups:
            # Use the first record as a template for the averaged entry.
            averaged_record = group.iloc[0].copy()
            
            for col in existing_metric_columns:
                values = group[col].dropna()
                
                if len(values) > 0:
                    avg_value = values.mean()
                    averaged_record[col] = round(avg_value, 1)
                else:
                    averaged_record[col] = None
            
            if 'total_score' in habitat_df.columns:
                total_values = group['total_score'].dropna()
                
                if len(total_values) > 0:
                    avg_total = total_values.mean()
                    averaged_record['total_score'] = round(avg_total)
                else:
                    averaged_record['total_score'] = None
            
            # Recalculate the habitat grade based on the new averaged score.
            if pd.notna(averaged_record['total_score']):
                averaged_record['habitat_grade'] = calculate_habitat_grade(averaged_record['total_score'])
            else:
                averaged_record['habitat_grade'] = "Unknown"
            
            averaged_records.append(averaged_record)
        
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
    Calculates a letter grade (A-F) from a total habitat score.
    
    The score is expected to be on a 1-100 scale.
    
    Args:
        total_score: A numeric total score.
        
    Returns:
        A string representing the letter grade ('A', 'B', 'C', 'D', 'F').
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

# Main processing functions

def load_habitat_data(site_name=None):
    """
    Executes the full pipeline to process and load habitat data into the database.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A DataFrame containing the processed habitat data from the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
  
    try: 
        # To prevent re-processing, check if data already exists in the target table.
        cursor.execute('SELECT COUNT(*) FROM habitat_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            habitat_df = process_habitat_csv_data(site_name)
            
            if habitat_df.empty:
                logger.warning(f"No habitat data found for processing.")
                return pd.DataFrame()
                
            assessment_id_map = insert_habitat_assessments(cursor, habitat_df)
            
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

    # Always return the current state of the data from the database.
    if site_name:
        return get_habitat_dataframe(site_name)
    else:
        return get_habitat_dataframe()

def process_habitat_csv_data(site_name=None):
    """
    Processes habitat data from a cleaned CSV file, resolving duplicates along the way.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A DataFrame with the processed habitat data.
    """
    try:
        habitat_df = load_csv_data('habitat')
        
        if habitat_df.empty:
            logger.error("Failed to load habitat data from cleaned CSV.")
            return pd.DataFrame()
        
        habitat_df = clean_column_names(habitat_df)
        
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
        
        # Create a mapping that only includes columns present in the DataFrame to avoid errors.
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in habitat_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        habitat_df = habitat_df.rename(columns=valid_mapping)
        
        habitat_df = resolve_habitat_duplicates(habitat_df)
        
        if site_name:
            habitat_df = habitat_df[habitat_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(habitat_df)} rows for site: {site_name}")
        
        if 'assessment_date' in habitat_df.columns:
            try:
                habitat_df['assessment_date'] = pd.to_datetime(habitat_df['assessment_date'])
                habitat_df['assessment_date_str'] = habitat_df['assessment_date'].dt.strftime('%Y-%m-%d')
                habitat_df['year'] = habitat_df['assessment_date'].dt.year
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        elif 'year' not in habitat_df.columns:
            # If no date or year is available, use the current year as a fallback.
            logger.warning("No assessment_date or year column found, using current year as placeholder")
            habitat_df['year'] = datetime.now().year
        
        save_processed_data(habitat_df, 'habitat_data')
        
        return habitat_df
        
    except Exception as e:
        logger.error(f"Error processing habitat CSV data: {e}")
        return pd.DataFrame()

def insert_habitat_assessments(cursor, habitat_df):
    """
    Inserts unique habitat assessments into the database.
    
    Args:
        cursor: A database cursor.
        habitat_df: A DataFrame with the processed habitat data.
    
    Returns:
        A dictionary mapping sample_ids to their new assessment_ids.
    """
    try:
        assessment_id_map = {}
        
        if 'site_name' not in habitat_df.columns or 'sample_id' not in habitat_df.columns:
            logger.error("Missing required columns site_name or sample_id")
            return assessment_id_map
            
        unique_assessments = habitat_df.drop_duplicates(subset=['site_name', 'sample_id']).copy()
        
        for _, assessment in unique_assessments.iterrows():
            cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (assessment['site_name'],))
            site_result = cursor.fetchone()

            if site_result:
                site_id = site_result[0]
            else:
                logger.error(f"Site '{assessment['site_name']}' not found in database. Run site processing first.")
                continue
            
            assessment_date = assessment.get('assessment_date_str', None)
            if assessment_date is None and 'assessment_date' in assessment:
                try:
                    assessment_date = pd.to_datetime(assessment['assessment_date']).strftime('%Y-%m-%d')
                except:
                    assessment_date = None
            
            year = assessment.get('year')
            
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
            
            assessment_id_map[assessment['sample_id']] = assessment_id
        
        logger.info(f"Inserted {len(assessment_id_map)} habitat assessments")
        return assessment_id_map
        
    except Exception as e:
        logger.error(f"Error inserting habitat assessments: {e}")
        return {}

def insert_metrics_data(cursor, habitat_df, assessment_id_map):
    """
    Inserts habitat metrics and summary scores into the database for each assessment.
    
    Args:
        cursor: A database cursor.
        habitat_df: A DataFrame with the processed habitat data.
        assessment_id_map: A dictionary mapping sample_ids to assessment_ids.
    
    Returns:
        The total number of metrics records inserted.
    """
    try:
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
        
        # Determine which metrics are actually available in the DataFrame.
        available_metrics = [col for col in expected_metrics if col in habitat_df.columns]
        
        if not available_metrics:
            logger.error("No habitat metrics columns found in data")
            return 0
            
        metrics_count = 0
        summary_count = 0
        
        for sample_id, sample_df in habitat_df.groupby('sample_id'):
            if pd.isna(sample_id) or sample_id not in assessment_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No assessment_id found for sample_id={sample_id}")
                continue
                
            assessment_id = assessment_id_map[sample_id]
            
            # Clear existing data to prevent duplicates and handle updates.
            cursor.execute('DELETE FROM habitat_metrics WHERE assessment_id = ?', (assessment_id,))
            cursor.execute('DELETE FROM habitat_summary_scores WHERE assessment_id = ?', (assessment_id,))
            
            # Use the first row in case duplicates still exist after processing.
            row = sample_df.iloc[0]
            
            for metric_name in available_metrics:
                if pd.notna(row.get(metric_name)):
                    try:
                        # Format the metric name for display purposes (e.g., 'instream_cover' -> 'Instream Cover').
                        display_name = metric_name.replace('_', ' ').title()
                        
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
            
            # Use the habitat grade from duplicate resolution, which may have been recalculated.
            habitat_grade = row.get('habitat_grade', "Unknown")
            
            # Ensure the habitat grade is a valid, expected value.
            valid_grades = ["A", "B", "C", "D", "F"]
            if habitat_grade not in valid_grades:
                logger.warning(f"Invalid habitat_grade '{habitat_grade}' for sample_id={sample_id}, setting to Unknown")
                habitat_grade = "Unknown"
            
            if 'total_score' in row and pd.notna(row['total_score']) and habitat_grade != "Unknown":
                try:
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