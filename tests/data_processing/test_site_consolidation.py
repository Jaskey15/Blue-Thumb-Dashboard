"""
Test suite for site consolidation functionality.
Tests the logic in data_processing.consolidate_sites module.
"""

import unittest
import pandas as pd
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from data_processing.consolidate_sites import (
    extract_sites_from_csv, 
    detect_conflicts, 
    consolidate_sites,
    save_consolidated_data
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_site_consolidation", category="testing")


class TestSiteConsolidation(unittest.TestCase):
    """Test site consolidation functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Sample data for testing
        self.sample_site_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Tenmile Creek at Davis', 'Red River at Bridge'],
            'Latitude': [35.1234, 34.5678, 33.9876],
            'Longitude': [-97.1234, -96.5678, -95.9876],
            'County': ['Cleveland', 'Murray', 'Bryan'],
            'RiverBasin': ['Canadian', 'Washita', 'Red'],
            'Mod_Ecoregion': ['Cross Timbers', 'Cross Timbers', 'South Central Plains']
        })
        
        self.sample_chemical_data = pd.DataFrame({
            'SiteName': ['Blue Creek at Highway 9', 'Boggy Creek at Main St', 'Tenmile Creek at Davis'],
            'Latitude': [35.1234, 34.2345, 34.5678],
            'Longitude': [-97.1234, -96.2345, -96.5678],
            'County': ['Cleveland', 'Pontotoc', 'Murray'],
            'RiverBasin': ['Canadian', 'Red', 'Washita']
        })
        
        self.sample_updated_chemical_data = pd.DataFrame({
            'Site Name': ['Blue Creek at Highway 9', 'New Site from Updated Data'],
            'lat': [35.1234, 35.5555],
            'lon': [-97.1234, -97.5555],
            'CountyName': ['Cleveland', 'Logan']
        })

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_dir)

    def test_extract_sites_basic_functionality(self):
        """Test basic site extraction from CSV configuration."""
        # Create a mock configuration for site_data
        config = {
            'file': 'test_site_data.csv',
            'site_column': 'SiteName',
            'lat_column': 'Latitude',
            'lon_column': 'Longitude',
            'county_column': 'County',
            'basin_column': 'RiverBasin',
            'ecoregion_column': 'Mod_Ecoregion',
            'description': 'Test site data'
        }
        
        # Mock the file loading to return our sample data
        with patch('data_processing.consolidate_sites.pd.read_csv') as mock_read_csv:
            with patch('data_processing.consolidate_sites.os.path.exists', return_value=True):
                mock_read_csv.return_value = self.sample_site_data
                
                result = extract_sites_from_csv(config)
                
                # Verify we got the expected number of sites
                self.assertEqual(len(result), 3)
                
                # Verify all expected columns are present
                expected_columns = ['site_name', 'latitude', 'longitude', 'county', 'river_basin', 'ecoregion']
                for col in expected_columns:
                    self.assertIn(col, result.columns)
                
                # Verify site names are correctly extracted
                expected_sites = ['Blue Creek at Highway 9', 'Tenmile Creek at Davis', 'Red River at Bridge']
                actual_sites = result['site_name'].tolist()
                self.assertEqual(set(actual_sites), set(expected_sites))

    def test_extract_sites_missing_columns(self):
        """Test extraction when some metadata columns are missing."""
        config = {
            'file': 'test_chemical_data.csv',
            'site_column': 'SiteName',
            'lat_column': 'Latitude',
            'lon_column': 'Longitude',
            'county_column': 'County',
            'basin_column': 'RiverBasin',
            'ecoregion_column': None,  # This column doesn't exist in chemical data
            'description': 'Test chemical data'
        }
        
        with patch('data_processing.consolidate_sites.pd.read_csv') as mock_read_csv:
            with patch('data_processing.consolidate_sites.os.path.exists', return_value=True):
                mock_read_csv.return_value = self.sample_chemical_data
                
                result = extract_sites_from_csv(config)
                
                # Should still return data but with None for missing ecoregion
                self.assertEqual(len(result), 3)
                self.assertTrue(result['ecoregion'].isnull().all())

    def test_extract_sites_file_not_found(self):
        """Test behavior when CSV file doesn't exist."""
        config = {
            'file': 'nonexistent.csv',
            'site_column': 'SiteName',
            'lat_column': 'Latitude',
            'lon_column': 'Longitude',
            'county_column': 'County',
            'basin_column': 'RiverBasin',
            'ecoregion_column': 'Mod_Ecoregion',
            'description': 'Nonexistent file'
        }
        
        with patch('data_processing.consolidate_sites.os.path.exists', return_value=False):
            result = extract_sites_from_csv(config)
            
            # Should return empty DataFrame when file doesn't exist
            self.assertTrue(result.empty)

    def test_detect_conflicts_no_conflicts(self):
        """Test conflict detection when there are no conflicts."""
        existing_site = pd.Series({
            'latitude': 35.1234,
            'longitude': -97.1234,
            'county': 'Cleveland',
            'river_basin': 'Canadian',
            'ecoregion': 'Cross Timbers'
        })
        
        new_site = pd.Series({
            'latitude': 35.1234,  # Same coordinates
            'longitude': -97.1234,
            'county': 'Cleveland',  # Same metadata
            'river_basin': 'Canadian',
            'ecoregion': None  # Missing data, not a conflict
        })
        
        conflicts = detect_conflicts('Test Site', existing_site, new_site)
        self.assertEqual(len(conflicts), 0)

    def test_detect_conflicts_coordinate_conflict(self):
        """Test conflict detection for coordinate differences."""
        existing_site = pd.Series({
            'latitude': 35.1234,
            'longitude': -97.1234,
            'county': 'Cleveland',
            'river_basin': 'Canadian',
            'ecoregion': 'Cross Timbers'
        })
        
        new_site = pd.Series({
            'latitude': 35.9999,  # Different latitude
            'longitude': -97.1234,
            'county': 'Cleveland',
            'river_basin': 'Canadian',
            'ecoregion': 'Cross Timbers'
        })
        
        conflicts = detect_conflicts('Test Site', existing_site, new_site)
        self.assertEqual(len(conflicts), 1)
        self.assertIn('latitude', conflicts[0])

    def test_detect_conflicts_metadata_conflict(self):
        """Test conflict detection for metadata differences."""
        existing_site = pd.Series({
            'latitude': 35.1234,
            'longitude': -97.1234,
            'county': 'Cleveland',
            'river_basin': 'Canadian',
            'ecoregion': 'Cross Timbers'
        })
        
        new_site = pd.Series({
            'latitude': 35.1234,
            'longitude': -97.1234,
            'county': 'McClain',  # Different county
            'river_basin': 'Canadian',
            'ecoregion': 'Cross Timbers'
        })
        
        conflicts = detect_conflicts('Test Site', existing_site, new_site)
        self.assertEqual(len(conflicts), 1)
        self.assertIn('county', conflicts[0])

    @patch('data_processing.consolidate_sites.extract_sites_from_csv')
    def test_consolidate_sites_priority_order(self, mock_extract):
        """Test that sites are processed in correct priority order."""
        # Mock the extract function to return different data for different configs
        def side_effect(config):
            if 'site_data' in config['file']:
                return pd.DataFrame({
                    'site_name': ['Blue Creek at Highway 9'],
                    'latitude': [35.1234],
                    'longitude': [-97.1234],
                    'county': ['Cleveland'],
                    'river_basin': ['Canadian'],
                    'ecoregion': ['Cross Timbers'],
                    'source_file': ['site_data.csv'],
                    'source_description': ['Master site data']
                })
            elif 'chemical_data' in config['file']:
                return pd.DataFrame({
                    'site_name': ['Blue Creek at Highway 9', 'New Chemical Site'],
                    'latitude': [35.1234, 34.5555],
                    'longitude': [-97.1234, -96.5555],
                    'county': ['Cleveland', 'Pontotoc'],
                    'river_basin': ['Canadian', 'Red'],
                    'ecoregion': [None, None],
                    'source_file': ['chemical_data.csv', 'chemical_data.csv'],
                    'source_description': ['Original chemical data', 'Original chemical data']
                })
            else:
                return pd.DataFrame()
        
        mock_extract.side_effect = side_effect
        
        consolidated_sites, conflicts_df = consolidate_sites()
        
        # Should have 2 sites total (1 from site_data, 1 new from chemical_data)
        self.assertEqual(len(consolidated_sites), 2)
        
        # Blue Creek should have data from site_data (higher priority)
        blue_creek = consolidated_sites[consolidated_sites['site_name'] == 'Blue Creek at Highway 9']
        self.assertEqual(len(blue_creek), 1)
        self.assertEqual(blue_creek.iloc[0]['ecoregion'], 'Cross Timbers')  # From site_data
        
        # Should have no conflicts since no conflicting data
        self.assertTrue(conflicts_df.empty)

    @patch('data_processing.consolidate_sites.extract_sites_from_csv')
    def test_consolidate_sites_metadata_filling(self, mock_extract):
        """Test that missing metadata gets filled from lower priority sources."""
        def side_effect(config):
            if 'site_data' in config['file']:
                return pd.DataFrame({
                    'site_name': ['Blue Creek at Highway 9'],
                    'latitude': [35.1234],
                    'longitude': [-97.1234],
                    'county': [None],  # Missing county in site_data
                    'river_basin': ['Canadian'],
                    'ecoregion': ['Cross Timbers'],
                    'source_file': ['site_data.csv'],
                    'source_description': ['Master site data']
                })
            elif 'chemical_data' in config['file']:
                return pd.DataFrame({
                    'site_name': ['Blue Creek at Highway 9'],
                    'latitude': [35.1234],
                    'longitude': [-97.1234],
                    'county': ['Cleveland'],  # County available in chemical_data
                    'river_basin': ['Canadian'],
                    'ecoregion': [None],
                    'source_file': ['chemical_data.csv'],
                    'source_description': ['Original chemical data']
                })
            else:
                return pd.DataFrame()
        
        mock_extract.side_effect = side_effect
        
        consolidated_sites, conflicts_df = consolidate_sites()
        
        # Should have 1 site with county filled from chemical_data
        self.assertEqual(len(consolidated_sites), 1)
        blue_creek = consolidated_sites.iloc[0]
        self.assertEqual(blue_creek['county'], 'Cleveland')  # Filled from chemical_data
        self.assertEqual(blue_creek['ecoregion'], 'Cross Timbers')  # From site_data

    def test_save_consolidated_data(self):
        """Test saving consolidated data to CSV files."""
        # Create sample consolidated data
        consolidated_sites = pd.DataFrame({
            'site_name': ['Site 1', 'Site 2'],
            'latitude': [35.1, 34.5],
            'longitude': [-97.1, -96.5],
            'county': ['County A', 'County B'],
            'river_basin': ['Basin 1', 'Basin 2'],
            'ecoregion': ['Eco 1', 'Eco 2']
        })
        
        conflicts_df = pd.DataFrame({
            'site_name': ['Conflict Site'],
            'conflicts': [['latitude: 35.1 vs 35.2']],
            'existing_source': ['site_data.csv'],
            'new_source': ['chemical_data.csv']
        })
        
        with patch('data_processing.consolidate_sites.os.path.join') as mock_join:
            with patch('data_processing.consolidate_sites.pd.DataFrame.to_csv') as mock_to_csv:
                mock_join.return_value = '/fake/path/output.csv'
                
                save_consolidated_data(consolidated_sites, conflicts_df)
                
                # Should call to_csv twice (once for sites, once for conflicts)
                self.assertEqual(mock_to_csv.call_count, 2)

    def test_empty_input_handling(self):
        """Test behavior with empty input data."""
        with patch('data_processing.consolidate_sites.extract_sites_from_csv') as mock_extract:
            mock_extract.return_value = pd.DataFrame()  # Always return empty
            
            consolidated_sites, conflicts_df = consolidate_sites()
            
            # Should handle empty input gracefully
            self.assertTrue(consolidated_sites.empty)
            self.assertTrue(conflicts_df.empty)

    def test_site_name_cleaning(self):
        """Test that site names are properly cleaned during extraction."""
        # Test data with whitespace issues
        messy_data = pd.DataFrame({
            'SiteName': ['  Blue Creek at Highway 9  ', 'Tenmile Creek at Davis\n', 'Red  River   at Bridge'],
            'Latitude': [35.1234, 34.5678, 33.9876],
            'Longitude': [-97.1234, -96.5678, -95.9876]
        })
        
        config = {
            'file': 'test.csv',
            'site_column': 'SiteName',
            'lat_column': 'Latitude',
            'lon_column': 'Longitude',
            'county_column': None,
            'basin_column': None,
            'ecoregion_column': None,
            'description': 'Test data'
        }
        
        with patch('data_processing.consolidate_sites.pd.read_csv') as mock_read_csv:
            with patch('data_processing.consolidate_sites.os.path.exists', return_value=True):
                mock_read_csv.return_value = messy_data
                
                result = extract_sites_from_csv(config)
                
                # Site names should be cleaned of extra whitespace
                expected_clean_names = [
                    'Blue Creek at Highway 9',
                    'Tenmile Creek at Davis',
                    'Red River at Bridge'
                ]
                actual_names = result['site_name'].tolist()
                self.assertEqual(actual_names, expected_clean_names)


if __name__ == '__main__':
    # Set up test discovery and run tests
    unittest.main(verbosity=2)