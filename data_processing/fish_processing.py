"""
Processes and loads fish community assessment data into the database.

This module handles the full pipeline for fish data, including distinguishing
between true replicates and data entry errors using the `bt_fieldwork_validator`.
It validates IBI scores, inserts collection events, and loads detailed metrics.
"""

import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from data_processing.biological_utils import insert_collection_events, remove_invalid_biological_values, convert_columns_to_numeric
from data_processing.bt_fieldwork_validator import load_bt_field_work_dates, categorize_and_process_duplicates, correct_collection_dates
from data_processing import setup_logging

logger = setup_logging("fish_processing", category="processing")

# Helper functions

def validate_ibi_scores(fish_df):
    """
    Validates that the total_score is the sum of its IBI component scores.
    
    Args:
        fish_df: A DataFrame containing the fish metrics data.
    
    Returns:
        The DataFrame with a 'score_validated' column indicating validation status.
    """
    try:
        df = fish_df.copy()
        
        score_columns = ['total_species_score', 'sensitive_benthic_score', 
                         'sunfish_species_score', 'intolerant_species_score',
                         'tolerant_score', 'insectivorous_score', 
                         'lithophilic_score']
        
        existing_columns = [col for col in score_columns if col in df.columns]
        
        if len(existing_columns) < len(score_columns):
            missing = set(score_columns) - set(existing_columns)
            logger.warning(f"Missing some IBI component columns: {missing}")
        
        if existing_columns and 'total_score' in df.columns:
            df['calculated_score'] = df[existing_columns].sum(axis=1)
            
            mismatch_mask = df['calculated_score'] != df['total_score']
            mismatches = df[mismatch_mask]
            
            if not mismatches.empty:
                logger.warning(f"Found {len(mismatches)} records where total_score doesn't match sum of components.")
                df['score_validated'] = ~mismatch_mask
            else:
                logger.info("All total_score values match sum of components.")
                df['score_validated'] = True
            
            df = df.drop(columns=['calculated_score'])
        
        return df
    
    except Exception as e:
        logger.error(f"Error validating IBI scores: {e}")
        return fish_df

# Main processing and insertion functions

def process_fish_csv_data(site_name=None):
    """
    Processes fish data from a cleaned CSV file, including advanced replicate handling.
    
    Args:
        site_name: An optional site name to filter the data for.
    
    Returns:
        A DataFrame with the processed fish data.
    """
    try:
        logger.info("Starting fish data processing with replicate handling")
        
        fish_df = load_csv_data('fish', parse_dates=['Date'])
        
        if fish_df.empty:
            logger.error("Failed to load fish data from cleaned CSV.")
            return pd.DataFrame()
        
        fish_df = clean_column_names(fish_df)
        
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'date': 'collection_date',
            'year': 'year',
            'totalspecies': 'total_species',
            'sensitivebenthic': 'sensitive_benthic_species',
            'sunfishspecies': 'sunfish_species',
            'intolerantspecies': 'intolerant_species',
            'percenttolerant': 'proportion_tolerant',
            'percentinsectivore': 'proportion_insectivorous',
            'percentlithophil': 'proportion_lithophilic',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'sunfishspeciesibi': 'sunfish_species_score',
            'intolerantspeciesibi': 'intolerant_species_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score',
            'percentreference': 'comparison_to_reference',
            'fishscore': 'integrity_class'
        }
        
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in fish_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        fish_df = fish_df.rename(columns=valid_mapping)
        
        if site_name:
            fish_df = fish_df[fish_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(fish_df)} rows for site: {site_name}")
        
        if 'collection_date' in fish_df.columns:
            try:
                fish_df['collection_date'] = pd.to_datetime(fish_df['collection_date'])
                fish_df['collection_date_str'] = fish_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Use BT field data as the authoritative source for date correction and replicate handling.
        bt_df = load_bt_field_work_dates()
        fish_df = correct_collection_dates(fish_df, bt_df)
        fish_df = categorize_and_process_duplicates(fish_df, bt_df)
        
        fish_df = remove_invalid_biological_values(fish_df, invalid_values=[-999, -99])
        fish_df = convert_columns_to_numeric(fish_df)
        fish_df = validate_ibi_scores(fish_df)
        
        save_processed_data(fish_df, 'fish_data')

        logger.info(f"Fish processing complete: {len(fish_df)} final records")
        return fish_df
        
    except Exception as e:
        logger.error(f"Error processing fish CSV data: {e}")
        return pd.DataFrame()

def insert_fish_collection_events(cursor, fish_df):
    """
    Inserts fish collection events into the database using a shared utility function.
    
    Args:
        cursor: A database cursor.
        fish_df: A DataFrame with the processed fish data.
    
    Returns:
        A dictionary mapping each sample_id to its new event_id.
    """
    try:
        table_name = 'fish_collection_events'
        grouping_columns = ['site_name', 'sample_id']
        column_mapping = {
            'site_id': 'site_name',
            'sample_id': 'sample_id',
            'collection_date': 'collection_date_str',
            'year': 'year'
        }
        
        event_id_map = insert_collection_events(
            cursor=cursor,
            df=fish_df,
            table_name=table_name,
            grouping_columns=grouping_columns,
            column_mapping=column_mapping
        )
        
        return event_id_map
        
    except Exception as e:
        logger.error(f"Error inserting fish collection events: {e}")
        return {}

