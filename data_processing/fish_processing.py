import logging
import pandas as pd
import sqlite3
import os
from datetime import datetime
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
        
        # Load fish data from CSV
        fish_df = process_fish_csv_data(site_name)
        
        if fish_df.empty:
            logger.warning(f"No fish data found for processing.")
            return pd.DataFrame()
            
        # Process sites from the data
        unique_sites = fish_df['site_name'].unique()
        logger.info(f"Found {len(unique_sites)} unique sites in the fish data.")
            
        unique_sites = fish_df[site_column].unique()
        logger.info(f"Found {len(unique_sites)} unique sites in the fish data.")
        
        # In load_fish_data:
        for site in unique_sites:
            site_df = fish_df[fish_df['site_name'] == site]
            # Pass site DataFrame to insert_site_data for additional site info
            site_id = insert_site_data(cursor, site, site_df)
            
            if site_id:
                # Get event IDs and map in one step
                count, event_map = insert_collection_events(cursor, site_id, site_df)
                insert_metrics_data(cursor, site_id, site_df, event_map)
            
        conn.commit()
        logger.info("Fish data loaded successfully")

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
        
        # ADDED: Log original column names for debugging
        logger.debug(f"Original fish data columns: {', '.join(fish_df.columns)}")
        
        # Verify required columns exist
        required_columns = [
            'SiteName', 'SAMPLEID', 'Date', 'Year',
            'Total.Species', 'Sensitive.Benthic', 'Sunfish.Species', 
            'Intolerant.Species', 'Percent.Tolerant', 'Percent.Insectivore', 
            'Percent.Lithophil', 'Total.Species.IBI', 'Sensitive.Benthic.IBI',
            'Sunfish.Species.IBI', 'Intolerant.Species.IBI', 'Percent.Tolerant.IBI',
            'Percent.Insectivore.IBI', 'Percent.Lithophil.IBI', 'OKIBI.Score',
            'Percent.Reference', 'Fish.Score'
        ]
        
        # CHANGE: Check for required columns case-insensitively
        missing_columns = []
        for req_col in required_columns:
            if not any(col.lower() == req_col.lower() for col in fish_df.columns):
                missing_columns.append(req_col)
                
        if missing_columns:
            logger.warning(f"Missing some columns in fish data: {', '.join(missing_columns)}")
            # Continue with available columns, but log the warning
        
        # Clean column names for consistency
        fish_df = clean_column_names(fish_df)
        
        # ADDED: Log cleaned column names for debugging
        logger.debug(f"Cleaned fish data columns: {', '.join(fish_df.columns)}")
        
        # Map to standardized column names if needed
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
                
                # Check if year from date matches year column
                fish_df['date_year'] = fish_df['collection_date'].dt.year
                year_mismatches = fish_df[fish_df['date_year'] != fish_df['year']]
                
                if not year_mismatches.empty:
                    logger.warning(f"Found {len(year_mismatches)} records where date year doesn't match year column.")
                    # Log some examples
                    for idx, row in year_mismatches.head(5).iterrows():
                        logger.warning(f"Year mismatch at sample {row.get('sample_id')}: Date={row.get('collection_date_str')} (year={row.get('date_year')}), Year column={row.get('year')}")
                
                # Use the year from date as our canonical year
                fish_df['year'] = fish_df['date_year']
                
            except Exception as e:
                logger.error(f"Error processing dates: {e}")
        
        # Check for invalid data
        invalid_columns = ['total_species_score', 'sensitive_benthic_score', 
                           'sunfish_species_score', 'intolerant_species_score',
                           'tolerant_score', 'insectivorous_score', 
                           'lithophilic_score']
        
        # Filter for invalid columns that exist in the DataFrame
        existing_invalid_cols = [col for col in invalid_columns if col in fish_df.columns]
        
        if existing_invalid_cols:
            invalid_rows = fish_df[fish_df[existing_invalid_cols].eq(-999).any(axis=1)]
            
            if not invalid_rows.empty:
                logger.warning(f"Found {len(invalid_rows)} rows with invalid scores (-999). These will be excluded.")
                fish_df = fish_df[~fish_df.index.isin(invalid_rows.index)]
        
        # Validate IBI scores
        fish_df = validate_ibi_scores(fish_df)
        
        # Filter by site name if provided
        if site_name:               
            site_filter = fish_df[site_column].str.lower() == site_name.lower()
            filtered_df = fish_df[site_filter]
            
            if filtered_df.empty:
                logger.warning(f"No fish data found for site: {site_name}")
                return pd.DataFrame()
            
            logger.info(f"Filtered to {len(filtered_df)} fish records for site: {site_name}")
            return filtered_df
        
        return fish_df
        
    except Exception as e:
        logger.error(f"Error processing fish CSV data: {e}")
        return pd.DataFrame()

