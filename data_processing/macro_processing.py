"""
macro_processing.py - Macroinvertebrate Community Data Processing

This module processes macroinvertebrate community assessment data from cleaned CSV files 
and loads it into the database. Handles multiple habitat types per collection event and 
calculates biological condition assessments for Blue Thumb stream monitoring.

Key Functions:
- process_macro_csv_data(): Process macroinvertebrate data from cleaned CSV
- insert_macro_collection_events(): Handle complex collection events with multiple habitats
- insert_metrics_data(): Insert metrics and summary scores into database
- load_macroinvertebrate_data(): Main pipeline to process and load macro data

Macro Metrics:
- 6 metrics: Taxa Richness, EPT Taxa, EPT Abundance, HBI Score, 
  % Contribution Dominants, Shannon-Weaver Diversity
- Biological Conditions: Non-impaired, Slightly Impaired, Moderately Impaired, Severely Impaired
- Habitat types: Riffle, Pool, etc. (multiple per site/date)

Data Structure:
- Collection events grouped by site_name + sample_id + habitat
- Supports seasonal collections (Spring/Fall) with habitat-specific assessments

Usage:
- Run directly to test macroinvertebrate data processing
- Import functions for use in the main data pipeline
- Use data_queries.py for retrieving macroinvertebrate data from database
"""

