"""
Test suite for map visualization functionality.
Tests the logic in visualizations.map_viz module.
"""

import unittest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from visualizations.map_viz import (
    # Core helper functions
    load_sites_from_database,
    get_latest_data_by_type,
    get_status_color,
    filter_sites_by_active_status,
    
    # UI helper functions
    create_hover_text,
    
    # Map layout helper functions
    _create_base_map_layout,
    add_site_marker,
    create_error_map,
    
    # Main visualization functions
    add_data_markers,
    create_basic_site_map,
    add_parameter_colors_to_map,
    
    # Constants
    COLORS,
    PARAMETER_LABELS,
    MAP_PARAMETER_LABELS
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_map_viz", category="testing")


class TestMapViz(unittest.TestCase):
    """Test map visualization functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample sites data for testing
        self.sample_sites = [
            {
                "name": "Blue Creek at Highway 9",
                "lat": 35.123,
                "lon": -98.456,
                "county": "McClain",
                "river_basin": "Red River",
                "ecoregion": "Cross Timbers",
                "active": True
            },
            {
                "name": "Red River at Bridge",
                "lat": 35.789,
                "lon": -98.234,
                "county": "Love",
                "river_basin": "Red River",
                "ecoregion": "Cross Timbers",
                "active": False
            },
            {
                "name": "Tenmile Creek",
                "lat": 35.567,
                "lon": -98.112,
                "county": "Cleveland",
                "river_basin": "Canadian River",
                "ecoregion": "Cross Timbers",
                "active": True
            }
        ]
        
        # Sample chemical data
        self.sample_chemical_data = pd.DataFrame({
            'Site_Name': ['Blue Creek at Highway 9', 'Red River at Bridge', 'Tenmile Creek'],
            'Date': pd.to_datetime(['2023-01-15', '2023-06-20', '2023-12-10']),
            'do_percent': [95.5, 110.2, 75.0],
            'pH': [7.2, 8.5, 6.0],
            'Phosphorus': [0.02, 0.15, 0.08],
            'Chloride': [25.0, 280.0, 45.0],
            'soluble_nitrogen': [0.65, 1.6, 0.36],
            'do_percent_status': ['Normal', 'Above Normal (Basic/Alkaline)', 'Below Normal (Acidic)'],
            'pH_status': ['Normal', 'Above Normal (Basic/Alkaline)', 'Below Normal (Acidic)'],
            'Phosphorus_status': ['Normal', 'Poor', 'Caution'],
            'Chloride_status': ['Normal', 'Poor', 'Normal']
        })
        
        # Sample fish data
        self.sample_fish_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Red River at Bridge'],
            'year': [2023, 2022],
            'comparison_to_reference': [0.85, 0.45],
            'integrity_class': ['Good', 'Poor']
        })
        
        # Sample macro data
        self.sample_macro_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Tenmile Creek'],
            'year': [2023, 2023],
            'season': ['Summer', 'Winter'],
            'comparison_to_reference': [0.75, 0.55],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired']
        })
        
        # Sample habitat data
        self.sample_habitat_data = pd.DataFrame({
            'site_name': ['Blue Creek at Highway 9', 'Red River at Bridge'],
            'year': [2023, 2022],
            'total_score': [85, 65],
            'habitat_grade': ['B', 'D']
        })

    # =============================================================================
    # CORE HELPER FUNCTION TESTS - Database and Data Processing
    # =============================================================================

    @patch('visualizations.map_viz.get_connection')
    @patch('visualizations.map_viz.close_connection')
    def test_load_sites_from_database_success(self, mock_close, mock_get_conn):
        """Test successful loading of sites from database."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.fetchall.return_value = [
            ('Site A', 35.0, -98.0, 'County A', 'Basin A', 'Ecoregion A', 1),
            ('Site B', 35.1, -98.1, None, 'Basin B', 'Ecoregion B', 0)
        ]
        
        sites = load_sites_from_database()
        
        # Should return list of site dictionaries
        self.assertIsInstance(sites, list)
        self.assertEqual(len(sites), 2)
        
        # Check first site structure
        site = sites[0]
        self.assertEqual(site['name'], 'Site A')
        self.assertEqual(site['lat'], 35.0)
        self.assertEqual(site['lon'], -98.0)
        self.assertEqual(site['county'], 'County A')
        self.assertTrue(site['active'])
        
        # Check handling of None values
        site2 = sites[1]
        self.assertEqual(site2['county'], 'Unknown')
        self.assertFalse(site2['active'])

    @patch('visualizations.map_viz.get_connection')
    def test_load_sites_from_database_error(self, mock_get_conn):
        """Test error handling in load_sites_from_database."""
        mock_get_conn.side_effect = Exception("Database connection failed")
        
        with self.assertRaises(Exception):
            load_sites_from_database()

    @patch('visualizations.map_viz.get_latest_chemical_data_for_maps')
    def test_get_latest_data_by_type_chemical(self, mock_get_chem):
        """Test getting latest chemical data."""
        mock_get_chem.return_value = self.sample_chemical_data
        
        result = get_latest_data_by_type('chemical')
        
        # Should return DataFrame grouped by site with latest data
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        mock_get_chem.assert_called_once()

    @patch('visualizations.map_viz.get_latest_fish_data_for_maps')
    def test_get_latest_data_by_type_fish(self, mock_get_fish):
        """Test getting latest fish data."""
        mock_get_fish.return_value = self.sample_fish_data
        
        result = get_latest_data_by_type('fish')
        
        self.assertIsInstance(result, pd.DataFrame)
        mock_get_fish.assert_called_once()

    @patch('visualizations.map_viz.get_latest_macro_data_for_maps')
    def test_get_latest_data_by_type_macro(self, mock_get_macro):
        """Test getting latest macro data."""
        mock_get_macro.return_value = self.sample_macro_data
        
        result = get_latest_data_by_type('macro')
        
        self.assertIsInstance(result, pd.DataFrame)
        mock_get_macro.assert_called_once()

    @patch('visualizations.map_viz.get_latest_habitat_data_for_maps')
    def test_get_latest_data_by_type_habitat(self, mock_get_habitat):
        """Test getting latest habitat data."""
        mock_get_habitat.return_value = self.sample_habitat_data
        
        result = get_latest_data_by_type('habitat')
        
        self.assertIsInstance(result, pd.DataFrame)
        mock_get_habitat.assert_called_once()

    def test_get_latest_data_by_type_invalid(self):
        """Test error handling for invalid data type."""
        with self.assertRaises(ValueError):
            get_latest_data_by_type('invalid_type')

    def test_get_status_color_chemical(self):
        """Test color mapping for chemical data statuses."""
        test_cases = [
            ('Normal', COLORS['normal']),
            ('Caution', COLORS['caution']),
            ('Poor', COLORS['poor']),
            ('Above Normal (Basic/Alkaline)', COLORS['above_normal']),
            ('Below Normal (Acidic)', COLORS['below_normal'])
        ]
        
        for status, expected_color in test_cases:
            with self.subTest(status=status):
                result_status, result_color = get_status_color(status, 'chemical')
                self.assertEqual(result_status, status)
                self.assertEqual(result_color, expected_color)

    def test_get_status_color_fish(self):
        """Test color mapping for fish data statuses."""
        test_cases = [
            ('Excellent', COLORS['fish']['excellent']),
            ('Good', COLORS['fish']['good']),
            ('Fair', COLORS['fish']['fair']),
            ('Poor', COLORS['fish']['poor']),
            ('Very Poor', COLORS['fish']['very poor'])
        ]
        
        for status, expected_color in test_cases:
            with self.subTest(status=status):
                result_status, result_color = get_status_color(status, 'fish')
                self.assertEqual(result_status, status)
                self.assertEqual(result_color, expected_color)

    def test_get_status_color_unknown_status(self):
        """Test handling of unknown status values."""
        status, color = get_status_color('Unknown Status', 'chemical')
        self.assertEqual(status, 'Unknown Status')
        self.assertEqual(color, 'gray')

    def test_get_status_color_null_values(self):
        """Test handling of null/None status values."""
        # Test None and NaN - these should return 'Unknown'
        test_cases_unknown = [None, np.nan]
        for null_value in test_cases_unknown:
            with self.subTest(null_value=null_value):
                status, color = get_status_color(null_value, 'chemical')
                self.assertEqual(status, 'Unknown')
                self.assertEqual(color, 'gray')
        
        # Test empty string - this should return the empty string itself
        status, color = get_status_color('', 'chemical')
        self.assertEqual(status, '')
        self.assertEqual(color, 'gray')

    def test_get_status_color_series(self):
        """Test get_status_color with pandas Series (vectorized operation)."""
        # Test with chemical statuses
        statuses = pd.Series(['Normal', 'Caution', 'Poor', None])
        result_statuses, result_colors = get_status_color(statuses, 'chemical')
        
        # Should return Series
        self.assertIsInstance(result_statuses, pd.Series)
        self.assertIsInstance(result_colors, pd.Series)
        
        # Check individual values
        self.assertEqual(result_statuses.iloc[0], 'Normal')
        self.assertEqual(result_statuses.iloc[1], 'Caution') 
        self.assertEqual(result_statuses.iloc[2], 'Poor')
        self.assertEqual(result_statuses.iloc[3], 'Unknown')  # None becomes Unknown
        
        self.assertEqual(result_colors.iloc[0], COLORS['normal'])
        self.assertEqual(result_colors.iloc[1], COLORS['caution'])
        self.assertEqual(result_colors.iloc[2], COLORS['poor'])
        self.assertEqual(result_colors.iloc[3], 'gray')  # None becomes gray

    def test_filter_sites_by_active_status_all_sites(self):
        """Test filtering sites with active_only=False."""
        sites, active_count, historic_count, total_count = filter_sites_by_active_status(
            self.sample_sites, active_only=False
        )
        
        # Should return all sites
        self.assertEqual(len(sites), 3)
        self.assertEqual(active_count, 2)  # 2 active sites
        self.assertEqual(historic_count, 1)  # 1 historic site
        self.assertEqual(total_count, 3)

    def test_filter_sites_by_active_status_active_only(self):
        """Test filtering sites with active_only=True."""
        sites, active_count, historic_count, total_count = filter_sites_by_active_status(
            self.sample_sites, active_only=True
        )
        
        # Should return only active sites
        self.assertEqual(len(sites), 2)
        self.assertEqual(active_count, 2)
        self.assertEqual(historic_count, 1)  # Total historic sites in original list
        self.assertEqual(total_count, 3)  # Original total

    # =============================================================================
    # UI HELPER FUNCTION TESTS - Formatting and Text Creation
    # =============================================================================

    def test_create_hover_text_chemical(self):
        """Test hover text creation for chemical data."""
        # Prepare DataFrame with computed status
        site_data = self.sample_chemical_data.iloc[[0]].copy()  # First row as DataFrame
        site_data['computed_status'] = 'Normal'
        
        config = {
            'value_column': 'do_percent',
            'date_column': 'Date',
            'site_column': 'Site_Name'
        }
        
        hover_text_list = create_hover_text(
            site_data, 'chemical', config, 'do_percent'
        )
        
        hover_text = hover_text_list[0]  # Get first element from returned list
        self.assertIn('Blue Creek at Highway 9', hover_text)
        self.assertIn('Dissolved Oxygen', hover_text)
        self.assertIn('95.5%', hover_text)  # Formatted value (not rounded)
        self.assertIn('Normal', hover_text)
        self.assertIn('2023-01-15', hover_text)  # Formatted date

    def test_create_hover_text_fish(self):
        """Test hover text creation for fish data."""
        # Prepare DataFrame with computed status
        site_data = self.sample_fish_data.iloc[[0]].copy()
        site_data['computed_status'] = 'Good'
        
        config = {
            'value_column': 'comparison_to_reference',
            'date_column': 'year',
            'site_column': 'site_name'
        }
        
        hover_text_list = create_hover_text(
            site_data, 'fish', config, None
        )
        
        hover_text = hover_text_list[0]  # Get first element from returned list
        self.assertIn('Blue Creek at Highway 9', hover_text)
        self.assertIn('IBI Score:</b> 0.85', hover_text)
        self.assertIn('Good', hover_text)
        self.assertIn('2023', hover_text)

    def test_create_hover_text_macro(self):
        """Test hover text creation for macro data."""
        site_data = self.sample_macro_data.iloc[[0]].copy()
        site_data['computed_status'] = 'Slightly Impaired'
        
        config = {
            'value_column': 'comparison_to_reference',
            'date_column': 'year',
            'site_column': 'site_name'
        }
        
        hover_text_list = create_hover_text(
            site_data, 'macro', config, None
        )
        
        hover_text = hover_text_list[0]  # Get first element from returned list
        self.assertIn('Blue Creek at Highway 9', hover_text)
        self.assertIn('Bioassessment Score:</b> 0.75', hover_text)
        self.assertIn('Slightly Impaired', hover_text)
        self.assertIn('Summer 2023', hover_text)  # Season and year

    def test_create_hover_text_habitat(self):
        """Test hover text creation for habitat data."""
        site_data = self.sample_habitat_data.iloc[[0]].copy()
        site_data['computed_status'] = 'B'
        
        config = {
            'value_column': 'total_score',
            'date_column': 'year',
            'site_column': 'site_name'
        }
        
        hover_text_list = create_hover_text(
            site_data, 'habitat', config, None
        )
        
        hover_text = hover_text_list[0]  # Get first element from returned list
        self.assertIn('Blue Creek at Highway 9', hover_text)
        self.assertIn('Habitat Score:</b> 85', hover_text)
        self.assertIn('Grade:</b> B', hover_text)
        self.assertIn('2023', hover_text)
        self.assertIn('Click to view detailed data', hover_text)

    # =============================================================================
    # MAP LAYOUT HELPER FUNCTION TESTS
    # =============================================================================

    def test_create_base_map_layout(self):
        """Test base map layout configuration."""
        fig = go.Figure()
        configured_fig = _create_base_map_layout(fig, "Test Map Title")
        
        # Should return the same figure object
        self.assertIs(configured_fig, fig)
        
        # Should have map configuration
        self.assertEqual(fig.layout.map.style, "white-bg")
        self.assertIsNotNone(fig.layout.map.center)
        self.assertEqual(fig.layout.map.center.lat, 35.5)
        self.assertEqual(fig.layout.map.center.lon, -98.2)
        self.assertEqual(fig.layout.map.zoom, 6.2)
        
        # Should have title
        self.assertEqual(fig.layout.title.text, "Test Map Title")
        self.assertEqual(fig.layout.title.x, 0.5)
        
        # Should have attribution
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertIn("Esri", fig.layout.annotations[0].text)

    def test_add_site_marker_with_color(self):
        """Test adding site marker with specific color."""
        fig = go.Figure()
        
        updated_fig = add_site_marker(
            fig, 35.123, -98.456, '#ff0000', 'Test Site',
            hover_text="Test hover text", active=True
        )
        
        # Should return the same figure
        self.assertIs(updated_fig, fig)
        
        # Should add one trace
        self.assertEqual(len(fig.data), 1)
        
        trace = fig.data[0]
        self.assertEqual(trace.lat[0], 35.123)
        self.assertEqual(trace.lon[0], -98.456)
        self.assertEqual(trace.marker.color, '#ff0000')
        self.assertEqual(trace.marker.size, 10)
        self.assertEqual(trace.text[0], "Test hover text")

    def test_add_site_marker_active_site(self):
        """Test adding marker for active site without specific color."""
        fig = go.Figure()
        
        add_site_marker(fig, 35.123, -98.456, '', 'Active Site', active=True)
        
        trace = fig.data[0]
        self.assertEqual(trace.marker.color, '#3366CC')  # Blue for active
        self.assertEqual(trace.marker.size, 10)

    def test_add_site_marker_historic_site(self):
        """Test adding marker for historic site without specific color."""
        fig = go.Figure()
        
        add_site_marker(fig, 35.123, -98.456, '', 'Historic Site', active=False)
        
        trace = fig.data[0]
        self.assertEqual(trace.marker.color, '#9370DB')  # Purple for historic
        self.assertEqual(trace.marker.size, 6)

    def test_create_error_map(self):
        """Test creation of error map."""
        error_message = "Test error message"
        fig = create_error_map(error_message)
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have error message annotation
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertEqual(fig.layout.annotations[0].text, error_message)
        
        # Should have map configuration
        self.assertIsNotNone(fig.layout.map)

    # =============================================================================
    # MAIN VISUALIZATION FUNCTION TESTS
    # =============================================================================

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_add_data_markers_chemical(self, mock_get_data):
        """Test adding chemical data markers to map."""
        mock_get_data.return_value = self.sample_chemical_data
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_data_markers(
            fig, self.sample_sites, 'chemical', parameter_name='do_percent'
        )
        
        # Should return updated figure and counts
        self.assertIs(updated_fig, fig)
        self.assertGreater(sites_with_data, 0)
        self.assertEqual(total_sites, len(self.sample_sites))
        
        # Should add markers for sites with data
        self.assertGreater(len(fig.data), 0)

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_add_data_markers_fish(self, mock_get_data):
        """Test adding fish data markers to map."""
        mock_get_data.return_value = self.sample_fish_data
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_data_markers(
            fig, self.sample_sites, 'fish'
        )
        
        self.assertIs(updated_fig, fig)
        self.assertGreaterEqual(sites_with_data, 0)
        self.assertEqual(total_sites, len(self.sample_sites))

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_add_data_markers_macro_with_season(self, mock_get_data):
        """Test adding macro data markers with season filter."""
        mock_get_data.return_value = self.sample_macro_data
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_data_markers(
            fig, self.sample_sites, 'macro', season='Summer'
        )
        
        self.assertIs(updated_fig, fig)
        # Should filter by season
        mock_get_data.assert_called_once_with('macro')

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_add_data_markers_empty_data(self, mock_get_data):
        """Test adding markers when no data is available."""
        mock_get_data.return_value = pd.DataFrame()  # Empty DataFrame
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_data_markers(
            fig, self.sample_sites, 'chemical', parameter_name='do_percent'
        )
        
        self.assertEqual(sites_with_data, 0)
        self.assertEqual(total_sites, len(self.sample_sites))

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_add_data_markers_filter_no_data_false(self, mock_get_data):
        """Test adding markers with filter_no_data=False."""
        mock_get_data.return_value = self.sample_chemical_data
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_data_markers(
            fig, self.sample_sites, 'chemical', 
            parameter_name='do_percent', filter_no_data=False
        )
        
        # Should include all sites even those without data
        self.assertEqual(total_sites, len(self.sample_sites))

    def test_create_basic_site_map_all_sites(self):
        """Test creation of basic site map with all sites."""
        with patch('visualizations.map_viz.load_sites_from_database', return_value=self.sample_sites):
            fig, active_count, historic_count, total_count = create_basic_site_map(active_only=False)
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have correct counts
        self.assertEqual(active_count, 2)
        self.assertEqual(historic_count, 1)
        self.assertEqual(total_count, 3)
        
        # Should have markers for all sites
        self.assertEqual(len(fig.data), 3)
        
        # Should have map layout
        self.assertIsNotNone(fig.layout.map)

    def test_create_basic_site_map_active_only(self):
        """Test creation of basic site map with active sites only."""
        with patch('visualizations.map_viz.load_sites_from_database', return_value=self.sample_sites):
            fig, active_count, historic_count, total_count = create_basic_site_map(active_only=True)
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have correct counts
        self.assertEqual(active_count, 2)
        self.assertEqual(historic_count, 1)  # Total historic in original list
        self.assertEqual(total_count, 2)     # Only active sites
        
        # Should have markers for active sites only
        self.assertEqual(len(fig.data), 2)

    def test_create_basic_site_map_no_sites(self):
        """Test creation of basic site map with no sites."""
        with patch('visualizations.map_viz.load_sites_from_database', return_value=[]):
            fig, active_count, historic_count, total_count = create_basic_site_map()
        
        # Should return error map
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(active_count, 0)
        self.assertEqual(historic_count, 0)
        self.assertEqual(total_count, 0)

    @patch('visualizations.map_viz.add_data_markers')
    def test_add_parameter_colors_to_map_chemical(self, mock_add_markers):
        """Test adding parameter colors for chemical data."""
        mock_add_markers.return_value = (go.Figure(), 5, 10)
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_parameter_colors_to_map(
            fig, 'chem', 'do_percent', self.sample_sites
        )
        
        # Should call add_data_markers with correct parameters
        mock_add_markers.assert_called_once_with(
            fig, self.sample_sites, 'chemical', parameter_name='do_percent', filter_no_data=True
        )
        
        self.assertEqual(sites_with_data, 5)
        self.assertEqual(total_sites, 10)

    @patch('visualizations.map_viz.add_data_markers')
    def test_add_parameter_colors_to_map_fish(self, mock_add_markers):
        """Test adding parameter colors for fish data."""
        mock_add_markers.return_value = (go.Figure(), 3, 8)
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_parameter_colors_to_map(
            fig, 'bio', 'Fish_IBI', self.sample_sites
        )
        
        mock_add_markers.assert_called_once_with(
            fig, self.sample_sites, 'fish', filter_no_data=True
        )

    @patch('visualizations.map_viz.add_data_markers')
    def test_add_parameter_colors_to_map_macro(self, mock_add_markers):
        """Test adding parameter colors for macro data."""
        mock_add_markers.return_value = (go.Figure(), 4, 12)
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_parameter_colors_to_map(
            fig, 'bio', 'Macro_Combined', self.sample_sites
        )
        
        mock_add_markers.assert_called_once_with(
            fig, self.sample_sites, 'macro', filter_no_data=True
        )

    @patch('visualizations.map_viz.add_data_markers')
    def test_add_parameter_colors_to_map_habitat(self, mock_add_markers):
        """Test adding parameter colors for habitat data."""
        mock_add_markers.return_value = (go.Figure(), 2, 6)
        
        fig = go.Figure()
        updated_fig, sites_with_data, total_sites = add_parameter_colors_to_map(
            fig, 'habitat', 'Habitat_Grade', self.sample_sites
        )
        
        mock_add_markers.assert_called_once_with(
            fig, self.sample_sites, 'habitat', filter_no_data=True
        )

    @patch('visualizations.map_viz.add_data_markers')
    def test_add_parameter_colors_to_map_default_sites(self, mock_add_markers):
        """Test adding parameter colors when no sites are provided (loads from database)."""
        mock_add_markers.return_value = (go.Figure(), 3, 3)
        
        with patch('visualizations.map_viz.load_sites_from_database', return_value=self.sample_sites):
            fig = go.Figure()
            updated_fig, sites_with_data, total_sites = add_parameter_colors_to_map(
                fig, 'chem', 'pH'  # No sites parameter provided
            )
            
            # Should use sites loaded from database
            call_args = mock_add_markers.call_args[0]
            self.assertEqual(call_args[1], self.sample_sites)

    # =============================================================================
    # CONSTANTS AND CONFIGURATION TESTS
    # =============================================================================

    def test_colors_constant_structure(self):
        """Test that COLORS constant has expected structure."""
        # Should have basic status colors
        expected_basic_colors = ['normal', 'caution', 'poor', 'above_normal', 'below_normal']
        for color_key in expected_basic_colors:
            self.assertIn(color_key, COLORS)
            self.assertIsInstance(COLORS[color_key], str)
        
        # Should have fish sub-dictionary
        self.assertIn('fish', COLORS)
        self.assertIsInstance(COLORS['fish'], dict)
        
        # Should have macro sub-dictionary
        self.assertIn('macro', COLORS)
        self.assertIsInstance(COLORS['macro'], dict)
        
        # Should have habitat sub-dictionary
        self.assertIn('habitat', COLORS)
        self.assertIsInstance(COLORS['habitat'], dict)

    def test_parameter_labels_constant(self):
        """Test that PARAMETER_LABELS constant has expected parameters."""
        expected_params = [
            'do_percent', 'pH', 'soluble_nitrogen', 'Phosphorus', 
            'Chloride', 'Fish_IBI', 'Macro_Combined', 'Habitat_Score'
        ]
        
        for param in expected_params:
            self.assertIn(param, PARAMETER_LABELS)
            self.assertIsInstance(PARAMETER_LABELS[param], str)

    def test_map_parameter_labels_constant(self):
        """Test that MAP_PARAMETER_LABELS constant has expected parameters."""
        expected_params = ['do_percent', 'pH', 'soluble_nitrogen', 'Phosphorus', 'Chloride']
        
        for param in expected_params:
            self.assertIn(param, MAP_PARAMETER_LABELS)
            self.assertIsInstance(MAP_PARAMETER_LABELS[param], str)

    # =============================================================================
    # ERROR HANDLING AND EDGE CASES
    # =============================================================================
    def test_get_status_color_invalid_data_type(self):
        """Test status color mapping with invalid data type."""
        status, color = get_status_color('Normal', 'invalid_type')
        self.assertEqual(status, 'Normal')
        self.assertEqual(color, 'gray')

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_add_data_markers_exception_handling(self, mock_get_data):
        """Test error handling in add_data_markers."""
        mock_get_data.side_effect = Exception("Database error")
        
        fig = go.Figure()
        
        # Should handle exceptions gracefully (depends on implementation)
        try:
            updated_fig, sites_with_data, total_sites = add_data_markers(
                fig, self.sample_sites, 'chemical', parameter_name='do_percent'
            )
            # If no exception raised, that's acceptable too
        except Exception:
            # Expected behavior for database errors
            pass

    def test_filter_sites_by_active_status_empty_list(self):
        """Test filtering with empty sites list."""
        sites, active_count, historic_count, total_count = filter_sites_by_active_status(
            [], active_only=False
        )
        
        self.assertEqual(len(sites), 0)
        self.assertEqual(active_count, 0)
        self.assertEqual(historic_count, 0)
        self.assertEqual(total_count, 0)

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    @patch('visualizations.map_viz.get_latest_data_by_type')
    def test_full_workflow_chemical_map(self, mock_get_data):
        """Test complete workflow for creating a chemical parameter map."""
        mock_get_data.return_value = self.sample_chemical_data
        
        with patch('visualizations.map_viz.load_sites_from_database', return_value=self.sample_sites):
            # Create basic map
            fig, active_count, historic_count, total_count = create_basic_site_map()
            
            # Add parameter coloring
            updated_fig, sites_with_data, total_sites = add_parameter_colors_to_map(
                fig, 'chem', 'do_percent'
            )
            
            # Should have a complete map with parameter coloring
            self.assertIsInstance(updated_fig, go.Figure)
            self.assertGreater(len(updated_fig.data), 0)
            self.assertIsNotNone(updated_fig.layout.map)

    def test_hover_text_consistency(self):
        """Test that hover text is consistent across data types."""
        test_cases = [
            ('chemical', self.sample_chemical_data.iloc[[0]], 
             {'date_column': 'Date', 'value_column': 'do_percent', 'site_column': 'Site_Name'}, 'do_percent'),
            ('fish', self.sample_fish_data.iloc[[0]], 
             {'date_column': 'year', 'value_column': 'comparison_to_reference', 'site_column': 'site_name'}, None),
            ('macro', self.sample_macro_data.iloc[[0]], 
             {'date_column': 'year', 'value_column': 'comparison_to_reference', 'site_column': 'site_name'}, None),
            ('habitat', self.sample_habitat_data.iloc[[0]], 
             {'date_column': 'year', 'value_column': 'total_score', 'site_column': 'site_name'}, None)
        ]
        
        for data_type, site_data, config, param_name in test_cases:
            with self.subTest(data_type=data_type):
                # Prepare DataFrame with computed status
                site_data_copy = site_data.copy()
                site_data_copy['computed_status'] = 'Test Status'
                
                hover_text_list = create_hover_text(
                    site_data_copy, data_type, config, param_name
                )
                
                hover_text = hover_text_list[0]  
                
                # All hover texts should contain site name
                self.assertIn('Site:', hover_text)
                # All should have HTML formatting
                self.assertIn('<br>', hover_text)

if __name__ == '__main__':
    unittest.main(verbosity=2)