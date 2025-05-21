import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import setup_logging, load_csv_data, clean_column_names

# Set up component-specific logging
logger = setup_logging("fish_processing")

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
        # Check if database structure is valid
        if not verify_database_structure():
            logger.error("Database structure verification failed. Please check the schema.")
            return pd.DataFrame()
        
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM fish_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Load fish data from CSV
            fish_df = process_fish_csv_data(site_name)
            
            if fish_df.empty:
                logger.warning(f"No fish data found for processing.")
                return pd.DataFrame()
                
            # Process sites and insert collection events
            insert_collection_events(cursor, fish_df)
            
            # Insert metrics and summary scores
            insert_metrics_data(cursor, fish_df)
            
            conn.commit()
            logger.info("Fish data loaded successfully")
        else:
            logger.info("Fish data already exists in the database")

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

    # If site_name was provided, return data only for that site
    if site_name:
        return get_fish_dataframe(site_name)
    else:
        return get_fish_dataframe()

def process_fish_csv_data(site_name=None):
    """
    Process fish data from CSV file.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with processed fish data
    """
    try:
        # Load raw fish data
        fish_df = load_csv_data('fish')
        
        if fish_df.empty:
            logger.error("Failed to load fish data from CSV.")
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
        
        # Handle date formatting
        if 'collection_date' in fish_df.columns:
            try:
                fish_df['collection_date'] = pd.to_datetime(fish_df['collection_date'])
                fish_df['collection_date_str'] = fish_df['collection_date'].dt.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Check for invalid data (-999 values)
        score_columns = [col for col in fish_df.columns if col.endswith('_score')]
        score_columns.append('comparison_to_reference')
        
        # Remove rows with -999 values in score columns
        invalid_mask = (fish_df[score_columns] == -999).any(axis=1)
        if invalid_mask.any():
            logger.warning(f"Removing {invalid_mask.sum()} rows with invalid scores (-999)")
            fish_df = fish_df[~invalid_mask]
        
        # Validate IBI scores (check if total_score matches sum of component scores)
        fish_df = validate_ibi_scores(fish_df)
        
        # Filter by site name if provided
        if site_name:
            if 'site_name' in fish_df.columns:
                site_filter = fish_df['site_name'].str.lower() == site_name.lower()
                filtered_df = fish_df[site_filter]
                
                if filtered_df.empty:
                    logger.warning(f"No fish data found for site: {site_name}")
                    return pd.DataFrame()
                
                logger.info(f"Filtered to {len(filtered_df)} fish records for site: {site_name}")
                return filtered_df
            else:
                logger.warning("No 'site_name' column found in data")
        
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

def insert_collection_events(cursor, fish_df):
    """
    Insert fish collection events into the database.
    
    Args:
        cursor: Database cursor
        fish_df: DataFrame with fish data
    
    Returns:
        dict: Dictionary mapping sample_ids to event_ids
    """
    try:
        event_id_map = {}  # Map sample_id to event_id for later use
        
        # Get unique collection events
        if 'site_name' not in fish_df.columns or 'sample_id' not in fish_df.columns:
            logger.error("Missing required columns site_name or sample_id")
            return event_id_map
            
        unique_events = fish_df.drop_duplicates(subset=['site_name', 'sample_id']).copy()
        
        for _, event in unique_events.iterrows():
            # Get or create site_id
            cursor.execute("SELECT site_id FROM sites WHERE site_name = ?", (event['site_name'],))
            site_result = cursor.fetchone()
            
            if site_result:
                site_id = site_result[0]
            else:
                # Insert minimal site data
                cursor.execute(
                    "INSERT INTO sites (site_name) VALUES (?)", 
                    (event['site_name'],)
                )
                site_id = cursor.lastrowid
            
            # Check if this sample is already in the database
            cursor.execute('''
                SELECT event_id FROM fish_collection_events 
                WHERE site_id = ? AND sample_id = ?
            ''', (site_id, event['sample_id']))
            
            result = cursor.fetchone()
            
            if result:
                # Sample already exists, store its event_id
                event_id_map[event['sample_id']] = result[0]
            else:
                # Insert new sample
                cursor.execute('''
                    INSERT INTO fish_collection_events 
                    (site_id, sample_id, collection_date, year)
                    VALUES (?, ?, ?, ?)
                ''', (
                    site_id, 
                    event['sample_id'], 
                    event.get('collection_date_str'), 
                    event.get('year')
                ))
                
                event_id = cursor.lastrowid
                event_id_map[event['sample_id']] = event_id
        
        logger.info(f"Processed {len(unique_events)} fish collection events")
        return event_id_map
        
    except Exception as e:
        logger.error(f"Error inserting collection events: {e}")
        return {}

def insert_metrics_data(cursor, fish_df):
    """
    Insert fish metrics and summary scores into the database.
    
    Args:
        cursor: Database cursor
        fish_df: DataFrame with fish data
    
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
            # Skip if no sample_id
            if pd.isna(sample_id):
                continue
                
            # Get site_id
            if 'site_name' not in sample_df.iloc[0]:
                continue
                
            site_name = sample_df.iloc[0]['site_name']
            
            # Get or create event_id
            cursor.execute('''
                SELECT e.event_id
                FROM fish_collection_events e
                JOIN sites s ON e.site_id = s.site_id
                WHERE s.site_name = ? AND e.sample_id = ?
            ''', (site_name, sample_id))
            
            event_result = cursor.fetchone()
            if not event_result:
                logger.warning(f"No event found for sample_id={sample_id}, site={site_name}")
                continue
                
            event_id = event_result[0]
            
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
            
            # Insert summary score
            if all(col in row for col in ['total_score', 'comparison_to_reference', 'integrity_class']):
                cursor.execute('''
                    INSERT INTO fish_summary_scores
                    (event_id, total_score, comparison_to_reference, integrity_class)
                    VALUES (?, ?, ?, ?)
                ''', (
                    event_id,
                    row['total_score'],
                    row['comparison_to_reference'],
                    row['integrity_class']
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

def verify_database_structure():
    """
    Verify that the database has the required tables and structure for fish data.
    
    Returns:
        bool: True if structure is valid, False otherwise
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = [
            'sites',
            'fish_collection_events',
            'fish_metrics',
            'fish_summary_scores'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone() is None:
                logger.error(f"Missing required table: {table}")
                return False
    
        logger.info("Fish database structure verified successfully")
        return True
    except Exception as e:
        logger.error(f"Error verifying database structure: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


if __name__ == "__main__":
    if verify_database_structure():
        fish_df = load_fish_data()
        logger.info("Fish data summary:")
        logger.info(f"Number of records: {len(fish_df)}")
        
        # Get list of sites
        sites = get_sites_with_fish_data()
        logger.info(f"Sites with fish data: {', '.join(sites)}")
    else:
        logger.error("Database verification failed. Please check the database structure.")