import logging
import pandas as pd
import sqlite3
from database.database import get_connection, close_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tenmile_creek.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_fish_data():
    """Load fish data into the database."""
    conn = get_connection()
    cursor = conn.cursor()
  
    try:
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM fish_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            insert_site_data(cursor)
            insert_collection_events(cursor)
            insert_reference_and_metrics_data(cursor)
            update_metric_results(cursor)
            update_metric_scores(cursor)
            calculate_summary_scores(cursor)

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

    return get_fish_dataframe()

def insert_site_data(cursor):
    """Insert site data into the database."""
    try:
        # Check if site data already exists
        cursor.execute('SELECT COUNT(*) FROM sites WHERE site_name = ?',
                       ('Tenmile Creek: Davis',))
        site_exists = cursor.fetchone()[0] > 0
        
        if not site_exists:
            # Insert site
            cursor.execute('''
            INSERT INTO sites (site_name)
            VALUES ('Tenmile Creek: Davis')
            ''')
            logger.debug("Inserted site data")
        else:
            logger.debug("Site already exists, skipping insertion")
    except Exception as e:
        logger.error(f"Error inserting site data: {e}")
        raise

def insert_collection_events(cursor):
    """Insert fish collection events into the database."""
    try:
        # Define collection events data
        collection_events = [
            (1, '2012-06-27', 2012), 
            (1, '2016-08-22', 2016),
            (1, '2022-06-22', 2022) 
        ]
        cursor.executemany('''
        INSERT INTO fish_collection_events (site_id, collection_date, year)
        VALUES (?, ?, ?)
        ''', collection_events)
        logger.debug(f"Inserted {len(collection_events)} collection_events")

    except Exception as e:
        logger.error(f"Error inserting collection events: {e}")
        raise

def insert_reference_and_metrics_data(cursor):
    """Insert fish reference values and metrics data"""
    try:
        # Define fish metrics
        fish_metrics = ['Total No. of species', 'No. of sensitive benthic species', 
                    'No. of sunfish species', 'No. of intolerant species',
                    'Proportion tolerant individuals', 'Proportion insectivorous cyprinid',
                    'Proportion lithophilic spawners']

        # Fish reference data
        fish_reference_data = [('Ouachita Mountains', [15, 4, 4, 5, 0.49, 0.17, 0.35])]

        # Validate reference data
        for region, values in fish_reference_data:
            if len(values) != len(fish_metrics):
                raise ValueError(f"Mismatch between metrics and values for {region}")
            
            # Check for valid numeric values
            for val in values:
                if not isinstance(val, (int, float)):
                     raise ValueError(f"Non-numeric value in reference data: {val}")
        
        # Prepare reference data
        fish_ref_data = []
        reference_id = 1 # Starting ID for reference values
        for region, values in fish_reference_data:
            for i, metric in enumerate(fish_metrics):
                fish_ref_data.append((reference_id, region, metric, values[i]))
                reference_id += 1

        # Fish event data
        fish_event_data = [
            (1, [22, 1, 6, 1, 0.35, 0.45, 0.02]),  # 2012
            (2, [18, 5, 6, 3, 0.49, 0.01, 0.32]),   # 2016
            (3, [24, 7, 7, 5, 0.48, 0.25, 0.19]),   # 2022
        ]

        # Validate event data
        for event_id, values in fish_event_data:
            if len(values) != len(fish_metrics):
                raise ValueError(f"Mismatch between metrics and values for event {event_id}")
            
            # Check for valid numeric values
            for val in values:
                if not isinstance(val, (int, float)):
                     raise ValueError(f"Non-numeric value in event data: {val}")
                
        # Prepare metrics data
        fish_data = []
        for event_id, values in fish_event_data:
            for i, metric in enumerate(fish_metrics):
                fish_data.append((event_id, metric, values[i]))

        # Insert reference values
        cursor.executemany('''
        INSERT INTO fish_reference_values (reference_id, region, metric_name, metric_value)
        VALUES (?, ?, ?, ?)
        ''', fish_ref_data)
        logger.debug(f"Inserted {len(fish_ref_data)} reference values")

        # Insert metrics
        cursor.executemany('''
        INSERT INTO fish_metrics (event_id, metric_name, raw_value)
        VALUES (?, ?, ?)
        ''', fish_data)
        logger.debug(f"Inserted {len(fish_data)} metrics")

    except Exception as e:
        logger.error(f"Error inserting reference and metrics data: {e}")
        raise

