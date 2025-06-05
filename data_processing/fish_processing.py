import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from data_processing.biological_utils import (
    insert_collection_events,
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from utils import setup_logging

logger = setup_logging("fish_processing", category="processing")

def load_fish_data(site_name=None):
    """
    Load fish data from CSV into the database.
    
    Args:
        site_name: Optional site name to filter data for (default: None, loads all sites)
    
    Returns:
        DataFrame with processed fish data
    """
    conn = get_connection()
    cursor = conn.cursor()
  
    try:
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM fish_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Load fish data from CSV
            fish_df = process_fish_csv_data(site_name)
            
            if fish_df.empty:
                logger.warning(f"No fish data found for processing.")
                return pd.DataFrame()
                
            # Insert collection events using shared utility
            event_id_map = insert_fish_collection_events(cursor, fish_df)
            
            # Insert metrics and summary scores
            insert_metrics_data(cursor, fish_df, event_id_map)
            
            conn.commit()
            logger.info("Fish data loaded successfully")
        else:
            logger.info("Fish data already exists in the database - skipping processing")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"SQLite error: {e}")
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading fish data: {e}")
        raise
    finally:
        close_connection(conn)

    # Always return current data state
    if site_name:
        return get_fish_dataframe(site_name)
    else:
        return get_fish_dataframe()

def process_fish_csv_data(site_name=None):
    """
    Process fish data from cleaned CSV file.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with processed fish data
    """
    try:
        # Load raw fish data from CLEANED CSV
        fish_df = load_csv_data('fish', parse_dates=['Date'])
        
        if fish_df.empty:
            logger.error("Failed to load fish data from cleaned CSV.")
            return pd.DataFrame()
        
        # Clean column names for consistency 
        fish_df = clean_column_names(fish_df)
        
        # Map to standardized column names
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
        
        # Create a mapping with only columns that exist in the dataframe
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in fish_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        fish_df = fish_df.rename(columns=valid_mapping)
        
        # Filter by site name if provided
        if site_name:
            fish_df = fish_df[fish_df['site_name'] == site_name]
            logger.info(f"Filtered to {len(fish_df)} rows for site: {site_name}")
        
        # Handle date formatting
        if 'collection_date' in fish_df.columns:
            try:
                fish_df['collection_date'] = pd.to_datetime(fish_df['collection_date'])
                fish_df['collection_date_str'] = fish_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Use shared biological utilities for data cleaning
        # Remove invalid values (-999, -99)
        fish_df = remove_invalid_biological_values(fish_df, invalid_values=[-999, -99])
        
        # Convert score columns to numeric
        fish_df = convert_columns_to_numeric(fish_df)
        
        # Validate IBI scores (check if total_score matches sum of component scores)
        fish_df = validate_ibi_scores(fish_df)
        
        save_processed_data(fish_df, 'fish_data')

        return fish_df
        
    except Exception as e:
        logger.error(f"Error processing fish CSV data: {e}")
        return pd.DataFrame()

def validate_ibi_scores(fish_df):
    """
    Validate that total_score equals the sum of IBI component scores.
    
    Args:
        fish_df: DataFrame with fish metrics data
    
    Returns:
        DataFrame with validated data
    """
    try:
        # Create a copy to avoid SettingWithCopyWarning
        df = fish_df.copy()
        
        # Calculate sum of component scores
        score_columns = ['total_species_score', 'sensitive_benthic_score', 
                         'sunfish_species_score', 'intolerant_species_score',
                         'tolerant_score', 'insectivorous_score', 
                         'lithophilic_score']
        
        # Check which columns exist
        existing_columns = [col for col in score_columns if col in df.columns]
        
        if len(existing_columns) < len(score_columns):
            missing = set(score_columns) - set(existing_columns)
            logger.warning(f"Missing some IBI component columns: {missing}")
        
        if existing_columns and 'total_score' in df.columns:
            df['calculated_score'] = df[existing_columns].sum(axis=1)
            
            # Find mismatches
            mismatch_mask = df['calculated_score'] != df['total_score']
            mismatches = df[mismatch_mask]
            
            if not mismatches.empty:
                logger.warning(f"Found {len(mismatches)} records where total_score doesn't match sum of components.")
                # Log some examples
                for idx, row in mismatches.head(5).iterrows():
                    logger.warning(f"Score mismatch at sample {row.get('sample_id')}: "
                                  f"total_score={row.get('total_score')}, "
                                  f"Sum of components={row.get('calculated_score')}")
                
                # Flag records with mismatches
                df['score_validated'] = ~mismatch_mask
            else:
                logger.info("All total_score values match sum of components.")
                df['score_validated'] = True
            
            # Drop the calculated column as we don't need it anymore
            df = df.drop(columns=['calculated_score'])
        
        return df
    
    except Exception as e:
        logger.error(f"Error validating IBI scores: {e}")
        return fish_df  # Return original dataframe if validation fails

