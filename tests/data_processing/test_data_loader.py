"""
Test suite for data_loader.py - Core CSV loading and utilities.
Tests the foundational data loading functionality used across all data processing modules.
"""

import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing import setup_logging
from data_processing.data_loader import (
    check_file_exists,
    clean_column_names,
    clean_site_name,
    clean_site_names_column,
    convert_bdl_values,
    filter_data_by_site,
    get_date_range,
    get_file_path,
    get_unique_sites,
    load_csv_data,
    save_processed_data,
)

# Set up logging for tests
logger = setup_logging("test_data_loader", category="testing")


class TestDataLoader(unittest.TestCase):
    """Test core data loading functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample data for testing
        self.sample_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', '  Tenmile Creek at Davis  ', 'Red\nRiver at Bridge'],
            'Date': ['2023-05-15', '2023-06-20', '2023-07-10'],
            'Parameter_A': [1.5, 2.3, 'BDL'],
            'Parameter B': [10, 15, 20],
            'County Name': ['Cleveland', 'Murray', 'Bryan']
        })
        
        self.sample_chemical_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Blue Creek at Highway 9', 'Tenmile Creek at Davis'],
            'Date': ['2023-05-15', '2023-06-15', '2023-05-15'],
            'DO': [8.5, 7.2, 9.1],
            'pH': [7.8, 7.5, 8.0]
        })

    def test_clean_site_name_basic(self):
        """Test basic site name cleaning functionality."""
        # Test normal cleaning
        self.assertEqual(clean_site_name('  Blue Creek  '), 'Blue Creek')
        self.assertEqual(clean_site_name('Site\nName'), 'Site Name')
        self.assertEqual(clean_site_name('Multiple   Spaces'), 'Multiple Spaces')
        
        # Test edge cases
        self.assertEqual(clean_site_name(''), '')
        self.assertTrue(pd.isna(clean_site_name(None)))
        self.assertTrue(pd.isna(clean_site_name(pd.NA)))

    def test_clean_site_names_column(self):
        """Test cleaning site names in a DataFrame column."""
        df = pd.DataFrame({
            'sitename': ['  Site A  ', 'Site\nB', 'Site   C'],
            'data': [1, 2, 3]
        })
        
        cleaned_df = clean_site_names_column(df, 'sitename', log_changes=False)
        
        expected_names = ['Site A', 'Site B', 'Site C']
        self.assertEqual(cleaned_df['sitename'].tolist(), expected_names)
        
        # Original DataFrame should be unchanged
        self.assertNotEqual(df['sitename'].tolist(), expected_names)

    def test_clean_site_names_column_missing_column(self):
        """Test behavior when site column doesn't exist."""
        df = pd.DataFrame({'other_column': [1, 2, 3]})
        
        result = clean_site_names_column(df, 'nonexistent_column', log_changes=False)
        
        # Should return original DataFrame unchanged
        pd.testing.assert_frame_equal(result, df)

    def test_clean_column_names(self):
        """Test column name standardization."""
        df = pd.DataFrame({
            'Site Name': [1, 2],
            'Parameter (mg/L)': [3, 4],
            'Value-Test': [5, 6],
            'Data.Point': [7, 8]
        })
        
        cleaned_df = clean_column_names(df)
        
        expected_columns = ['site_name', 'parameter_mg/l', 'value_test', 'datapoint']
        self.assertEqual(cleaned_df.columns.tolist(), expected_columns)

    @patch('data_processing.data_loader.pd.read_csv')
    @patch('data_processing.data_loader.check_file_exists')
    def test_load_csv_data_basic(self, mock_check_exists, mock_read_csv):
        """Test basic CSV data loading."""
        mock_check_exists.return_value = True
        mock_read_csv.return_value = self.sample_data
        
        result = load_csv_data('chemical', clean_site_names=False)
        
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 3)
        mock_read_csv.assert_called_once()

    @patch('data_processing.data_loader.check_file_exists')
    def test_load_csv_data_file_not_found(self, mock_check_exists):
        """Test loading when file doesn't exist."""
        mock_check_exists.return_value = False
        
        result = load_csv_data('nonexistent')
        
        self.assertTrue(result.empty)

    @patch('data_processing.data_loader.pd.read_csv')
    @patch('data_processing.data_loader.check_file_exists')
    def test_load_csv_data_with_site_cleaning(self, mock_check_exists, mock_read_csv):
        """Test CSV loading with automatic site name cleaning."""
        mock_check_exists.return_value = True
        mock_read_csv.return_value = self.sample_data
        
        result = load_csv_data('chemical', clean_site_names=True)
        
        # Should have cleaned the site names
        expected_names = ['Blue Creek at Highway 9', 'Tenmile Creek at Davis', 'Red River at Bridge']
        self.assertEqual(result['SiteName'].tolist(), expected_names)

    def test_filter_data_by_site(self):
        """Test filtering DataFrame by site name."""
        df = pd.DataFrame({
            'sitename': ['Blue Creek at Highway 9', 'Tenmile Creek', 'Blue Creek at Highway 9'],
            'value': [1, 2, 3]
        })
        
        filtered = filter_data_by_site(df, 'Blue Creek at Highway 9')
        
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(filtered['sitename'] == 'Blue Creek at Highway 9'))

    def test_filter_data_by_site_no_matches(self):
        """Test filtering when no matches found."""
        df = pd.DataFrame({
            'sitename': ['Site A', 'Site B'],
            'value': [1, 2]
        })
        
        filtered = filter_data_by_site(df, 'Nonexistent Site')
        
        self.assertTrue(filtered.empty)

    def test_filter_data_by_site_missing_column(self):
        """Test filtering when site column doesn't exist."""
        df = pd.DataFrame({'other_column': [1, 2, 3]})
        
        filtered = filter_data_by_site(df, 'Any Site')
        
        self.assertTrue(filtered.empty)

    @patch('data_processing.data_loader.load_csv_data')
    def test_get_unique_sites(self, mock_load_csv):
        """Test extracting unique sites from data."""
        # Create data that mimics what load_csv_data returns (with site names already cleaned)
        cleaned_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Tenmile Creek at Davis', 'Red River at Bridge'],
            'Date': ['2023-05-15', '2023-06-20', '2023-07-10']
        })
        mock_load_csv.return_value = cleaned_data
        
        sites = get_unique_sites('chemical')
        
        expected_sites = ['Blue Creek at Highway 9', 'Tenmile Creek at Davis', 'Red River at Bridge']
        self.assertEqual(set(sites), set(expected_sites))

    @patch('data_processing.data_loader.load_csv_data')
    def test_get_unique_sites_empty_data(self, mock_load_csv):
        """Test getting unique sites from empty data."""
        mock_load_csv.return_value = pd.DataFrame()
        
        sites = get_unique_sites('chemical')
        
        self.assertEqual(sites, [])

    def test_convert_bdl_values(self):
        """Test converting 'BDL' values to numeric."""
        df = pd.DataFrame({
            'param1': [1.5, 'BDL', 3.0],
            'param2': [10, 20, 'BDL']
        })
        
        bdl_columns = ['param1', 'param2']
        bdl_replacements = {'param1': 0.1, 'param2': 5.0}
        
        result = convert_bdl_values(df, bdl_columns, bdl_replacements)
        
        self.assertEqual(result.loc[1, 'param1'], 0.1)
        self.assertEqual(result.loc[2, 'param2'], 5.0)
        self.assertEqual(result.loc[0, 'param1'], 1.5)  # Unchanged

    @patch('data_processing.data_loader.load_csv_data')
    def test_get_date_range(self, mock_load_csv):
        """Test getting date range from data."""
        mock_data = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-15', '2023-06-20', '2023-12-10']),
            'value': [1, 2, 3]
        })
        mock_load_csv.return_value = mock_data
        
        min_date, max_date = get_date_range('chemical')
        
        self.assertEqual(min_date, pd.Timestamp('2023-01-15'))
        self.assertEqual(max_date, pd.Timestamp('2023-12-10'))

    def test_get_date_range_site_data(self):
        """Test that site data returns None for date range."""
        min_date, max_date = get_date_range('site')
        
        self.assertIsNone(min_date)
        self.assertIsNone(max_date)

    def test_get_file_path_basic(self):
        """Test getting file paths for different data types."""
        # Test interim data path
        path = get_file_path('chemical', processed=False)
        self.assertIn('cleaned_chemical_data.csv', path)
        self.assertIn('interim', path)
        
        # Test processed data path
        path = get_file_path('chemical', processed=True)
        self.assertIn('processed_chemical_data.csv', path)
        self.assertIn('processed', path)

    def test_get_file_path_unknown_type(self):
        """Test getting file path for unknown data type."""
        path = get_file_path('unknown_type')
        
        self.assertIsNone(path)

    @patch('data_processing.data_loader.os.path.exists')
    def test_check_file_exists(self, mock_exists):
        """Test file existence checking."""
        mock_exists.return_value = True
        self.assertTrue(check_file_exists('/fake/path/file.csv'))
        
        mock_exists.return_value = False
        self.assertFalse(check_file_exists('/fake/path/missing.csv'))

    @patch('data_processing.data_loader.pd.DataFrame.to_csv')
    def test_save_processed_data(self, mock_to_csv):
        """Test saving processed data to CSV."""
        df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        
        result = save_processed_data(df, 'test_data')
        
        self.assertTrue(result)
        mock_to_csv.assert_called_once()

    def test_save_processed_data_empty(self):
        """Test saving empty DataFrame."""
        df = pd.DataFrame()
        
        result = save_processed_data(df, 'test_data')
        
        self.assertFalse(result)

    def test_save_processed_data_special_characters(self):
        """Test saving data with special characters in type name."""
        df = pd.DataFrame({'col1': [1, 2]})
        
        with patch('data_processing.data_loader.pd.DataFrame.to_csv') as mock_to_csv:
            result = save_processed_data(df, 'test: data/with*special?chars')
            
            self.assertTrue(result)
            # Should sanitize the filename
            mock_to_csv.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2) 