def update_metric_results(cursor):
    """Update metric results based on reference values"""
    try:   
        # Update fish_metrics table with non-proportion metrics by dividing reference values
        cursor.execute('''
        UPDATE fish_metrics
        SET metric_result = (
            SELECT fish_metrics.raw_value / fish_reference_values.metric_value
            FROM fish_reference_values
            WHERE fish_metrics.metric_name = fish_reference_values.metric_name
            AND fish_reference_values.region = 'Ouachita Mountains'
        )
        WHERE metric_name NOT IN (
            'Proportion tolerant individuals',
            'Proportion insectivorous cyprinid',
            'Proportion lithophilic spawners'
        )
        ''')
        logger.debug("Updated metric results for non-proportion metrics")

        # Set proportion metrics to have same value for metric_result as raw_value
        cursor.execute('''
        UPDATE fish_metrics
        SET metric_result = raw_value
        WHERE metric_name IN (
            'Proportion tolerant individuals',
            'Proportion insectivorous cyprinid',
            'Proportion lithophilic spawners'
        )
        ''')
        logger.debug("Updated metric results for proportion metrics")

        # Verify all metrics have results
        cursor.execute("SELECT COUNT(*) FROM fish_metrics WHERE metric_result IS NULL")
        missing_results = cursor.fetchone()[0]
        if missing_results > 0:
            logger.warning(f"{missing_results} metrics are missing results")
    except Exception as e:
        logger.error(f"Error updating metric results: {e}")
        raise

def update_metric_scores(cursor):
    """Update metric scores based on IBI scoring criteria"""
    try:
        # Update scores for count metrics
        cursor.execute('''
        UPDATE fish_metrics
        SET metric_score = CASE
            WHEN metric_result > 0.67 THEN 5
            WHEN metric_result >= 0.33 THEN 3
            ELSE 1
        END
        WHERE metric_name IN (
            'Total No. of species',
            'No. of sensitive benthic species',
            'No. of sunfish species',
            'No. of intolerant species'
        )
        ''')

        # Update score for tolerant individuals (inverse relationship)
        cursor.execute('''
        UPDATE fish_metrics
        SET metric_score = CASE
            WHEN metric_result < 0.10 THEN 5
            WHEN metric_result <= 0.25 THEN 3
            ELSE 1
        END
        WHERE metric_name = 'Proportion tolerant individuals'
        ''')
        
        # Update score for insectivorous cyprinid
        cursor.execute('''
        UPDATE fish_metrics
        SET metric_score = CASE
            WHEN metric_result > 0.45 THEN 5
            WHEN metric_result >= 0.20 THEN 3
            ELSE 1
        END
        WHERE metric_name = 'Proportion insectivorous cyprinid'
        ''')
        # Update score for lithophilic spawners
        cursor.execute('''
        UPDATE fish_metrics
        SET metric_score = CASE
            WHEN metric_result > 0.36 THEN 5
            WHEN metric_result >= 0.18 THEN 3
            ELSE 1
        END
        WHERE metric_name = 'Proportion lithophilic spawners'
        ''')
        logger.debug("Updated metric scores")
    except Exception as e:
        logger.error(f"Error updating metric scores: {e}")
        raise

