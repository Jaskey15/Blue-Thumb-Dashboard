from database.database import get_connection, close_connection

def create_tables():
    """Create all database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create tables for fish collections
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sites (
        site_id INTEGER PRIMARY KEY,
        site_name TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_collection_events (
        event_id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        collection_date TEXT NOT NULL, -- Store in YYYY-MM-DD format
        year INTEGER NOT NULL,
        FOREIGN KEY (site_id) REFERENCES sites (site_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_reference_values (
        reference_id INTEGER PRIMARY KEY,
        region TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL,
        UNIQUE (region, metric_name)
    )
    ''')  

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_metrics (
        event_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        raw_value REAL NOT NULL,
        metric_result REAL,
        metric_score INTEGER CHECK (metric_score IN(1, 3, 5)),
        PRIMARY KEY (event_id, metric_name),
        FOREIGN KEY (event_id) REFERENCES fish_collection_events (event_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_summary_scores (
        event_id INTEGER NOT NULL,
        total_score INTEGER,
        comparison_to_reference REAL NOT NULL,
        integrity_class TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES fish_collection_events (event_id)
    )
    ''')    
    
    # Create tables for macroinvertebrates
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS macro_collection_events (
        event_id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        season TEXT CHECK (season IN ('Summer', 'Winter')),
        year INTEGER NOT NULL,
        habitat TEXT CHECK (habitat IN ('Riffle', 'Stream_veg', 'Wood')),
        FOREIGN KEY (site_id) REFERENCES sites (site_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS macro_reference_values (
        reference_id INTEGER PRIMARY KEY,
        region TEXT NOT NULL,
        season TEXT CHECK (season IN ('Summer', 'Winter')),
        habitat TEXT CHECK (habitat IN ('Riffle', 'Stream_veg', 'Wood')),
        metric_name TEXT NOT NULL,
        metric_value REAL, 
        UNIQUE (region, season, habitat, metric_name)
    )
    ''')  

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS macro_metrics (
        event_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        raw_value REAL NOT NULL,
        metric_result REAL,
        metric_score INTEGER CHECK (metric_score IN (0, 2, 4, 6)),
        PRIMARY KEY (event_id, metric_name),
        FOREIGN KEY (event_id) REFERENCES macro_collection_events (event_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS macro_summary_scores (
        event_id INTEGER NOT NULL,
        total_score INTEGER,
        comparison_to_reference REAL NOT NULL,
        biological_condition TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES macro_collection_events (event_id)
    )
    ''')    
    
    close_connection(conn)
    print("Database schema created successfully")

if __name__ == "__main__":
    create_tables()