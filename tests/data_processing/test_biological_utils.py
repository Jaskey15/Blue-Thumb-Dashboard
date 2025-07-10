"""
Test suite for shared biological data utilities.
Tests the logic in data_processing.biological_utils module.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.biological_utils import (
    convert_columns_to_numeric,
    insert_collection_events,
    remove_invalid_biological_values,
    validate_collection_event_data,
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_biological_utils", category="testing")


class TestBiologicalUtils(unittest.TestCase):
    """Test shared biological utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Basic biological data for testing
        self.basic_bio_data = pd.DataFrame({
            'site_name': ['Site1', 'Site2', 'Site3'],
            'sample_id': [101, 102, 103],
            'collection_date': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'year': [2023, 2023, 2023]
        })
        
        # Fish-style grouping data
        self.fish_style_data = self.basic_bio_data.copy()
        self.fish_style_data['total_species_score'] = [3, 5, 1]
        self.fish_style_data['total_score'] = [21, 19, 17]
        self.fish_style_data['collection_date_str'] = ['2023-01-01', '2023-01-02', '2023-01-03']
        
        # Macro-style grouping data (includes habitat)
        self.macro_style_data = self.basic_bio_data.copy()
        self.macro_style_data['habitat'] = ['Riffle', 'Pool', 'Vegetation']
        self.macro_style_data['season'] = ['Spring', 'Fall', 'Spring']
        self.macro_style_data['taxa_richness_score'] = [5, 3, 1]
        self.macro_style_data['collection_date_str'] = ['2023-01-01', '2023-01-02', '2023-01-03']

    # =============================================================================
    # VALIDATION TESTS
    # =============================================================================
    
    def test_validate_collection_event_data_valid(self):
        """Test validation with valid data."""
        result = validate_collection_event_data(
            self.basic_bio_data, 
            ['site_name', 'sample_id']
        )
        self.assertTrue(result)
    
    def test_validate_collection_event_data_missing_columns(self):
        """Test validation with missing required columns."""
        with self.assertRaises(ValueError):
            validate_collection_event_data(
                self.basic_bio_data, 
                ['site_name', 'missing_column']
            )
    
    def test_validate_collection_event_data_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        with self.assertRaises(ValueError):
            validate_collection_event_data(pd.DataFrame(), ['site_name'])

    def test_validate_collection_event_data_with_nulls(self):
        """Test validation with null values in grouping columns."""
        null_data = self.basic_bio_data.copy()
        null_data.loc[1, 'site_name'] = None
        
        # Should pass validation but log warning
        result = validate_collection_event_data(null_data, ['site_name', 'sample_id'])
        self.assertTrue(result)

    def test_validate_collection_event_data_with_required_columns(self):
        """Test validation with additional required columns."""
        result = validate_collection_event_data(
            self.basic_bio_data,
            ['site_name', 'sample_id'],
            required_columns=['collection_date', 'year']
        )
        self.assertTrue(result)
        
        # Test with missing required column
        with self.assertRaises(ValueError):
            validate_collection_event_data(
                self.basic_bio_data,
                ['site_name', 'sample_id'],
                required_columns=['missing_required_col']
            )

    # =============================================================================
    # COLLECTION EVENTS INSERTION TESTS  
    # =============================================================================
    
    def test_insert_collection_events_fish_style(self):
        """Test collection event insertion for fish-style data."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # site_id = 1
        mock_cursor.lastrowid = 123  # event_id = 123
        
        result = insert_collection_events(
            cursor=mock_cursor,
            df=self.fish_style_data,
            table_name='fish_collection_events',
            grouping_columns=['site_name', 'sample_id'],
            column_mapping={
                'site_id': 'site_name',
                'sample_id': 'sample_id', 
                'collection_date': 'collection_date_str',
                'year': 'year'
            }
        )
        
        # Should return mapping of sample_id -> event_id for fish
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)  # 3 unique samples
        
        # Verify database calls were made
        self.assertEqual(mock_cursor.execute.call_count, 6)  # 3 site lookups + 3 inserts
        
        # Check that sample_ids are keys (fish style)
        for sample_id in [101, 102, 103]:
            self.assertIn(sample_id, result)
        
    def test_insert_collection_events_macro_style(self):
        """Test collection event insertion for macro-style data."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.lastrowid = 456
        
        result = insert_collection_events(
            cursor=mock_cursor,
            df=self.macro_style_data,
            table_name='macro_collection_events',
            grouping_columns=['site_name', 'sample_id', 'habitat'],
            column_mapping={
                'site_id': 'site_name',
                'sample_id': 'sample_id',
                'habitat': 'habitat', 
                'season': 'season',
                'year': 'year'
            }
        )
        
        # Should return mapping of (sample_id, habitat) -> event_id for macro
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)  # 3 unique sample+habitat combinations
        
        # Check that tuples are keys (macro style)
        expected_keys = [(101, 'Riffle'), (102, 'Pool'), (103, 'Vegetation')]
        for key in expected_keys:
            self.assertIn(key, result)

    def test_insert_collection_events_site_not_found(self):
        """Test handling when site is not found in database."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Site not found
        
        result = insert_collection_events(
            cursor=mock_cursor,
            df=self.fish_style_data,
            table_name='fish_collection_events',
            grouping_columns=['site_name', 'sample_id'],
            column_mapping={
                'site_id': 'site_name',
                'sample_id': 'sample_id'
            }
        )
        
        # Should return empty dict when sites not found
        self.assertEqual(len(result), 0)

    def test_insert_collection_events_empty_data(self):
        """Test handling of empty data."""
        mock_cursor = MagicMock()
        
        # Empty DataFrame should raise ValueError as per validation logic
        with self.assertRaises(ValueError) as context:
            insert_collection_events(
                cursor=mock_cursor,
                df=pd.DataFrame(),
                table_name='fish_collection_events',
                grouping_columns=['site_name', 'sample_id'],
                column_mapping={}
            )
        
        self.assertIn("DataFrame is empty", str(context.exception))

    # =============================================================================
    # DATA CLEANING TESTS
    # =============================================================================
    
    def test_remove_invalid_biological_values_default(self):
        """Test removal of invalid values with default parameters."""
        test_data = pd.DataFrame({
            'site_name': ['Site1', 'Site2', 'Site3'],
            'total_species_score': [3, -999, 5],
            'comparison_to_reference': [0.85, -99, 0.65],
            'other_score': [1, 2, -999]
        })
        
        result = remove_invalid_biological_values(test_data)
        
        # Should remove rows with -999 or -99 in score columns
        self.assertEqual(len(result), 1)  # Only Site1 should remain
        self.assertEqual(result.iloc[0]['site_name'], 'Site1')
    
    def test_remove_invalid_biological_values_custom_values(self):
        """Test removal with custom invalid values."""
        test_data = pd.DataFrame({
            'site_name': ['Site1', 'Site2', 'Site3'],
            'metric_score': [5, -777, 3],
            'other_score': [1, 2, -888]
        })
        
        result = remove_invalid_biological_values(
            test_data,
            invalid_values=[-777, -888]
        )
        
        # Should remove rows with custom invalid values
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['site_name'], 'Site1')
    
    def test_remove_invalid_biological_values_custom_columns(self):
        """Test removal with custom column specification."""
        test_data = pd.DataFrame({
            'site_name': ['Site1', 'Site2'],
            'metric1': [5, -999], 
            'metric2': [3, 1],
            'other_col': [-999, 2]  # Should be ignored
        })
        
        result = remove_invalid_biological_values(
            test_data, 
            score_columns=['metric1', 'metric2']
        )
        
        # Should only check specified columns
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['site_name'], 'Site1')

    def test_remove_invalid_biological_values_no_score_columns(self):
        """Test behavior when no score columns are found."""
        test_data = pd.DataFrame({
            'site_name': ['Site1', 'Site2'],
            'description': ['A', 'B']
        })
        
        result = remove_invalid_biological_values(test_data)
        
        # Should return original data when no score columns found
        self.assertEqual(len(result), 2)
    
    def test_convert_columns_to_numeric_default(self):
        """Test numeric conversion with default column detection."""
        test_data = pd.DataFrame({
            'total_species_score': ['3', '5', '1'],
            'year': ['2023', '2023', '2023'],
            'comparison_to_reference': ['0.85', '0.65', '0.45'],
            'sample_id': ['101', '102', '103'],
            'site_name': ['Site1', 'Site2', 'Site3']  # Should not convert
        })
        
        result = convert_columns_to_numeric(test_data)
        
        # Score and numeric columns should be converted
        numeric_cols = ['total_species_score', 'year', 'comparison_to_reference', 'sample_id']
        for col in numeric_cols:
            self.assertTrue(pd.api.types.is_numeric_dtype(result[col]))
        
        # String columns should remain string/object
        self.assertTrue(pd.api.types.is_string_dtype(result['site_name']) or 
                       pd.api.types.is_object_dtype(result['site_name']))
    
    def test_convert_columns_to_numeric_custom_columns(self):
        """Test numeric conversion with specified columns."""
        test_data = pd.DataFrame({
            'col1': ['1', '2', '3'],
            'col2': ['4', '5', '6'], 
            'col3': ['a', 'b', 'c']
        })
        
        result = convert_columns_to_numeric(test_data, columns=['col1', 'col2'])
        
        # Only specified columns should be converted
        self.assertTrue(pd.api.types.is_numeric_dtype(result['col1']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result['col2']))
        self.assertFalse(pd.api.types.is_numeric_dtype(result['col3']))

    def test_convert_columns_to_numeric_error_handling(self):
        """Test numeric conversion with error handling."""
        test_data = pd.DataFrame({
            'good_col': ['1', '2', '3'],
            'bad_col': ['not', 'a', 'number']
        })
        
        # Default 'coerce' should handle errors gracefully
        result = convert_columns_to_numeric(test_data, columns=['good_col', 'bad_col'])
        
        # Good column should convert
        self.assertTrue(pd.api.types.is_numeric_dtype(result['good_col']))
        
        # Bad column should have NaN values
        self.assertTrue(result['bad_col'].isna().all())

    # =============================================================================
    # EDGE CASES
    # =============================================================================
    
    def test_empty_dataframe_handling(self):
        """Test that all functions handle empty DataFrames gracefully."""
        empty_df = pd.DataFrame()
        
        # All functions should return empty DataFrame without error
        result1 = remove_invalid_biological_values(empty_df)
        self.assertTrue(result1.empty)
        
        result2 = convert_columns_to_numeric(empty_df)
        self.assertTrue(result2.empty)
    
    def test_null_values_handling(self):
        """Test handling of null values in biological data."""
        null_data = pd.DataFrame({
            'site_name': ['Site1', None, 'Site3'],
            'sample_id': [101, 102, None],
            'total_score': [21, None, 19]
        })
        
        # Should handle null values gracefully
        result = convert_columns_to_numeric(null_data)
        self.assertFalse(result.empty)
        
        # Null values should be preserved
        self.assertTrue(pd.isna(result.iloc[1]['total_score']))

    def test_duplicate_handling_in_collection_events(self):
        """Test handling of duplicate events in collection events insertion."""
        # Create data with duplicate site+sample combinations
        duplicate_data = pd.DataFrame({
            'site_name': ['Site1', 'Site1', 'Site2'],
            'sample_id': [101, 101, 102],  # Duplicate
            'collection_date_str': ['2023-01-01', '2023-01-01', '2023-01-02'],
            'year': [2023, 2023, 2023]
        })
        
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.lastrowid = 123
        
        result = insert_collection_events(
            cursor=mock_cursor,
            df=duplicate_data,
            table_name='fish_collection_events',
            grouping_columns=['site_name', 'sample_id'],
            column_mapping={
                'site_id': 'site_name',
                'sample_id': 'sample_id',
                'collection_date': 'collection_date_str',
                'year': 'year'
            }
        )
        
        # Should handle duplicates by using drop_duplicates
        self.assertEqual(len(result), 2)  # Only unique combinations

    def test_column_mapping_missing_columns(self):
        """Test collection events insertion when mapped columns are missing."""
        incomplete_data = pd.DataFrame({
            'site_name': ['Site1'],
            'sample_id': [101]
            # Missing 'year' column
        })
        
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.lastrowid = 123
        
        result = insert_collection_events(
            cursor=mock_cursor,
            df=incomplete_data,
            table_name='fish_collection_events',
            grouping_columns=['site_name', 'sample_id'],
            column_mapping={
                'site_id': 'site_name',
                'sample_id': 'sample_id',
                'year': 'year'  # This column doesn't exist
            }
        )
        
        # Should handle missing columns gracefully
        self.assertEqual(len(result), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2) 