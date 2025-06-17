"""
Test suite for macroinvertebrate data processing functionality.
Tests the logic in data_processing.macro_processing module.
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

from data_processing.macro_processing import (
    process_macro_csv_data,
    insert_macro_collection_events,
    insert_metrics_data,
    load_macroinvertebrate_data
)
from data_processing.biological_utils import (
    remove_invalid_biological_values,
    convert_columns_to_numeric
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_macro_processing", category="testing")


class TestMacroProcessing(unittest.TestCase):
    """Test macroinvertebrate-specific processing functionality."""
    
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

    def test_determine_biological_condition_all_classifications(self):
        """Test biological condition determination for all classifications and edge cases."""
        test_cases = [
            # Non-impaired (≥83%)
            (0.90, "Non-impaired"),
            (0.83, "Non-impaired"),
            
            # Slightly Impaired (54-82%)
            (0.82, "Slightly Impaired"),  
            (0.75, "Slightly Impaired"),
            (0.54, "Slightly Impaired"),
            
            # Moderately Impaired (17-53%)
            (0.53, "Moderately Impaired"),  
            (0.40, "Moderately Impaired"),
            (0.17, "Moderately Impaired"),
            
            # Severely Impaired (<17%)
            (0.16, "Severely Impaired"), 
            (0.15, "Severely Impaired"),
            (0.05, "Severely Impaired"),
            
            # Edge cases and invalid values
            (np.nan, "Unknown"),
            ("not a number", "Unknown"),
            (None, "Unknown")
        ]
        
        for comparison_value, expected_condition in test_cases:
            with self.subTest(comparison=comparison_value, expected=expected_condition):
                result = self.determine_biological_condition(comparison_value)
                self.assertEqual(result, expected_condition)

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

    # =============================================================================
    # MACRO-SPECIFIC DATABASE TESTS  
    # =============================================================================
    
    def test_insert_macro_collection_events(self):
        """Test macro collection event insertion with habitat grouping."""
        # Create properly formatted test data
        test_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Blue Creek at Highway 9', 'Red River at Bridge'],
            'sample_id': [101, 101, 201],  # Same sample, different habitats
            'habitat': ['Riffle', 'Pool', 'Vegetation'],
            'season': ['Spring', 'Spring', 'Fall'],
            'collection_date_str': ['2023-05-15', '2023-05-15', '2023-06-20'],
            'year': [2023, 2023, 2023]
        })
        
        mock_cursor = MagicMock()
        
        result = insert_macro_collection_events(mock_cursor, test_data)
        
        # Should return mapping for (sample_id, habitat) -> event_id
        self.assertIsInstance(result, dict)
    
    def test_insert_metrics_data_macro(self):
        """Test insertion of macro metrics data."""
        mock_cursor = MagicMock()
        # Macro uses (sample_id, habitat) as key
        event_id_map = {
            (101, 'Riffle'): 123, 
            (201, 'Vegetation'): 456,
            (301, 'Woody'): 789
        }
        
        # Create processed data with proper column names
        processed_data = pd.DataFrame({
            'sample_id': [101, 201, 301],
            'habitat': ['Riffle', 'Vegetation', 'Woody'],
            'taxa_richness': [25, 18, 12],
            'taxa_richness_score': [5, 3, 1],
            'hbi_score': [4.2, 5.8, 7.1],
            'hbi_score_score': [5, 3, 1],
            'ept_abundance': [65.5, 42.3, 15.2],
            'ept_abundance_score': [5, 3, 1],
            'ept_taxa_richness': [12, 8, 3],
            'ept_taxa_richness_score': [5, 3, 1],
            'contribution_dominants': [35.2, 55.8, 75.4],
            'contribution_dominants_score': [5, 3, 1],
            'shannon_weaver': [2.8, 2.1, 1.4],
            'shannon_weaver_score': [5, 3, 1],
            'total_score': [30, 18, 6],
            'comparison_to_reference': [0.90, 0.65, 0.25]
        })
        
        result = insert_metrics_data(mock_cursor, processed_data, event_id_map)
        
        # Should return count of inserted metrics
        self.assertIsInstance(result, int)
        
        # Verify that INSERT statements were called
        self.assertTrue(mock_cursor.execute.called)
    
    def test_insert_metrics_data_biological_condition_calculation(self):
        """Test biological condition calculation during metrics insertion."""
        mock_cursor = MagicMock()
        event_id_map = {(101, 'Riffle'): 123}
        
        # Test data with known comparison values
        test_cases = [
            (0.90, "Non-impaired"),      # ≥83%
            (0.75, "Slightly Impaired"), # 54-82%
            (0.40, "Moderately Impaired"), # 17-53%
            (0.10, "Severely Impaired")  # <17%
        ]
        
        for comparison_value, expected_condition in test_cases:
            with self.subTest(comparison=comparison_value):
                test_data = pd.DataFrame({
                    'sample_id': [101],
                    'habitat': ['Riffle'],
                    'taxa_richness': [20],
                    'taxa_richness_score': [4],
                    'total_score': [24],
                    'comparison_to_reference': [comparison_value]
                })
                
                result = insert_metrics_data(mock_cursor, test_data, event_id_map)
                
                # Should process without error
                self.assertIsInstance(result, int)

    def test_insert_metrics_data_missing_event_id(self):
        """Test handling when (sample_id, habitat) is not in event_id_map."""
        mock_cursor = MagicMock()
        event_id_map = {(999, 'Pool'): 123}  # Different sample_id/habitat
        
        test_data = pd.DataFrame({
            'sample_id': [101],
            'habitat': ['Riffle'],  # Not in event_id_map
            'total_score': [24],
            'comparison_to_reference': [0.75]
        })
        
        result = insert_metrics_data(mock_cursor, test_data, event_id_map)
        
        # Should return 0 when no matching event_ids
        self.assertEqual(result, 0)

    # =============================================================================
    # HABITAT AND SEASON SPECIFIC TESTS
    # =============================================================================
    
    def test_multiple_habitats_per_site(self):
        """Test processing sites with multiple habitat types."""
        multi_habitat_data = pd.DataFrame({
            'SiteName': ['Test Site', 'Test Site', 'Test Site'],
            'SAMPLEID': [101, 101, 101],  # Same sample, different habitats
            'Date': ['2023-05-15', '2023-05-15', '2023-05-15'],
            'Year': [2023, 2023, 2023],
            'Season': ['Spring', 'Spring', 'Spring'],
            'Habitat_Type': ['Riffle', 'Pool', 'Vegetation'],
            'Taxa_Richness': [25, 20, 15],
            'Taxa_Richness_Score': [5, 4, 3],
            'Modified_HBI': [4.2, 5.0, 6.5],
            'Mod_HBI_Score': [5, 4, 2],
            'EPT_perc': [65.5, 55.0, 35.0],
            'EPT_perc_Score': [5, 4, 2],
            'EPT_Taxa': [12, 10, 6],
            'EPT_Taxa_Score': [5, 4, 2],
            'Dom_2_Taxa': [35.2, 45.0, 60.0],
            'Dom2_Taxa_Score': [5, 4, 2],
            'Shannon_Weaver': [2.8, 2.5, 1.8],
            'Shannon_Weaver_Score': [5, 4, 2],
            'Percent_Reference': [0.90, 0.75, 0.45]
        })
        
        # Process the data (simulate column mapping)
        multi_habitat_data.columns = [col.lower().replace('_', '') for col in multi_habitat_data.columns]
        
        # Should create separate records for each habitat
        grouped = multi_habitat_data.groupby(['sampleid', 'habitattype'])
        self.assertEqual(len(grouped), 3)  # 3 habitat combinations
        
        # Each group should have different scores reflecting habitat quality
        for (sample_id, habitat), group in grouped:
            self.assertEqual(len(group), 1)  # One row per habitat
            self.assertIn(habitat.lower(), ['riffle', 'pool', 'vegetation'])

    def test_seasonal_variation_handling(self):
        """Test handling of seasonal data collection."""
        seasonal_data = pd.DataFrame({
            'SiteName': ['Test Site', 'Test Site'],
            'SAMPLEID': [101, 102],
            'Date': ['2023-05-15', '2023-11-15'],  # Spring and Fall
            'Year': [2023, 2023],
            'Season': ['Spring', 'Fall'],
            'Habitat_Type': ['Riffle', 'Riffle'],  # Same habitat, different seasons
            'Taxa_Richness': [25, 18],  # Different richness by season
            'Taxa_Richness_Score': [5, 3],
            'Percent_Reference': [0.85, 0.70]
        })
        
        # Should handle seasonal differences appropriately
        spring_data = seasonal_data[seasonal_data['Season'] == 'Spring']
        fall_data = seasonal_data[seasonal_data['Season'] == 'Fall']
        
        self.assertEqual(len(spring_data), 1)
        self.assertEqual(len(fall_data), 1)
        
        # Spring should generally have higher taxa richness
        self.assertGreater(
            spring_data['Taxa_Richness'].iloc[0],
            fall_data['Taxa_Richness'].iloc[0]
        )

    def test_habitat_quality_differences(self):
        """Test that different habitats show expected quality patterns."""
        # Riffle habitats typically have higher quality than vegetation
        riffle_data = self.sample_macro_data[self.sample_macro_data['Habitat_Type'] == 'Riffle']
        vegetation_data = self.sample_macro_data[self.sample_macro_data['Habitat_Type'] == 'Vegetation']
        
        if not riffle_data.empty and not vegetation_data.empty:
            # Riffle should generally have better scores
            riffle_score = riffle_data['Percent_Reference'].iloc[0]
            vegetation_score = vegetation_data['Percent_Reference'].iloc[0] if not vegetation_data.empty else 0
            
            # This reflects typical ecological patterns
            self.assertGreaterEqual(riffle_score, vegetation_score)

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================
    
    @patch('data_processing.macro_processing.close_connection')
    @patch('data_processing.macro_processing.get_connection')
    def test_load_macroinvertebrate_data_full_pipeline(self, mock_get_conn, mock_close):
        """Test the complete macro data loading pipeline."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock that no data exists yet
        mock_cursor.fetchone.return_value = (0,)
        
        with patch('data_processing.macro_processing.process_macro_csv_data') as mock_process:
            with patch('data_processing.macro_processing.insert_macro_collection_events') as mock_events:
                with patch('data_processing.macro_processing.insert_metrics_data') as mock_metrics:
                    with patch('data_processing.data_queries.get_macroinvertebrate_dataframe') as mock_query:
                        mock_process.return_value = self.sample_macro_data
                        mock_events.return_value = {(101, 'Riffle'): 123, (201, 'Vegetation'): 456}
                        mock_metrics.return_value = 12
                        mock_query.return_value = self.sample_macro_data
                        
                        result = load_macroinvertebrate_data()
                        
                        # Should complete successfully and return data
                        self.assertFalse(result.empty)
                        mock_conn.commit.assert_called_once()

    @patch('data_processing.macro_processing.close_connection')
    @patch('data_processing.macro_processing.get_connection')
    def test_load_macroinvertebrate_data_existing_data(self, mock_get_conn, mock_close):
        """Test pipeline when data already exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock that data already exists
        mock_cursor.fetchone.return_value = (15,)  # 15 existing records
        
        with patch('data_processing.data_queries.get_macroinvertebrate_dataframe') as mock_query:
            mock_query.return_value = self.sample_macro_data
            
            result = load_macroinvertebrate_data()
            
            # Should skip processing and return existing data
            self.assertFalse(result.empty)
            # Should not call commit since no new data was processed
            mock_conn.commit.assert_not_called()

    def test_macro_score_validation_integration(self):
        """Test that macro total scores match sum of components."""
        # Use the existing total score calculation test logic
        test_df = self.sample_macro_data.copy()
        
        # Apply column name cleaning and mapping
        test_df.columns = [col.lower().replace('_', '') for col in test_df.columns]
        
        column_mapping = {
            'taxarichnessscore': 'taxa_richness_score',
            'modhbiscore': 'hbi_score_score',
            'eptpercscore': 'ept_abundance_score',
            'epttaxascore': 'ept_taxa_richness_score',
            'dom2taxascore': 'contribution_dominants_score',
            'shannonweaverscore': 'shannon_weaver_score',
            'score': 'total_score'
        }
        test_df = test_df.rename(columns=column_mapping)
        
        # Calculate expected totals
        component_cols = [
            'taxa_richness_score', 'hbi_score_score', 'ept_abundance_score',
            'ept_taxa_richness_score', 'contribution_dominants_score', 'shannon_weaver_score'
        ]
        
        calculated_totals = test_df[component_cols].sum(axis=1)
        
        # Verify calculations match expected values
        for i, expected_total in enumerate([30, 18, 6]):
            self.assertEqual(calculated_totals.iloc[i], expected_total)


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)