import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from data_processing.biological_utils import (
    insert_collection_events,
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from data_processing import setup_logging

# Set up logging
logger = setup_logging("macro_processing", category="processing")

def process_macro_csv_data(site_name=None):
    """
    Process macroinvertebrate data from cleaned CSV file.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        DataFrame with processed macroinvertebrate data
    """
    try:
        # Load raw macro data from CLEANED CSV
        macro_df = load_csv_data('macro')
        
        if macro_df.empty:
            logger.error("Failed to load macroinvertebrate data from cleaned CSV.")
            return pd.DataFrame()
        
        # Clean column names for consistency 
        macro_df = clean_column_names(macro_df)
        
        # Map to standardized column names 
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
        
        # Create a mapping with only columns that exist in the dataframe
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in macro_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        macro_df = macro_df.rename(columns=valid_mapping)
        
        # Filter by site name if provided 
        if site_name:
            macro_df = macro_df[macro_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(macro_df)} rows for site: {site_name}")
        
        # Handle date formatting 
        if 'collection_date' in macro_df.columns:
            try:
                macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
                macro_df['collection_date_str'] = macro_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Remove invalid values (-999, -99)
        macro_df = remove_invalid_biological_values(macro_df, invalid_values=[-999, -99])
        
        # Convert score columns to numeric
        macro_df = convert_columns_to_numeric(macro_df)
            
        # Calculate total score by summing individual metric scores
        metric_score_cols = [
            'taxa_richness_score', 
            'hbi_score_score', 
            'ept_abundance_score', 
            'ept_taxa_richness_score', 
            'contribution_dominants_score', 
            'shannon_weaver_score'
        ]
        
        # Check which columns exist and calculate total score
        available_score_cols = [col for col in metric_score_cols if col in macro_df.columns]

        if len(available_score_cols) == len(metric_score_cols):
            # Only calculate total if we have all the score columns
            macro_df['total_score'] = macro_df[available_score_cols].sum(axis=1)
            logger.info("Calculated total_score from all component score columns")
        elif available_score_cols:
            # If we only have some but not all score columns, we should log a warning
            logger.warning(f"Only found {len(available_score_cols)} of {len(metric_score_cols)} score columns")
            logger.warning(f"Missing: {set(metric_score_cols) - set(available_score_cols)}")
            
            # Calculate total from available columns but note it's incomplete
            macro_df['total_score'] = macro_df[available_score_cols].sum(axis=1).astype(int)
            logger.info("Calculated partial total_score from available component score columns")
        else:
            # No score columns available
            logger.warning("No metric score columns found, cannot calculate total_score")
            macro_df['total_score'] = None
        
        save_processed_data(macro_df, 'macro_data')
        
        return macro_df
        
    except Exception as e:
        logger.error(f"Error processing macroinvertebrate CSV data: {e}")
        return pd.DataFrame()

def insert_macro_collection_events(cursor, macro_df):
    """
    Insert macro collection events using the shared biological utility.
    
    Args:
        cursor: Database cursor
        macro_df: DataFrame with macro data
    
    Returns:
        dict: Dictionary mapping (sample_id, habitat) to event_id
    """
    try:
        # Define parameters for macro collection events
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
    Insert macroinvertebrate metrics and summary scores into the database.
    
    Args:
        cursor: Database cursor
        macro_df: DataFrame with macro data
        event_id_map: Dictionary mapping (sample_id, habitat) to event_id
    
    Returns:
        int: Number of metrics records inserted
    """
    try:
        # Define metric mappings
        metric_mappings = [
            ('Taxa Richness', 'taxa_richness', 'taxa_richness_score'),
            ('EPT Taxa Richness', 'ept_taxa_richness', 'ept_taxa_richness_score'),
            ('EPT Abundance', 'ept_abundance', 'ept_abundance_score'),
            ('HBI Score', 'hbi_score', 'hbi_score_score'),
            ('% Contribution Dominants', 'contribution_dominants', 'contribution_dominants_score'),
            ('Shannon-Weaver', 'shannon_weaver', 'shannon_weaver_score')
        ]
        
        # Track counts
        metrics_count = 0
        summary_count = 0
        
        # Check which metrics are available
        available_metrics = []
        for metric_name, raw_col, score_col in metric_mappings:
            if raw_col in macro_df.columns and score_col in macro_df.columns:
                available_metrics.append((metric_name, raw_col, score_col))
        
        if not available_metrics:
            logger.error("No metric data available in CSV")
            return 0
            
        # For each unique sample, insert metrics and summary
        for (sample_id, habitat), sample_df in macro_df.groupby(['sample_id', 'habitat']):
            # Skip if no sample_id or not in event_id_map
            mapping_key = (sample_id, habitat)
            if pd.isna(sample_id) or mapping_key not in event_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No event_id found for sample_id={sample_id}, habitat={habitat}")
                continue
                
            event_id = event_id_map[mapping_key]
            
            # Clear existing data for this event (to handle updates)
            cursor.execute('DELETE FROM macro_metrics WHERE event_id = ?', (event_id,))
            cursor.execute('DELETE FROM macro_summary_scores WHERE event_id = ?', (event_id,))
            
            # Get the data (first row in case of duplicates)
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
            
            # Determine biological condition
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
            
            # Insert summary score
            if all(col in row for col in ['total_score', 'comparison_to_reference']) and biological_condition:
                cursor.execute('''
                    INSERT INTO macro_summary_scores
                    (event_id, total_score, comparison_to_reference, biological_condition)
                    VALUES (?, ?, ?, ?)
                ''', (
                    event_id,
                    int(row['total_score']),             
                    float(row['comparison_to_reference']), 
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
    """Load macroinvertebrate data into the database."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM macro_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Process CSV data once at the top level
            macro_df = process_macro_csv_data()
            
            if macro_df.empty:
                logger.warning("No macroinvertebrate data to process")
                return pd.DataFrame()
            
            # Insert collection events using shared utility
            event_id_map = insert_macro_collection_events(cursor, macro_df)
            
            # Insert metrics and summary scores (now consolidated into one function)
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

    # Always return current data state using data_queries function
    from data_processing.data_queries import get_macroinvertebrate_dataframe
    return get_macroinvertebrate_dataframe()
           
if __name__ == "__main__":
   macro_df = load_macroinvertebrate_data()
   if not macro_df.empty:
       logger.info("Macroinvertebrate data summary:")
       logger.info(f"Number of records: {len(macro_df)}")
   else:
       logger.error("No macroinvertebrate data loaded. Check database setup.")