"""
Processes and loads macroinvertebrate assessment data into the database.

This module manages the data pipeline for macroinvertebrate samples,
including mapping source data, calculating IBI scores, and determining
biological condition based on Blue Thumb protocols.
"""

import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from data_processing.data_queries import get_macroinvertebrate_dataframe
from data_processing.biological_utils import (
    insert_collection_events,
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from data_processing import setup_logging

logger = setup_logging("macro_processing", category="processing")

# Main processing functions

def process_macro_csv_data(site_name=None):
    """
    Loads and processes macroinvertebrate data from the cleaned CSV file.

    This function handles data cleaning, standardization, and calculation
    of summary scores. It can be filtered for a specific site.

    Args:
        site_name (str, optional): A specific site name to filter the data.
                                   Defaults to None.

    Returns:
        A DataFrame with the processed macroinvertebrate data, or an empty
        DataFrame on error.
    """
    try:
        macro_df = load_csv_data('macro')
        
        if macro_df.empty:
            logger.error("Failed to load macroinvertebrate data from cleaned CSV.")
            return pd.DataFrame()
        
        macro_df = clean_column_names(macro_df)
        
        # Map source columns to the standardized database schema.
        column_mapping = {
            'sitename': 'site_name',
            'date': 'collection_date',
            'year': 'year',
            'season': 'season',
            'habitat_type': 'habitat',
            'sampleid': 'sample_id',
            'taxa_richness': 'taxa_richness',
            'modified_hbi': 'hbi_score',
            'ept_perc': 'ept_abundance',
            'ept_taxa': 'ept_taxa_richness',
            'dom_2_taxa': 'contribution_dominants',
            'shannon_weaver': 'shannon_weaver',
            'taxa_richness_score': 'taxa_richness_score',
            'mod_hbi_score': 'hbi_score_score',
            'ept_perc_score': 'ept_abundance_score',
            'ept_taxa_score': 'ept_taxa_richness_score',
            'dom2_taxa_score': 'contribution_dominants_score',
            'shannon_weaver_score': 'shannon_weaver_score',
            'percent_reference': 'comparison_to_reference'
        }
        
        # To avoid errors, create a mapping only with columns present in the dataframe.
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in macro_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        macro_df = macro_df.rename(columns=valid_mapping)
        
        if site_name:
            macro_df = macro_df[macro_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(macro_df)} rows for site: {site_name}")
        
        if 'collection_date' in macro_df.columns:
            try:
                macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
                macro_df['collection_date_str'] = macro_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Remove placeholder values (-999, -99) that indicate missing data.
        macro_df = remove_invalid_biological_values(macro_df, invalid_values=[-999, -99])
        
        macro_df = convert_columns_to_numeric(macro_df)
            
        # Calculate the total IBI score from its component metrics.
        metric_score_cols = [
            'taxa_richness_score', 
            'hbi_score_score', 
            'ept_abundance_score', 
            'ept_taxa_richness_score', 
            'contribution_dominants_score', 
            'shannon_weaver_score'
        ]
        
        # Verify all component score columns are present before summing.
        available_score_cols = [col for col in metric_score_cols if col in macro_df.columns]

        if len(available_score_cols) == len(metric_score_cols):
            macro_df['total_score'] = macro_df[available_score_cols].sum(axis=1)
            logger.info("Calculated total_score from all component score columns")
        elif available_score_cols:
            logger.warning(f"Only found {len(available_score_cols)} of {len(metric_score_cols)} score columns")
            logger.warning(f"Missing: {set(metric_score_cols) - set(available_score_cols)}")
            
            # Calculate a partial score if some component columns are missing.
            macro_df['total_score'] = macro_df[available_score_cols].sum(axis=1).astype(int)
            logger.info("Calculated partial total_score from available component score columns")
        else:
            # Handle cases where no score columns are found.
            logger.warning("No metric score columns found, cannot calculate total_score")
            macro_df['total_score'] = None
        
        save_processed_data(macro_df, 'macro_data')
        
        return macro_df
        
    except Exception as e:
        logger.error(f"Error processing macroinvertebrate CSV data: {e}")
        return pd.DataFrame()

def insert_macro_collection_events(cursor, macro_df):
    """
    Inserts macroinvertebrate collection events via the shared biological utility.

    Args:
        cursor: The database cursor.
        macro_df: DataFrame with processed macroinvertebrate data.

    Returns:
        A mapping from (sample_id, habitat) tuples to their database event_id.
    """
    try:
        # Define parameters for the shared collection event insertion utility.
        table_name = 'macro_collection_events'
        grouping_columns = ['site_name', 'sample_id', 'habitat']
        column_mapping = {
            'site_id': 'site_name',  
            'sample_id': 'sample_id',
            'collection_date': 'collection_date_str',  # Add collection_date
            'season': 'season',
            'year': 'year',
            'habitat': 'habitat'
        }
        
        event_id_map = insert_collection_events(
            cursor=cursor,
            df=macro_df,
            table_name=table_name,
            grouping_columns=grouping_columns,
            column_mapping=column_mapping
        )
        
        return event_id_map
        
    except Exception as e:
        logger.error(f"Error inserting macro collection events: {e}")
        return {}
    
def insert_metrics_data(cursor, macro_df, event_id_map):
    """
    Inserts macroinvertebrate metrics and summary scores for each collection event.

    Args:
        cursor: The database cursor.
        macro_df: DataFrame with processed macroinvertebrate data.
        event_id_map: A mapping from (sample_id, habitat) tuples to event_id.

    Returns:
        The total number of metrics records inserted.
    """
    try:
        # Map standardized metric names to their corresponding data columns.
        metric_mappings = [
            ('Taxa Richness', 'taxa_richness', 'taxa_richness_score'),
            ('EPT Taxa Richness', 'ept_taxa_richness', 'ept_taxa_richness_score'),
            ('EPT Abundance', 'ept_abundance', 'ept_abundance_score'),
            ('HBI Score', 'hbi_score', 'hbi_score_score'),
            ('% Contribution Dominants', 'contribution_dominants', 'contribution_dominants_score'),
            ('Shannon-Weaver', 'shannon_weaver', 'shannon_weaver_score')
        ]
        
        metrics_count = 0
        summary_count = 0
        
        # To avoid errors, check which metric columns are present in the dataframe.
        available_metrics = []
        for metric_name, raw_col, score_col in metric_mappings:
            if raw_col in macro_df.columns and score_col in macro_df.columns:
                available_metrics.append((metric_name, raw_col, score_col))
        
        if not available_metrics:
            logger.error("No metric data available in CSV")
            return 0
            
        for (sample_id, habitat), sample_df in macro_df.groupby(['sample_id', 'habitat']):
            # Skip records if the sample identifier is missing or has no corresponding event.
            mapping_key = (sample_id, habitat)
            if pd.isna(sample_id) or mapping_key not in event_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No event_id found for sample_id={sample_id}, habitat={habitat}")
                continue
                
            event_id = event_id_map[mapping_key]
            
            # Ensure data idempotency by clearing existing records for this event.
            cursor.execute('DELETE FROM macro_metrics WHERE event_id = ?', (event_id,))
            cursor.execute('DELETE FROM macro_summary_scores WHERE event_id = ?', (event_id,))
            
            # Use the first row of the group as the representative record.
            row = sample_df.iloc[0]
            
            # In the insert_metrics_data function, update the metrics insertion:
            for metric_name, raw_col, score_col in available_metrics:
                if pd.notna(row.get(raw_col)) and pd.notna(row.get(score_col)):
                    cursor.execute('''
                        INSERT INTO macro_metrics 
                        (event_id, metric_name, raw_value, metric_score)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        event_id,
                        metric_name,
                        float(row[raw_col]),  
                        int(row[score_col])  
                    ))
                    metrics_count += 1
            
            # Determine biological condition based on official comparison-to-reference thresholds.
            biological_condition = "Unknown" # Default fallback
            
            if 'comparison_to_reference' in row and pd.notna(row['comparison_to_reference']):
                comparison_value = float(row['comparison_to_reference']) * 100  # Convert to percentage
                
                if comparison_value >= 83:
                    biological_condition = "Non-impaired"
                elif comparison_value >= 54:
                    biological_condition = "Slightly Impaired"
                elif comparison_value >= 17:
                    biological_condition = "Moderately Impaired"
                else:
                    biological_condition = "Severely Impaired"
                    
                logger.debug(f"Calculated biological_condition: {biological_condition} (score: {comparison_value}%)")
            else:
                logger.warning(f"Cannot determine biological condition for sample_id={sample_id}, habitat={habitat} - missing comparison_to_reference data")
            
            if all(col in row for col in ['total_score', 'comparison_to_reference']) and biological_condition:
                cursor.execute('''
                    INSERT INTO macro_summary_scores
                    (event_id, total_score, comparison_to_reference, biological_condition)
                    VALUES (?, ?, ?, ?)
                ''', (
                    event_id,
                    int(row['total_score']),             
                    round(float(row['comparison_to_reference']), 2),
                    biological_condition
                ))
                summary_count += 1
            else:
                logger.warning(f"Missing required columns for summary scores for sample_id={sample_id}, habitat={habitat}")
        
        logger.info(f"Inserted {metrics_count} macro metrics and {summary_count} summary records")
        return metrics_count
        
    except Exception as e:
        logger.error(f"Error inserting metrics data: {e}")
        return 0

def load_macroinvertebrate_data():
    """
    Executes the full pipeline to process and load all macroinvertebrate data.

    This function coordinates CSV processing and database insertion. It will
    skip execution if data already exists in the target tables to prevent
    accidental reprocessing.

    Returns:
        A DataFrame containing the processed macroinvertebrate data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # To prevent reprocessing, check if data already exists in the target table.
        cursor.execute('SELECT COUNT(*) FROM macro_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            macro_df = process_macro_csv_data()
            
            if macro_df.empty:
                logger.warning("No macroinvertebrate data to process")
                return pd.DataFrame()
            
            event_id_map = insert_macro_collection_events(cursor, macro_df)
            
            insert_metrics_data(cursor, macro_df, event_id_map)

            conn.commit()   
            logger.info("Macroinvertebrate data loaded successfully")
        else:
            logger.info("Macroinvertebrate data already exists in the database - skipping processing")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"SQLite error: {e}")
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading macroinvertebrate: {e}")
        raise
    finally:
        close_connection(conn)

    # Always return the current state of the data from the database.
    return get_macroinvertebrate_dataframe()
           
if __name__ == "__main__":
   macro_df = load_macroinvertebrate_data()
   if not macro_df.empty:
       logger.info("Macroinvertebrate data summary:")
       logger.info(f"Number of records: {len(macro_df)}")
   else:
       logger.error("No macroinvertebrate data loaded. Check database setup.")