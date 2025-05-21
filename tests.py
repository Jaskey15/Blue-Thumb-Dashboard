import unittest
import os
import pandas as pd
import numpy as np
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock

# Import your utils
from utils import load_markdown_content, create_image_with_caption, safe_div, format_value

# Import data processing modules
from data_processing.data_loader import clean_column_names, filter_data_by_site, convert_bdl_values
from data_processing.chemical_processing import convert_bdl_value, determine_status as chem_determine_status
from data_processing.fish_processing import validate_ibi_scores
from data_processing.macro_processing import determine_biological_condition
from data_processing.habitat_processing import process_habitat_csv_data

# Import visualization modules
from visualizations.map_viz import create_site_map, determine_status
from visualizations.chemical_viz import get_parameter_label, get_parameter_name
from visualizations.fish_viz import create_fish_viz
from visualizations.macro_viz import create_macro_viz
from visualizations.habitat_viz import create_habitat_viz


# New test classes for data processing modules
class DataLoaderTests(unittest.TestCase):
    def test_clean_column_names(self):
        """Test cleaning column names."""
        # Create a test DataFrame with messy column names
        df = pd.DataFrame({
            'Column Name': [1, 2, 3],
            'Another-Column': [4, 5, 6],
            'Third.Column (Test)': [7, 8, 9]
        })
        
        # Clean the column names
        cleaned_df = clean_column_names(df)
        
        # Check that the column names were cleaned correctly
        expected_columns = ['column_name', 'another_column', 'thirdcolumn_test']
        self.assertEqual(list(cleaned_df.columns), expected_columns)
    
    def test_filter_data_by_site(self):
        """Test filtering data by site name."""
        # Create a test DataFrame with site data
        df = pd.DataFrame({
            'sitename': ['Site A', 'Site B', 'Site A', 'Site C'],
            'value': [10, 20, 30, 40]
        })
        
        # Filter for Site A
        filtered_df = filter_data_by_site(df, 'Site A')
        
        # Check that only Site A rows were returned
        self.assertEqual(len(filtered_df), 2)
        self.assertTrue(all(filtered_df['sitename'] == 'Site A'))
        
        # Test with a site that doesn't exist
        empty_df = filter_data_by_site(df, 'Nonexistent Site')
        self.assertTrue(empty_df.empty)
    
    def test_convert_bdl_values(self):
        """Test converting BDL values to numeric values."""
        # Create a test DataFrame with BDL values
        df = pd.DataFrame({
            'col1': [1, 'BDL', 3, 'BDL'],
            'col2': [4, 5, 'BDL', 7]
        })
        
        # Define BDL replacements
        bdl_replacements = {'col1': 0.5, 'col2': 0.2}
        
        # Convert BDL values
        converted_df = convert_bdl_values(df, ['col1', 'col2'], bdl_replacements)
        
        # Check that BDL values were replaced correctly
        self.assertEqual(converted_df['col1'][1], 0.5)
        self.assertEqual(converted_df['col1'][3], 0.5)
        self.assertEqual(converted_df['col2'][2], 0.2)

class ChemicalProcessingTests(unittest.TestCase):
    def test_convert_bdl_value(self):
        """Test converting zero values to BDL replacement values."""
        # Test with a zero value
        self.assertEqual(convert_bdl_value(0, 0.5), 0.5)
        
        # Test with a non-zero value
        self.assertEqual(convert_bdl_value(1.2, 0.5), 1.2)
        
        # Test with NaN - should return NaN
        self.assertTrue(np.isnan(convert_bdl_value(np.nan, 0.5)))
        
        # Test with a string that can be converted to a number
        self.assertEqual(convert_bdl_value("0", 0.5), 0.5)
        
        # Test with a string that cannot be converted to a number
        self.assertTrue(np.isnan(convert_bdl_value("not a number", 0.5)))
    
    def test_determine_status(self):
        """Test determination of status based on parameter values."""
        # Create a mock reference values dictionary
        reference_values = {
            'do_percent': {'normal min': 80, 'normal max': 130, 'caution min': 50, 'caution max': 150},
            'pH': {'normal min': 6.5, 'normal max': 9.0},
            'soluble_nitrogen': {'normal': 0.8, 'caution': 1.5},
            'Chloride': {'poor': 250}
        }
        
        # Test do_percent status determination
        self.assertEqual(chem_determine_status('do_percent', 100, reference_values), "Normal")
        self.assertEqual(chem_determine_status('do_percent', 40, reference_values), "Poor")
        self.assertEqual(chem_determine_status('do_percent', 60, reference_values), "Caution")
        self.assertEqual(chem_determine_status('do_percent', 140, reference_values), "Caution")
        self.assertEqual(chem_determine_status('do_percent', 160, reference_values), "Poor")
        
        # Test pH status determination
        self.assertEqual(chem_determine_status('pH', 7.0, reference_values), "Normal")
        self.assertEqual(chem_determine_status('pH', 10.0, reference_values), "Outside Normal")
        self.assertEqual(chem_determine_status('pH', 6.0, reference_values), "Outside Normal")
        
        # Test nitrogen status determination
        self.assertEqual(chem_determine_status('soluble_nitrogen', 0.5, reference_values), "Normal")
        self.assertEqual(chem_determine_status('soluble_nitrogen', 1.0, reference_values), "Caution")
        self.assertEqual(chem_determine_status('soluble_nitrogen', 2.0, reference_values), "Poor")
        
        # Test unknown parameter (should return Normal)
        self.assertEqual(chem_determine_status('unknown_param', 100, reference_values), "Normal")
        
        # Test NaN value (should return Unknown)
        self.assertEqual(chem_determine_status('do_percent', np.nan, reference_values), "Unknown")