def insert_fish_collection_events(cursor, fish_df):
    """
    Insert fish collection events using the shared biological utility.
    
    Args:
        cursor: Database cursor
        fish_df: DataFrame with fish data
    
    Returns:
        dict: Dictionary mapping sample_id to event_id
    """
    try:
        # Define parameters for fish collection events
        table_name = 'fish_collection_events'
        grouping_columns = ['site_name', 'sample_id']
        column_mapping = {
            'site_id': 'site_name',  # Will be looked up automatically
            'sample_id': 'sample_id',
            'collection_date': 'collection_date_str',
            'year': 'year'
        }
        
        # Use shared utility function
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
    Insert fish metrics and summary scores into the database.
    
    Args:
        cursor: Database cursor
        fish_df: DataFrame with fish data
        event_id_map: Dictionary mapping sample_id to event_id
    
    Returns:
        int: Number of metrics records inserted
    """
    try:
        # Define metric mappings
        metric_mappings = [
            ('Total No. of species', 'total_species', 'total_species_score'),
            ('No. of sensitive benthic species', 'sensitive_benthic_species', 'sensitive_benthic_score'),
            ('No. of sunfish species', 'sunfish_species', 'sunfish_species_score'),
            ('No. of intolerant species', 'intolerant_species', 'intolerant_species_score'),
            ('Proportion tolerant individuals', 'proportion_tolerant', 'tolerant_score'),
            ('Proportion insectivorous cyprinid', 'proportion_insectivorous', 'insectivorous_score'),
            ('Proportion lithophilic spawners', 'proportion_lithophilic', 'lithophilic_score')
        ]
        
        # Track counts
        metrics_count = 0
        summary_count = 0
        
        # Check which metrics are available
        available_metrics = []
        for metric_name, raw_col, score_col in metric_mappings:
            if raw_col in fish_df.columns and score_col in fish_df.columns:
                available_metrics.append((metric_name, raw_col, score_col))
        
        if not available_metrics:
            logger.error("No metric data available in CSV")
            return 0
            
        # For each unique sample, insert metrics and summary
        for sample_id, sample_df in fish_df.groupby('sample_id'):
            # Skip if no sample_id or not in event_id_map
            if pd.isna(sample_id) or sample_id not in event_id_map:
                if not pd.isna(sample_id):
                    logger.warning(f"No event_id found for sample_id={sample_id}")
                continue
                
            event_id = event_id_map[sample_id]
            
            # Clear existing data for this event (to handle updates)
            cursor.execute('DELETE FROM fish_metrics WHERE event_id = ?', (event_id,))
            cursor.execute('DELETE FROM fish_summary_scores WHERE event_id = ?', (event_id,))
            
            # Get the data (first row in case of duplicates)
            row = sample_df.iloc[0]
            
            # Insert metrics for this event
            for metric_name, raw_col, score_col in available_metrics:
                if pd.notna(row.get(raw_col)) and pd.notna(row.get(score_col)):
                    # For proportion metrics, use raw value as result
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
            
            # Determine integrity class - use CSV value first, calculate as fallback
            integrity_class = "Unknown"  # Default fallback

            # Primary: Use pre-calculated integrity_class from CSV
            if 'integrity_class' in row and pd.notna(row['integrity_class']) and str(row['integrity_class']).strip():
                integrity_class = str(row['integrity_class']).strip()
                logger.debug(f"Using pre-calculated integrity_class: {integrity_class} for sample_id={sample_id}")
            else:
                # Fallback: Calculate using simplified cutoffs
                if 'comparison_to_reference' in row and pd.notna(row['comparison_to_reference']):
                    comparison_value = float(row['comparison_to_reference']) * 100  # Convert to percentage
                    
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
                        
                    logger.info(f"Calculated integrity_class: {integrity_class} (score: {comparison_value}%) for sample_id={sample_id}")
                else:
                    logger.warning(f"Cannot determine integrity class for sample_id={sample_id} - missing both integrity_class and comparison_to_reference data")

            # Validate the integrity class value
            valid_classes = ["Excellent", "Good", "Fair", "Poor", "Very Poor"]
            if integrity_class not in valid_classes:
                logger.warning(f"Invalid integrity_class '{integrity_class}' for sample_id={sample_id}, setting to Unknown")
                integrity_class = "Unknown"

            # Insert summary score
            if all(col in row for col in ['total_score', 'comparison_to_reference']) and integrity_class != "Unknown":
                cursor.execute('''
                    INSERT INTO fish_summary_scores
                    (event_id, total_score, comparison_to_reference, integrity_class)
                    VALUES (?, ?, ?, ?)
                ''', (
                    event_id,
                    row['total_score'],
                    row['comparison_to_reference'],
                    integrity_class  # Use determined integrity_class (CSV first, calculated fallback)
                ))
                summary_count += 1
            else:
                logger.warning(f"Missing required columns for summary scores for sample_id={sample_id}")
        
        logger.info(f"Inserted {metrics_count} fish metrics and {summary_count} summary records")
        return metrics_count
        
    except Exception as e:
        logger.error(f"Error inserting metrics data: {e}")
        return 0

def get_fish_dataframe(site_name=None):
    """
    Query to get fish data with summary scores.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with fish data
    """
    conn = None
    try:
        conn = get_connection()
        
        # Base query
        fish_query = '''
        SELECT 
            e.event_id,
            s.site_name,
            e.year,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        JOIN 
            sites s ON e.site_id = s.site_id
        '''
        
        # Add filter for site if provided
        params = []
        if site_name:
            fish_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Add ordering
        fish_query += " ORDER BY e.year"
        
        # Execute query
        fish_df = pd.read_sql_query(fish_query, conn, params=params)
        
        # Validation of the dataframe
        if fish_df.empty:
            if site_name:
                logger.warning(f"No fish data found for site: {site_name}")
            else:
                logger.warning("No fish data found in the database")
        else: 
            logger.info(f"Retrieved {len(fish_df)} fish collection records")

            # Check for missing values
            missing_values = fish_df.isnull().sum().sum()
            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values in the fish data")
    
        return fish_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_fish_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving fish data: {e}")
        return pd.DataFrame({'error': ['Error retrieving fish data']})
    finally:
        if conn:
            close_connection(conn)

def get_fish_metrics_data_for_table(site_name=None):
    """
    Query the database to get detailed fish metrics data for the metrics table display.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        Tuple of (metrics_df, summary_df) for display
    """
    conn = None
    try:
        conn = get_connection()
        
        # Base query for metrics data
        metrics_query = '''
        SELECT 
            s.site_name,
            e.year,
            e.sample_id,
            m.metric_name,
            m.raw_value,
            m.metric_score
        FROM 
            fish_metrics m
        JOIN 
            fish_collection_events e ON m.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        # Base query for summary data
        summary_query = '''
        SELECT 
            s.site_name,
            e.year,
            e.sample_id,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        JOIN
            sites s ON e.site_id = s.site_id
        '''
        
        # Add filter for site name if provided
        params = []
        if site_name:
            where_clause = ' WHERE s.site_name = ?'
            metrics_query += where_clause
            summary_query += where_clause
            params.append(site_name)
        
        # Add order by clause
        metrics_query += ' ORDER BY s.site_name, e.year, m.metric_name'
        summary_query += ' ORDER BY s.site_name, e.year'
        
        # Execute queries
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        logger.debug(f"Retrieved fish metrics data: {len(metrics_df)} metric records and {summary_df.shape[0]} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving fish metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)

def get_sites_with_fish_data():
    """
    Get a list of sites that have fish data.
    
    Returns:
        List of site names
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT s.site_name
            FROM sites s
            JOIN fish_collection_events e ON s.site_id = e.site_id
            ORDER BY s.site_name
        ''')
        
        sites = [row[0] for row in cursor.fetchall()]
        logger.debug(f"Found {len(sites)} sites with fish data")
        return sites
        
    except Exception as e:
        logger.error(f"Error getting sites with fish data: {e}")
        return []
        
    finally:
        if conn:
            close_connection(conn)

if __name__ == "__main__":
    # Skip verification, just try to load and see what happens
    fish_df = load_fish_data()
    if not fish_df.empty:
        logger.info("Fish data summary:")
        logger.info(f"Number of records: {len(fish_df)}")
        sites = get_sites_with_fish_data()
        logger.info(f"Sites with fish data: {', '.join(sites)}")
    else:
        logger.error("No fish data loaded. Check database setup.")