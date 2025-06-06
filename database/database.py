import os
import sqlite3

def get_connection():
    """Create and return a database connection."""
    db_path = os.path.join(os.path.dirname(__file__), 'blue_thumb.db')
    conn = sqlite3.connect(db_path)
    return conn

def close_connection(conn):
    """Safely close a database connection."""
    if conn:
        conn.commit()
        conn.close()

def execute_query(query, params=None):
    """Execute a SQL query with error handling."""
    conn = get_connection(db_name)
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        close_connection(conn)