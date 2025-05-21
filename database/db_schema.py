from database.database import get_connection, close_connection

def insert_default_parameters(cursor):
    """
    Insert default chemical parameters into the database.
    
    Args:
        cursor: Database cursor
        
    Returns:
        bool: True if successful
    """
    # Define the parameters
    parameters = [
        (1, 'Dissolved Oxygen', 'do_percent', 'Dissolved Oxygen', 'Percent saturation of dissolved oxygen', '%'),
        (2, 'pH', 'pH', 'pH', 'Measure of acidity/alkalinity', 'pH units'),
        (3, 'Soluble Nitrogen', 'soluble_nitrogen', 'Nitrogen', 'Total soluble nitrogen including nitrate, nitrite, and ammonia', 'mg/L'),
        (4, 'Phosphorus', 'Phosphorus', 'Phosphorus', 'Orthophosphate phosphorus', 'mg/L'),
        (5, 'Chloride', 'Chloride', 'Chloride', 'Chloride ion concentration', 'mg/L')
    ]
    
    # Insert the parameters
    cursor.executemany('''
    INSERT OR IGNORE INTO chemical_parameters 
    (parameter_id, parameter_name, parameter_code, display_name, description, unit)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', parameters)
    
    print(f"Inserted {len(parameters)} chemical parameters")
    return True

def insert_default_reference_values(cursor):
    """
    Insert default chemical reference values into the database.
    
    Args:
        cursor: Database cursor
        
    Returns:
        bool: True if successful
    """
    # Define the reference values
    reference_values = [
        # do_percent reference values
        (1, 1, 'normal_min', 80, 'Minimum for normal range'),
        (2, 1, 'normal_max', 130, 'Maximum for normal range'),
        (3, 1, 'caution_min', 50, 'Minimum for caution range'),
        (4, 1, 'caution_max', 150, 'Maximum for caution range'),
        
        # pH reference values
        (5, 2, 'normal_min', 6.5, 'Minimum for normal range'),
        (6, 2, 'normal_max', 9.0, 'Maximum for normal range'),
        
        # Soluble Nitrogen reference values
        (7, 3, 'normal', 0.8, 'Normal threshold'),
        (8, 3, 'caution', 1.5, 'Caution threshold'),
        
        # Phosphorus reference values
        (9, 4, 'normal', 0.05, 'Normal threshold'),
        (10, 4, 'caution', 0.1, 'Caution threshold'),
        
        # Chloride reference values
        (11, 5, 'poor', 250, 'Poor threshold')
    ]
    
    # Insert the reference values
    cursor.executemany('''
    INSERT OR IGNORE INTO chemical_reference_values
    (reference_id, parameter_id, threshold_type, value, description)
    VALUES (?, ?, ?, ?, ?)
    ''', reference_values)
    
    print(f"Inserted {len(reference_values)} chemical reference values")
    return True

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
        season TEXT CHECK (season IN ('Summer', 'Winter')),
        year INTEGER NOT NULL,
        habitat TEXT CHECK (habitat IN ('Riffle', 'Vegetation', 'Woody')),
        FOREIGN KEY (site_id) REFERENCES sites (site_id)
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
    
    # Run some initial population of common tables
    # Insert key chemical parameters
    cursor.execute("SELECT COUNT(*) FROM chemical_parameters")
    if cursor.fetchone()[0] == 0:
        # Insert default parameters and reference values
        insert_default_parameters(cursor)
        insert_default_reference_values(cursor)
        
        conn.commit()
        print("Initial chemical parameters and reference values added")
    
    close_connection(conn)
    print("Database schema created successfully")

if __name__ == "__main__":
    create_tables()