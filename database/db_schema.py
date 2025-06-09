from database.database import get_connection, close_connection

def create_tables():
    """Create all database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Sites table - common to all data types
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sites (
        site_id INTEGER PRIMARY KEY,
        site_name TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        county TEXT,
        river_basin TEXT,
        ecoregion TEXT,
        active BOOLEAN DEFAULT 1,
        last_chemical_reading_date TEXT,
        UNIQUE(site_name)
    )
    ''')

    # ---------- CHEMICAL DATA TABLES ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chemical_collection_events (
        event_id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        sample_id INTEGER,
        collection_date TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        FOREIGN KEY (site_id) REFERENCES sites (site_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chemical_parameters (
        parameter_id INTEGER PRIMARY KEY,
        parameter_name TEXT NOT NULL,
        parameter_code TEXT NOT NULL,
        display_name TEXT NOT NULL,
        description TEXT,
        unit TEXT,
        UNIQUE(parameter_code)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chemical_reference_values (
        reference_id INTEGER PRIMARY KEY,
        parameter_id INTEGER NOT NULL,
        threshold_type TEXT NOT NULL,
        value REAL NOT NULL,
        description TEXT,
        FOREIGN KEY (parameter_id) REFERENCES chemical_parameters (parameter_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chemical_measurements (
        event_id INTEGER NOT NULL,
        parameter_id INTEGER NOT NULL,
        value REAL,
        bdl_flag BOOLEAN DEFAULT 0,
        status TEXT,
        PRIMARY KEY (event_id, parameter_id),
        FOREIGN KEY (event_id) REFERENCES chemical_collection_events (event_id),
        FOREIGN KEY (parameter_id) REFERENCES chemical_parameters (parameter_id)
    )
    ''')

    # ---------- FISH DATA TABLES ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_collection_events (
        event_id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        sample_id INTEGER NOT NULL,
        collection_date TEXT NOT NULL,
        year INTEGER NOT NULL,
        FOREIGN KEY (site_id) REFERENCES sites (site_id),
        UNIQUE(site_id, sample_id)
    )
    ''')

    # Reference values table - currently don't have access to this data
    # If reference values by region become available in the future, uncomment this table
    '''
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fish_reference_values (
        reference_id INTEGER PRIMARY KEY,
        region TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL,
        UNIQUE (region, metric_name)
    )
    """)
    '''  

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fish_metrics (
        event_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        raw_value REAL NOT NULL,
        metric_result REAL,
        metric_score INTEGER,
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
    
    # ---------- MACROINVERTEBRATE DATA TABLES ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS macro_collection_events (
        event_id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        sample_id INTEGER,
        collection_date TEXT NOT NULL,  
        season TEXT CHECK (season IN ('Summer', 'Winter')),
        year INTEGER NOT NULL,
        habitat TEXT CHECK (habitat IN ('Riffle', 'Vegetation', 'Woody')),
        FOREIGN KEY (site_id) REFERENCES sites (site_id)
        UNIQUE(site_id, sample_id, habitat)
    )
    ''')

    # Reference values table - currently don't have access to this data
    # If reference values by region become available in the future, uncomment this table
    '''
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS macro_reference_values (
        reference_id INTEGER PRIMARY KEY,
        region TEXT NOT NULL,
        season TEXT CHECK (season IN ('Summer', 'Winter')),
        habitat TEXT CHECK (habitat IN ('Riffle', 'Vegetation', 'Woody')),
        metric_name TEXT NOT NULL,
        metric_value REAL, 
        UNIQUE (region, season, habitat, metric_name)
    )
    """)  
    '''

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS macro_metrics (
        metric_id INTEGER PRIMARY KEY,  
        event_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        raw_value REAL NOT NULL,
        metric_score INTEGER,
        FOREIGN KEY (event_id) REFERENCES macro_collection_events (event_id),
        UNIQUE (event_id, metric_name)  
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
    
    # ---------- HABITAT DATA TABLES ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habitat_assessments (
        assessment_id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        assessment_date TEXT NOT NULL,
        year INTEGER NOT NULL,
        FOREIGN KEY (site_id) REFERENCES sites (site_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habitat_metrics (
        assessment_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        score REAL NOT NULL,
        PRIMARY KEY (assessment_id, metric_name),
        FOREIGN KEY (assessment_id) REFERENCES habitat_assessments (assessment_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habitat_summary_scores (
    assessment_id INTEGER NOT NULL,
    total_score REAL NOT NULL,
    habitat_grade TEXT NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES habitat_assessments (assessment_id)
    )
    ''')

    # Create database indexes to optimize map queries by site, date, and season
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chemical_site_date ON chemical_collection_events(site_id, collection_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chemical_measurements ON chemical_measurements(event_id, parameter_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_macro_site_season ON macro_collection_events(site_id, season, year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fish_site_year ON fish_collection_events(site_id, year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_habitat_site_year ON habitat_assessments(site_id, year)')
    
    close_connection(conn)
    print("Database schema created successfully")

if __name__ == "__main__":
    create_tables()