class FishProcessingTests(unittest.TestCase):
    def test_validate_ibi_scores(self):
        """Test validation of IBI scores."""
        # Create a test DataFrame with IBI scores
        df = pd.DataFrame({
            'total_species_score': [3, 5, 2],
            'sensitive_benthic_score': [2, 3, 1],
            'sunfish_species_score': [4, 2, 3],
            'intolerant_species_score': [1, 2, 1],
            'tolerant_score': [5, 3, 2],
            'insectivorous_score': [2, 1, 3],
            'lithophilic_score': [3, 4, 2],
            'total_score': [20, 21, 14]  # First row sum is correct, second is not
        })
        
        # Validate IBI scores
        validated_df = validate_ibi_scores(df)
        
        # Check that validation flags were added correctly
        self.assertEqual(validated_df['score_validated'][0], True)  # 3+2+4+1+5+2+3 = 20
        self.assertEqual(validated_df['score_validated'][1], False)  # 5+3+2+2+3+1+4 = 20, but calculated value is 21
        self.assertEqual(validated_df['score_validated'][2], True)  # 2+1+3+1+2+3+2 = 14

class MacroProcessingTests(unittest.TestCase):
    def test_determine_biological_condition(self):
        """Test determination of biological condition based on comparison values."""
        # Test each condition threshold
        self.assertEqual(determine_biological_condition(0.85), "Non-impaired")
        self.assertEqual(determine_biological_condition(0.75), "Slightly Impaired")
        self.assertEqual(determine_biological_condition(0.40), "Moderately Impaired")
        self.assertEqual(determine_biological_condition(0.15), "Severely Impaired")
        
        # Test edge cases
        self.assertEqual(determine_biological_condition(0.83), "Slightly Impaired")
        self.assertEqual(determine_biological_condition(0.54), "Slightly Impaired")
        self.assertEqual(determine_biological_condition(0.17), "Moderately Impaired")
        
        # Test with NaN
        self.assertEqual(determine_biological_condition(np.nan), "Unknown")
        
        # Test with non-numeric value
        self.assertEqual(determine_biological_condition("not a number"), "Unknown")

class HabitatProcessingTests(unittest.TestCase):
    @patch('data_processing.habitat_processing.load_csv_data')
    def test_process_habitat_csv_data(self, mock_load_csv_data):
        """Test processing of habitat CSV data."""
        # Create a mock habitat DataFrame
        mock_df = pd.DataFrame({
            'sitename': ['Site A', 'Site B'],
            'sampleid': [1, 2],
            'date': ['2022-01-01', '2022-02-01'],
            'instreamhabitat': [10, 15],
            'poolbottomsubstrate': [8, 12],
            'poolvariability': [5, 8],
            'total': [80, 90],
            'habitatgrade': ['Good', 'Excellent']
        })
        
        # Configure the mock to return our test DataFrame
        mock_load_csv_data.return_value = mock_df
        
        # Call the function with a specific site
        result_df = process_habitat_csv_data('Site A')
        
        # Verify the function called load_csv_data correctly
        mock_load_csv_data.assert_called_once_with('habitat')
        
        # Check that the result contains only Site A data
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df['site_name'].iloc[0], 'Site A')
        
        # Verify column renaming
        self.assertIn('instream_cover', result_df.columns)
        self.assertIn('pool_bottom_substrate', result_df.columns)
        self.assertIn('pool_variability', result_df.columns)

if __name__ == '__main__':
    unittest.main()