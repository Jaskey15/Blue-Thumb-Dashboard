"""
Tests for database operations including CRUD operations and transaction handling.

This module tests:
- Basic CRUD operations
- Transaction management
- Error handling
- Connection management
- Batch operations
- Query performance
"""

import sqlite3

import pytest

from database.database import close_connection, execute_query, get_connection


class TestBasicOperations:
    """Test basic database operations."""
    
    def test_insert_operation(self, temp_db):
        """Test basic insert operation."""
        cursor = temp_db.cursor()
        
        # Insert test data
        cursor.execute("""
            INSERT INTO sites (site_name, latitude, longitude)
            VALUES (?, ?, ?)
        """, ('Test Site', 35.0, -97.0))
        temp_db.commit()
        
        # Verify insertion
        cursor.execute("SELECT site_name, latitude, longitude FROM sites")
        result = cursor.fetchone()
        assert result == ('Test Site', 35.0, -97.0)
    
    def test_update_operation(self, temp_db):
        """Test basic update operation."""
        cursor = temp_db.cursor()
        
        # Insert initial data
        cursor.execute("""
            INSERT INTO sites (site_name, latitude, longitude)
            VALUES (?, ?, ?)
        """, ('Test Site', 35.0, -97.0))
        temp_db.commit()
        
        # Update data
        cursor.execute("""
            UPDATE sites 
            SET latitude = ?, longitude = ?
            WHERE site_name = ?
        """, (36.0, -98.0, 'Test Site'))
        temp_db.commit()
        
        # Verify update
        cursor.execute("""
            SELECT latitude, longitude 
            FROM sites 
            WHERE site_name = ?
        """, ('Test Site',))
        result = cursor.fetchone()
        assert result == (36.0, -98.0)
    
    def test_delete_operation(self, temp_db):
        """Test basic delete operation."""
        cursor = temp_db.cursor()
        
        # Insert test data
        cursor.execute("""
            INSERT INTO sites (site_name)
            VALUES (?)
        """, ('Test Site',))
        temp_db.commit()
        
        # Delete data
        cursor.execute("DELETE FROM sites WHERE site_name = ?", ('Test Site',))
        temp_db.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM sites WHERE site_name = ?", ('Test Site',))
        count = cursor.fetchone()[0]
        assert count == 0

class TestTransactionManagement:
    """Test transaction management."""
    
    def test_successful_transaction(self, temp_db):
        """Test successful transaction with multiple operations."""
        cursor = temp_db.cursor()
        
        try:
            # Start transaction
            cursor.execute("""
                INSERT INTO sites (site_name, latitude, longitude)
                VALUES (?, ?, ?)
            """, ('Site 1', 35.0, -97.0))
            
            cursor.execute("""
                INSERT INTO sites (site_name, latitude, longitude)
                VALUES (?, ?, ?)
            """, ('Site 2', 36.0, -98.0))
            
            temp_db.commit()
            
            # Verify both inserts succeeded
            cursor.execute("SELECT COUNT(*) FROM sites")
            count = cursor.fetchone()[0]
            assert count == 2
            
        except Exception:
            temp_db.rollback()
            raise
    
    def test_failed_transaction_rollback(self, temp_db):
        """Test transaction rollback on failure."""
        cursor = temp_db.cursor()
        
        try:
            # First insert (should succeed)
            cursor.execute("""
                INSERT INTO sites (site_name, latitude, longitude)
                VALUES (?, ?, ?)
            """, ('Site 1', 35.0, -97.0))
            
            # Second insert (should fail due to duplicate name)
            cursor.execute("""
                INSERT INTO sites (site_name, latitude, longitude)
                VALUES (?, ?, ?)
            """, ('Site 1', 36.0, -98.0))
            
            temp_db.commit()
            
        except sqlite3.IntegrityError:
            temp_db.rollback()
        
        # Verify no data was inserted
        cursor.execute("SELECT COUNT(*) FROM sites")
        count = cursor.fetchone()[0]
        assert count == 0

class TestErrorHandling:
    """Test database error handling."""
    
    def test_execute_query_success(self, temp_db):
        """Test execute_query with successful operation."""
        result = execute_query(
            "INSERT INTO sites (site_name) VALUES (?)",
            ('Test Site',)
        )
        assert result is not None
        
        # Verify insertion
        cursor = temp_db.cursor()
        cursor.execute("SELECT site_name FROM sites")
        site = cursor.fetchone()
        assert site[0] == 'Test Site'
    
    def test_execute_query_error(self, temp_db):
        """Test execute_query with failed operation."""
        # Try to insert duplicate site name
        execute_query(
            "INSERT INTO sites (site_name) VALUES (?)",
            ('Test Site',)
        )
        
        with pytest.raises(sqlite3.IntegrityError):
            execute_query(
                "INSERT INTO sites (site_name) VALUES (?)",
                ('Test Site',)
            )

