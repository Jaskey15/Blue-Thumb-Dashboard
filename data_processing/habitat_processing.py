import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from utils import setup_logging

# Set up component-specific logging
logger = setup_logging("habitat_processing", category="processing")

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
            insert_habitat_metrics(cursor, habitat_df, assessment_id_map)
            insert_habitat_summary_scores(cursor, habitat_df, assessment_id_map)
            
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
    if site_name:
        return get_habitat_dataframe(site_name)
    else:
        return get_habitat_dataframe()

def process_habitat_csv_data(site_name=None):
    """
    Process habitat data from CSV file.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with processed habitat data
    """
    try:
        # Load raw habitat data
        habitat_df = load_csv_data('habitat')
        
        if habitat_df.empty:
            logger.error("Failed to load habitat data from CSV.")
            return pd.DataFrame()
        
        # Clean column names for consistency
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
            'habitatscore': 'total_score',
            'habitatgrade': 'habitat_grade'
        }
        
        # Create a mapping with only columns that exist in the dataframe
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in habitat_df.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        habitat_df = habitat_df.rename(columns=valid_mapping)
        
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

def insert_habitat_metrics(cursor, habitat_df, assessment_id_map):
    """
    Insert habitat metrics data into the database.
    
    Args:
        cursor: Database cursor
        habitat_df: DataFrame with habitat data
        assessment_id_map: Dictionary mapping sample_ids to assessment_ids
    
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
            
        # Check for required sample_id column
        if 'sample_id' not in habitat_df.columns:
            logger.error("Missing required column 'sample_id'")
            return 0
            
        # Track metrics inserted
        metrics_inserted = 0
        
        # For each assessment, insert metrics
        for _, row in habitat_df.iterrows():
            # Get assessment_id using sample_id
            sample_id = row['sample_id']
            
            if sample_id not in assessment_id_map:
                continue
                
            assessment_id = assessment_id_map[sample_id]
                
            # Insert each available metric
            for metric_name in available_metrics:
                if pd.notna(row.get(metric_name)):
                    try:
                        # Format metric name for display
                        display_name = metric_name.replace('_', ' ').title()
                        
                        cursor.execute('''
                            INSERT INTO habitat_metrics 
                            (assessment_id, metric_name, score)
                            VALUES (?, ?, ?)
                        ''', (
                            assessment_id,
                            display_name,
                            float(row[metric_name])
                        ))
                        metrics_inserted += 1
                    except Exception as e:
                        logger.error(f"Error inserting metric {metric_name}: {e}")
        
        logger.info(f"Inserted {metrics_inserted} habitat metrics")
        return metrics_inserted
        
    except Exception as e:
        logger.error(f"Error inserting habitat metrics: {e}")
        return 0

def insert_habitat_summary_scores(cursor, habitat_df, assessment_id_map):
    """
    Insert habitat summary scores into the database.
    
    Args:
        cursor: Database cursor
        habitat_df: DataFrame with habitat data
        assessment_id_map: Dictionary mapping sample_ids to assessment_ids
    
    Returns:
        int: Number of summary records inserted
    """
    try:
        # Check if required columns exist
        required_columns = ['sample_id', 'total_score', 'habitat_grade']
        missing_columns = [col for col in required_columns if col not in habitat_df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {', '.join(missing_columns)}")
            return 0
            
        # Check for duplicate column names - this could be causing our issue
        duplicate_columns = habitat_df.columns[habitat_df.columns.duplicated()].tolist()
        if duplicate_columns:
            logger.warning(f"Duplicate column names detected: {duplicate_columns}")
            
            # Create a clean DataFrame with unique column names
            clean_df = habitat_df.copy()
            clean_df.columns = pd.Series(clean_df.columns).map(lambda x: f"{x}_{clean_df.columns.get_loc(x)}" if x in duplicate_columns else x)
            habitat_df = clean_df
            
        # Track summaries inserted
        summaries_inserted = 0
        
        # Process unique sample_ids to avoid duplicates
        unique_assessments = habitat_df.drop_duplicates(subset=['sample_id']).copy()
        
        # For each unique assessment, insert summary scores
        for idx, row in unique_assessments.iterrows():
            try:
                # Get assessment_id using sample_id
                sample_id = row['sample_id']
                
                if sample_id not in assessment_id_map:
                    logger.warning(f"Sample ID {sample_id} not found in assessment map")
                    continue
                    
                assessment_id = assessment_id_map[sample_id]
                
                # Handle the total_score regardless of whether it's a Series or scalar
                if isinstance(row['total_score'], pd.Series):
                    # If it's a Series, take the first value
                    logger.warning(f"total_score is a Series for sample_id {sample_id}, using first value")
                    # Get the first numeric value
                    total_score_values = [v for v in row['total_score'] if isinstance(v, (int, float)) or 
                                         (isinstance(v, str) and v.replace('.', '', 1).isdigit())]
                    if total_score_values:
                        total_score = float(total_score_values[0])
                    else:
                        # Fallback to the first value and try to convert it
                        try:
                            total_score = float(row['total_score'].iloc[0])
                        except:
                            logger.error(f"Could not convert any total_score values to float for sample_id {sample_id}")
                            continue
                else:
                    # If it's already a scalar value
                    try:
                        total_score = float(row['total_score'])
                    except:
                        logger.error(f"Could not convert total_score to float for sample_id {sample_id}")
                        continue
                
                # Get habitat grade
                if isinstance(row['habitat_grade'], pd.Series):
                    logger.warning(f"habitat_grade is a Series for sample_id {sample_id}, using first value")
                    habitat_grade = str(row['habitat_grade'].iloc[0])
                else:
                    habitat_grade = str(row['habitat_grade'])
                
                # Insert summary scores
                cursor.execute('''
                    INSERT INTO habitat_summary_scores
                    (assessment_id, total_score, habitat_grade)
                    VALUES (?, ?, ?)
                ''', (
                    assessment_id,
                    total_score,
                    habitat_grade
                ))
                
                summaries_inserted += 1
                
            except Exception as e:
                logger.error(f"Error processing row at index {idx} for sample_id {sample_id if 'sample_id' in row else 'unknown'}: {e}")
        
        logger.info(f"Inserted {summaries_inserted} habitat summary scores")
        return summaries_inserted
        
    except Exception as e:
        logger.error(f"Error inserting habitat summary scores: {e}")
        return 0

def get_habitat_dataframe(site_name=None):
    """
    Query to get habitat data with summary scores.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with habitat data
    """
    conn = None
    try:
        conn = get_connection()
        
        # Base query
        habitat_query = '''
        SELECT 
            a.assessment_id,
            s.site_name,
            a.assessment_date,
            a.year,
            h.total_score,
            h.habitat_grade
        FROM 
            habitat_summary_scores h
        JOIN 
            habitat_assessments a ON h.assessment_id = a.assessment_id
        JOIN 
            sites s ON a.site_id = s.site_id
        '''
        
        # Add filter for site if provided
        params = []
        if site_name:
            habitat_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Add ordering
        habitat_query += " ORDER BY a.year"
        
        # Execute query
        habitat_df = pd.read_sql_query(habitat_query, conn, params=params)
        
        # Validation of the dataframe
        if habitat_df.empty:
            if site_name:
                logger.warning(f"No habitat data found for site: {site_name}")
            else:
                logger.warning("No habitat data found in the database")
        else: 
            logger.info(f"Retrieved {len(habitat_df)} habitat assessment records")

            # Check for missing values
            missing_values = habitat_df.isnull().sum().sum()
            if missing_values > 0:
                logger.warning(f"Found {missing_values} missing values in the habitat data")
    
        return habitat_df
    except sqlite3.Error as e:
        logger.error(f"SQLite error in get_habitat_dataframe: {e}")
        return pd.DataFrame({'error': ['Database error occurred']})
    except Exception as e:
        logger.error(f"Error retrieving habitat data: {e}")
        return pd.DataFrame({'error': ['Error retrieving habitat data']})
    finally:
        if conn:
            close_connection(conn)

def get_habitat_metrics_data_for_table(site_name=None):
    """
    Query the database to get detailed habitat metrics data for the metrics table display.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with metrics data formatted for display
    """
    conn = None
    try:
        conn = get_connection()
        
        # Base query for metrics data
        metrics_query = '''
        SELECT 
            s.site_name,
            a.year,
            m.metric_name,
            m.score
        FROM 
            habitat_metrics m
        JOIN 
            habitat_assessments a ON m.assessment_id = a.assessment_id
        JOIN
            sites s ON a.site_id = s.site_id
        '''
        
        # Add site filter if needed
        params = []
        if site_name:
            metrics_query += " WHERE s.site_name = ?"
            params.append(site_name)
            
        # Add order by clause
        metrics_query += ' ORDER BY s.site_name, a.year, m.metric_name'
        
        # Execute query
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        
        # If metrics are found, pivot the data to create a table with years as columns
        if not metrics_df.empty:
            # Pivot the data
            pivot_df = metrics_df.pivot_table(
                index='metric_name',
                columns='year',
                values='score',
                aggfunc='first'
            )
            
            # Reset index to make metric_name a column
            pivot_df = pivot_df.reset_index()
            
            # Convert column names to strings
            pivot_df.columns = pivot_df.columns.astype(str)
            
            # Rename index column from 'metric_name' to 'Parameter'
            pivot_df = pivot_df.rename(columns={'metric_name': 'Parameter'})
            
            logger.info(f"Retrieved and pivoted habitat metrics data for {len(pivot_df)} metrics")
            return pivot_df
        else:
            logger.warning("No habitat metrics data found")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error retrieving habitat metrics data for table: {e}")
        return pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)

if __name__ == "__main__":
    habitat_df = load_habitat_data()
    if not habitat_df.empty:
        logger.info("Habitat data summary:")
        logger.info(f"Number of records: {len(habitat_df)}")
    else:
        logger.error("No habitat data loaded. Check database setup.")