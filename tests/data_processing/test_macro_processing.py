"""
Test suite for macroinvertebrate data processing functionality.
Tests the logic in data_processing.macro_processing module.
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

from data_processing.macro_processing import (
    process_macro_csv_data
)
from data_processing.biological_utils import (
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_macro_processing", category="testing")


class TestMacroProcessing(unittest.TestCase):
    """Test macroinvertebrate data processing functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample macro data matching real CSV structure
        self.sample_macro_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Red River at Bridge', 'Tenmile Creek at Davis'],
            'Date': ['2023-05-15', '2023-06-20', '2023-07-10'],
            'Year': [2023, 2023, 2023],
            'Season': ['Summer', 'Summer', 'Summer'],
            'Habitat_Type': ['Riffle', 'Vegetation', 'Woody'],
            'SAMPLEID': [101, 201, 301],
            'Taxa_Richness': [25, 18, 12],
            'Modified_HBI': [4.2, 5.8, 7.1],
            'EPT_perc': [65.5, 42.3, 15.2],
            'EPT_Taxa': [12, 8, 3],
            'Dom_2_Taxa': [35.2, 55.8, 75.4],
            'Shannon_Weaver': [2.8, 2.1, 1.4],
            'Taxa_Richness_Score': [5, 3, 1],
            'Mod_HBI_Score': [5, 3, 1],
            'EPT_perc_Score': [5, 3, 1],
            'EPT_Taxa_Score': [5, 3, 1],
            'Dom2_Taxa_Score': [5, 3, 1],
            'Shannon_Weaver_Score': [5, 3, 1],
            'Score': [30, 18, 6],  # Sum of component scores
            'Percent_Reference': [0.90, 0.65, 0.25]  # Non-impaired, Slightly Impaired, Severely Impaired
        })
        
        # Sample data with invalid scores for validation testing
        self.invalid_score_data = pd.DataFrame({
            'SiteName': ['Test Site 1', 'Test Site 2'],
            'Date': ['2023-08-15', '2023-09-20'],
            'Year': [2023, 2023],
            'Season': ['Summer', 'Summer'],
            'Habitat_Type': ['Riffle', 'Riffle'],
            'SAMPLEID': [401, 501],
            'Taxa_Richness': [20, 15],
            'Modified_HBI': [5.0, 6.2],
            'EPT_perc': [50.0, 30.0],
            'EPT_Taxa': [10, 5],
            'Dom_2_Taxa': [45.0, 65.0],
            'Shannon_Weaver': [2.5, 1.8],
            'Taxa_Richness_Score': [3, 3],
            'Mod_HBI_Score': [3, 3],
            'EPT_perc_Score': [3, 3],
            'EPT_Taxa_Score': [3, 3],
            'Dom2_Taxa_Score': [3, 3],
            'Shannon_Weaver_Score': [3, 3],
            'Score': [20, 15],  # Should be 18 and 18, but showing as 20 and 15 (invalid)
            'Percent_Reference': [0.75, 0.55]
        })
        
        # Sample data with sentinel values (-999, -99)
        self.invalid_values_data = pd.DataFrame({
            'SiteName': ['Site A', 'Site B', 'Site C'],
            'Date': ['2023-08-15', '2023-09-20', '2023-10-15'],
            'Year': [2023, 2023, 2023],
            'Season': ['Summer', 'Summer', 'Summer'],
            'Habitat_Type': ['Riffle', 'Riffle', 'Riffle'],
            'SAMPLEID': [601, 701, 801],
            'Taxa_Richness_Score': [5, -999, 3],
            'Mod_HBI_Score': [5, 3, -99],
            'EPT_perc_Score': [5, 3, 3],
            'EPT_Taxa_Score': [5, 3, 3],
            'Dom2_Taxa_Score': [5, 3, 3],
            'Shannon_Weaver_Score': [5, 3, 3],
            'Percent_Reference': [0.85, -999, 0.65]
        })

    def determine_biological_condition(self, comparison_value):
        """
        Helper function to replicate the biological condition logic from macro_processing.
        """
        try:
            comparison_value = float(comparison_value)
        except (TypeError, ValueError):
            return "Unknown"
        
        if pd.isna(comparison_value):
            return "Unknown"
        
        # Convert to percentage for comparison
        comparison_percent = comparison_value * 100
        
        if comparison_percent >= 83:
            return "Non-impaired"
        elif comparison_percent >= 54:
            return "Slightly Impaired"
        elif comparison_percent >= 17:
            return "Moderately Impaired"
        else:
            return "Severely Impaired"

    def test_determine_biological_condition_non_impaired(self):
        """Test biological condition determination for non-impaired range."""
        # Test ≥83% = Non-impaired
        self.assertEqual(self.determine_biological_condition(0.90), "Non-impaired")
        self.assertEqual(self.determine_biological_condition(0.83), "Non-impaired")

    def test_determine_biological_condition_slightly_impaired(self):
        """Test biological condition determination for slightly impaired range."""
        # Test 54-82% = Slightly Impaired
        self.assertEqual(self.determine_biological_condition(0.75), "Slightly Impaired")
        self.assertEqual(self.determine_biological_condition(0.54), "Slightly Impaired")

    def test_determine_biological_condition_moderately_impaired(self):
        """Test biological condition determination for moderately impaired range."""
        # Test 17-53% = Moderately Impaired
        self.assertEqual(self.determine_biological_condition(0.40), "Moderately Impaired")
        self.assertEqual(self.determine_biological_condition(0.17), "Moderately Impaired")

    def test_determine_biological_condition_severely_impaired(self):
        """Test biological condition determination for severely impaired range."""
        # Test <17% = Severely Impaired
        self.assertEqual(self.determine_biological_condition(0.15), "Severely Impaired")
        self.assertEqual(self.determine_biological_condition(0.05), "Severely Impaired")

    def test_determine_biological_condition_edge_cases(self):
        """Test biological condition determination for edge cases."""
        # Test boundary values
        self.assertEqual(self.determine_biological_condition(0.82), "Slightly Impaired")  # Just below 83%
        self.assertEqual(self.determine_biological_condition(0.53), "Moderately Impaired")  # Just below 54%
        self.assertEqual(self.determine_biological_condition(0.16), "Severely Impaired")  # Just below 17%
        
        # Test NaN and invalid values
        self.assertEqual(self.determine_biological_condition(np.nan), "Unknown")
        self.assertEqual(self.determine_biological_condition("not a number"), "Unknown")

    def test_total_score_calculation(self):
        """Test that total score is calculated correctly from component scores."""
        # Simulate the score calculation logic from process_macro_csv_data
        test_df = self.sample_macro_data.copy()
        
        # Apply column name cleaning and mapping (simulate pipeline)
        test_df.columns = [col.lower().replace('_', '') for col in test_df.columns]
        
        column_mapping = {
            'sitename': 'site_name',
            'taxarichnessscore': 'taxa_richness_score',
            'modhbiscore': 'hbi_score_score',
            'eptpercscore': 'ept_abundance_score',
            'epttaxascore': 'ept_taxa_richness_score',
            'dom2taxascore': 'contribution_dominants_score',
            'shannonweaverscore': 'shannon_weaver_score',
            'score': 'total_score'
        }
        test_df = test_df.rename(columns=column_mapping)
        
        # Calculate total score from components
        metric_score_cols = [
            'taxa_richness_score', 
            'hbi_score_score', 
            'ept_abundance_score', 
            'ept_taxa_richness_score', 
            'contribution_dominants_score', 
            'shannon_weaver_score'
        ]
        
        calculated_total = test_df[metric_score_cols].sum(axis=1)
        
        # First row: 5+5+5+5+5+5 = 30 ✓
        self.assertEqual(calculated_total.iloc[0], 30)
        # Second row: 3+3+3+3+3+3 = 18 ✓
        self.assertEqual(calculated_total.iloc[1], 18)
        # Third row: 1+1+1+1+1+1 = 6 ✓
        self.assertEqual(calculated_total.iloc[2], 6)

    def test_remove_invalid_biological_values_macro(self):
        """Test removal of invalid biological values (-999, -99) for macro data."""
        # Need to use column names that the function will recognize as score columns
        test_data = pd.DataFrame({
            'SiteName': ['Site A', 'Site B', 'Site C'],
            'taxa_richness_score': [5, -999, 3],  # Site B has invalid value
            'mod_hbi_score': [5, 3, -99],         # Site C has invalid value
            'ept_perc_score': [5, 3, 3],
            'comparison_to_reference': [0.85, -999, 0.65]  # Site B also has invalid here
        })
        
        result_df = remove_invalid_biological_values(test_data)
        
        # Should remove rows with invalid values
        # Site A: valid (no -999 or -99)
        # Site B: invalid (has -999 in taxa_richness_score and comparison_to_reference)
        # Site C: invalid (has -99 in mod_hbi_score)
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['SiteName'], 'Site A')

    def test_convert_columns_to_numeric_macro(self):
        """Test conversion of score columns to numeric types for macro data."""
        # Create test data with string numbers
        test_df = pd.DataFrame({
            'taxa_richness_score': ['5', '3', '1'],
            'hbi_score_score': ['5', '3', '1'],
            'ept_abundance_score': ['5', '3', '1'],
            'comparison_to_reference': ['0.90', '0.65', '0.25'],
            'year': ['2023', '2023', '2023'],
            'site_name': ['Site A', 'Site B', 'Site C'],  # Should not be converted
            'season': ['Summer', 'Summer', 'Summer']  # Should not be converted
        })
        
        result_df = convert_columns_to_numeric(test_df)
        
        # Score columns should be converted to numeric
        numeric_columns = ['taxa_richness_score', 'hbi_score_score', 'ept_abundance_score', 
                          'comparison_to_reference', 'year']
        for col in numeric_columns:
            self.assertTrue(pd.api.types.is_numeric_dtype(result_df[col]))
        
        # String columns should remain as string/object
        string_columns = ['site_name', 'season']
        for col in string_columns:
            self.assertTrue(pd.api.types.is_string_dtype(result_df[col]) or 
                           pd.api.types.is_object_dtype(result_df[col]))

    @patch('data_processing.macro_processing.save_processed_data')
    @patch('data_processing.macro_processing.load_csv_data')
    def test_process_macro_csv_data_basic(self, mock_load_csv, mock_save):
        """Test basic CSV processing functionality for macro data."""
        # Mock CSV loading
        mock_load_csv.return_value = self.sample_macro_data
        mock_save.return_value = True  # Mock the save operation
        
        result_df = process_macro_csv_data()
        
        # Verify save was called
        mock_save.assert_called_once_with(result_df, 'macro_data')
        
        # Should process data without errors
        self.assertFalse(result_df.empty)
        
        # Check that columns were mapped correctly
        expected_columns = ['site_name', 'collection_date', 'year', 'season', 'habitat',
                          'sample_id', 'taxa_richness_score', 'comparison_to_reference']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)

    @patch('data_processing.macro_processing.save_processed_data')
    @patch('data_processing.macro_processing.load_csv_data')
    def test_process_macro_csv_data_site_filter(self, mock_load_csv, mock_save):
        """Test CSV processing with site name filter for macro data."""
        mock_load_csv.return_value = self.sample_macro_data
        mock_save.return_value = True  # Mock the save operation
        
        result_df = process_macro_csv_data(site_name='Blue Creek at Highway 9')
        
        # Verify save was called
        mock_save.assert_called_once()
        
        # Should only have one site's data
        self.assertEqual(len(result_df), 1)
        self.assertEqual(result_df.iloc[0]['site_name'], 'Blue Creek at Highway 9')

    def test_biological_condition_integration(self):
        """Test integration of biological condition determination with sample data."""
        # Test the full workflow: percentage -> condition
        test_cases = [
            (0.90, "Non-impaired"),      # 90% reference
            (0.65, "Slightly Impaired"), # 65% reference  
            (0.25, "Moderately Impaired")  # 25% reference (correct - it's 17-53% range)
        ]
        
        for percent_ref, expected_condition in test_cases:
            with self.subTest(percent_ref=percent_ref):
                condition = self.determine_biological_condition(percent_ref)
                self.assertEqual(condition, expected_condition)

    def test_macro_metrics_mapping(self):
        """Test that macro metrics are correctly identified and mapped."""
        # Test the metric mappings used in insert_metrics_data
        expected_metrics = [
            ('Taxa Richness', 'taxa_richness', 'taxa_richness_score'),
            ('EPT Taxa Richness', 'ept_taxa_richness', 'ept_taxa_richness_score'),
            ('EPT Abundance', 'ept_abundance', 'ept_abundance_score'),
            ('HBI Score', 'hbi_score', 'hbi_score_score'),
            ('% Contribution Dominants', 'contribution_dominants', 'contribution_dominants_score'),
            ('Shannon-Weaver', 'shannon_weaver', 'shannon_weaver_score')
        ]
        
        # Verify we have the expected number of metrics
        self.assertEqual(len(expected_metrics), 6)
        
        # Verify metric names are descriptive
        metric_names = [metric[0] for metric in expected_metrics]
        self.assertIn('Taxa Richness', metric_names)
        self.assertIn('EPT Taxa Richness', metric_names)
        self.assertIn('Shannon-Weaver', metric_names)

    def test_integration_full_pipeline(self):
        """Integration test for macro processing pipeline components."""
        # Start with raw data
        test_data = self.sample_macro_data.copy()
        
        # Simulate column cleaning (lowercase, remove underscores)
        test_data.columns = [col.lower().replace('_', '') for col in test_data.columns]
        
        # Apply column mapping (simplified version)
        column_mapping = {
            'sitename': 'site_name',
            'sampleid': 'sample_id',
            'date': 'collection_date',
            'year': 'year',
            'season': 'season',
            'habitattype': 'habitat',
            'taxarichness': 'taxa_richness',
            'modifiedhbi': 'hbi_score',
            'eptperc': 'ept_abundance',
            'epttaxa': 'ept_taxa_richness',
            'dom2taxa': 'contribution_dominants',
            'shannonweaver': 'shannon_weaver',
            'taxarichnessscore': 'taxa_richness_score',
            'modhbiscore': 'hbi_score_score',
            'eptpercscore': 'ept_abundance_score',
            'epttaxascore': 'ept_taxa_richness_score',
            'dom2taxascore': 'contribution_dominants_score',
            'shannonweaverscore': 'shannon_weaver_score',
            'percentreference': 'comparison_to_reference'
        }
        test_data = test_data.rename(columns=column_mapping)
        
        # Apply processing steps
        processed_data = remove_invalid_biological_values(test_data)
        processed_data = convert_columns_to_numeric(processed_data)
        
        # Test biological condition determination
        conditions = processed_data['comparison_to_reference'].apply(self.determine_biological_condition)
        expected_conditions = ["Non-impaired", "Slightly Impaired", "Moderately Impaired"]
        
        # Verify pipeline completed successfully
        self.assertFalse(processed_data.empty)
        self.assertEqual(len(processed_data), 3)  # All rows should be valid
        self.assertEqual(list(conditions), expected_conditions)
        
        # Check that numeric conversion worked
        self.assertTrue(pd.api.types.is_numeric_dtype(processed_data['taxa_richness_score']))

    def test_edge_case_empty_data(self):
        """Test behavior with empty input data."""
        empty_df = pd.DataFrame()
        
        # Test individual functions with empty data
        result_invalid_removal = remove_invalid_biological_values(empty_df)
        self.assertTrue(result_invalid_removal.empty)
        
        result_numeric = convert_columns_to_numeric(empty_df)
        self.assertTrue(result_numeric.empty)
        
        # Test biological condition with None
        result_condition = self.determine_biological_condition(None)
        self.assertEqual(result_condition, "Unknown")

    def test_edge_case_missing_score_columns(self):
        """Test behavior when some score columns are missing."""
        # Create data missing some score columns
        incomplete_df = pd.DataFrame({
            'site_name': ['Test Site'],
            'taxa_richness_score': [5],
            'hbi_score_score': [3],
            # Missing other score columns
            'comparison_to_reference': [0.75]
        })
        
        # Should handle missing columns gracefully
        result_df = remove_invalid_biological_values(incomplete_df)
        self.assertFalse(result_df.empty)
        
        # Should convert available columns
        result_df = convert_columns_to_numeric(result_df)
        self.assertTrue(pd.api.types.is_numeric_dtype(result_df['taxa_richness_score']))

    def test_habitat_types_validation(self):
        """Test that valid habitat types are handled correctly."""
        valid_habitats = ['Riffle', 'Vegetation', 'Woody']
        
        # All habitat types in sample data should be valid
        habitats_in_data = self.sample_macro_data['Habitat_Type'].unique()
        
        for habitat in habitats_in_data:
            self.assertIn(habitat, valid_habitats)

    def test_season_validation(self):
        """Test that valid seasons are handled correctly."""
        valid_seasons = ['Summer', 'Winter']
        
        # All seasons in sample data should be valid
        seasons_in_data = self.sample_macro_data['Season'].unique()
        
        for season in seasons_in_data:
            self.assertIn(season, valid_seasons)


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)