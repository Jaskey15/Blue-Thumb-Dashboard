"""
Test suite for chemical data processing functionality.
Tests the logic in data_processing.chemical_processing module.
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

from data_processing.chemical_processing import (
    process_chemical_data_from_csv
)
from data_processing.chemical_utils import (
    validate_chemical_data,
    determine_status,
    apply_bdl_conversions,
    calculate_soluble_nitrogen,
    convert_bdl_value
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_chemical_processing", category="testing")


class TestChemicalProcessing(unittest.TestCase):
    """Test chemical data processing functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample chemical data for testing (matching your real CSV structure)
        self.sample_chemical_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Tenmile Creek at Davis', 'Red River at Bridge'],
            'Date': ['2023-05-15', '2023-06-20', '2023-07-10'],
            'DO.Saturation': [95.5, 110.2, 88.0],
            'pH.Final.1': [7.2, 8.1, 6.8],
            'Nitrate.Final.1': [0.5, 0.0, 1.2],  # Zero for BDL testing
            'Nitrite.Final.1': [0.0, 0.05, 0.1],  # Zero for BDL testing
            'Ammonia.Final.1': [0.1, 0.0, 0.3],  # Zero for BDL testing
            'OP.Final.1': [0.02, 0.08, 0.15],
            'Chloride.Final.1': [25.0, 45.0, 280.0]  # Last value exceeds threshold
        })
        
        # Sample reference values for testing
        self.sample_reference_values = {
            'do_percent': {
                'normal min': 80, 
                'normal max': 130, 
                'caution min': 50,
                'caution max': 150
            },
            'pH': {
                'normal min': 6.5, 
                'normal max': 9.0
            },
            'soluble_nitrogen': {
                'normal': 0.8, 
                'caution': 1.5
            },
            'Phosphorus': {
                'normal': 0.05, 
                'caution': 0.1
            },
            'Chloride': {
                'poor': 250
            }
        }

    def test_convert_bdl_value_basic(self):
        """Test basic BDL value conversion."""
        # Test zero conversion
        self.assertEqual(convert_bdl_value(0, 0.3), 0.3)
        
        # Test non-zero value unchanged
        self.assertEqual(convert_bdl_value(1.5, 0.3), 1.5)
        
        # Test NaN handling
        self.assertTrue(np.isnan(convert_bdl_value(np.nan, 0.3)))
        
        # Test string zero conversion
        self.assertEqual(convert_bdl_value("0", 0.3), 0.3)
        
        # Test invalid string handling
        self.assertTrue(np.isnan(convert_bdl_value("invalid", 0.3)))

    def test_apply_bdl_conversions(self):
        """Test applying BDL conversions to DataFrame columns."""
        # Create test data with zeros
        test_df = pd.DataFrame({
            'Nitrate': [0.5, 0.0, 1.2],
            'Nitrite': [0.0, 0.05, 0.1],
            'Ammonia': [0.1, 0.0, 0.3],
            'Other_Param': [1.0, 2.0, 3.0]  # Should not be affected
        })
        
        result_df = apply_bdl_conversions(test_df)
        
        # Check that zeros were replaced with BDL values
        self.assertEqual(result_df.loc[1, 'Nitrate'], 0.3)  # BDL_VALUES['Nitrate']
        self.assertEqual(result_df.loc[0, 'Nitrite'], 0.03)  # BDL_VALUES['Nitrite']
        self.assertEqual(result_df.loc[1, 'Ammonia'], 0.03)  # BDL_VALUES['Ammonia']
        
        # Check that non-zero values were unchanged
        self.assertEqual(result_df.loc[0, 'Nitrate'], 0.5)
        self.assertEqual(result_df.loc[1, 'Nitrite'], 0.05)
        
        # Check that non-BDL columns were unchanged
        self.assertEqual(result_df.loc[0, 'Other_Param'], 1.0)

    def test_calculate_soluble_nitrogen(self):
        """Test calculation of total soluble nitrogen."""
        # Create test data with nitrogen components
        test_df = pd.DataFrame({
            'Nitrate': [0.5, 1.0, 0.0],
            'Nitrite': [0.1, 0.05, 0.0],
            'Ammonia': [0.2, 0.15, 0.0]
        })
        
        result_df = calculate_soluble_nitrogen(test_df)
        
        # Check that soluble_nitrogen was calculated correctly
        self.assertIn('soluble_nitrogen', result_df.columns)
        
        # First row: 0.5 + 0.1 + 0.2 = 0.8
        self.assertAlmostEqual(result_df.loc[0, 'soluble_nitrogen'], 0.8, places=3)
        
        # Second row: 1.0 + 0.05 + 0.15 = 1.2
        self.assertAlmostEqual(result_df.loc[1, 'soluble_nitrogen'], 1.2, places=3)
        
        # Third row: All zeros should use BDL values: 0.3 + 0.03 + 0.03 = 0.36
        self.assertAlmostEqual(result_df.loc[2, 'soluble_nitrogen'], 0.36, places=3)

    def test_calculate_soluble_nitrogen_missing_columns(self):
        """Test soluble nitrogen calculation with missing columns."""
        # Create test data missing some nitrogen columns
        test_df = pd.DataFrame({
            'Nitrate': [0.5, 1.0],
            'Nitrite': [0.1, 0.05]
            # Missing Ammonia column
        })
        
        result_df = calculate_soluble_nitrogen(test_df)
        
        # Should return original DataFrame unchanged when columns are missing
        self.assertNotIn('soluble_nitrogen', result_df.columns)

    def test_determine_status_do_percent(self):
        """Test status determination for dissolved oxygen."""
        ref_values = self.sample_reference_values
        
        # Test normal range
        self.assertEqual(determine_status('do_percent', 100, ref_values), "Normal")
        self.assertEqual(determine_status('do_percent', 80, ref_values), "Normal")
        self.assertEqual(determine_status('do_percent', 130, ref_values), "Normal")
        
        # Test caution range
        self.assertEqual(determine_status('do_percent', 60, ref_values), "Caution")
        self.assertEqual(determine_status('do_percent', 140, ref_values), "Caution")
        
        # Test poor range
        self.assertEqual(determine_status('do_percent', 40, ref_values), "Poor")
        self.assertEqual(determine_status('do_percent', 160, ref_values), "Poor")
        
        # Test NaN
        self.assertEqual(determine_status('do_percent', np.nan, ref_values), "Unknown")

    def test_determine_status_ph(self):
        """Test status determination for pH."""
        ref_values = self.sample_reference_values
        
        # Test normal range
        self.assertEqual(determine_status('pH', 7.0, ref_values), "Normal")
        self.assertEqual(determine_status('pH', 6.5, ref_values), "Normal")
        self.assertEqual(determine_status('pH', 9.0, ref_values), "Normal")
        
        # Test outside normal range
        self.assertEqual(determine_status('pH', 6.0, ref_values), "Below Normal")
        self.assertEqual(determine_status('pH', 10.0, ref_values), "Above Normal")

    def test_determine_status_nitrogen(self):
        """Test status determination for nitrogen."""
        ref_values = self.sample_reference_values
        
        # Test normal range
        self.assertEqual(determine_status('soluble_nitrogen', 0.5, ref_values), "Normal")
        
        # Test caution range
        self.assertEqual(determine_status('soluble_nitrogen', 1.0, ref_values), "Caution")
        
        # Test poor range
        self.assertEqual(determine_status('soluble_nitrogen', 2.0, ref_values), "Poor")

    def test_determine_status_chloride(self):
        """Test status determination for chloride."""
        ref_values = self.sample_reference_values
        
        # Test normal (below threshold)
        self.assertEqual(determine_status('Chloride', 200, ref_values), "Normal")
        
        # Test poor (above threshold)
        self.assertEqual(determine_status('Chloride', 300, ref_values), "Poor")

    def test_determine_status_unknown_parameter(self):
        """Test status determination for unknown parameter."""
        ref_values = self.sample_reference_values
        
        # Should return Normal for unknown parameters
        self.assertEqual(determine_status('unknown_param', 100, ref_values), "Normal")

    def test_validate_chemical_data_basic(self):
        """Test basic chemical data validation."""
        # Create test data with some invalid values
        test_df = pd.DataFrame({
            'do_percent': [95.5, 250.0, 88.0],  # Second value too high
            'pH': [7.2, 15.0, 6.8],  # Second value invalid
            'Chloride': [25.0, -5.0, 45.0]  # Second value negative
        })
        
        result_df = validate_chemical_data(test_df, remove_invalid=True)
        
        # Check that invalid values were removed (set to NaN)
        self.assertTrue(pd.isna(result_df.loc[1, 'pH']))  # pH 15.0 should be removed
        self.assertTrue(pd.isna(result_df.loc[1, 'Chloride']))  # Negative chloride should be removed
        
        # Check that valid values remain
        self.assertEqual(result_df.loc[0, 'do_percent'], 95.5)
        self.assertEqual(result_df.loc[0, 'pH'], 7.2)

    @patch('data_processing.chemical_processing.save_processed_data')
    @patch('data_processing.chemical_processing.os.path.exists')
    @patch('data_processing.chemical_processing.pd.read_csv')
    def test_process_chemical_data_from_csv_basic(self, mock_read_csv, mock_exists, mock_save_data):
        """Test basic CSV processing functionality."""
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock CSV reading
        mock_read_csv.return_value = self.sample_chemical_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df, key_params, ref_values = process_chemical_data_from_csv()
        
        # Verify mocks were called
        mock_read_csv.assert_called_once()
        mock_save_data.assert_called_once()
        
        # Check that data was processed
        self.assertFalse(result_df.empty)
        
        # Check that columns were renamed correctly
        expected_columns = ['Site_Name', 'Date', 'do_percent', 'pH', 'Nitrate', 
                          'Nitrite', 'Ammonia', 'Phosphorus', 'Chloride']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)
        
        # Check that soluble_nitrogen was calculated
        self.assertIn('soluble_nitrogen', result_df.columns)
        
        # Check that key parameters were returned
        self.assertIsInstance(key_params, list)
        self.assertIn('do_percent', key_params)
        
        # Check that reference values were returned
        self.assertIsInstance(ref_values, dict)

    @patch('data_processing.chemical_processing.save_processed_data')
    @patch('data_processing.chemical_processing.os.path.exists')
    @patch('data_processing.chemical_processing.pd.read_csv')
    def test_process_chemical_data_site_filter(self, mock_read_csv, mock_exists, mock_save_data):
        """Test CSV processing with site name filter."""
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock CSV reading
        mock_read_csv.return_value = self.sample_chemical_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df, _, _ = process_chemical_data_from_csv(site_name='Blue Creek at Highway 9')
        
        # Verify mocks were called
        mock_read_csv.assert_called_once()
        mock_save_data.assert_called_once()
        
        # Should only have one site's data
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['Site_Name'], 'Blue Creek at Highway 9')

    @patch('data_processing.chemical_processing.save_processed_data')
    @patch('data_processing.chemical_processing.os.path.exists')
    @patch('data_processing.chemical_processing.pd.read_csv')
    def test_integration_full_pipeline(self, mock_read_csv, mock_exists, mock_save_data):
        """Integration test for the full chemical processing pipeline."""
        # Create comprehensive test data
        test_data = pd.DataFrame({
            'SiteName': ['Test Site 1', 'Test Site 2'],
            'Date': ['2023-05-15', '2023-06-20'],
            'DO.Saturation': [0.0, 110.2],  # First has BDL
            'pH.Final.1': [7.2, 8.1],
            'Nitrate.Final.1': [0.0, 1.2],  # First has BDL
            'Nitrite.Final.1': [0.05, 0.1],
            'Ammonia.Final.1': [0.1, 0.0],  # Second has BDL
            'OP.Final.1': [0.02, 0.15],
            'Chloride.Final.1': [25.0, 300.0]  # Second exceeds threshold
        })
        
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock CSV reading
        mock_read_csv.return_value = test_data
        
        # Mock save to prevent file writes
        mock_save_data.return_value = True
        
        result_df, key_params, ref_values = process_chemical_data_from_csv()
        
        # Verify mocks were called
        mock_read_csv.assert_called_once()
        mock_save_data.assert_called_once()
        
        # Verify processing steps occurred
        self.assertFalse(result_df.empty)
        self.assertEqual(len(result_df), 2)
        
        # Check BDL conversion occurred
        # First site should have Nitrate converted from 0 to BDL value (0.3)
        self.assertEqual(result_df.iloc[0]['Nitrate'], 0.3)
        
        # Check soluble nitrogen calculation
        self.assertIn('soluble_nitrogen', result_df.columns)
        
        # Verify all sites processed
        sites = result_df['Site_Name'].unique()
        self.assertEqual(len(sites), 2)

    def test_edge_case_empty_data(self):
        """Test behavior with empty input data."""
        empty_df = pd.DataFrame()
        
        # Test individual functions with empty data
        result_bdl = apply_bdl_conversions(empty_df)
        self.assertTrue(result_bdl.empty)
        
        result_nitrogen = calculate_soluble_nitrogen(empty_df)
        self.assertTrue(result_nitrogen.empty)
        
        result_validation = validate_chemical_data(empty_df)
        self.assertTrue(result_validation.empty)

    def test_edge_case_all_null_values(self):
        """Test behavior with all null values."""
        null_df = pd.DataFrame({
            'Nitrate': [np.nan, np.nan],
            'Nitrite': [np.nan, np.nan],
            'Ammonia': [np.nan, np.nan]
        })
        
        # Should handle null values gracefully
        result_df = calculate_soluble_nitrogen(null_df)
        self.assertIn('soluble_nitrogen', result_df.columns)
        
        # Soluble nitrogen should be calculated using BDL values
        self.assertFalse(pd.isna(result_df.loc[0, 'soluble_nitrogen']))

if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)