def calculate_summary_scores(cursor):
    """Calculate and insert summary scores into the database."""
    try:
        # Verify all metrics have scores
        cursor.execute("SELECT COUNT(*) FROM fish_metrics WHERE metric_score IS NULL")
        missing_scores = cursor.fetchone()[0]
        if missing_scores > 0:
            logger.warning(f"{missing_scores} metrics are missing scores")


        # Calculate and insert summary scores
        cursor.execute('''
        INSERT INTO fish_summary_scores (event_id, total_score, comparison_to_reference, integrity_class)
        SELECT 
            event_id,
            SUM(metric_score) AS total_score,
            SUM(metric_score) / 25.0 AS comparison_to_reference,  -- 25.0 is Ouachita Mountains reference score
            CASE
                WHEN SUM(metric_score) / 25.0 > 0.97 THEN 'Excellent'
                WHEN SUM(metric_score) / 25.0 >= 0.8 THEN 'Good'
                WHEN SUM(metric_score) / 25.0 >= 0.67 THEN 'Fair'
                WHEN SUM(metric_score) / 25.0 >= 0.47 THEN 'Poor'
                ELSE 'Very Poor'
            END AS integrity_class
        FROM fish_metrics
        GROUP BY event_id
        ''')
        logger.debug("Calculated and inserted summary scores")
    except Exception as e:
        logger.error(f"Error calculating summary scores: {e}")
        raise

def get_fish_dataframe():   
    """Query the database and return a dataframe with fish data"""
    conn = None 
    try:
        conn = get_connection()
        fish_query = '''
        SELECT 
            f.event_id,
            e.collection_date,
            e.year,
            f.total_score,
            f.comparison_to_reference,
            f.integrity_class
        FROM 
            fish_summary_scores f
        JOIN 
            fish_collection_events e ON f.event_id = e.event_id
        ORDER BY 
            e.year
        '''
        fish_df = pd.read_sql_query(fish_query, conn)

        # Validation of the dataframe
        if fish_df.empty:
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

def get_fish_metrics_data_for_table():
    """Query the database to get detailed fish metrics data for the metrics table display"""
    conn = None
    try:
        conn = get_connection()
        
        # Query to get all metrics for each collection event
        metrics_query = '''
        SELECT 
            e.year,
            m.metric_name,
            m.raw_value,
            m.metric_score
        FROM 
            fish_metrics m
        JOIN 
            fish_collection_events e ON m.event_id = e.event_id
        ORDER BY 
            e.year, m.metric_name
        '''
        
        metrics_df = pd.read_sql_query(metrics_query, conn)
        
        # Query to get summary scores
        summary_query = '''
        SELECT 
            e.year,
            s.total_score,
            s.comparison_to_reference,
            s.integrity_class
        FROM 
            fish_summary_scores s
        JOIN 
            fish_collection_events e ON s.event_id = e.event_id
        ORDER BY 
            e.year
        '''
        
        summary_df = pd.read_sql_query(summary_query, conn)
        
        logger.debug(f"Retrieved metrics data for {len(metrics_df)} records and {summary_df.shape[0]} summary records")
        
        return metrics_df, summary_df
    
    except Exception as e:
        logger.error(f"Error retrieving fish metrics data for table: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    finally:
        if conn:
            close_connection(conn)

def verify_database_structure():
    """Verify that the database has the required tables and structure."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = [
            'sites',
            'fish_collection_events',
            'fish_reference_values',
            'fish_metrics',
            'fish_summary_scores'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone() is None:
                logger.error(f"Missing required table: {table}")
                return False
        
        logger.info("Database structure verified successfully")
        return True
    except Exception as e:
        logger.error(f"Error verifying database structure: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)

if __name__ == "__main__":
    # Verify database before attempting to load data
    if verify_database_structure():
        fish_df = load_fish_data()
        logger.info("Fish data summary:")
        logger.info(f"Number of records: {len(fish_df)}")
    else:
        logger.error("Database verification failed. Please check the database structure.")