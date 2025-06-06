import pandas as pd
import sqlite3
from database.database import get_connection, close_connection
from data_processing.data_loader import load_csv_data, clean_column_names, save_processed_data
from utils import setup_logging

# Set up component-specific logging
logger = setup_logging("habitat_processing", category="processing")

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
            logger.info("No habitat duplicate groups found")
            return habitat_df
        
        logger.info(f"Found {len(duplicate_groups)} habitat duplicate groups to resolve")
        
        # Process each duplicate group
        averaged_records = []
        
        for site_name, date_str, group in duplicate_groups:
            # Convert date for logging (handle both string and datetime)
            if isinstance(date_str, str):
                date_for_logging = date_str
            else:
                date_for_logging = date_str.strftime('%Y-%m-%d') if pd.notna(date_str) else 'Unknown'
                
            logger.info(f"Averaging {len(group)} records for {site_name} on {date_for_logging}")
            
            # Calculate averages for specified columns
            averaged_record = group.iloc[0].copy()  # Start with first record as template
            
            # Track original values for logging
            original_total_scores = []
            
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
                    original_total_scores = total_values.tolist()
                else:
                    averaged_record['total_score'] = None
            
            # Calculate new habitat grade based on averaged total score (1-100 scale)
            if pd.notna(averaged_record['total_score']):
                averaged_record['habitat_grade'] = calculate_habitat_grade(averaged_record['total_score'])
            else:
                averaged_record['habitat_grade'] = "Unknown"
            
            # Log the averaging details
            if original_total_scores:
                original_scores_str = ', '.join([f"{score:.1f}" for score in original_total_scores])
                logger.info(f"  {site_name} ({date_for_logging}): Total scores [{original_scores_str}] → "
                           f"{averaged_record['total_score']} (Grade: {averaged_record['habitat_grade']})")
            
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
        
        # Log summary
        original_count = len(habitat_df)
        final_count = len(result_df)
        duplicates_resolved = original_count - final_count
        
        logger.info(f"Habitat duplicate resolution complete:")
        logger.info(f"  - Original records: {original_count}")
        logger.info(f"  - Final records: {final_count}")
        logger.info(f"  - Duplicates resolved: {duplicates_resolved}")
        
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
    
    if total_score > 90:
        return "A"
    elif total_score >= 80:
        return "B"
    elif total_score >= 70:
        return "C"
    elif total_score >= 60:
        return "D"
    else:
        return "F"

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
        
        # RESOLVE DUPLICATES - NEW STEP
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