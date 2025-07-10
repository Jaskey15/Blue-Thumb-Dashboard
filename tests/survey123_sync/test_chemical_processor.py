"""
Tests for chemical processing adapter functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import sqlite3
import tempfile
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'cloud_functions', 'survey123_sync'))

# Mock Cloud Function specific modules before importing
sys.modules['functions_framework'] = MagicMock()
sys.modules['google.cloud'] = MagicMock() 
sys.modules['google.cloud.storage'] = MagicMock()

from chemical_processor import (
    get_reference_values_from_db,
    process_survey123_chemical_data,
    insert_processed_data_to_db,
    classify_active_sites_in_db
)


class TestChemicalProcessor(unittest.TestCase):
    """Test chemical processing adapter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample Survey123 data that would come from ArcGIS API
        self.sample_survey123_data = pd.DataFrame({
            'Site Name': ['Test Site 1', 'Test Site 2'],
            'Sampling Date': ['5/15/2023, 10:30 AM', '6/20/2023, 2:15 PM'],
            '% Oxygen Saturation': [95.5, 88.0],
            'pH #1': [7.2, 6.8],
            'pH #2': [7.5, 6.5],
            'Nitrate #1': [0.5, 1.2],
            'Nitrate #2': [0.6, 1.1],
            'Nitrite #1': [0.05, 0.1],
            'Nitrite #2': [0.04, 0.12],
            'Ammonia Nitrogen Range Selection': ['Low', 'Mid'],
            'Ammonia Nitrogen Low Reading #1': [0.1, 0.3],
            'Ammonia Nitrogen Low Reading #2': [0.12, 0.28],
            'Ammonia_nitrogen_midrange1_Final': [np.nan, 0.4],
            'Ammonia_nitrogen_midrange2_Final': [np.nan, 0.38],
            'Orthophosphate Range Selection': ['Low', 'High'],
            'Orthophosphate_Low1_Final': [0.02, 0.15],
            'Orthophosphate_Low2_Final': [0.03, 0.14],
            'Orthophosphate_High1_Final': [np.nan, 0.1],
            'Orthophosphate_High2_Final': [np.nan, 0.12],
            'Chloride Range Selection': ['Low', 'High'],
            'Chloride_Low1_Final': [25.0, 45.0],
            'Chloride_Low2_Final': [26.0, 44.0],
            'Chloride_High1_Final': [np.nan, 280.0],
            'Chloride_High2_Final': [np.nan, 275.0]
        })
        
        # Sample reference values
        self.sample_reference_values = {
            'do_percent': {'normal min': 80, 'normal max': 130},
            'pH': {'normal min': 6.5, 'normal max': 9.0},
            'soluble_nitrogen': {'normal': 0.8, 'caution': 1.5},
            'Phosphorus': {'normal': 0.05, 'caution': 0.1},
            'Chloride': {'poor': 250}
        }
    
    @patch('chemical_processor.pd.read_sql_query')
    def test_get_reference_values_from_db_success(self, mock_read_sql):
        """Test successful retrieval of reference values from database."""
        # Mock database query result
        mock_read_sql.return_value = pd.DataFrame({
            'parameter_code': ['do_percent', 'do_percent', 'pH', 'pH'],
            'threshold_type': ['normal_min', 'normal_max', 'normal_min', 'normal_max'],
            'value': [80, 130, 6.5, 9.0]
        })
        
        # Mock database connection
        mock_conn = MagicMock()
        
        result = get_reference_values_from_db(mock_conn)
        
        # Verify structure
        self.assertIn('do_percent', result)
        self.assertIn('pH', result)
        self.assertEqual(result['do_percent']['normal min'], 80)
        self.assertEqual(result['do_percent']['normal max'], 130)
        self.assertEqual(result['pH']['normal min'], 6.5)
        self.assertEqual(result['pH']['normal max'], 9.0)
    
    @patch('chemical_processor.pd.read_sql_query')
    def test_get_reference_values_from_db_empty(self, mock_read_sql):
        """Test handling of empty reference values."""
        # Mock empty query result
        mock_read_sql.return_value = pd.DataFrame()
        
        mock_conn = MagicMock()
        
        with self.assertRaises(Exception) as context:
            get_reference_values_from_db(mock_conn)
        
        self.assertIn("No chemical reference values found", str(context.exception))
    
    @patch('chemical_processor.pd.read_sql_query')
    def test_get_reference_values_from_db_error(self, mock_read_sql):
        """Test handling of database errors."""
        # Mock database error
        mock_read_sql.side_effect = Exception("Database connection failed")
        
        mock_conn = MagicMock()
        
        with self.assertRaises(Exception) as context:
            get_reference_values_from_db(mock_conn)
        
        self.assertIn("Cannot retrieve chemical reference values", str(context.exception))
    
    def test_process_survey123_chemical_data_success(self):
        """Test successful processing of Survey123 data."""
        result_df = process_survey123_chemical_data(self.sample_survey123_data.copy())
        
        # Verify DataFrame was processed
        self.assertFalse(result_df.empty)
        self.assertEqual(len(result_df), 2)
        
        # Verify required columns are present
        expected_columns = ['Site_Name', 'Date', 'Year', 'Month', 'do_percent', 
                          'pH', 'Nitrate', 'Nitrite', 'Ammonia', 'Phosphorus', 
                          'Chloride', 'soluble_nitrogen']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)
        
        # Verify data processing worked correctly
        # pH should select worst case (furthest from 7)
        self.assertEqual(result_df.iloc[0]['pH'], 7.5)  # 7.5 is further from 7 than 7.2
        self.assertEqual(result_df.iloc[1]['pH'], 6.5)  # 6.5 is further from 7 than 6.8
        
        # Nitrate should select higher value
        self.assertEqual(result_df.iloc[0]['Nitrate'], 0.6)  # Greater of 0.5 and 0.6
        self.assertEqual(result_df.iloc[1]['Nitrate'], 1.2)  # Greater of 1.2 and 1.1
        
        # Nitrite should select higher value
        self.assertEqual(result_df.iloc[0]['Nitrite'], 0.05)  # Greater of 0.05 and 0.04
        self.assertEqual(result_df.iloc[1]['Nitrite'], 0.12)  # Greater of 0.1 and 0.12
        
        # Conditional nutrients should work based on range selection
        self.assertEqual(result_df.iloc[0]['Ammonia'], 0.12)  # Low range, greater of 0.1 and 0.12
        self.assertEqual(result_df.iloc[1]['Ammonia'], 0.4)   # Mid range, greater of 0.4 and 0.38
        
        # Phosphorus (orthophosphate) should work based on range selection
        self.assertEqual(result_df.iloc[0]['Phosphorus'], 0.03)  # Low range
        self.assertEqual(result_df.iloc[1]['Phosphorus'], 0.12)  # High range
        
        # Chloride should work based on range selection
        self.assertEqual(result_df.iloc[0]['Chloride'], 26.0)  # Low range
        self.assertEqual(result_df.iloc[1]['Chloride'], 280.0)  # High range
    
    def test_process_survey123_chemical_data_empty(self):
        """Test processing of empty DataFrame."""
        empty_df = pd.DataFrame()
        
        result_df = process_survey123_chemical_data(empty_df)
        
        # Should return empty DataFrame
        self.assertTrue(result_df.empty)
    
    def test_process_survey123_chemical_data_error_handling(self):
        """Test error handling in processing pipeline."""
        # Create invalid data that should cause processing errors
        invalid_df = pd.DataFrame({
            'Site Name': ['Test Site'],
            'Invalid Column': ['Invalid Data']
        })
        
        result_df = process_survey123_chemical_data(invalid_df)
        
        # Should return empty DataFrame on error
        self.assertTrue(result_df.empty)
    
    @patch('chemical_processor.sqlite3.connect')
    @patch('chemical_processor.get_reference_values_from_db')
    def test_insert_processed_data_to_db_success(self, mock_get_ref, mock_connect):
        """Test successful database insertion."""
        # Mock processed data
        processed_data = pd.DataFrame({
            'Site_Name': ['Test Site 1'],
            'Date': [pd.Timestamp('2023-01-15')],
            'Year': [2023],
            'Month': [1],
            'do_percent': [95.5],
            'pH': [7.2],
            'soluble_nitrogen': [0.8],
            'Phosphorus': [0.05],
            'Chloride': [25.0]
        })
        
        # Mock database connection and operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock reference values
        mock_get_ref.return_value = self.sample_reference_values
        
        # Mock site lookup query
        site_df = pd.DataFrame({
            'site_id': [1],
            'site_name': ['Test Site 1']
        })
        with patch('chemical_processor.pd.read_sql_query', return_value=site_df):
            # Mock event ID retrieval
            mock_cursor.fetchone.return_value = (123,)  # event_id
            
            result = insert_processed_data_to_db(processed_data, '/fake/path/db.sqlite')
        
        # Verify success
        self.assertIn('records_inserted', result)
        self.assertGreater(result['records_inserted'], 0)
        
        # Verify database operations were called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('chemical_processor.sqlite3.connect')
    def test_insert_processed_data_to_db_empty_data(self, mock_connect):
        """Test handling of empty data insertion."""
        empty_df = pd.DataFrame()
        
        result = insert_processed_data_to_db(empty_df, '/fake/path/db.sqlite')
        
        # Should return appropriate result for empty data
        self.assertEqual(result['records_inserted'], 0)
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'No data to insert')
        
        # Should not attempt database connection
        mock_connect.assert_not_called()
    
    @patch('chemical_processor.sqlite3.connect')
    @patch('chemical_processor.get_reference_values_from_db')
    def test_insert_processed_data_to_db_site_not_found(self, mock_get_ref, mock_connect):
        """Test handling when site is not found in database."""
        # Mock processed data with unknown site
        processed_data = pd.DataFrame({
            'Site_Name': ['Unknown Site'],
            'Date': [pd.Timestamp('2023-01-15')],
            'do_percent': [95.5]
        })
        
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock reference values
        mock_get_ref.return_value = self.sample_reference_values
        
        # Mock empty site lookup (site not found)
        empty_site_df = pd.DataFrame(columns=['site_id', 'site_name'])
        with patch('chemical_processor.pd.read_sql_query', return_value=empty_site_df):
            result = insert_processed_data_to_db(processed_data, '/fake/path/db.sqlite')
        
        # Should still succeed but insert 0 records
        self.assertEqual(result['records_inserted'], 0)
    
    @patch('chemical_processor.sqlite3.connect')
    def test_insert_processed_data_to_db_database_error(self, mock_connect):
        """Test handling of database connection errors."""
        # Mock database connection error
        mock_connect.side_effect = Exception("Database connection failed")
        
        processed_data = pd.DataFrame({
            'Site_Name': ['Test Site'],
            'Date': [pd.Timestamp('2023-01-15')],
            'do_percent': [95.5]
        })
        
        result = insert_processed_data_to_db(processed_data, '/fake/path/db.sqlite')
        
        # Should return error result
        self.assertEqual(result['records_inserted'], 0)
        self.assertIn('error', result)
        self.assertIn('Database connection failed', result['error'])

    def test_classify_active_sites_in_db_success(self):
        """Test successful site classification."""
        # Create a temporary in-memory database
        with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
            # Setup test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            
            # Create minimal required tables
            cursor.execute('''
                CREATE TABLE sites (
                    site_id INTEGER PRIMARY KEY,
                    site_name TEXT NOT NULL,
                    active BOOLEAN DEFAULT 1,
                    last_chemical_reading_date TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE chemical_collection_events (
                    event_id INTEGER PRIMARY KEY,
                    site_id INTEGER NOT NULL,
                    collection_date TEXT NOT NULL,
                    FOREIGN KEY (site_id) REFERENCES sites (site_id)
                )
            ''')
            
            # Insert test data
            cursor.execute("INSERT INTO sites (site_id, site_name) VALUES (1, 'Active Site')")
            cursor.execute("INSERT INTO sites (site_id, site_name) VALUES (2, 'Historic Site')")
            
            # Add recent data for active site (within 1 year)
            cursor.execute("INSERT INTO chemical_collection_events (site_id, collection_date) VALUES (1, '2023-12-01')")
            
            # Add old data for historic site (more than 1 year old)
            cursor.execute("INSERT INTO chemical_collection_events (site_id, collection_date) VALUES (2, '2020-01-01')")
            
            conn.commit()
            conn.close()
            
            # Test the classification function
            result = classify_active_sites_in_db(temp_db.name)
            
            # Verify results
            self.assertNotIn('error', result)
            self.assertEqual(result['sites_classified'], 2)
            self.assertEqual(result['active_count'], 1)
            self.assertEqual(result['historic_count'], 1)
            self.assertIn('cutoff_date', result)
            self.assertIn('most_recent_date', result)
    
    def test_classify_active_sites_in_db_no_chemical_data(self):
        """Test site classification with no chemical data."""
        # Create a temporary in-memory database
        with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
            # Setup test database with sites but no chemical data
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE sites (
                    site_id INTEGER PRIMARY KEY,
                    site_name TEXT NOT NULL,
                    active BOOLEAN DEFAULT 1,
                    last_chemical_reading_date TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE chemical_collection_events (
                    event_id INTEGER PRIMARY KEY,
                    site_id INTEGER NOT NULL,
                    collection_date TEXT NOT NULL,
                    FOREIGN KEY (site_id) REFERENCES sites (site_id)
                )
            ''')
            
            cursor.execute("INSERT INTO sites (site_id, site_name) VALUES (1, 'Test Site')")
            
            conn.commit()
            conn.close()
            
            # Test the classification function
            result = classify_active_sites_in_db(temp_db.name)
            
            # Should return error for no chemical data
            self.assertIn('error', result)
            self.assertEqual(result['sites_classified'], 0)
    
    def test_classify_active_sites_in_db_database_error(self):
        """Test handling of database errors during classification."""
        # Test with non-existent database file
        result = classify_active_sites_in_db('/non/existent/path/test.db')
        
        # Should return error result
        self.assertIn('error', result)
        self.assertEqual(result['sites_classified'], 0)


if __name__ == '__main__':
    unittest.main() 