def insert_metrics_data(cursor, fish_df, event_id_map):
    """
    Inserts fish metrics and summary scores into the database for each collection event.
    
    Args:
        cursor: A database cursor.
        fish_df: A DataFrame with the processed fish data.
        event_id_map: A dictionary mapping sample_ids to event_ids.
    
    Returns:
        The total number of metrics records inserted.
    """
    try:
        metric_mappings = [
            ('Total No. of species', 'total_species', 'total_species_score'),
            ('No. of sensitive benthic species', 'sensitive_benthic_species', 'sensitive_benthic_score'),
            ('No. of sunfish species', 'sunfish_species', 'sunfish_species_score'),
            ('No. of intolerant species', 'intolerant_species', 'intolerant_species_score'),
            ('Proportion tolerant individuals', 'proportion_tolerant', 'tolerant_score'),
            ('Proportion insectivorous cyprinid', 'proportion_insectivorous', 'insectivorous_score'),
            ('Proportion lithophilic spawners', 'proportion_lithophilic', 'lithophilic_score')
        ]
        
        metrics_count = 0
        summary_count = 0
        
        # Determine which metrics are actually available in the DataFrame to avoid errors.
        available_metrics = []
        for metric_name, raw_col, score_col in metric_mappings:
            if raw_col in fish_df.columns and score_col in fish_df.columns:
                available_metrics.append((metric_name, raw_col, score_col))
        
        if not available_metrics:
            logger.error("No metric data available in CSV")
            return 0
            
        for sample_id, sample_df in fish_df.groupby('sample_id'):
            if pd.isna(sample_id) or sample_id not in event_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No event_id found for sample_id={sample_id}")
                continue
                
            event_id = event_id_map[sample_id]
            
            # Clear existing data for this event to handle updates and prevent duplicates.
            cursor.execute('DELETE FROM fish_metrics WHERE event_id = ?', (event_id,))
            cursor.execute('DELETE FROM fish_summary_scores WHERE event_id = ?', (event_id,))
            
            # Use the first row in case duplicates still exist after processing.
            row = sample_df.iloc[0]
            
            for metric_name, raw_col, score_col in available_metrics:
                if pd.notna(row.get(raw_col)) and pd.notna(row.get(score_col)):
                    # For proportion-based metrics, the raw value is stored as the result.
                    metric_result = row[raw_col] if metric_name.startswith('Proportion') else None
                    
                    cursor.execute('''
                        INSERT INTO fish_metrics 
                        (event_id, metric_name, raw_value, metric_result, metric_score)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        event_id,
                        metric_name,
                        row[raw_col],
                        metric_result,
                        row[score_col]
                    ))
                    metrics_count += 1
            
            # Determine integrity class, prioritizing the pre-calculated value from the CSV.
            integrity_class = "Unknown"

            if 'integrity_class' in row and pd.notna(row['integrity_class']) and str(row['integrity_class']).strip():
                integrity_class = str(row['integrity_class']).strip()
            else:
                # Fallback to calculating the class if it's not provided.
                if 'comparison_to_reference' in row and pd.notna(row['comparison_to_reference']):
                    comparison_value = float(row['comparison_to_reference']) * 100
                    
                    if comparison_value >= 97:
                        integrity_class = "Excellent"
                    elif comparison_value >= 76:
                        integrity_class = "Good"
                    elif comparison_value >= 60:
                        integrity_class = "Fair"
                    elif comparison_value >= 47:
                        integrity_class = "Poor"
                    else:
                        integrity_class = "Very Poor"

            # Ensure the integrity class is a valid, expected value before insertion.
            valid_classes = ["Excellent", "Good", "Fair", "Poor", "Very Poor"]
            if integrity_class not in valid_classes:
                logger.warning(f"Invalid integrity_class '{integrity_class}' for sample_id={sample_id}, setting to Unknown")
                integrity_class = "Unknown"

            if all(col in row for col in ['total_score', 'comparison_to_reference']) and integrity_class != "Unknown":
                cursor.execute('''
                    INSERT INTO fish_summary_scores
                    (event_id, total_score, comparison_to_reference, integrity_class)
                    VALUES (?, ?, ?, ?)
                ''', (
                    event_id,
                    row['total_score'],
                    round(float(row['comparison_to_reference']), 2),
                    integrity_class
                ))
                summary_count += 1
            else:
                logger.warning(f"Missing required columns for summary scores for sample_id={sample_id}")
        
        logger.info(f"Inserted {metrics_count} fish metrics and {summary_count} summary records")
        return metrics_count
        
    except Exception as e:
        logger.error(f"Error inserting metrics data: {e}")
        return 0

def load_fish_data(site_name=None):
    """
    Executes the full pipeline to process and load fish data into the database.
    
    Args:
        site_name: An optional site name to filter data for. If None, all sites are loaded.
    
    Returns:
        True if the processing was successful, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
  
    try:
        # To prevent re-processing, check if data already exists in the target table.
        cursor.execute('SELECT COUNT(*) FROM fish_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            fish_df = process_fish_csv_data(site_name)
            
            if fish_df.empty:
                logger.warning("No fish data found for processing.")
                return False
                
            event_id_map = insert_fish_collection_events(cursor, fish_df)
            
            insert_metrics_data(cursor, fish_df, event_id_map)
            
            conn.commit()
            logger.info("Fish data loaded successfully")
            return True
        else:
            logger.info("Fish data already exists in the database - skipping processing")
            return True

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading fish data: {e}")
        return False
    finally:
        close_connection(conn)

if __name__ == "__main__":
    success = load_fish_data()
    if success:
        logger.info("Fish data processing completed successfully")
    else:
        logger.error("Fish data processing failed. Check database setup.")