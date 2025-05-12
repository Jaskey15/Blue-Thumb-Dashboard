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

def load_macroinvertebrate_data():
    """Load macroinvertebrate data into the database."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if data already exists
        cursor.execute('Select COUNT(*) FROM macro_summary_scores')
        data_exists = cursor.fetchone()[0] > 0

        if not data_exists:
            # Insert data
            insert_collection_events(cursor)
            insert_reference_and_metrics_data(cursor)
            update_metric_results(cursor)
            update_metric_scores(cursor)
            calculate_summary_scores(cursor)

            conn.commit()   
            logger.info("Macroinvertebrate data loaded successfully")
        else:
            logger.info("Macroinvertebrate data already exists in the database")

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

    return get_macroinvertebrate_dataframe()

def insert_collection_events(cursor):
    """Insert macroinvertebrate collection events into the database."""
    try:
        # Define collection events data
        collection_events = [
            (1, 'Winter', 2014, 'Riffle'), 
            (1, 'Winter', 2017, 'Riffle'),
            (1, 'Winter', 2018, 'Riffle'),
            (1, 'Winter', 2020, 'Riffle'),
            (1, 'Winter', 2021, 'Riffle'),
            (1, 'Winter', 2022, 'Riffle'),
            (1, 'Summer', 2013, 'Riffle'),
            (1, 'Summer', 2014, 'Riffle'),
            (1, 'Summer', 2019, 'Riffle'),
            (1, 'Summer', 2020, 'Riffle'),
            (1, 'Summer', 2021, 'Riffle'),
            (1, 'Summer', 2022, 'Riffle')
        ]

        cursor.executemany('''
        INSERT INTO macro_collection_events (site_id, season, year, habitat)
        VALUES (?, ?, ?, ?)
        ''', collection_events)

        logger.debug(f"Inserted {len(collection_events)} macroinvertebrate collection events")
    except Exception as e:
        logger.error(f"Error inserting collection events: {e}")
        raise

def insert_reference_and_metrics_data(cursor):
    """Insert macroinvertebrate reference values and metrics data"""
    try:
        # Define macroinvertebrate metrics
        macro_metrics = ['Taxa Richness', 'EPT Taxa Richness', 'EPT Abundance',
                    'HBI Score', '% Contribution Dominants', 'Shannon-Weaver']

        # Macroinvertebrates reference data
        macro_reference_data = [
            ("Ouachita Mountains", "Winter", "Riffle", [21.34, 11.2, 0.45, 5.03, 0.40, 2.49]),
            ("Ouachita Mountains", "Summer", "Riffle", [21.96, 9.9, 0.61, 4.68, 0.37, 2.51])
        ]

        # Validate reference data
        for region, season, habitat, values in macro_reference_data:
            if len(values) != len(macro_metrics):
                raise ValueError(f"Mismatch between metrics and values for {region}, {season}")
            
            for val in values:
                if not isinstance(val, (int, float)):
                    raise ValueError(f"Non-numeric value in reference data: {val}")
                
        # Prepare reference data
        macro_ref_data = []
        reference_id = 1 # Starting ID for reference values
        for region, season, habitat, values in macro_reference_data:
            for i, metric in enumerate(macro_metrics):
                macro_ref_data.append((reference_id, region, season, habitat, metric, values[i]))
                reference_id += 1

        # Macroinvertebrate event data 
        macro_event_data = [
            # Winter collections
            (1, [12, 4, 0.13, 5.52, 0.79, 1.18]),  # 2014
            (2, [8, 2, 0.06, 5.80, 0.85, 1.03]),   # 2017
            (3, [17, 4, 0.25, 5.70, 0.52, 2.20]),   # 2018
            (4, [15, 7, 0.44, 4.57, 0.56, 2.04]),   # 2020
            (5, [19, 6, 0.19, 5.39, 0.49, 2.33]),   # 2021
            (6, [16, 7, 0.20, 5.61, 0.64, 1.75]),   # 2022

            # Summer collections
            (7, [18, 5, 0.07, 5.75, 0.48, 2.24]),   # 2013
            (8, [12, 2, 0.02, 5.50, 0.67, 1.66]),   # 2014
            (9, [18, 5, 0.09, 5.70, 0.38, 2.23]),   # 2019
            (10, [17, 7, 0.16, 5.10, 0.49, 2.19]),   # 2020
            (11, [18, 6, 0.23, 4.92, 0.45, 2.25]),   # 2021
            (12, [20, 8, 0.31, 5.06, 0.29, 2.68])   # 2022
        ]

        # Validate metric data
        for event_id, values in macro_event_data:
            if len(values) != len(macro_metrics):
                raise ValueError(f"Mismatch between metrics and values for event {event_id}")
            
            for val in values:
                if not isinstance(val, (int, float)):
                    raise ValueError(f"Non-numeric value in event data: {val}")
            
        # Prepare metrics data
        macro_data = []
        for event_id, values in macro_event_data:
            for i, metric in enumerate(macro_metrics):
                macro_data.append((event_id, metric, values[i]))

        # Insert into reference values
        cursor.executemany('''
        INSERT INTO macro_reference_values (reference_id, region, season, habitat, metric_name, metric_value)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', macro_ref_data)
        logger.debug(f"Inserted {len(macro_ref_data)} reference values")

        # Insert metrics
        cursor.executemany('''
        INSERT INTO macro_metrics (event_id, metric_name, raw_value)
        VALUES (?, ?, ?)
        ''', macro_data)
        logger.debug(f"Inserted {len(macro_data)} metrics")
    except Exception as e:
        logger.error(f"Error inserting reference and metrics data: {e}")
        raise

def update_metric_results(cursor):
    """Update metric results based on reference values"""
    try:   
        # Update macro_metrics table with non-proportion metrics by dividing reference values
        cursor.execute('''
        UPDATE macro_metrics
        SET metric_result = (
            SELECT macro_metrics.raw_value / macro_reference_values.metric_value
            FROM macro_reference_values
            JOIN macro_collection_events ON macro_collection_events.event_id = macro_metrics.event_id
            WHERE macro_metrics.metric_name = macro_reference_values.metric_name
            AND macro_collection_events.season = macro_reference_values.season
            AND macro_reference_values.region = 'Ouachita Mountains'
            AND macro_reference_values.habitat = 'Riffle'
        )
        WHERE metric_name IN (
            'Taxa Richness', 
            'EPT Taxa Richness'
        );
        ''')
        logger.debug("Updated metric results for Taxa Richeness and EPT Taxa Richness")

        # Special case for HBI Score - invert the ratio (reference/raw)
        cursor.execute('''
        UPDATE macro_metrics
        SET metric_result = (
            SELECT macro_reference_values.metric_value / macro_metrics.raw_value
            FROM macro_reference_values
            JOIN macro_collection_events ON macro_collection_events.event_id = macro_metrics.event_id
            WHERE macro_metrics.metric_name = macro_reference_values.metric_name
            AND macro_collection_events.season = macro_reference_values.season
            AND macro_reference_values.region = 'Ouachita Mountains'
            AND macro_reference_values.habitat = 'Riffle'
        )
        WHERE metric_name = 'HBI Score';
        ''')
        logger.debug("Updated metric results for HBI Score")

        # Set proportion metrics to have same value for metric_result as raw_value
        cursor.execute('''
        UPDATE macro_metrics
        SET metric_result = raw_value
        WHERE metric_name IN (
            'EPT Abundance',
            '% Contribution Dominants',
            'Shannon-Weaver'
        )
        ''')
        logger.debug("Updated metric results for proportion metrics")

        # Verify all metrics have results
        cursor.execute("SELECT COUNT(*) FROM macro_metrics WHERE metric_result IS NULL")
        missing_results = cursor.fetchone()[0]
        if missing_results > 0:
            logger.warning(f"{missing_results} metrics are missing results")
    except Exception as e:
        logger.error(f"Error updating metric results: {e}")
        raise

def update_metric_scores(cursor):
    """Update metric scores based on bioassessment scoring criteria"""
    try:
        scoring_queries = [
            ('''
            UPDATE macro_metrics
            SET metric_score = CASE
                WHEN metric_result > 0.80 THEN 6
                WHEN metric_result >= 0.60 THEN 4
                WHEN metric_result >= 0.40 THEN 2
                ELSE 0
            END
            WHERE metric_name = 'Taxa Richness';
            ''', 'Taxa Richness'),

            ('''
            UPDATE macro_metrics
            SET metric_score = CASE
                WHEN metric_result > 0.85 THEN 6
                WHEN metric_result >= 0.70 THEN 4
                WHEN metric_result >= 0.50 THEN 2
                ELSE 0
            END
            WHERE metric_name = 'HBI Score';
            ''', 'HBI Score'),

            ('''
            UPDATE macro_metrics
            SET metric_score = CASE
                WHEN raw_value > 0.30 THEN 6
                WHEN raw_value > 0.20 THEN 4
                WHEN raw_value >= 0.10 THEN 2
                ELSE 0
            END
            WHERE metric_name = 'EPT Abundance';
            ''', 'EPT Abundance'),

            ('''
            UPDATE macro_metrics
            SET metric_score = CASE
                WHEN metric_result > 0.90 THEN 6
                WHEN metric_result >= 0.80 THEN 4
                WHEN metric_result >= 0.70 THEN 2
                ELSE 0
            END
            WHERE metric_name = 'EPT Taxa Richness';
            ''', 'EPT Taxa Richness'),

            ('''
            UPDATE macro_metrics
            SET metric_score = CASE
                WHEN raw_value < 0.60 THEN 6
                WHEN raw_value <= 0.70 THEN 4
                WHEN raw_value <= 0.80 THEN 2
                ELSE 0
            END
            WHERE metric_name = '% Contribution Dominants';
            ''', '% Contribution Dominants'),

           ('''
            UPDATE macro_metrics
            SET metric_score = CASE
                WHEN raw_value > 3.5 THEN 6
                WHEN raw_value >= 2.5 THEN 4
                WHEN raw_value >= 1.5 THEN 2
                ELSE 0
            END
            WHERE metric_name = 'Shannon-Weaver';
            ''', 'Shannon-Weaver')
        ]

        for query, metric_name in scoring_queries:
            cursor.execute(query)
            logger.debug(f"Updated metric scores for {metric_name}")

        # Verify all metrics have scores
        cursor.execute("SELECT COUNT(*) FROM macro_metrics WHERE metric_score IS NULL")
        missing_scores = cursor.fetchone()[0]
        if missing_scores > 0:
            logger.warning(f"{missing_scores} metrics are missing scores")
    except Exception as e:
        logger.error(f"Error updating metric scores: {e}")
        raise

def calculate_summary_scores(cursor):
    """Calculate and insert summary scores into the database."""
    try:
        cursor.execute('''
        WITH scores AS (
            SELECT 
                m.event_id,
                SUM(m.metric_score) AS total_score,
                CASE
                    WHEN e.season = 'Winter' THEN SUM(m.metric_score) / 32.0 -- Winter reference score
                    WHEN e.season = 'Summer' THEN SUM(m.metric_score) / 34.0 -- Summer reference score
                END AS comparison_to_reference
            FROM macro_metrics m
            JOIN macro_collection_events e ON m.event_id = e.event_id
            GROUP BY m.event_id, e.season
        )
        INSERT INTO macro_summary_scores (event_id, total_score, comparison_to_reference, biological_condition)
        SELECT 
            event_id,
            total_score,
            comparison_to_reference,
            CASE
                WHEN comparison_to_reference > 0.83 THEN 'Non-impaired'
                WHEN comparison_to_reference >= 0.54 THEN 'Slightly Impaired'
                WHEN comparison_to_reference >= 0.17 THEN 'Moderately Impaired'
                ELSE 'Severely Impaired'
            END AS biological_condition
        FROM scores;
        ''')
        logger.debug("Calculated and inserted summary scores")

        # Verify summary scores were created for all events
        cursor.execute('''
        SELECT COUNT(*) FROM macro_collection_events e
        LEFT JOIN macro_summary_scores s ON e.event_id = s.event_id
        WHERE s.event_id IS NULL
        ''')
        missing_summaries = cursor.fetchone()[0]
        if missing_summaries > 0:
            logger.warning(f"{missing_summaries} collection events are missing summary scores")
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
            s.event_id,
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
            
def verify_macro_database_structure():
    """Verify that the database has the required tables and structure for macroinvertebrate data."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check for required tables
        required_tables = [
            'sites',
            'macro_collection_events',
            'macro_reference_values',
            'macro_metrics',
            'macro_summary_scores'
        ]

        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone() is None:
                logger.error(f"Missing required table: {table}")
                return False
    
        logger.info("Macroinvertebrate database structure verified successfully")
        return True
    except Exception as e:
        logger.error(f"Error verifying macroinvertebrate database structure: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


if __name__ == "__main__":
    if verify_macro_database_structure():
        macro_df = load_macroinvertebrate_data()
        logger.info("Macroinvertebrate data summary:")
        logger.info(f"Number of records: {len(macro_df)}")
    else:
        logger.error("Database verification failed. Please check the database structure.")