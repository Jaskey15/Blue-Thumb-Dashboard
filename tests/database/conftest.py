"""
Database test fixtures and utilities.

This module provides pytest fixtures for database testing, including:
- Temporary database creation and cleanup
- Connection management
- Mock data insertion
- Test state verification
"""

import os
import tempfile
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path if needed
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.database import get_connection
from database.db_schema import create_tables

@pytest.fixture(scope="function")
def temp_db_path():
    """Create a temporary database file path."""
    # Create a temporary file
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_blue_thumb.db")
    
    yield db_path
    
    # Cleanup after test
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception as e:
        print(f"Warning: Failed to cleanup temporary database: {e}")

@pytest.fixture(scope="function")
def mock_path_join(temp_db_path):
    """Mock os.path.join to return our temporary database path."""
    original_join = os.path.join
    
    def mock_join(*args):
        if 'blue_thumb.db' in args:
            return temp_db_path
        return original_join(*args)
    
    with patch('os.path.join', side_effect=mock_join):
        yield

@pytest.fixture(scope="function")
def temp_db(mock_path_join):
    """Create a temporary database with schema."""
    # Create tables
    create_tables()
    
    # Get connection to yield
    conn = get_connection()
    yield conn
    
    # Cleanup
    conn.close()

@pytest.fixture(scope="function")
def mock_site_data():
    """Return mock site data for testing."""
    return [
        {
            'site_id': 'TEST001',
            'site_name': 'Test Creek at Test Road',
            'latitude': 35.123,
            'longitude': -97.456,
            'county': 'Test County',
            'active': True
        },
        {
            'site_id': 'TEST002',
            'site_name': 'Mock Stream at Mock Bridge',
            'latitude': 35.789,
            'longitude': -97.123,
            'county': 'Mock County',
            'active': True
        }
    ]

@pytest.fixture(scope="function")
def mock_chemical_data():
    """Return mock chemical data for testing."""
    return [
        {
            'site_id': 'TEST001',
            'collection_date': '2023-01-01',
            'parameter': 'dissolved_oxygen',
            'value': 8.5,
            'units': 'mg/L'
        },
        {
            'site_id': 'TEST001',
            'collection_date': '2023-01-01',
            'parameter': 'ph',
            'value': 7.2,
            'units': 'pH units'
        }
    ]

@pytest.fixture(scope="function")
def db_with_mock_data(temp_db, mock_site_data, mock_chemical_data):
    """Create a database with mock data inserted."""
    # Insert mock site data
    temp_db.executemany(
        """
        INSERT INTO sites (site_id, site_name, latitude, longitude, county, active)
        VALUES (:site_id, :site_name, :latitude, :longitude, :county, :active)
        """,
        mock_site_data
    )
    
    # Insert mock chemical data
    temp_db.executemany(
        """
        INSERT INTO chemical_data (site_id, collection_date, parameter, value, units)
        VALUES (:site_id, :collection_date, :parameter, :value, :units)
        """,
        mock_chemical_data
    )
    
    temp_db.commit()
    return temp_db

def verify_table_exists(conn, table_name):
    """Helper function to verify if a table exists."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

@pytest.fixture(scope="function")
def verify_db_state():
    """Fixture to provide database state verification."""
    def _verify_db_state(conn, expected_tables=None):
        """
        Verify database state matches expectations.
        
        Args:
            conn: Database connection
            expected_tables: List of table names that should exist
        
        Returns:
            bool: True if state matches expectations
        """
        if expected_tables is None:
            expected_tables = ['sites', 'chemical_data', 'fish_data', 'macro_data', 'habitat_data']
            
        for table in expected_tables:
            if not verify_table_exists(conn, table):
                return False
        return True
    
    return _verify_db_state 