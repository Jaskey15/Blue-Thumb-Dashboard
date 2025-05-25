import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from utils import setup_logging

# Set up logging
logger = setup_logging("macro_processing", category="processing")

def load_macroinvertebrate_data():
    """Load macroinvertebrate data into the database."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM macro_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Insert data
            insert_collection_events(cursor)
            insert_reference_and_metrics_data(cursor)
            calculate_summary_scores(cursor)

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

    # Always return current data state
    return get_macroinvertebrate_dataframe()

def process_macro_csv_data(site_name=None):
    """
    Process macroinvertebrate data from CSV file.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        DataFrame with processed macroinvertebrate data
    """
    try:
        # Load raw macro data
        macro_df = load_csv_data('macro')
        
        if macro_df.empty:
            logger.error("Failed to load macroinvertebrate data from CSV.")
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
        
        # Handle date formatting
        if 'collection_date' in macro_df.columns:
            try:
                macro_df['collection_date'] = pd.to_datetime(macro_df['collection_date'])
                macro_df['collection_date_str'] = macro_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Check for invalid data (-99 or -999 values)
        score_columns = [col for col in macro_df.columns if col.endswith('_score')]
        score_columns.append('comparison_to_reference')
        
        # Remove rows with -99 or -999 values in score columns or comparison_to_reference
        invalid_mask = (macro_df[score_columns] == -99).any(axis=1) | (macro_df[score_columns] == -999).any(axis=1)
        if invalid_mask.any():
            logger.warning(f"Removing {invalid_mask.sum()} rows with invalid scores (-99 or -999)")
            macro_df = macro_df[~invalid_mask]
        
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
            macro_df['total_score'] = macro_df[available_score_cols].sum(axis=1)
            logger.info("Calculated partial total_score from available component score columns")
        else:
            # No score columns available
            logger.warning("No metric score columns found, cannot calculate total_score")
            macro_df['total_score'] = None
        
        # Determine biological condition based on comparison_to_reference
        if 'comparison_to_reference' in macro_df.columns:
            macro_df['biological_condition'] = macro_df['comparison_to_reference'].apply(determine_biological_condition)
            logger.info("Determined biological_condition based on comparison_to_reference")
        
        save_processed_data(macro_df, 'macro_data')
        
        return macro_df
        
    except Exception as e:
        logger.error(f"Error processing macroinvertebrate CSV data: {e}")
        return pd.DataFrame()

def determine_biological_condition(comparison_value):
    """
    Determine biological condition based on comparison to reference value.
    Uses Table 6 thresholds.
    
    Args:
        comparison_value: The comparison to reference value (0-1 proportion)
        
    Returns:
        str: Biological condition category
    """
    if pd.isna(comparison_value):
        return "Unknown"
        
    try:
        comparison_value = float(comparison_value)
        
        if comparison_value > 0.83:
            return "Non-impaired"
        elif comparison_value >= 0.54:
            return "Slightly Impaired"
        elif comparison_value >= 0.17:
            return "Moderately Impaired"
        else:
            return "Severely Impaired"
    except:
        return "Unknown"

def insert_collection_events(cursor):
    """Insert macroinvertebrate collection events into the database."""
    try:
        # Process data from CSV
        macro_df = process_macro_csv_data()
        
        if macro_df.empty:
            logger.warning("No macroinvertebrate data to insert")
            return
            
        # Get required columns
        required_cols = ['site_name', 'sample_id', 'season', 'year', 'habitat']
        missing_cols = [col for col in required_cols if col not in macro_df.columns]
        
        if missing_cols:
            logger.error(f"Missing required columns for collection events: {missing_cols}")
            return
            
        # Get unique collection events
        unique_events = macro_df.drop_duplicates(subset=['site_name', 'sample_id', 'season', 'year']).copy()
        
        # Insert each collection event
        for _, event in unique_events.iterrows():
            # Get site_id (assumes site already exists)
            cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (event['site_name'],))
            site_result = cursor.fetchone()

            if site_result:
                site_id = site_result[0]
            else:
                logger.error(f"Site '{event['site_name']}' not found in database. Run site processing first.")
                continue  # Skip this event
            
            # Insert collection event
            cursor.execute('''
                INSERT INTO macro_collection_events 
                (site_id, sample_id, season, year, habitat)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                site_id, 
                event.get('sample_id'), 
                event.get('season'), 
                event.get('year'), 
                event.get('habitat')
            ))
        
        logger.info(f"Inserted {len(unique_events)} macroinvertebrate collection events")
        
    except Exception as e:
        logger.error(f"Error inserting collection events: {e}")
        raise

def insert_reference_and_metrics_data(cursor):
    """Insert macroinvertebrate reference values and metrics data"""
    try:
        # Process data from CSV
        macro_df = process_macro_csv_data()
        
        if macro_df.empty:
            logger.warning("No macroinvertebrate data to insert")
            return
        
        # Group by sample_id - only process each unique sample once
        unique_samples = macro_df.drop_duplicates(subset=['sample_id']).copy()
        logger.info(f"Processing metrics for {len(unique_samples)} unique samples")
            
        # Define metric mappings
        metric_mappings = [
            ('Taxa Richness', 'taxa_richness', 'taxa_richness_score'),
            ('EPT Taxa Richness', 'ept_taxa_richness', 'ept_taxa_richness_score'),
            ('EPT Abundance', 'ept_abundance', 'ept_abundance_score'),
            ('HBI Score', 'hbi_score', 'hbi_score_score'),
            ('% Contribution Dominants', 'contribution_dominants', 'contribution_dominants_score'),
            ('Shannon-Weaver', 'shannon_weaver', 'shannon_weaver_score')
        ]
        
        # Check which metrics are available
        available_metrics = []
        for metric_name, raw_col, score_col in metric_mappings:
            if raw_col in unique_samples.columns and score_col in unique_samples.columns:
                available_metrics.append((metric_name, raw_col, score_col))
        
        # Track metrics for debugging
        metrics_by_event = {}
        
        # For each unique sample, insert metrics
        for _, row in unique_samples.iterrows():
            # Skip if missing required fields
            if 'site_name' not in row or 'sample_id' not in row:
                continue
                
            # Get the event_id
            cursor.execute('''
                SELECT e.event_id
                FROM macro_collection_events e
                JOIN sites s ON e.site_id = s.site_id
                WHERE s.site_name = ? AND e.sample_id = ?
            ''', (row['site_name'], row['sample_id']))
            
            event_result = cursor.fetchone()
            if not event_result:
                logger.warning(f"No event found for sample_id={row.get('sample_id')}, site={row.get('site_name')}")
                continue
                
            event_id = event_result[0]
            metrics_by_event[event_id] = set()
            
            # Insert metrics for this event
            for metric_name, raw_col, score_col in available_metrics:
                if pd.notna(row.get(raw_col)) and pd.notna(row.get(score_col)):
                    cursor.execute('''
                        INSERT INTO macro_metrics 
                        (event_id, metric_name, raw_value, metric_score)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        event_id,
                        metric_name,
                        row[raw_col],
                        row[score_col]
                    ))
                    metrics_by_event[event_id].add(metric_name)
        
        # Log summary
        logger.info(f"Processed metrics for {len(metrics_by_event)} events")
        total_metrics = sum(len(metrics) for metrics in metrics_by_event.values())
        logger.info(f"Inserted {total_metrics} total metrics")
        
    except Exception as e:
        logger.error(f"Error inserting reference and metrics data: {e}")
        raise

def calculate_summary_scores(cursor):
    """Calculate and insert summary scores into the database."""
    try:
        # Process data from CSV
        macro_df = process_macro_csv_data()
        
        if macro_df.empty:
            logger.warning("No macroinvertebrate data to calculate summary scores")
            return
            
        # Check for required columns
        required_cols = ['site_name', 'sample_id', 'total_score', 'comparison_to_reference']
        missing_cols = [col for col in required_cols if col not in macro_df.columns]
        
        if missing_cols:
            logger.error(f"Missing required columns for summary scores: {missing_cols}")
            return
            
        # For each collection event, insert summary scores
        for _, row in macro_df.iterrows():
            # Get the event_id
            cursor.execute('''
                SELECT e.event_id
                FROM macro_collection_events e
                JOIN sites s ON e.site_id = s.site_id
                WHERE s.site_name = ? AND e.sample_id = ?
            ''', (row['site_name'], row['sample_id']))
            
            event_result = cursor.fetchone()
            if not event_result:
                continue
                
            event_id = event_result[0]
            
            # Determine biological condition
            biological_condition = determine_biological_condition(row['comparison_to_reference'])
            
            # Insert summary score
            cursor.execute('''
                INSERT INTO macro_summary_scores
                (event_id, total_score, comparison_to_reference, biological_condition)
                VALUES (?, ?, ?, ?)
            ''', (
                event_id,
                row['total_score'],
                row['comparison_to_reference'],
                biological_condition
            ))
        
        logger.info("Calculated and inserted summary scores")
            
    except Exception as e:
        logger.error(f"Error calculating summary scores: {e}")
        raise

def get_macroinvertebrate_dataframe():
    """Query to get macroinvertebrate data with years and seasons"""
    conn = None
    try:
        conn = get_connection()
        macro_query = '''
        SELECT 
            m.event_id,
            s.site_name,
            e.year,
            e.season,
            m.total_score,
            m.comparison_to_reference,
            m.biological_condition
        FROM 
            macro_summary_scores m
        JOIN 
            macro_collection_events e ON m.event_id = e.event_id
        JOIN 
            sites s ON e.site_id = s.site_id
        ORDER BY 
            e.season, e.year
        '''
        macro_df = pd.read_sql_query(macro_query, conn)
        
        # Validation of the dataframe
        if macro_df.empty:
            logger.warning("No macroinvertebrate data found in the database")
        else: 
            logger.info(f"Retrieved {len(macro_df)} macroinvertebrate collection records")

            # Check for missing values
            missing_values = macro_df.isnull().sum().sum()
            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values in the macroinvertebrate data")
    
        return macro_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_macroinvertebrate_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving macroinvertebrate data: {e}")
        return pd.DataFrame({'error': ['Error retrieving macroinvertebrate data']})
    finally:
        if conn:
            close_connection(conn)

def get_macro_metrics_data_for_table():
    """Query the database to get detailed macroinvertebrate metrics data for the metrics table display"""
    conn = None
    try:
        conn = get_connection()
        
        # Query to get all metrics for each collection event
        metrics_query = '''
        SELECT 
            e.event_id,
            e.year,
            e.season,
            m.metric_name,
            m.raw_value,
            m.metric_score
        FROM 
            macro_metrics m
        JOIN 
            macro_collection_events e ON m.event_id = e.event_id
        ORDER BY 
            e.season, e.year, m.metric_name
        '''
        
        metrics_df = pd.read_sql_query(metrics_query, conn)
        
        # Query to get summary scores
        summary_query = '''
        SELECT 
            e.event_id,
            e.year,
            e.season,
            s.total_score,
            s.comparison_to_reference,
            s.biological_condition
        FROM 
            macro_summary_scores s
        JOIN 
            macro_collection_events e ON s.event_id = e.event_id
        ORDER BY 
            e.season, e.year
        '''
        
        summary_df = pd.read_sql_query(summary_query, conn)
        
        logger.debug(f"Retrieved macro metrics data for {len(metrics_df)} records and {summary_df.shape[0]} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving macroinvertebrate metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)
            
if __name__ == "__main__":
    macro_df = load_macroinvertebrate_data()
    if not macro_df.empty:
        logger.info("Macroinvertebrate data summary:")
        logger.info(f"Number of records: {len(macro_df)}")
    else:
        logger.error("No macroinvertebrate data loaded. Check database setup.")