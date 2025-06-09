"""
Test suite for duplicate site merging functionality.
Tests the coordinate-based site consolidation logic in merge_sites.py.
"""

import unittest
import pandas as pd
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.merge_sites import (
    find_duplicate_coordinate_groups,
    determine_preferred_site,
    analyze_coordinate_duplicates,
    merge_duplicate_sites,
    transfer_site_data
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_duplicate_merging", category="testing")


class TestDuplicateMerging(unittest.TestCase):
    """Test coordinate-based duplicate site merging functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample sites with coordinate duplicates
        self.sample_sites_with_duplicates = pd.DataFrame({
            'site_id': [1, 2, 3, 4, 5],
            'site_name': ['Blue Creek Site A', 'Blue Creek Site B', 'Red River Main', 'Red River Alt', 'Unique Site'],
            'rounded_lat': [35.123, 35.123, 34.567, 34.567, 33.999],  # First 4 have duplicates
            'rounded_lon': [-97.123, -97.123, -96.567, -96.567, -95.999],
            'latitude': [35.1234, 35.1235, 34.5678, 34.5679, 33.9999],  # Slightly different actual coords
            'longitude': [-97.1234, -97.1235, -96.5678, -96.5679, -95.9999],
            'county': ['Cleveland', 'Cleveland', 'Murray', 'Murray', 'Bryan'],
            'river_basin': ['Canadian', 'Canadian', 'Red', 'Red', 'Red'],
            'ecoregion': ['Cross Timbers', 'Cross Timbers', 'Plains', 'Plains', 'Plains']
        })
        
        # Sample sites with no duplicates
        self.sample_sites_no_duplicates = pd.DataFrame({
            'site_id': [1, 2, 3],
            'site_name': ['Site A', 'Site B', 'Site C'],
            'rounded_lat': [35.123, 34.567, 33.999],
            'rounded_lon': [-97.123, -96.567, -95.999],
            'latitude': [35.1234, 34.5678, 33.9999],
            'longitude': [-97.1234, -96.5678, -95.9999]
        })
        
        # Sample CSV site lists for priority testing
        self.updated_chemical_sites = {'Blue Creek Site A', 'Some Other Site'}
        self.chemical_data_sites = {'Red River Main', 'Another Site'}

    @patch('data_processing.merge_sites.get_connection')
    def test_find_duplicate_coordinate_groups_with_duplicates(self, mock_get_connection):
        """Test finding coordinate duplicates when they exist."""
        # Mock database connection and query result
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        # Mock pd.read_sql_query to return our test data
        with patch('data_processing.merge_sites.pd.read_sql_query') as mock_read_sql:
            mock_read_sql.return_value = self.sample_sites_with_duplicates
            
            result = find_duplicate_coordinate_groups()
            
            # Should return only the duplicate sites (4 out of 5)
            self.assertEqual(len(result), 4)
            
            # Should have 2 groups of duplicates
            duplicate_groups = result.groupby(['rounded_lat', 'rounded_lon'])
            self.assertEqual(len(duplicate_groups), 2)

    @patch('data_processing.merge_sites.get_connection')
    def test_find_duplicate_coordinate_groups_no_duplicates(self, mock_get_connection):
        """Test finding coordinate duplicates when none exist."""
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        with patch('data_processing.merge_sites.pd.read_sql_query') as mock_read_sql:
            mock_read_sql.return_value = self.sample_sites_no_duplicates
            
            result = find_duplicate_coordinate_groups()
            
            # Should return empty DataFrame when no duplicates
            self.assertTrue(result.empty)

    def test_determine_preferred_site_updated_chemical_priority(self):
        """Test site selection prioritizes updated_chemical_data sites."""
        # Create a group with one site in updated_chemical
        group = self.sample_sites_with_duplicates[
            self.sample_sites_with_duplicates['rounded_lat'] == 35.123
        ].copy()
        
        preferred_site, sites_to_merge, reason = determine_preferred_site(
            group, self.updated_chemical_sites, self.chemical_data_sites
        )
        
        # Should prefer the site in updated_chemical_data
        self.assertEqual(preferred_site['site_name'], 'Blue Creek Site A')
        self.assertIn("updated_chemical", reason.lower())
        self.assertEqual(len(sites_to_merge), 1)  # Other site should be merged

    def test_determine_preferred_site_chemical_data_priority(self):
        """Test site selection falls back to chemical_data sites."""
        # Create a group with one site in chemical_data (but not updated_chemical)
        group = self.sample_sites_with_duplicates[
            self.sample_sites_with_duplicates['rounded_lat'] == 34.567
        ].copy()
        
        preferred_site, sites_to_merge, reason = determine_preferred_site(
            group, self.updated_chemical_sites, self.chemical_data_sites
        )
        
        # Should prefer the site in chemical_data
        self.assertEqual(preferred_site['site_name'], 'Red River Main')
        self.assertIn("chemical_data", reason.lower())
        self.assertEqual(len(sites_to_merge), 1)

    def test_determine_preferred_site_longest_name_fallback(self):
        """Test site selection falls back to longest name when no CSV matches."""
        # Create a group where neither site is in CSV data
        group = pd.DataFrame({
            'site_id': [10, 11],
            'site_name': ['Short', 'Much Longer Site Name'],
            'rounded_lat': [40.000, 40.000],
            'rounded_lon': [-100.000, -100.000]
        })
        
        empty_csv_sites = set()  # No sites in either CSV
        
        preferred_site, sites_to_merge, reason = determine_preferred_site(
            group, empty_csv_sites, empty_csv_sites
        )
        
        # Should prefer the longer name
        self.assertEqual(preferred_site['site_name'], 'Much Longer Site Name')
        self.assertIn("longest name", reason.lower())

    @patch('data_processing.merge_sites.get_connection')
    def test_transfer_site_data_basic(self, mock_get_connection):
        """Test transferring data between sites."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock the count queries to return some data
        mock_cursor.fetchone.side_effect = [
            (5,),  # chemical_collection_events
            (3,),  # fish_collection_events  
            (2,),  # macro_collection_events
            (1,)   # habitat_assessments
        ]
        
        result = transfer_site_data(mock_cursor, from_site_id=2, to_site_id=1)
        
        # Should return counts of transferred data
        expected_total = 5 + 3 + 2 + 1
        total_transferred = sum(result.values())
        self.assertEqual(total_transferred, expected_total)
        
        # Should have called UPDATE for each table with data
        self.assertEqual(mock_cursor.execute.call_count, 8)  # 4 counts + 4 updates

    @patch('data_processing.merge_sites.load_csv_files')
    @patch('data_processing.merge_sites.find_duplicate_coordinate_groups') 
    @patch('data_processing.merge_sites.get_connection')
    def test_analyze_coordinate_duplicates_with_data(self, mock_get_connection, mock_find_dupes, mock_load_csv):
        """Test analyzing coordinate duplicates when duplicates exist."""
        # Mock CSV loading
        mock_load_csv.return_value = (
            pd.DataFrame({'SiteName': ['Site A', 'Site B']}),  # site_data
            pd.DataFrame({'Site Name': ['Blue Creek Site A']}),  # updated_chemical
            pd.DataFrame({'SiteName': ['Red River Main']})  # chemical_data
        )
        
        # Mock finding duplicates
        mock_find_dupes.return_value = self.sample_sites_with_duplicates[
            self.sample_sites_with_duplicates['site_id'].isin([1, 2])  # Just one duplicate group
        ]
        
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        result = analyze_coordinate_duplicates()
        
        # Should return analysis results
        self.assertIsNotNone(result)
        self.assertIn('total_duplicate_sites', result)
        self.assertIn('duplicate_groups', result)
        self.assertEqual(result['total_duplicate_sites'], 2)
        self.assertEqual(result['duplicate_groups'], 1)

    @patch('data_processing.merge_sites.load_csv_files')
    @patch('data_processing.merge_sites.find_duplicate_coordinate_groups')
    @patch('data_processing.merge_sites.get_connection')
    def test_analyze_coordinate_duplicates_no_data(self, mock_get_connection, mock_find_dupes, mock_load_csv):
        """Test analyzing coordinate duplicates when none exist."""
        mock_load_csv.return_value = (
            pd.DataFrame({'SiteName': ['Site A']}),
            pd.DataFrame({'Site Name': ['Site B']}),
            pd.DataFrame({'SiteName': ['Site C']})
        )
        
        # Mock no duplicates found
        mock_find_dupes.return_value = pd.DataFrame()
        
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        result = analyze_coordinate_duplicates()
        
        # Should return zero counts
        self.assertEqual(result['total_duplicate_sites'], 0)
        self.assertEqual(result['duplicate_groups'], 0)

    @patch('data_processing.merge_sites.load_csv_files')
    @patch('data_processing.merge_sites.find_duplicate_coordinate_groups')
    @patch('data_processing.merge_sites.get_connection')
    def test_merge_duplicate_sites_integration(self, mock_get_connection, mock_find_dupes, mock_load_csv):
        """Integration test for the complete merge process."""
        # Mock CSV loading
        mock_load_csv.return_value = (
            pd.DataFrame({'SiteName': ['Site A']}),
            pd.DataFrame({'Site Name': ['Blue Creek Site A']}),
            pd.DataFrame({'SiteName': ['Red River Main']})
        )
        
        # Mock finding one group of duplicates
        duplicate_group = self.sample_sites_with_duplicates[
            self.sample_sites_with_duplicates['rounded_lat'] == 35.123
        ].copy()
        mock_find_dupes.return_value = duplicate_group
        
        # Mock database operations
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock transfer counts (some data to transfer)
        mock_cursor.fetchone.side_effect = [
            (2,), (1,), (0,), (1,)  # Counts for the transfer
        ]
        
        result = merge_duplicate_sites()
        
        # Should complete successfully
        self.assertTrue(result)
        
        # Should have called commit (not rollback)
        mock_conn.commit.assert_called()

    def test_edge_case_empty_group(self):
        """Test behavior with empty coordinate group."""
        empty_group = pd.DataFrame()
        
        preferred_site, sites_to_merge, reason = determine_preferred_site(
            empty_group, self.updated_chemical_sites, self.chemical_data_sites
        )
        
        # Should handle empty group gracefully
        self.assertIsNone(preferred_site)
        self.assertEqual(len(sites_to_merge), 0)


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)