def validate_ibi_scores(fish_df):
    """
    Validate that OKIBI.Score (total_score) equals the sum of IBI component scores.
    
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
                logger.warning(f"Found {len(mismatches)} records where OKIBI.Score doesn't match sum of components.")
                # Log some examples
                for idx, row in mismatches.head(5).iterrows():
                    logger.warning(f"Score mismatch at sample {row.get('sample_id')}: "
                                  f"OKIBI.Score={row.get('total_score')}, "
                                  f"Sum of components={row.get('calculated_score')}")
                
                # Flag records with mismatches
                df['score_validated'] = ~mismatch_mask
            else:
                logger.info("All OKIBI.Score values match sum of components.")
                df['score_validated'] = True
            
            # Drop the calculated column as we don't need it anymore
            df = df.drop(columns=['calculated_score'])
        
        return df
    
    except Exception as e:
        logger.error(f"Error validating IBI scores: {e}")
        return fish_df  # Return original dataframe if validation fails

def insert_site_data(cursor, site_name, site_df=None):
    """
    Check if site exists in database; if not, create it with minimal information.
    
    Args:
        cursor: Database cursor
        site_name: Name of the site
        site_df: Optional DataFrame with additional site info
    
    Returns:
        int: site_id of the inserted or existing site
    """
    try:
        # Check if site already exists
        cursor.execute('SELECT site_id FROM sites WHERE site_name = ?', (site_name,))
        site_result = cursor.fetchone()
        
        if site_result:
            logger.debug(f"Site already exists: {site_name}, site_id={site_result[0]}")
            return site_result[0]
        
        # Site doesn't exist - create minimal entry
        logger.warning(f"Site '{site_name}' not found in sites table. Creating minimal entry.")
        
        # Extract minimal site info if DataFrame provided
        lat = lon = county = river_basin = ecoregion = None
        
        if site_df is not None and not site_df.empty:
            # Get first row with most complete data
            site_info = site_df.iloc[0]
            
            # Only check columns we need for minimal site entry
            if 'latitude' in site_df.columns:
                lat = site_info['latitude']
            if 'longitude' in site_df.columns:
                lon = site_info['longitude']
        
        # Insert site data
        cursor.execute('''
            INSERT INTO sites (site_name, latitude, longitude, county, river_basin, ecoregion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (site_name, lat, lon, county, river_basin, ecoregion))
        
        site_id = cursor.lastrowid
        logger.info(f"Created minimal site entry: {site_name}, site_id={site_id}")
        return site_id
        
    except Exception as e:
        logger.error(f"Error inserting site data for {site_name}: {e}")
        return None

def insert_collection_events(cursor, site_id, site_df):
    """
    Insert fish collection events into the database.
    
    Args:
        cursor: Database cursor
        site_id: ID of the site
        site_df: DataFrame with fish data for this site
    
    Returns:
        tuple: (Number of collection events inserted, Dictionary mapping sample_ids to event_ids)
    """
    try:
        # Define required columns - sample_id is the primary identifier
        required_columns = ['sample_id']
        optional_columns = ['collection_date_str', 'year']
        
        # Ensure sample_id column exists
        if 'sample_id' not in site_df.columns:
            logger.error(f"Missing required column 'sample_id' for collection events")
            return 0, {}
            
        # Get unique samples by sample_id (the true unique identifier)
        available_columns = [col for col in required_columns + optional_columns if col in site_df.columns]
        samples = site_df.drop_duplicates(subset=['sample_id'])
        
        count = 0
        event_id_map = {}  # Map sample_id to event_id for later use
        
        for _, sample in samples.iterrows():
            sample_id = sample['sample_id']
                
            # Extract date and year if available
            collection_date = sample.get('collection_date_str')
            year = sample.get('year')
            
            # Ensure year is available (derive from date if needed)
            if year is None and collection_date is not None:
                try:
                    # Try to extract year from date
                    year = pd.to_datetime(collection_date).year
                    logger.debug(f"Derived year {year} from collection_date {collection_date}")
                except:
                    logger.warning(f"Could not derive year from collection_date {collection_date}")
                    
            # Check if this sample is already in the database
            cursor.execute('''
                SELECT event_id FROM fish_collection_events 
                WHERE site_id = ? AND sample_id = ?
            ''', (site_id, sample_id))
            
            result = cursor.fetchone()
            
            if result:
                # Sample already exists, store its event_id
                event_id_map[sample_id] = result[0]
                logger.debug(f"Sample already exists: site_id={site_id}, sample_id={sample_id}, event_id={result[0]}")
            else:
                # Insert new sample
                cursor.execute('''
                    INSERT INTO fish_collection_events (site_id, sample_id, collection_date, year)
                    VALUES (?, ?, ?, ?)
                ''', (site_id, sample_id, collection_date, year))
                
                event_id = cursor.lastrowid
                event_id_map[sample_id] = event_id
                count += 1
                logger.debug(f"Inserted new sample: site_id={site_id}, sample_id={sample_id}, event_id={event_id}")
        
        logger.info(f"Inserted {count} new collection events for site_id={site_id}")
        return count, event_id_map
        
    except Exception as e:
        logger.error(f"Error inserting collection events for site_id={site_id}: {e}")
        return 0, {}

def insert_metrics_data(cursor, site_id, site_df, event_map=None):
    """
    Insert fish metrics and summary scores into the database.
    
    Args:
        cursor: Database cursor
        site_id: ID of the site
        site_df: DataFrame with fish data for this site
        event_map: Optional dictionary mapping sample_ids to event_ids
    
    Returns:
        int: Number of metrics records inserted
    """
    try:
        # If event_map wasn't provided, query for it
        if event_map is None:
            cursor.execute('''
                SELECT event_id, sample_id FROM fish_collection_events 
                WHERE site_id = ?
            ''', (site_id,))
            
            event_map = {sample_id: event_id for event_id, sample_id in cursor.fetchall()}
        
        if not event_map:
            logger.warning(f"No collection events found for site_id={site_id}")
            return 0
        
        # Prepare metrics for insertion
        metrics_count = 0
        summary_count = 0
        
        for sample_id, events_df in site_df.groupby('sample_id'):
            if sample_id not in event_map:
                logger.warning(f"No event_id found for sample_id={sample_id}")
                continue
                
            event_id = event_map[sample_id]
            
            # There should be only one row per sample_id, but just in case
            sample_data = events_df.iloc[0]
            
            # Clear existing metrics for this event (to handle updates)
            cursor.execute('DELETE FROM fish_metrics WHERE event_id = ?', (event_id,))
            
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
            
            # Insert metrics data
            metrics_data = []
            for metric_name, raw_col, score_col in metric_mappings:
                # Check if columns exist in the DataFrame
                if raw_col in sample_data and score_col in sample_data:
                    raw_value = sample_data[raw_col]
                    metric_score = sample_data[score_col]
                    
                    # For proportion metrics, use raw value as result
                    metric_result = raw_value if metric_name.startswith('Proportion') else None
                    
                    metrics_data.append((event_id, metric_name, raw_value, metric_result, metric_score))
            
            if metrics_data:
                cursor.executemany('''
                    INSERT INTO fish_metrics (event_id, metric_name, raw_value, metric_result, metric_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', metrics_data)
                
                metrics_count += len(metrics_data)
            
            # Insert summary scores (clear existing first)
            cursor.execute('DELETE FROM fish_summary_scores WHERE event_id = ?', (event_id,))
            
            # Check if required columns exist
            if all(col in sample_data for col in ['total_score', 'comparison_to_reference', 'integrity_class']):
                cursor.execute('''
                    INSERT INTO fish_summary_scores (event_id, total_score, comparison_to_reference, integrity_class)
                    VALUES (?, ?, ?, ?)
                ''', (event_id, sample_data['total_score'], 
                      sample_data['comparison_to_reference'], 
                      sample_data['integrity_class']))
                
                summary_count += 1
            else:
                logger.warning(f"Missing required summary score columns for sample_id={sample_id}")
        
        logger.info(f"Inserted {metrics_count} metrics and {summary_count} summary records for site_id={site_id}")
        return metrics_count
        
    except Exception as e:
        logger.error(f"Error inserting metrics data for site_id={site_id}: {e}")
        return 0

def get_fish_metrics_data_for_table(site_name=None, year=None):
    """
    Query the database to get detailed fish metrics data for the metrics table display.
    
    Args:
        site_name: Optional site name to filter data for
        year: Optional year to filter data for
    
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
        
        # Add filters for site name and/or year if provided
        params = []
        where_clauses = []
        
        if site_name:
            where_clauses.append('s.site_name = ?')
            params.append(site_name)
            
        if year is not None:
            where_clauses.append('e.year = ?')
            params.append(year)
        
        # Add WHERE clause if any filters were specified
        if where_clauses:
            where_clause = ' WHERE ' + ' AND '.join(where_clauses)
            metrics_query += where_clause
            summary_query += where_clause
        
        # Add order by clause
        metrics_query += ' ORDER BY s.site_name, e.year, e.sample_id, m.metric_name'
        summary_query += ' ORDER BY s.site_name, e.year, e.sample_id'
        
        # Execute queries
        metrics_df = pd.read_sql_query(metrics_query, conn, params=params)
        summary_df = pd.read_sql_query(summary_query, conn, params=params)
        
        filter_desc = ""
        if site_name:
            filter_desc += f" for site '{site_name}'"
        if year is not None:
            filter_desc += f" from year {year}"
            
        logger.debug(f"Retrieved metrics data{filter_desc}: {len(metrics_df)} metric records and {summary_df.shape[0]} summary records")
        
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

