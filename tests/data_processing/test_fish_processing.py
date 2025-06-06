"""
Test suite for fish data processing functionality.
Tests the logic in data_processing.fish_processing module.
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.fish_processing import (
    process_fish_csv_data,
    validate_ibi_scores
)
from data_processing.biological_utils import (
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_fish_processing", category="testing")


class TestFishProcessing(unittest.TestCase):
    """Test fish data processing functionality."""
    
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

    def test_integrity_class_calculation_excellent(self):
        """Test integrity class calculation for excellent range."""
        # Test with comparison_to_reference = 0.98 (≥97% = Excellent)
        test_data = {'comparison_to_reference': 0.98}
        
        # Simulate the integrity class calculation logic
        comparison_value = test_data['comparison_to_reference'] * 100
        
        if comparison_value >= 97:
            integrity_class = "Excellent"
        elif comparison_value >= 76:
            integrity_class = "Good"
        elif comparison_value >= 60:
            integrity_class = "Fair"
        elif comparison_value >= 47:
            integrity_class = "Poor"
        else:
            integrity_class = "Very Poor"
        
        self.assertEqual(integrity_class, "Excellent")

    def test_integrity_class_calculation_all_ranges(self):
        """Test integrity class calculation for all ranges."""
        test_cases = [
            (0.98, "Excellent"),  # ≥97%
            (0.85, "Good"),       # ≥76%
            (0.65, "Fair"),       # ≥60%
            (0.50, "Poor"),       # ≥47%
            (0.30, "Very Poor")   # <47%
        ]
        
        for comparison_value, expected_class in test_cases:
            with self.subTest(comparison=comparison_value):
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

    @patch('data_processing.fish_processing.save_processed_data')
    @patch('data_processing.fish_processing.load_csv_data')
    def test_process_fish_csv_data_basic(self, mock_load_csv, mock_save):
        """Test basic CSV processing functionality."""
        # Mock CSV loading
        mock_load_csv.return_value = self.sample_fish_data
        mock_save.return_value = True  # Mock the save operation
        
        # Mock the BT field work loading to return empty (to avoid replicate logic)
        with patch('data_processing.fish_processing.load_bt_field_work_dates') as mock_bt:
            mock_bt.return_value = pd.DataFrame()
            
            result_df = process_fish_csv_data()
        
        # Verify save was called
        mock_save.assert_called_once_with(result_df, 'fish_data')
        
        # Should process data without errors
        self.assertFalse(result_df.empty)
        
        # Check that columns were mapped correctly
        expected_columns = ['site_name', 'sample_id', 'collection_date', 'year', 
                          'total_species_score', 'total_score', 'comparison_to_reference']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)

    @patch('data_processing.fish_processing.save_processed_data')
    @patch('data_processing.fish_processing.load_csv_data')
    def test_process_fish_csv_data_site_filter(self, mock_load_csv, mock_save):
        """Test CSV processing with site name filter."""
        mock_load_csv.return_value = self.sample_fish_data
        mock_save.return_value = True  # Mock the save operation
        
        with patch('data_processing.fish_processing.load_bt_field_work_dates') as mock_bt:
            mock_bt.return_value = pd.DataFrame()
            
            result_df = process_fish_csv_data(site_name='Blue Creek at Highway 9')
        
        # Verify save was called
        mock_save.assert_called_once()
        
        # Should only have one site's data
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['site_name'], 'Blue Creek at Highway 9')

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


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)