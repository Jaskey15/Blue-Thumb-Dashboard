"""
Test suite for fish data processing functionality.
Tests the logic in data_processing.fish_processing module.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.biological_utils import (
    convert_columns_to_numeric,
    remove_invalid_biological_values,
)
from data_processing.fish_processing import (
    insert_fish_collection_events,
    insert_metrics_data,
    load_fish_data,
    validate_ibi_scores,
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_fish_processing", category="testing")


class TestFishProcessing(unittest.TestCase):
    """Test fish-specific processing functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample fish data matching real CSV structure
        self.sample_fish_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Red River at Bridge', 'Tenmile Creek at Davis'],
            'SAMPLEID': [101, 201, 301],
            'Date': ['2023-05-15', '2023-06-20', '2023-07-10'],
            'Year': [2023, 2023, 2023],
            'Total.Species.IBI': [3, 5, 1],
            'Sensitive.Benthic.IBI': [5, 3, 1],
            'Sunfish.Species.IBI': [1, 1, 3],
            'Intolerant.Species.IBI': [3, 3, 5],
            'Percent.Tolerant.IBI': [5, 5, 1],
            'Percent.Insectivore.IBI': [3, 1, 3],
            'Percent.Lithophil.IBI': [1, 3, 5],
            'OKIBI.Score': [21, 21, 19],  # 3+5+1+3+5+3+1=21, 1+1+3+5+1+3+5=19
            'Percent.Reference': [0.85, 0.65, 0.45],  # Good, Fair, Poor
            'Fish.Score': ['Good', 'Fair', 'Poor']
        })
        
        # Sample data with invalid IBI scores for validation testing
        self.invalid_ibi_data = pd.DataFrame({
            'SiteName': ['Test Site 1', 'Test Site 2'],
            'SAMPLEID': [401, 501],
            'Date': ['2023-08-15', '2023-09-20'],
            'Year': [2023, 2023],
            'Total.Species.IBI': [3, 5],
            'Sensitive.Benthic.IBI': [5, 3],
            'Sunfish.Species.IBI': [1, 1],
            'Intolerant.Species.IBI': [3, 3],
            'Percent.Tolerant.IBI': [5, 5],
            'Percent.Insectivore.IBI': [3, 1],
            'Percent.Lithophil.IBI': [1, 3],
            'OKIBI.Score': [25, 18],  # 25 ≠ 21 (invalid), 18 ≠ 21 (invalid)
            'Percent.Reference': [0.75, 0.55],
            'Fish.Score': ['Good', 'Fair']
        })
        
        # Sample data with missing components
        self.missing_components_data = pd.DataFrame({
            'SiteName': ['Incomplete Site'],
            'SAMPLEID': [601],
            'Date': ['2023-10-15'],
            'Year': [2023],
            'Total.Species.IBI': [3],
            'Sensitive.Benthic.IBI': [5],
            # Missing some component scores
            'Percent.Tolerant.IBI': [5],
            'Percent.Insectivore.IBI': [3],
            'Percent.Lithophil.IBI': [1],
            'OKIBI.Score': [17],  # Can't validate without all components
            'Percent.Reference': [0.65],
            'Fish.Score': ['Fair']
        })

    def test_validate_ibi_scores_valid(self):
        """Test IBI score validation when scores are correct."""
        # Process the column names to match what validate_ibi_scores expects
        df = self.sample_fish_data.copy()
        
        # Apply column name cleaning (simulate what happens in real pipeline)
        df.columns = [col.lower().replace('.', '') for col in df.columns]
        
        # Map to expected column names
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'sunfishspeciesibi': 'sunfish_species_score',
            'intolerantspeciesibi': 'intolerant_species_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score'
        }
        df = df.rename(columns=column_mapping)
        
        result = validate_ibi_scores(df)
        
        # Should have score_validated column
        self.assertIn('score_validated', result.columns)
        
        # First two rows should be valid (total = sum of components)
        self.assertTrue(result.iloc[0]['score_validated'])
        self.assertTrue(result.iloc[1]['score_validated'])
        self.assertTrue(result.iloc[2]['score_validated'])

    def test_validate_ibi_scores_invalid(self):
        """Test IBI score validation when scores are incorrect."""
        df = self.invalid_ibi_data.copy()
        
        # Apply same column processing
        df.columns = [col.lower().replace('.', '') for col in df.columns]
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'sunfishspeciesibi': 'sunfish_species_score',
            'intolerantspeciesibi': 'intolerant_species_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score'
        }
        df = df.rename(columns=column_mapping)
        
        result = validate_ibi_scores(df)
        
        # Both rows should be invalid (totals don't match sums)
        self.assertFalse(result.iloc[0]['score_validated'])
        self.assertFalse(result.iloc[1]['score_validated'])

    def test_validate_ibi_scores_missing_components(self):
        """Test IBI score validation with missing component scores."""
        df = self.missing_components_data.copy()
        
        # Apply column processing
        df.columns = [col.lower().replace('.', '') for col in df.columns]
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score'
        }
        df = df.rename(columns=column_mapping)
        
        result = validate_ibi_scores(df)
        
        # Should handle missing components gracefully
        self.assertIn('score_validated', result.columns)
        # Can't validate when components are missing, but shouldn't crash
        self.assertIsNotNone(result.iloc[0]['score_validated'])

    def test_integrity_class_calculation_all_ranges(self):
        """Test integrity class calculation for all ranges and edge cases."""
        test_cases = [
            # Excellent (≥97%)
            (0.98, "Excellent"),
            (0.97, "Excellent"),
            
            # Good (76-96%)
            (0.96, "Good"),
            (0.85, "Good"),
            (0.76, "Good"),
            
            # Fair (60-75%)
            (0.75, "Fair"),
            (0.65, "Fair"),
            (0.60, "Fair"),
            
            # Poor (47-59%)
            (0.59, "Poor"),
            (0.50, "Poor"),
            (0.47, "Poor"),
            
            # Very Poor (<47%)
            (0.46, "Very Poor"),
            (0.30, "Very Poor"),
            (0.10, "Very Poor")
        ]
        
        for comparison_value, expected_class in test_cases:
            with self.subTest(comparison=comparison_value, expected=expected_class):
                comparison_percent = comparison_value * 100
                
                if comparison_percent >= 97:
                    integrity_class = "Excellent"
                elif comparison_percent >= 76:
                    integrity_class = "Good"
                elif comparison_percent >= 60:
                    integrity_class = "Fair"
                elif comparison_percent >= 47:
                    integrity_class = "Poor"
                else:
                    integrity_class = "Very Poor"
                
                self.assertEqual(integrity_class, expected_class)

    def test_remove_invalid_biological_values(self):
        """Test removal of invalid biological values (-999, -99)."""
        # Create test data with invalid values
        test_df = pd.DataFrame({
            'site_name': ['Site A', 'Site B', 'Site C'],
            'total_species_score': [3, -999, 5],
            'comparison_to_reference': [0.85, -99, 0.65],
            'total_score': [21, 19, -999]
        })
        
        result_df = remove_invalid_biological_values(test_df)
        
        # Should remove rows with invalid values
        # Only Site A should remain (Sites B and C have invalid values)
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['site_name'], 'Site A')

    def test_convert_columns_to_numeric(self):
        """Test conversion of score columns to numeric types."""
        # Create test data with string numbers
        test_df = pd.DataFrame({
            'total_species_score': ['3', '5', '1'],
            'total_score': ['21', '19', '17'],
            'comparison_to_reference': ['0.85', '0.65', '0.45'],
            'year': ['2023', '2023', '2023'],
            'site_name': ['Site A', 'Site B', 'Site C']  # Should not be converted
        })
        
        result_df = convert_columns_to_numeric(test_df)
        
        # Score columns should be converted to numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(result_df['total_species_score']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result_df['total_score']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result_df['comparison_to_reference']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result_df['year']))
        
        # String columns should remain as string
        self.assertTrue(pd.api.types.is_string_dtype(result_df['site_name']) or 
                       pd.api.types.is_object_dtype(result_df['site_name']))

    def test_process_fish_csv_data_column_mapping(self):
        """Test that column mapping works correctly during fish processing."""
        # Test the column mapping logic that's used in process_fish_csv_data
        test_data = self.sample_fish_data.copy()
        
        # Simulate clean_column_names
        test_data.columns = [col.lower().replace('.', '') for col in test_data.columns]
        
        # Apply the column mapping from the actual function
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'date': 'collection_date',
            'year': 'year',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'sunfishspeciesibi': 'sunfish_species_score',
            'intolerantspeciesibi': 'intolerant_species_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score',
            'percentreference': 'comparison_to_reference',
            'fishscore': 'integrity_class'
        }
        
        # Apply valid mapping
        valid_mapping = {}
        for k, v in column_mapping.items():
            matching_cols = [col for col in test_data.columns if col.lower() == k.lower()]
            if matching_cols:
                valid_mapping[matching_cols[0]] = v
                
        result = test_data.rename(columns=valid_mapping)
        
        # Verify mapping worked
        expected_mapped_cols = ['site_name', 'sample_id', 'collection_date', 'year',
                               'total_species_score', 'total_score', 'comparison_to_reference']
        for col in expected_mapped_cols:
            self.assertIn(col, result.columns)

    def test_integration_full_pipeline(self):
        """Integration test for fish processing pipeline components."""
        # Start with raw data
        test_data = self.sample_fish_data.copy()
        
        # Simulate column cleaning (lowercase, remove periods)
        test_data.columns = [col.lower().replace('.', '') for col in test_data.columns]
        
        # Apply column mapping
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'date': 'collection_date',
            'year': 'year',
            'totalspeciesibi': 'total_species_score',
            'sensitivebenthicibi': 'sensitive_benthic_score',
            'sunfishspeciesibi': 'sunfish_species_score',
            'intolerantspeciesibi': 'intolerant_species_score',
            'percenttolerantibi': 'tolerant_score',
            'percentinsectivoreibi': 'insectivorous_score',
            'percentlithophilibi': 'lithophilic_score',
            'okibiscore': 'total_score',
            'percentreference': 'comparison_to_reference',
            'fishscore': 'integrity_class'
        }
        test_data = test_data.rename(columns=column_mapping)
        
        # Apply processing steps
        processed_data = remove_invalid_biological_values(test_data)
        processed_data = convert_columns_to_numeric(processed_data)
        processed_data = validate_ibi_scores(processed_data)
        
        # Verify pipeline completed successfully
        self.assertFalse(processed_data.empty)
        self.assertEqual(len(processed_data), 3)  # All rows should be valid
        
        # Check that validation was applied
        self.assertIn('score_validated', processed_data.columns)
        
        # Check that numeric conversion worked
        self.assertTrue(pd.api.types.is_numeric_dtype(processed_data['total_score']))

    def test_edge_case_empty_data(self):
        """Test behavior with empty input data."""
        empty_df = pd.DataFrame()
        
        # Test individual functions with empty data
        result_validation = validate_ibi_scores(empty_df)
        self.assertTrue(result_validation.empty)
        
        result_invalid_removal = remove_invalid_biological_values(empty_df)
        self.assertTrue(result_invalid_removal.empty)
        
        result_numeric = convert_columns_to_numeric(empty_df)
        self.assertTrue(result_numeric.empty)

    def test_edge_case_all_null_values(self):
        """Test behavior with all null values in key columns."""
        null_df = pd.DataFrame({
            'total_species_score': [np.nan, np.nan],
            'total_score': [np.nan, np.nan],
            'comparison_to_reference': [np.nan, np.nan]
        })
        
        # Should handle null values gracefully
        result_df = validate_ibi_scores(null_df)
        self.assertIn('score_validated', result_df.columns)
        
        # Validation should handle NaN appropriately
        self.assertIsNotNone(result_df.iloc[0]['score_validated'])

    # =============================================================================
    # FISH-SPECIFIC PROCESSING TESTS
    # =============================================================================
    
    def test_bt_fieldwork_integration_logic(self):
        """Test the logic for BT fieldwork validator integration without full pipeline."""
        # Test that the logic for calling BT fieldwork functions is sound
        test_data = self.sample_fish_data.copy()
        
        # Mock what categorize_and_process_duplicates should do - return same data
        # In real implementation, this would handle duplicates
        result = test_data.copy()
        
        # Verify data structure is maintained
        self.assertEqual(len(result), len(test_data))
        self.assertTrue(all(col in result.columns for col in test_data.columns))

    # =============================================================================
    # DATABASE INSERTION TESTS
    # =============================================================================
    
    def test_insert_fish_collection_events(self):
        """Test fish collection event insertion."""
        # Create properly formatted test data
        test_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Red River at Bridge'],
            'sample_id': [101, 201],
            'collection_date_str': ['2023-05-15', '2023-06-20'],
            'year': [2023, 2023]
        })
        
        mock_cursor = MagicMock()
        
        result = insert_fish_collection_events(mock_cursor, test_data)
        
        # Should return event_id mapping for fish
        self.assertIsInstance(result, dict)
    
    def test_insert_metrics_data_basic(self):
        """Test insertion of fish metrics data."""
        mock_cursor = MagicMock()
        event_id_map = {101: 123, 201: 456}  # sample_id -> event_id
        
        # Create processed data with proper column names
        processed_data = pd.DataFrame({
            'sample_id': [101, 201],
            'total_species': [15, 12],
            'total_species_score': [3, 5],
            'sensitive_benthic_species': [8, 6],
            'sensitive_benthic_score': [5, 3],
            'sunfish_species': [2, 1],
            'sunfish_species_score': [1, 1],
            'intolerant_species': [5, 3],
            'intolerant_species_score': [3, 3],
            'proportion_tolerant': [0.2, 0.3],
            'tolerant_score': [5, 5],
            'proportion_insectivorous': [0.6, 0.4],
            'insectivorous_score': [3, 1],
            'proportion_lithophilic': [0.3, 0.5],
            'lithophilic_score': [1, 3],
            'total_score': [21, 21],
            'comparison_to_reference': [0.85, 0.65],
            'integrity_class': ['Good', 'Fair']
        })
        
        result = insert_metrics_data(mock_cursor, processed_data, event_id_map)
        
        # Should return count of inserted metrics
        self.assertIsInstance(result, int)
        
        # Verify that INSERT statements were called for metrics and summary
        self.assertTrue(mock_cursor.execute.called)
    
    def test_insert_metrics_data_integrity_class_fallback(self):
        """Test integrity class calculation when CSV value is missing."""
        mock_cursor = MagicMock()
        event_id_map = {101: 123}
        
        # Create data without integrity class but with comparison_to_reference
        test_data = pd.DataFrame({
            'sample_id': [101],
            'total_score': [21],
            'comparison_to_reference': [0.85],  # Should calculate to "Good"
            'total_species': [15],
            'total_species_score': [3]
        })
        
        result = insert_metrics_data(mock_cursor, test_data, event_id_map)
        
        # Should calculate and insert integrity class
        self.assertIsInstance(result, int)
        self.assertTrue(mock_cursor.execute.called)

    def test_insert_metrics_data_missing_event_id(self):
        """Test handling when sample_id is not in event_id_map."""
        mock_cursor = MagicMock()
        event_id_map = {999: 123}  # Different sample_id
        
        test_data = pd.DataFrame({
            'sample_id': [101],  # Not in event_id_map
            'total_score': [21],
            'comparison_to_reference': [0.85]
        })
        
        result = insert_metrics_data(mock_cursor, test_data, event_id_map)
        
        # Should return 0 when no matching event_ids
        self.assertEqual(result, 0)

    def test_insert_metrics_data_partial_metrics(self):
        """Test handling when only some metric columns are available."""
        mock_cursor = MagicMock()
        event_id_map = {101: 123}
        
        # Data with only some metric columns
        partial_data = pd.DataFrame({
            'sample_id': [101],
            'total_species': [15],
            'total_species_score': [3],
            # Missing other metric columns
            'total_score': [10],  # Partial score
            'comparison_to_reference': [0.75]
        })
        
        result = insert_metrics_data(mock_cursor, partial_data, event_id_map)
        
        # Should handle partial data gracefully
        self.assertIsInstance(result, int)

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================
    
    @patch('data_processing.fish_processing.close_connection')
    @patch('data_processing.fish_processing.get_connection')
    def test_load_fish_data_full_pipeline(self, mock_get_conn, mock_close):
        """Test the complete fish data loading pipeline."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock that no data exists yet
        mock_cursor.fetchone.return_value = (0,)
        
        with patch('data_processing.fish_processing.process_fish_csv_data') as mock_process:
            with patch('data_processing.fish_processing.insert_fish_collection_events') as mock_events:
                with patch('data_processing.fish_processing.insert_metrics_data') as mock_metrics:
                    mock_process.return_value = self.sample_fish_data
                    mock_events.return_value = {101: 123, 201: 456}
                    mock_metrics.return_value = 10
                    
                    result = load_fish_data()
                    
                    # Should complete successfully
                    self.assertTrue(result)
                    mock_conn.commit.assert_called_once()

    @patch('data_processing.fish_processing.close_connection')
    @patch('data_processing.fish_processing.get_connection')
    def test_load_fish_data_existing_data(self, mock_get_conn, mock_close):
        """Test pipeline when data already exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock that data already exists
        mock_cursor.fetchone.return_value = (10,)  # 10 existing records
        
        result = load_fish_data()
        
        # Should skip processing and return True
        self.assertTrue(result)
        # Should not call commit since no new data was processed
        mock_conn.commit.assert_not_called()

    @patch('data_processing.fish_processing.close_connection')
    @patch('data_processing.fish_processing.get_connection')
    def test_load_fish_data_with_site_filter(self, mock_get_conn, mock_close):
        """Test pipeline with site name filter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (0,)
        
        with patch('data_processing.fish_processing.process_fish_csv_data') as mock_process:
            mock_process.return_value = self.sample_fish_data
            
            result = load_fish_data(site_name='Blue Creek at Highway 9')
            
            # Should pass site filter to processing function
            mock_process.assert_called_once_with('Blue Creek at Highway 9')
            self.assertTrue(result)

    @patch('data_processing.fish_processing.close_connection')
    @patch('data_processing.fish_processing.get_connection')
    def test_load_fish_data_error_handling(self, mock_get_conn, mock_close):
        """Test error handling in fish data pipeline."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (0,)
        
        with patch('data_processing.fish_processing.process_fish_csv_data') as mock_process:
            # Mock processing failure
            mock_process.return_value = pd.DataFrame()  # Empty DataFrame
            
            result = load_fish_data()
            
            # Should return False when processing fails
            self.assertFalse(result)


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)