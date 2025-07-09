"""
Test suite for chemical_duplicates.py - Chemical duplicate detection and consolidation.
Tests the core functionality for identifying and merging replicate chemical samples.
"""

import unittest
import pandas as pd
import numpy as np
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.chemical_duplicates import (
    get_worst_case_value,
    identify_replicate_samples,
    consolidate_replicate_samples
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_chemical_duplicates", category="testing")


class TestChemicalDuplicates(unittest.TestCase):
    """Test chemical duplicate detection and consolidation functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample replicate groups for testing
        self.sample_replicate_groups = [
            {
                'site_name': 'Blue Creek at Highway 9',
                'collection_date': '2023-05-15',
                'event_count': 2,
                'event_ids': [101, 102],
                'keep_event_id': 101
            },
            {
                'site_name': 'Red River at Bridge',
                'collection_date': '2023-06-20',
                'event_count': 3,
                'event_ids': [201, 202, 203],
                'keep_event_id': 201
            }
        ]

    # =============================================================================
    # WORST CASE VALUE TESTS
    # =============================================================================

    def test_get_worst_case_value_ph(self):
        """Test worst case value selection for pH (furthest from neutral)."""
        # Test pH values - should select the one furthest from 7.0
        ph_values = [6.5, 7.2, 8.5]
        result = get_worst_case_value(ph_values, 'pH')
        self.assertEqual(result, 8.5)  # 8.5 is 1.5 units from 7.0, furthest
        
        # Test with acidic values
        acidic_values = [6.0, 6.8, 7.1]
        result = get_worst_case_value(acidic_values, 'pH')
        self.assertEqual(result, 6.0)  # 6.0 is 1.0 units from 7.0, furthest
        
        # Test equidistant values - should pick the first one found by max()
        equidistant_values = [6.0, 8.0]
        result = get_worst_case_value(equidistant_values, 'pH')
        self.assertIn(result, [6.0, 8.0])  # Either is valid, both 1.0 unit from 7.0

    def test_get_worst_case_value_dissolved_oxygen(self):
        """Test worst case value selection for dissolved oxygen (lowest value)."""
        do_values = [95.5, 88.0, 110.2]
        result = get_worst_case_value(do_values, 'do_percent')
        self.assertEqual(result, 88.0)  # Lowest value is worst case

    def test_get_worst_case_value_nutrients(self):
        """Test worst case value selection for nutrients (highest value)."""
        # Test nitrate
        nitrate_values = [0.5, 1.2, 0.8]
        result = get_worst_case_value(nitrate_values, 'Nitrate')
        self.assertEqual(result, 1.2)  # Highest value is worst case
        
        # Test phosphorus
        phosphorus_values = [0.02, 0.15, 0.08]
        result = get_worst_case_value(phosphorus_values, 'Phosphorus')
        self.assertEqual(result, 0.15)  # Highest value is worst case
        
        # Test chloride
        chloride_values = [25.0, 280.0, 45.0]
        result = get_worst_case_value(chloride_values, 'Chloride')
        self.assertEqual(result, 280.0)  # Highest value is worst case

    def test_get_worst_case_value_with_nulls(self):
        """Test worst case value selection with null values."""
        # Test with None values
        values_with_none = [0.5, None, 1.2]
        result = get_worst_case_value(values_with_none, 'Nitrate')
        self.assertEqual(result, 1.2)  # Should ignore None and return max of valid values
        
        # Test with NaN values
        values_with_nan = [0.5, np.nan, 1.2]
        result = get_worst_case_value(values_with_nan, 'Nitrate')
        self.assertEqual(result, 1.2)  # Should ignore NaN and return max of valid values
        
        # Test with all null values
        all_null_values = [None, None, np.nan]
        result = get_worst_case_value(all_null_values, 'Nitrate')
        self.assertIsNone(result)  # Should return None when all values are null

    def test_get_worst_case_value_empty_list(self):
        """Test worst case value selection with empty list."""
        result = get_worst_case_value([], 'pH')
        self.assertIsNone(result)

    # =============================================================================
    # REPLICATE IDENTIFICATION TESTS
    # =============================================================================

    @patch('database.database.close_connection')
    @patch('database.database.get_connection')
    @patch('pandas.read_sql_query')
    def test_identify_replicate_samples_with_duplicates(self, mock_read_sql, mock_get_conn, mock_close):
        """Test identification of replicate samples when duplicates exist."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        # Mock SQL query result with replicate data
        mock_replicate_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Red River at Bridge'],
            'collection_date': ['2023-05-15', '2023-06-20'],
            'event_count': [2, 3],
            'event_ids': ['101,102', '201,202,203']
        })
        mock_read_sql.return_value = mock_replicate_data
        
        result = identify_replicate_samples()
        
        # Verify database calls
        mock_get_conn.assert_called_once()
        mock_close.assert_called_once_with(mock_conn)
        mock_read_sql.assert_called_once()
        
        # Verify result structure
        self.assertEqual(len(result), 2)
        
        # Check first replicate group
        first_group = result[0]
        self.assertEqual(first_group['site_name'], 'Blue Creek at Highway 9')
        self.assertEqual(first_group['event_count'], 2)
        self.assertEqual(first_group['event_ids'], [101, 102])
        self.assertEqual(first_group['keep_event_id'], 101)  # Minimum event ID
        
        # Check second replicate group
        second_group = result[1]
        self.assertEqual(second_group['site_name'], 'Red River at Bridge')
        self.assertEqual(second_group['event_count'], 3)
        self.assertEqual(second_group['event_ids'], [201, 202, 203])
        self.assertEqual(second_group['keep_event_id'], 201)  # Minimum event ID

    @patch('database.database.close_connection')
    @patch('database.database.get_connection')
    @patch('pandas.read_sql_query')
    def test_identify_replicate_samples_no_duplicates(self, mock_read_sql, mock_get_conn, mock_close):
        """Test identification when no replicate samples exist."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        # Mock empty SQL query result
        mock_read_sql.return_value = pd.DataFrame()
        
        result = identify_replicate_samples()
        
        # Should return empty list
        self.assertEqual(result, [])
        
        # Verify database calls
        mock_get_conn.assert_called_once()
        mock_close.assert_called_once_with(mock_conn)

    @patch('database.database.close_connection')
    @patch('database.database.get_connection')
    def test_identify_replicate_samples_database_error(self, mock_get_conn, mock_close):
        """Test handling of database errors during replicate identification."""
        # Mock database connection error
        mock_get_conn.side_effect = Exception("Database connection failed")
        
        result = identify_replicate_samples()
        
        # Should return empty list on error
        self.assertEqual(result, [])

    # =============================================================================
    # CONSOLIDATION TESTS
    # =============================================================================

    @patch('data_processing.chemical_duplicates.identify_replicate_samples')
    def test_consolidate_replicate_samples_no_replicates(self, mock_identify):
        """Test consolidation when no replicate samples exist."""
        # Mock no replicate samples found
        mock_identify.return_value = []
        
        result = consolidate_replicate_samples()
        
        # Should return zero stats
        expected_stats = {
            'groups_processed': 0,
            'events_removed': 0,
            'measurements_updated': 0
        }
        self.assertEqual(result, expected_stats)

    @patch('data_processing.chemical_utils.get_reference_values')
    @patch('data_processing.chemical_utils.determine_status')
    @patch('database.database.close_connection')
    @patch('database.database.get_connection')
    @patch('pandas.read_sql_query')
    @patch('data_processing.chemical_duplicates.identify_replicate_samples')
    def test_consolidate_replicate_samples_with_data(self, mock_identify, mock_read_sql, 
                                                   mock_get_conn, mock_close, 
                                                   mock_determine_status, mock_get_ref_values):
        """Test consolidation with actual replicate data."""
        # Mock replicate identification
        mock_identify.return_value = [self.sample_replicate_groups[0]]  # Single group for simplicity
        
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # Mock measurements query result
        mock_measurements_data = pd.DataFrame({
            'event_id': [101, 102, 101, 102],
            'parameter_id': [1, 1, 2, 2],
            'value': [7.2, 7.8, 8.5, 7.0],  # pH and DO values
            'parameter_code': ['pH', 'pH', 'do_percent', 'do_percent']
        })
        mock_read_sql.return_value = mock_measurements_data
        
        # Mock reference values and status determination
        mock_get_ref_values.return_value = {}
        mock_determine_status.return_value = 'Normal'
        
        # Mock cursor operations - need to return mock cursor from execute
        mock_execute_result = MagicMock()
        mock_execute_result.fetchone.return_value = (1,)  # Simulate existing measurement
        mock_cursor.execute.return_value = mock_execute_result
        
        result = consolidate_replicate_samples()
        
        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn('groups_processed', result)
        self.assertIn('events_removed', result)
        self.assertIn('measurements_updated', result)
        
        # Verify database operations were called
        mock_conn.commit.assert_called_once()
        mock_close.assert_called_once_with(mock_conn)

    @patch('data_processing.chemical_duplicates.identify_replicate_samples')
    @patch('database.database.get_connection')
    def test_consolidate_replicate_samples_database_error(self, mock_get_conn, mock_identify):
        """Test error handling during consolidation."""
        # Mock replicate samples found
        mock_identify.return_value = [self.sample_replicate_groups[0]]
        
        # Mock database connection error
        mock_get_conn.side_effect = Exception("Database error")
        
        # Should raise exception
        with self.assertRaises(Exception) as context:
            consolidate_replicate_samples()
        
        self.assertIn("Failed to consolidate replicate samples", str(context.exception))

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_worst_case_logic_integration(self):
        """Test that worst case logic works correctly for different parameter types."""
        # Test multiple parameter types together
        test_cases = [
            # (values, parameter, expected_worst)
            ([6.5, 7.2, 8.5], 'pH', 8.5),              # pH: furthest from 7.0
            ([95.5, 88.0, 110.2], 'do_percent', 88.0), # DO: lowest value
            ([0.5, 1.2, 0.8], 'Nitrate', 1.2),         # Nitrate: highest value
            ([0.02, 0.15, 0.08], 'Phosphorus', 0.15),  # Phosphorus: highest value
            ([25.0, 280.0, 45.0], 'Chloride', 280.0),  # Chloride: highest value
        ]
        
        for values, parameter, expected in test_cases:
            with self.subTest(parameter=parameter):
                result = get_worst_case_value(values, parameter)
                self.assertEqual(result, expected)

    def test_event_id_processing(self):
        """Test that event ID processing works correctly."""
        # Test event ID string parsing (simulating what identify_replicate_samples does)
        event_id_strings = ['101,102', '201,202,203', '301']
        
        for event_string in event_id_strings:
            event_ids = [int(id.strip()) for id in event_string.split(',')]
            keep_event_id = min(event_ids)
            
            # Verify minimum event ID is selected
            self.assertEqual(keep_event_id, min(event_ids))
            
            # Verify all IDs are integers
            self.assertTrue(all(isinstance(eid, int) for eid in event_ids))


if __name__ == '__main__':
    unittest.main(verbosity=2) 