"""
Test suite for habitat processing functionality.
Tests the logic in data_processing.habitat_processing module.
"""

import unittest
import pandas as pd
import numpy as np
import os
import sys
from unittest.mock import patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.habitat_processing import (
    process_habitat_csv_data,
    resolve_habitat_duplicates,
    calculate_habitat_grade
)
from data_processing.biological_utils import (
    convert_columns_to_numeric
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_habitat_processing", category="testing")


class TestHabitatProcessing(unittest.TestCase):
    """Test habitat assessment processing functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample habitat data matching real CSV structure
        self.sample_habitat_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Red River at Bridge', 'Test Site'],
            'SAMPLEID': [101, 201, 301],
            'Date': ['2023-05-15', '2023-06-20', '2023-07-10'],
            'Instream.Habitat': [8.5, 7.2, 5.8],
            'Pool.Bottom.Substrate': [7.2, 6.8, 4.5],
            'Pool.Variability': [6.8, 7.5, 5.2],
            'Canopy.Cover': [9.1, 8.0, 6.1],
            'Presence.of.rocky.runs.and.riffles': [8.0, 7.8, 5.9],
            'Flow...low.flow': [7.5, 8.2, 6.0],
            'Channel.Alteration': [8.8, 7.9, 5.5],
            'Channel.Sinuosity': [7.9, 8.1, 5.8],
            'Bank.Stability': [8.3, 7.6, 5.7],
            'Bank.Vegetation.Stability': [8.7, 8.3, 6.2],
            'Streamside.Cover': [9.0, 8.5, 6.0],
            'Total': [89.8, 85.9, 64.7],  # B, B, D grades respectively
            'Habitat.Grade': ['B', 'B', 'D']
        })
        
        # Test data with duplicates for averaging tests
        self.duplicate_habitat_data = pd.DataFrame({
            'SiteName': ['Same Site', 'Same Site', 'Another Site'],
            'SAMPLEID': [401, 402, 501],
            'Date': ['2023-08-15', '2023-08-15', '2023-09-20'],  # First two are duplicates
            'Instream.Habitat': [8.0, 9.0, 7.5],               # Should average to 8.5
            'Pool.Bottom.Substrate': [7.0, 8.0, 6.5],          # Should average to 7.5
            'Pool.Variability': [6.0, 7.0, 5.0],               # Should average to 6.5
            'Canopy.Cover': [8.0, 9.0, 6.0],                   # Should average to 8.5
            'Presence.of.rocky.runs.and.riffles': [7.0, 8.0, 6.0],  # Should average to 7.5
            'Flow...low.flow': [8.0, 9.0, 6.0],                # Should average to 8.5
            'Channel.Alteration': [8.0, 9.0, 7.0],             # Should average to 8.5
            'Channel.Sinuosity': [7.0, 8.0, 6.0],              # Should average to 7.5
            'Bank.Stability': [8.0, 9.0, 7.0],                 # Should average to 8.5
            'Bank.Vegetation.Stability': [8.0, 9.0, 6.0],      # Should average to 8.5
            'Streamside.Cover': [8.0, 9.0, 6.0],               # Should average to 8.5
            'Total': [85, 95, 75],                              # Should average to 90 (grade A)
            'Habitat.Grade': ['B', 'A', 'C']
        })

    def calculate_habitat_grade_helper(self, total_score):
        """Helper function to replicate habitat grade calculation logic."""
        if pd.isna(total_score):
            return "Unknown"
        
        if total_score > 90:
            return "A"
        elif total_score >= 80:
            return "B"
        elif total_score >= 70:
            return "C"
        elif total_score >= 60:
            return "D"
        else:
            return "F"

    def test_calculate_habitat_grade_all_ranges(self):
        """Test habitat grade calculation for all grade ranges and edge cases."""
        # Test each grade with representative and boundary values
        test_cases = [
            # (score, expected_grade)
            (100, "A"), (95, "A"), (90, "A"),           # A grade: ≥90
            (89, "B"), (85, "B"), (80, "B"),            # B grade: 80-89
            (79, "C"), (75, "C"), (70, "C"),            # C grade: 70-79
            (69, "D"), (65, "D"), (60, "D"),            # D grade: 60-69
            (59, "F"), (30, "F"), (0, "F"),             # F grade: <60
        ]
        
        for score, expected_grade in test_cases:
            with self.subTest(score=score):
                self.assertEqual(calculate_habitat_grade(score), expected_grade)
        
        # Test edge cases
        self.assertEqual(calculate_habitat_grade(np.nan), "Unknown")
        self.assertEqual(calculate_habitat_grade(None), "Unknown")

    def test_resolve_habitat_duplicates_no_duplicates(self):
        """Test duplicate resolution when no duplicates exist."""
        # Use data with unique site/date combinations
        result_df = resolve_habitat_duplicates(self.sample_habitat_data)
        
        # Should return same data unchanged when no duplicates
        self.assertEqual(len(result_df), len(self.sample_habitat_data))
        pd.testing.assert_frame_equal(result_df.reset_index(drop=True), self.sample_habitat_data.reset_index(drop=True))

    def test_resolve_habitat_duplicates_with_duplicates(self):
        """Test duplicate resolution averaging logic."""
        # First, we need to map column names to match what resolve_habitat_duplicates expects
        mapped_data = self.duplicate_habitat_data.copy()
        
        # Apply the same column mapping that would happen in real processing
        column_mapping = {
            'SiteName': 'site_name',
            'SAMPLEID': 'sample_id',
            'Date': 'assessment_date',
            'Instream.Habitat': 'instream_cover',
            'Pool.Bottom.Substrate': 'pool_bottom_substrate',
            'Pool.Variability': 'pool_variability',
            'Canopy.Cover': 'canopy_cover',
            'Presence.of.rocky.runs.and.riffles': 'rocky_runs_riffles',
            'Flow...low.flow': 'flow',
            'Channel.Alteration': 'channel_alteration',
            'Channel.Sinuosity': 'channel_sinuosity',
            'Bank.Stability': 'bank_stability',
            'Bank.Vegetation.Stability': 'bank_vegetation_stability',
            'Streamside.Cover': 'streamside_cover',
            'Total': 'total_score',
            'Habitat.Grade': 'habitat_grade'
        }
        mapped_data = mapped_data.rename(columns=column_mapping)
        
        result_df = resolve_habitat_duplicates(mapped_data)
        
        # Should reduce from 3 records to 2 (duplicates averaged)
        self.assertEqual(len(result_df), 2)
        
        # Find the averaged record for 'Same Site'
        same_site_record = result_df[result_df['site_name'] == 'Same Site']
        self.assertEqual(len(same_site_record), 1)
        
        # Check averaged values (8.0 and 9.0 should average to 8.5)
        averaged_record = same_site_record.iloc[0]
        self.assertAlmostEqual(averaged_record['instream_cover'], 8.5, places=1)
        self.assertAlmostEqual(averaged_record['pool_bottom_substrate'], 7.5, places=1)

    def test_resolve_habitat_duplicates_averaging_logic(self):
        """Test specific averaging calculations and rounding rules."""
        # Create data that tests rounding rules
        test_data = pd.DataFrame({
            'site_name': ['Test Site', 'Test Site'],
            'assessment_date': ['2023-08-15', '2023-08-15'],
            'instream_cover': [8.33, 8.67],         # Should average to 8.5
            'pool_bottom_substrate': [7.25, 7.74], # Should average to 7.5
            'total_score': [85.4, 94.6],           # Should average to 90 (rounded to integer)
            'habitat_grade': ['B', 'A']
        })
        
        result_df = resolve_habitat_duplicates(test_data)
        
        # Should have 1 record after averaging
        self.assertEqual(len(result_df), 1)
        
        averaged_record = result_df.iloc[0]
        
        # Test individual metric rounding (to 1 decimal place)
        self.assertAlmostEqual(averaged_record['instream_cover'], 8.5, places=1)
        self.assertAlmostEqual(averaged_record['pool_bottom_substrate'], 7.5, places=1)
        
        # Test total score rounding (to nearest integer)
        self.assertEqual(averaged_record['total_score'], 90)
        
        # Test that grade was recalculated (90 points = grade A)
        self.assertEqual(averaged_record['habitat_grade'], 'A')

    @patch('data_processing.habitat_processing.save_processed_data')
    @patch('data_processing.habitat_processing.clean_column_names')
    @patch('data_processing.habitat_processing.load_csv_data')
    def test_process_habitat_csv_data_basic(self, mock_load_csv, mock_clean_columns, mock_save_data):
        """Test CSV loading and column mapping."""
        # Mock the CSV loading to return our test data
        mock_load_csv.return_value = self.sample_habitat_data
        
        # Mock clean_column_names to simulate the column cleaning process
        cleaned_data = self.sample_habitat_data.copy()
        cleaned_data.columns = [col.lower().replace('.', '').replace(' ', '').replace('_', '') for col in cleaned_data.columns]
        mock_clean_columns.return_value = cleaned_data
        
        # Mock save_processed_data to prevent writing to actual files
        mock_save_data.return_value = True
        
        result_df = process_habitat_csv_data()
        
        # Verify mocks were called correctly
        mock_load_csv.assert_called_once_with('habitat')
        mock_clean_columns.assert_called_once()
        mock_save_data.assert_called_once()
        
        # Should have processed the data
        self.assertFalse(result_df.empty)
        self.assertEqual(len(result_df), 3)
        
        # Check that columns were mapped correctly
        expected_columns = ['site_name', 'sample_id', 'assessment_date', 'instream_cover',
                          'pool_bottom_substrate', 'total_score', 'habitat_grade']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)

    @patch('data_processing.habitat_processing.save_processed_data')
    @patch('data_processing.habitat_processing.clean_column_names')
    @patch('data_processing.habitat_processing.load_csv_data')
    def test_process_habitat_csv_data_site_filter(self, mock_load_csv, mock_clean_columns, mock_save_data):
        """Test CSV processing with site name filter."""
        # Mock the CSV loading
        mock_load_csv.return_value = self.sample_habitat_data
        
        # Mock clean_column_names
        cleaned_data = self.sample_habitat_data.copy()
        cleaned_data.columns = [col.lower().replace('.', '').replace(' ', '').replace('_', '') for col in cleaned_data.columns]
        mock_clean_columns.return_value = cleaned_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df = process_habitat_csv_data(site_name='Blue Creek at Highway 9')
        
        # Verify the site filter was applied
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['site_name'], 'Blue Creek at Highway 9')

    def test_convert_columns_to_numeric_habitat(self):
        """Test numeric conversion for habitat scores."""
        # Create test data with string values that should be numeric
        test_df = pd.DataFrame({
            'total_score': ['89.8', '85.9', '64.7'],
            'instream_cover': ['8.5', '7.2', '5.8'],
            'sample_id': ['101', '201', '301'],
            'site_name': ['Site A', 'Site B', 'Site C']  # Should not be converted
        })
        
        # Define columns that should be converted (similar to habitat processing)
        numeric_columns = ['total_score', 'instream_cover', 'sample_id']
        
        result_df = convert_columns_to_numeric(test_df, columns=numeric_columns)
        
        # Check that numeric columns were converted
        self.assertEqual(result_df['total_score'].dtype, 'float64')
        self.assertEqual(result_df['instream_cover'].dtype, 'float64')
        self.assertEqual(result_df['sample_id'].dtype, 'int64')
        
        # Check that string column remained unchanged
        self.assertEqual(result_df['site_name'].dtype, 'object')

    @patch('data_processing.habitat_processing.save_processed_data')
    @patch('data_processing.habitat_processing.clean_column_names')
    @patch('data_processing.habitat_processing.load_csv_data')
    def test_integration_full_pipeline(self, mock_load_csv, mock_clean_columns, mock_save_data):
        """Integration test for full habitat processing pipeline."""
        # Use duplicate data to test end-to-end processing including duplicate resolution
        mock_load_csv.return_value = self.duplicate_habitat_data
        
        # Mock clean_column_names to simulate column cleaning
        cleaned_data = self.duplicate_habitat_data.copy()
        cleaned_data.columns = [col.lower().replace('.', '').replace(' ', '').replace('_', '') for col in cleaned_data.columns]
        mock_clean_columns.return_value = cleaned_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df = process_habitat_csv_data()
        
        # Verify mocks were called
        mock_load_csv.assert_called_once_with('habitat')
        mock_save_data.assert_called_once()
        
        # Should have processed and resolved duplicates
        self.assertEqual(len(result_df), 2)  # 3 original -> 2 after duplicate resolution
        
        # Should have all expected columns after processing
        expected_columns = ['site_name', 'assessment_date', 'total_score', 'habitat_grade']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)
        
        # Check that duplicate resolution occurred
        same_site_records = result_df[result_df['site_name'] == 'Same Site']
        self.assertEqual(len(same_site_records), 1)  # Duplicates should be averaged

    def test_edge_case_empty_data(self):
        """Test behavior with empty input data."""
        empty_df = pd.DataFrame()
        
        # Test individual functions with empty data
        result_duplicates = resolve_habitat_duplicates(empty_df)
        self.assertTrue(result_duplicates.empty)
        
        result_numeric = convert_columns_to_numeric(empty_df)
        self.assertTrue(result_numeric.empty)

    @patch('data_processing.habitat_processing.save_processed_data')
    @patch('data_processing.habitat_processing.clean_column_names')
    @patch('data_processing.habitat_processing.load_csv_data')
    def test_edge_case_missing_columns(self, mock_load_csv, mock_clean_columns, mock_save_data):
        """Test behavior when required columns are missing."""
        # Create data missing some habitat metrics
        incomplete_data = pd.DataFrame({
            'SiteName': ['Test Site'],
            'Date': ['2023-05-15'],
            'Total': [75],
            'Habitat.Grade': ['C']
            # Missing individual habitat metric columns
        })
        
        mock_load_csv.return_value = incomplete_data
        
        # Mock clean_column_names
        cleaned_data = incomplete_data.copy()
        cleaned_data.columns = [col.lower().replace('.', '').replace(' ', '').replace('_', '') for col in cleaned_data.columns]
        mock_clean_columns.return_value = cleaned_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df = process_habitat_csv_data()
        
        # Should still process but may have fewer columns
        self.assertFalse(result_df.empty)

    @patch('data_processing.habitat_processing.save_processed_data')
    @patch('data_processing.habitat_processing.clean_column_names') 
    @patch('data_processing.habitat_processing.load_csv_data')
    def test_habitat_metrics_mapping(self, mock_load_csv, mock_clean_columns, mock_save_data):
        """Test that all 11 individual habitat metrics are correctly identified."""
        # Define the expected 11 habitat metrics after column mapping
        expected_metrics = [
            'instream_cover',
            'pool_bottom_substrate', 
            'pool_variability',
            'canopy_cover',
            'rocky_runs_riffles',
            'flow',
            'channel_alteration',
            'channel_sinuosity',
            'bank_stability',
            'bank_vegetation_stability',
            'streamside_cover'
        ]
        
        mock_load_csv.return_value = self.sample_habitat_data
        
        # Mock clean_column_names
        cleaned_data = self.sample_habitat_data.copy()
        cleaned_data.columns = [col.lower().replace('.', '').replace(' ', '').replace('_', '') for col in cleaned_data.columns]
        mock_clean_columns.return_value = cleaned_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df = process_habitat_csv_data()
        
        # Check that all expected habitat metrics are present in the result
        for metric in expected_metrics:
            self.assertIn(metric, result_df.columns, f"Missing habitat metric: {metric}")

    def test_duplicate_resolution_with_nulls(self):
        """Test duplicate resolution when some values are null."""
        # Create test data with null values
        test_data = pd.DataFrame({
            'site_name': ['Test Site', 'Test Site'],
            'assessment_date': ['2023-08-15', '2023-08-15'],
            'instream_cover': [8.0, np.nan],        # One null value
            'pool_bottom_substrate': [7.0, 8.0],   # Both valid
            'total_score': [85, 90],
            'habitat_grade': ['B', 'A']
        })
        
        result_df = resolve_habitat_duplicates(test_data)
        
        # Should have 1 record after averaging
        self.assertEqual(len(result_df), 1)
        
        averaged_record = result_df.iloc[0]
        
        # Should average only non-null values
        self.assertAlmostEqual(averaged_record['instream_cover'], 8.0, places=1)  # Only non-null value
        self.assertAlmostEqual(averaged_record['pool_bottom_substrate'], 7.5, places=1)  # Average of 7.0 and 8.0

if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)