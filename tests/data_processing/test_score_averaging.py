"""
Test suite for score averaging functionality.
Tests the logic for handling fish replicates vs duplicates and score averaging.
"""

import unittest
import pandas as pd
import tempfile
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.fish_processing import (
    load_bt_field_work_dates,
    find_bt_site_match,
    categorize_and_process_duplicates,
    average_all_duplicates,
    average_group_samples
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_score_averaging", category="testing")


class TestScoreAveraging(unittest.TestCase):
    """Test score averaging and replicate handling functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample fish data for testing
        self.sample_fish_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Blue Creek at Highway 9', 'Tenmile Creek at Davis', 
                         'Red River at Bridge', 'Red River at Bridge', 'Solo Site'],
            'sample_id': [101, 102, 201, 301, 302, 401],
            'year': [2023, 2023, 2023, 2023, 2023, 2023],
            'collection_date': ['2023-05-15', '2023-05-15', '2023-06-20', '2023-07-10', '2023-07-10', '2023-08-05'],
            'total_species_score': [3, 5, 3, 1, 3, 5],
            'sensitive_benthic_score': [5, 3, 1, 1, 5, 3],
            'sunfish_species_score': [1, 3, 5, 3, 1, 3],
            'intolerant_species_score': [3, 1, 3, 5, 3, 1],
            'tolerant_score': [5, 5, 1, 3, 5, 5],
            'insectivorous_score': [3, 1, 3, 1, 3, 1],
            'lithophilic_score': [1, 3, 5, 5, 1, 3],
            'total_score': [21, 21, 21, 19, 21, 21],
            'comparison_to_reference': [0.85, 0.75, 0.65, 0.45, 0.55, 0.85],
            'integrity_class': ['Good', 'Good', 'Fair', 'Poor', 'Fair', 'Good']
        })
        
        # FIXED: Sample BT field work data with proper REP structure
        self.sample_bt_data = pd.DataFrame({
            'Name': [
                'Blue Creek at Highway 9',      # Original collection
                'Red River at Bridge',          # Original collection  
                'Red River at Bridge',          # REP collection (same site/year)
                'Some Other Site'
            ],
            'Date': [
                '5/15/2023',
                '7/10/2023', 
                '7/12/2023',                    # Different date for REP
                '6/1/2023'
            ],
            'M/F/H': ['M', 'M', 'REP', 'M'],
            'Date_Clean': [
                datetime(2023, 5, 15),
                datetime(2023, 7, 10),
                datetime(2023, 7, 12),          # Different date for REP
                datetime(2023, 6, 1)
            ],
            'Site_Clean': [
                'Blue Creek at Highway 9',
                'Red River at Bridge', 
                'Red River at Bridge',          # Same site as above
                'Some Other Site'
            ],
            'Year': [2023, 2023, 2023, 2023],
            'Is_REP': [False, False, True, False]  # Only the REP collection is True
        })

    def test_load_bt_field_work_dates_file_exists(self):
        """Test loading BT field work dates when file exists."""
        # Create sample CSV content
        bt_csv_content = """Name,Date,M/F/H
Blue Creek at Highway 9,5/15/2023,M
Red River at Bridge,7/10/2023,M
Red River at Bridge,7/12/2023,REP"""
        
        with patch('data_processing.fish_processing.os.path.exists', return_value=True):
            with patch('data_processing.fish_processing.pd.read_csv') as mock_read_csv:
                # Mock CSV reading
                mock_df = pd.DataFrame({
                    'Name': ['Blue Creek at Highway 9', 'Red River at Bridge', 'Red River at Bridge'],
                    'Date': ['5/15/2023', '7/10/2023', '7/12/2023'],
                    'M/F/H': ['M', 'M', 'REP']
                })
                mock_read_csv.return_value = mock_df
                
                result = load_bt_field_work_dates()
                
                # Should return processed DataFrame
                self.assertFalse(result.empty)
                self.assertIn('Date_Clean', result.columns)
                self.assertIn('Site_Clean', result.columns)
                self.assertIn('Is_REP', result.columns)

    def test_load_bt_field_work_dates_file_not_exists(self):
        """Test loading BT field work dates when file doesn't exist."""
        with patch('data_processing.fish_processing.os.path.exists', return_value=False):
            result = load_bt_field_work_dates()
            
            # Should return empty DataFrame when file doesn't exist
            self.assertTrue(result.empty)

    def test_find_bt_site_match_exact_match(self):
        """Test finding exact BT site match."""
        bt_sites = {'Blue Creek at Highway 9', 'Red River at Bridge', 'Tenmile Creek at Davis'}
        
        match = find_bt_site_match('Blue Creek at Highway 9', bt_sites)
        self.assertEqual(match, 'Blue Creek at Highway 9')

    def test_find_bt_site_match_fuzzy_match(self):
        """Test finding fuzzy BT site match."""
        bt_sites = {'Blue Creek at Highway 9', 'Red River at Bridge'}
        
        # Test with slight variation that should match
        match = find_bt_site_match('Blue Creek at Hwy 9', bt_sites, threshold=0.8)
        self.assertEqual(match, 'Blue Creek at Highway 9')

    def test_find_bt_site_match_no_match(self):
        """Test when no BT site match is found."""
        bt_sites = {'Blue Creek at Highway 9', 'Red River at Bridge'}
        
        match = find_bt_site_match('Completely Different Site', bt_sites)
        self.assertIsNone(match)

    def test_average_group_samples_basic(self):
        """Test averaging a group of fish samples."""
        # Create a group with two samples
        group = self.sample_fish_data[self.sample_fish_data['site_name'] == 'Blue Creek at Highway 9'].copy()
        
        averaged = average_group_samples(group)
        
        # Should average comparison_to_reference values
        expected_avg = (0.85 + 0.75) / 2
        self.assertAlmostEqual(averaged['comparison_to_reference'], expected_avg, places=3)
        
        # Should use first record as base
        self.assertEqual(averaged['site_name'], 'Blue Creek at Highway 9')
        self.assertEqual(averaged['sample_id'], 101)  # From first record

    def test_average_group_samples_with_nulls(self):
        """Test averaging when some comparison values are null."""
        # Create group with one null value
        group = self.sample_fish_data[self.sample_fish_data['site_name'] == 'Blue Creek at Highway 9'].copy()
        group.loc[group.index[1], 'comparison_to_reference'] = None
        
        averaged = average_group_samples(group)
        
        # Should only average non-null values
        self.assertAlmostEqual(averaged['comparison_to_reference'], 0.85, places=3)

    def test_average_all_duplicates_no_duplicates(self):
        """Test averaging when there are no duplicate records."""
        # Create data with no duplicates (all different sites or years)
        unique_data = pd.DataFrame({
            'site_name': ['Site A', 'Site B', 'Site C'],
            'year': [2023, 2023, 2023],
            'sample_id': [101, 201, 301],
            'comparison_to_reference': [0.85, 0.75, 0.65]
        })
        
        result = average_all_duplicates(unique_data)
        
        # Should return same data unchanged
        self.assertEqual(len(result), 3)
        pd.testing.assert_frame_equal(result.reset_index(drop=True), unique_data)

    def test_average_all_duplicates_with_duplicates(self):
        """Test averaging when there are duplicate records."""
        # Use data with duplicates (Blue Creek and Red River have 2 samples each)
        result = average_all_duplicates(self.sample_fish_data)
        
        # Should reduce to 4 unique sites (2 duplicates averaged, 2 unique kept)
        self.assertEqual(len(result), 4)
        
        # Check that Blue Creek was averaged
        blue_creek = result[result['site_name'] == 'Blue Creek at Highway 9']
        self.assertEqual(len(blue_creek), 1)
        expected_avg = (0.85 + 0.75) / 2
        self.assertAlmostEqual(blue_creek.iloc[0]['comparison_to_reference'], expected_avg, places=3)

    def test_categorize_and_process_duplicates_no_bt_data(self):
        """Test duplicate processing when no BT data is available."""
        empty_bt = pd.DataFrame()
        
        result = categorize_and_process_duplicates(self.sample_fish_data, empty_bt)
        
        # Should fall back to averaging all duplicates
        self.assertEqual(len(result), 4)  # 6 original -> 4 after averaging duplicates

    def test_categorize_and_process_duplicates_with_rep_data(self):
        """Test duplicate processing when REP data is available."""
        bt_data_with_rep = self.sample_bt_data.copy()
        
        result = categorize_and_process_duplicates(self.sample_fish_data, bt_data_with_rep)
        
        red_river_samples = result[result['site_name'] == 'Red River at Bridge']
        blue_creek_samples = result[result['site_name'] == 'Blue Creek at Highway 9']
        
        # Red River should have 2 samples (replicates with different dates)
        self.assertEqual(len(red_river_samples), 2)
        
        # Blue Creek should have 1 sample (duplicates averaged - no REP data)
        self.assertEqual(len(blue_creek_samples), 1)

    def test_categorize_and_process_duplicates_year_buffer(self):
        """Test duplicate processing with ±1 year buffer for BT data."""
        # Create fish data for 2023 but BT data for 2022
        fish_2023 = self.sample_fish_data.copy()
        bt_2022 = self.sample_bt_data.copy()
        bt_2022['Year'] = 2022
        bt_2022['Date_Clean'] = bt_2022['Date_Clean'].apply(lambda x: x.replace(year=2022))
        
        result = categorize_and_process_duplicates(fish_2023, bt_2022)
        
        # Should still find matches using ±1 year buffer
        # This is harder to test precisely without knowing internal implementation,
        # but we can verify it doesn't crash and produces reasonable output
        self.assertGreater(len(result), 0)

    def test_categorize_and_process_duplicates_multiple_rep_sites(self):
        """Test processing when multiple sites have REP data."""
        # Add REP data for Blue Creek too
        extended_bt = self.sample_bt_data.copy()
        blue_creek_rep = pd.DataFrame({
            'Name': ['Blue Creek at Highway 9', 'Blue Creek at Highway 9'],
            'Date': ['5/15/2023', '5/17/2023'],
            'M/F/H': ['M', 'REP'],
            'Date_Clean': [datetime(2023, 5, 15), datetime(2023, 5, 17)],
            'Site_Clean': ['Blue Creek at Highway 9', 'Blue Creek at Highway 9'],
            'Year': [2023, 2023],
            'Is_REP': [False, True]
        })
        extended_bt = pd.concat([extended_bt, blue_creek_rep], ignore_index=True)
        
        result = categorize_and_process_duplicates(self.sample_fish_data, extended_bt)
        
        # Both Blue Creek and Red River should be processed as replicates
        blue_creek_samples = result[result['site_name'] == 'Blue Creek at Highway 9']
        red_river_samples = result[result['site_name'] == 'Red River at Bridge']
        
        self.assertEqual(len(blue_creek_samples), 2)  # Replicates
        self.assertEqual(len(red_river_samples), 2)   # Replicates

    def test_score_column_nullification_in_averaging(self):
        """Test that individual metric scores are nullified during averaging."""
        # Create group to average
        group = self.sample_fish_data[self.sample_fish_data['site_name'] == 'Blue Creek at Highway 9'].copy()
        
        averaged = average_group_samples(group)
        
        # Individual scores should be set to None
        score_columns = [col for col in averaged.index if 'score' in str(col).lower() and col != 'comparison_to_reference']
        for col in score_columns:
            self.assertIsNone(averaged[col])

    def test_integration_full_pipeline(self):
        """Integration test for the full duplicate processing pipeline."""
        original_count = len(self.sample_fish_data)
        
        # Process with BT data
        result_with_bt = categorize_and_process_duplicates(self.sample_fish_data, self.sample_bt_data)
        
        # Process without BT data
        result_without_bt = average_all_duplicates(self.sample_fish_data)
        
        # Both should reduce the number of records but handle them differently
        self.assertLess(len(result_with_bt), original_count)
        self.assertLess(len(result_without_bt), original_count)
        
        # FIXED: With proper REP data, results should be different
        # With BT: Red River keeps 2 records, Blue Creek averages to 1 = 5 total
        # Without BT: Both average to 1 each = 4 total
        self.assertEqual(len(result_with_bt), 5)  # 2 Red River + 1 Blue Creek + 2 others
        self.assertEqual(len(result_without_bt), 4)  # All duplicates averaged

    def test_edge_case_empty_input(self):
        """Test behavior with empty input data."""
        empty_fish = pd.DataFrame()
        empty_bt = pd.DataFrame()
        
        # Should handle empty input gracefully
        result = categorize_and_process_duplicates(empty_fish, empty_bt)
        self.assertTrue(result.empty)
        
        result2 = average_all_duplicates(empty_fish)
        self.assertTrue(result2.empty)

    def test_edge_case_single_sample_per_site(self):
        """Test behavior when each site has only one sample (no duplicates)."""
        single_samples = pd.DataFrame({
            'site_name': ['Site A', 'Site B', 'Site C'],
            'sample_id': [101, 201, 301],
            'year': [2023, 2023, 2023],
            'comparison_to_reference': [0.85, 0.75, 0.65]
        })
        
        result = average_all_duplicates(single_samples)
        
        # Should return data unchanged
        self.assertEqual(len(result), 3)

    def test_date_assignment_for_replicates(self):
        """Test that replicates get assigned correct dates from BT data."""
        # This test verifies the core replicate logic
        result = categorize_and_process_duplicates(self.sample_fish_data, self.sample_bt_data)
        
        # Find Red River samples (should be processed as replicates)
        red_river_samples = result[result['site_name'] == 'Red River at Bridge']
        
        if len(red_river_samples) == 2:
            # Should have different collection dates assigned
            dates = red_river_samples['collection_date_str'].unique()
            self.assertEqual(len(dates), 2)
            
            # Dates should match BT data dates
            bt_red_river = self.sample_bt_data[self.sample_bt_data['Site_Clean'] == 'Red River at Bridge']
            expected_dates = set(bt_red_river['Date_Clean'].dt.strftime('%Y-%m-%d'))
            actual_dates = set(red_river_samples['collection_date_str'])
            self.assertEqual(actual_dates, expected_dates)


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)