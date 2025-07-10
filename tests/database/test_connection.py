"""
Tests for database connection handling.

This module tests:
- Connection establishment
- Connection pooling
- Error handling
- Resource cleanup
"""

import sqlite3
from unittest.mock import patch

import pytest

from database.database import get_connection


def test_get_connection_success(mock_path_join):
    """Test successful database connection."""
    conn = get_connection()
    assert conn is not None
    assert isinstance(conn, sqlite3.Connection)
    conn.close()

def test_connection_is_writable(temp_db):
    """Test that connection has write permissions."""
    cursor = temp_db.cursor()
    cursor.execute("CREATE TABLE test_write (id INTEGER PRIMARY KEY)")
    cursor.execute("INSERT INTO test_write (id) VALUES (1)")
    temp_db.commit()
    
    cursor.execute("SELECT * FROM test_write")
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == 1

def test_connection_isolation(mock_path_join):
    """Test that connections are isolated from each other."""
    # First connection creates and commits data
    conn1 = get_connection()
    cursor1 = conn1.cursor()
    cursor1.execute("CREATE TABLE test_isolation (id INTEGER PRIMARY KEY)")
    cursor1.execute("INSERT INTO test_isolation (id) VALUES (1)")
    conn1.commit()
    
    # Second connection should see committed data
    conn2 = get_connection()
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT * FROM test_isolation")
    result = cursor2.fetchone()
    assert result is not None
    assert result[0] == 1
    
    # But uncommitted changes should not be visible
    cursor1.execute("INSERT INTO test_isolation (id) VALUES (2)")
    # No commit here
    
    cursor2.execute("SELECT COUNT(*) FROM test_isolation")
    count = cursor2.fetchone()[0]
    assert count == 1  # Should only see the committed row
    
    conn1.close()
    conn2.close()

def test_connection_error_handling(mock_path_join):
    """Test handling of connection errors."""
    non_existent_path = "/path/that/does/not/exist/db.sqlite"
    
    # Test with non-existent directory
    with pytest.raises(sqlite3.OperationalError):
        with patch('os.path.join', return_value=non_existent_path):
            get_connection()

def test_connection_closes_properly(temp_db):
    """Test that connections are properly closed."""
    cursor = temp_db.cursor()
    
    # Should be able to execute queries
    cursor.execute("SELECT 1")
    assert cursor.fetchone() == (1,)
    
    # Close the connection
    temp_db.close()
    
    # Attempting to use closed connection should raise error
    with pytest.raises(sqlite3.ProgrammingError):
        cursor.execute("SELECT 1")

def test_concurrent_connections(mock_path_join):
    """Test handling multiple concurrent connections."""
    # Create multiple connections
    connections = [get_connection() for _ in range(5)]
    
    try:
        # Each connection should be able to read/write
        for i, conn in enumerate(connections):
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test_concurrent (id INTEGER PRIMARY KEY)")
            cursor.execute("INSERT INTO test_concurrent (id) VALUES (?)", (i+1,))
            conn.commit()
        
        # Verify each connection can read all committed data
        for conn in connections:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_concurrent")
            count = cursor.fetchone()[0]
            assert count == 5
    
    finally:
        # Clean up connections
        for conn in connections:
            conn.close()

def test_connection_with_timeout(mock_path_join):
    """Test connection timeout handling."""
    conn = get_connection()
    
    # Verify timeout setting
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout")
    timeout = cursor.fetchone()[0]
    assert timeout > 0  # Should have a non-zero timeout
    
    conn.close()

def test_connection_foreign_keys(temp_db):
    """Test that foreign key constraints are enabled."""
    cursor = temp_db.cursor()
    
    # Create test tables with foreign key constraint
    cursor.execute("""
        CREATE TABLE parent (
            id INTEGER PRIMARY KEY
        )
    """)
    
    cursor.execute("""
        CREATE TABLE child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            FOREIGN KEY (parent_id) REFERENCES parent(id)
        )
    """)
    
    # Insert parent row
    cursor.execute("INSERT INTO parent (id) VALUES (1)")
    
    # This should work (valid foreign key)
    cursor.execute("INSERT INTO child (id, parent_id) VALUES (1, 1)")
    
    # This should fail (invalid foreign key)
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO child (id, parent_id) VALUES (2, 999)")

def test_connection_journal_mode(temp_db):
    """Test that journal mode is properly set."""
    cursor = temp_db.cursor()
    
    # Check journal mode
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0].upper()
    assert journal_mode in ['WAL', 'DELETE']  # Should be either WAL or DELETE 