def get_fish_years_for_site(site_name):
    """
    Get a list of years with fish data for a specific site.
    
    Args:
        site_name: Name of the site
    
    Returns:
        List of years sorted in ascending order
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT e.year
            FROM fish_collection_events e
            JOIN sites s ON e.site_id = s.site_id
            WHERE s.site_name = ?
            ORDER BY e.year
        ''', (site_name,))
        
        years = [row[0] for row in cursor.fetchall()]
        logger.debug(f"Found {len(years)} years with fish data for site: {site_name}")
        return years
        
    except Exception as e:
        logger.error(f"Error getting years with fish data for site {site_name}: {e}")
        return []
        
    finally:
        if conn:
            close_connection(conn)

def get_fish_metrics_by_site_year(site_name, year=None):
    """
    Get detailed fish metrics for a specific site and optionally a specific year.
    
    Args:
        site_name: Name of the site
        year: Optional year to filter for
    
    Returns:
        DataFrame with detailed metrics data
    """
    conn = None
    try:
        conn = get_connection()
        
        query = '''
            SELECT 
                s.site_name,
                e.year,
                e.sample_id,
                e.collection_date,
                m.metric_name,
                m.raw_value,
                m.metric_result,
                m.metric_score,
                f.total_score,
                f.comparison_to_reference,
                f.integrity_class
            FROM 
                fish_metrics m
            JOIN 
                fish_collection_events e ON m.event_id = e.event_id
            JOIN
                sites s ON e.site_id = s.site_id
            JOIN
                fish_summary_scores f ON e.event_id = f.event_id
            WHERE 
                s.site_name = ?
        '''
        
        params = [site_name]
        
        if year is not None:
            query += ' AND e.year = ?'
            params.append(year)
            
        query += ' ORDER BY e.year, e.collection_date, e.sample_id, m.metric_name'
        
        metrics_df = pd.read_sql_query(query, conn, params=params)
        
        if metrics_df.empty:
            logger.warning(f"No fish metrics found for site: {site_name}" + 
                          (f", year: {year}" if year else ""))
        else:
            logger.info(f"Retrieved {len(metrics_df)} fish metrics for site: {site_name}" + 
                       (f", year: {year}" if year else ""))
            
        return metrics_df
        
    except Exception as e:
        logger.error(f"Error retrieving fish metrics for site {site_name}: {e}")
        return pd.DataFrame()
        
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
        
        # Check if the fish_collection_events table has the sample_id column
        cursor.execute("PRAGMA table_info(fish_collection_events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'sample_id' not in columns:
            logger.warning("fish_collection_events table is missing sample_id column. Adding it now.")
            
            # Add the sample_id column
            try:
                cursor.execute("ALTER TABLE fish_collection_events ADD COLUMN sample_id INTEGER")
                conn.commit()
                logger.info("Added sample_id column to fish_collection_events table")
            except sqlite3.Error as e:
                logger.error(f"Error adding sample_id column: {e}")
                return False
        
        # Verify the sites table has the additional columns from the new schema
        cursor.execute("PRAGMA table_info(sites)")
        columns = [row[1] for row in cursor.fetchall()]
        
        expected_site_columns = ['site_id', 'site_name', 'latitude', 'longitude', 'county', 'river_basin', 'ecoregion']
        missing_columns = [col for col in expected_site_columns if col not in columns]
        
        if missing_columns:
            logger.warning(f"sites table is missing columns: {', '.join(missing_columns)}. Adding them now.")
            
            # Add missing columns to the sites table
            for col in missing_columns:
                try:
                    cursor.execute(f"ALTER TABLE sites ADD COLUMN {col} TEXT")
                    logger.info(f"Added {col} column to sites table")
                except sqlite3.Error as e:
                    logger.error(f"Error adding {col} column: {e}")
                    # Continue with other columns even if one fails
            
            conn.commit()
        
        logger.info("Database structure verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying database structure: {e}")
        return False
        
    finally:
        if conn:
            close_connection(conn)

def clean_fish_metrics(site_name=None):
    """
    Clean up invalid or duplicate fish metrics data in the database.
    
    Args:
        site_name: Optional site name to filter cleanup for
    
    Returns:
        int: Number of records cleaned
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start with finding duplicate sample_ids for the same site
        if site_name:
            cursor.execute('''
                SELECT e.site_id, e.sample_id, COUNT(*) as count
                FROM fish_collection_events e
                JOIN sites s ON e.site_id = s.site_id
                WHERE s.site_name = ?
                GROUP BY e.site_id, e.sample_id
                HAVING count > 1
            ''', (site_name,))
        else:
            cursor.execute('''
                SELECT site_id, sample_id, COUNT(*) as count
                FROM fish_collection_events
                GROUP BY site_id, sample_id
                HAVING count > 1
            ''')
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate sample IDs in fish_collection_events")
            
            # Clean up duplicates by keeping only the most recent entry
            for site_id, sample_id, count in duplicates:
                # Find the duplicate event_ids
                cursor.execute('''
                    SELECT event_id, collection_date
                    FROM fish_collection_events
                    WHERE site_id = ? AND sample_id = ?
                    ORDER BY year DESC, collection_date DESC
                ''', (site_id, sample_id))
                
                events = cursor.fetchall()
                # Keep the first one (most recent), delete the rest
                keep_event_id = events[0][0]
                
                for event_id, _ in events[1:]:
                    # Delete metrics and summary scores for this event
                    cursor.execute('DELETE FROM fish_metrics WHERE event_id = ?', (event_id,))
                    cursor.execute('DELETE FROM fish_summary_scores WHERE event_id = ?', (event_id,))
                    cursor.execute('DELETE FROM fish_collection_events WHERE event_id = ?', (event_id,))
                    logger.debug(f"Deleted duplicate event_id={event_id} for sample_id={sample_id}")
        
        # Look for metrics with null or invalid scores
        if site_name:
            cursor.execute('''
                SELECT m.event_id, m.metric_name
                FROM fish_metrics m
                JOIN fish_collection_events e ON m.event_id = e.event_id
                JOIN sites s ON e.site_id = s.site_id
                WHERE s.site_name = ? AND (m.metric_score IS NULL OR m.metric_score < 0)
            ''', (site_name,))
        else:
            cursor.execute('''
                SELECT event_id, metric_name
                FROM fish_metrics
                WHERE metric_score IS NULL OR metric_score < 0
            ''')
        
        invalid_metrics = cursor.fetchall()
        
        if invalid_metrics:
            logger.warning(f"Found {len(invalid_metrics)} fish metrics with invalid scores")
            
            # Delete the invalid metrics
            for event_id, metric_name in invalid_metrics:
                cursor.execute('''
                    DELETE FROM fish_metrics 
                    WHERE event_id = ? AND metric_name = ?
                ''', (event_id, metric_name))
                logger.debug(f"Deleted invalid metric {metric_name} for event_id={event_id}")
        
        # Commit all changes
        conn.commit()
        
        # Return total number of cleaned records
        total_cleaned = len(duplicates) + len(invalid_metrics)
        if total_cleaned > 0:
            logger.info(f"Cleaned {total_cleaned} fish data records")
        else:
            logger.info("No invalid fish data records found to clean")
            
        return total_cleaned
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning fish metrics: {e}")
        return 0
        
    finally:
        if conn:
            close_connection(conn)

if __name__ == "__main__":
    # Verify database before attempting to load data
    if verify_database_structure():
        # Clean any existing data to ensure consistency
        clean_fish_metrics()
        
        # Load all fish data
        fish_df = load_fish_data()
        logger.info("Fish data summary:")
        logger.info(f"Number of records: {len(fish_df)}")
        
        # Get list of sites
        sites = get_sites_with_fish_data()
        logger.info(f"Sites with fish data: {', '.join(sites)}")
        
        # Print sample data for verification
        if not fish_df.empty:
            logger.info("\nSample data:")
            site_sample = fish_df['site_name'].iloc[0]
            logger.info(f"Data for site: {site_sample}")
            
            # Get years for this site
            years = get_fish_years_for_site(site_sample)
            logger.info(f"Years with data: {', '.join(map(str, years))}")
            
            # Get metrics for the most recent year
            if years:
                recent_year = max(years)
                metrics = get_fish_metrics_by_site_year(site_sample, recent_year)
                logger.info(f"Most recent year ({recent_year}) has {len(metrics)} metric records")
    else:
        logger.error("Database verification failed. Please check the database structure.")