class TestBatchOperations:
    """Test batch database operations."""
    
    def test_batch_insert(self, temp_db):
        """Test batch insert operation."""
        cursor = temp_db.cursor()
        
        # Prepare batch data
        sites = [
            ('Site 1', 35.0, -97.0),
            ('Site 2', 36.0, -98.0),
            ('Site 3', 37.0, -99.0)
        ]
        
        # Execute batch insert
        cursor.executemany("""
            INSERT INTO sites (site_name, latitude, longitude)
            VALUES (?, ?, ?)
        """, sites)
        temp_db.commit()
        
        # Verify all inserts
        cursor.execute("SELECT COUNT(*) FROM sites")
        count = cursor.fetchone()[0]
        assert count == 3
    
    def test_batch_update(self, temp_db):
        """Test batch update operation."""
        cursor = temp_db.cursor()
        
        # Insert initial data
        sites = [
            ('Site 1', 35.0, -97.0),
            ('Site 2', 36.0, -98.0),
            ('Site 3', 37.0, -99.0)
        ]
        cursor.executemany("""
            INSERT INTO sites (site_name, latitude, longitude)
            VALUES (?, ?, ?)
        """, sites)
        
        # Prepare batch updates
        updates = [
            (True, 'Site 1'),
            (True, 'Site 2'),
            (False, 'Site 3')
        ]
        
        # Execute batch update
        cursor.executemany("""
            UPDATE sites 
            SET active = ?
            WHERE site_name = ?
        """, updates)
        temp_db.commit()
        
        # Verify updates
        cursor.execute("SELECT COUNT(*) FROM sites WHERE active = 1")
        active_count = cursor.fetchone()[0]
        assert active_count == 2

class TestConnectionManagement:
    """Test connection management."""
    
    def test_connection_commit(self, temp_db):
        """Test changes are committed properly."""
        # Make changes
        cursor = temp_db.cursor()
        cursor.execute("""
            INSERT INTO sites (site_name)
            VALUES (?)
        """, ('Test Site',))
        temp_db.commit()
        
        # Close connection
        temp_db.close()
        
        # Open new connection and verify changes persisted
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT site_name FROM sites")
        result = cursor.fetchone()
        assert result[0] == 'Test Site'
        conn.close()
    
    def test_connection_rollback(self, temp_db):
        """Test changes are rolled back properly."""
        cursor = temp_db.cursor()
        
        # Make changes without commit
        cursor.execute("""
            INSERT INTO sites (site_name)
            VALUES (?)
        """, ('Test Site',))
        
        # Rollback changes
        temp_db.rollback()
        
        # Verify changes were rolled back
        cursor.execute("SELECT COUNT(*) FROM sites")
        count = cursor.fetchone()[0]
        assert count == 0
    
    def test_close_connection(self):
        """Test connection is closed properly."""
        conn = get_connection()
        close_connection(conn)
        
        # Verify connection is closed
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

class TestQueryPerformance:
    """Test query performance with larger datasets."""
    
    def test_large_batch_insert_performance(self, temp_db):
        """Test performance of large batch insert."""
        cursor = temp_db.cursor()
        
        # Create large batch of test data
        sites = [
            (f'Site {i}', 35.0 + (i/100), -97.0 - (i/100))
            for i in range(1000)
        ]
        
        # Measure insertion time
        cursor.executemany("""
            INSERT INTO sites (site_name, latitude, longitude)
            VALUES (?, ?, ?)
        """, sites)
        temp_db.commit()
        
        # Verify all data was inserted
        cursor.execute("SELECT COUNT(*) FROM sites")
        count = cursor.fetchone()[0]
        assert count == 1000
    
    def test_indexed_query_performance(self, temp_db):
        """Test query performance with indexes."""
        cursor = temp_db.cursor()
        
        # Create test data
        sites = [
            (f'Site {i}', 35.0 + (i/100), -97.0 - (i/100))
            for i in range(1000)
        ]
        cursor.executemany("""
            INSERT INTO sites (site_name, latitude, longitude)
            VALUES (?, ?, ?)
        """, sites)
        temp_db.commit()
        
        # Create index
        cursor.execute("CREATE INDEX idx_site_name ON sites(site_name)")
        temp_db.commit()
        
        # Query with index
        cursor.execute("""
            SELECT * FROM sites 
            WHERE site_name = ?
        """, ('Site 500',))
        result = cursor.fetchone()
        assert result is not None
        assert result[1] == 'Site 500' 