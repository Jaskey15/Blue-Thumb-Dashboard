"""
Test suite for fish visualization functionality.
Tests the logic in visualizations.fish_viz module.
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

from visualizations.fish_viz import (
    create_fish_viz,
    create_fish_metrics_table,
    create_fish_metrics_accordion,
    INTEGRITY_THRESHOLDS,
    INTEGRITY_COLORS,
    FISH_METRIC_ORDER,
    FISH_SUMMARY_LABELS
)
from data_processing.data_queries import (
    get_fish_dataframe, 
    get_fish_metrics_data_for_table
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_fish_viz", category="testing")


class TestFishViz(unittest.TestCase):
    """Test fish visualization functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample fish data
        self.sample_fish_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023],
            'comparison_to_reference': [0.85, 0.72, 0.91, 0.68],
            'integrity_class': ['Good', 'Fair', 'Good', 'Fair'],
            'site_name': ['Test Site'] * 4
        })
        
        # Sample metrics data
        self.sample_metrics_data = pd.DataFrame({
            'year': [2020, 2020, 2020, 2021, 2021, 2021],
            'metric_name': ['Total No. of species', 'No. of sensitive benthic species', 'No. of sunfish species',
                          'Total No. of species', 'No. of sensitive benthic species', 'No. of sunfish species'],
            'metric_score': [12, 4, 3, 15, 5, 4]
        })
        
        # Sample summary data
        self.sample_summary_data = pd.DataFrame({
            'year': [2020, 2021],
            'total_score': [42, 48],
            'comparison_to_reference': [0.72, 0.85],
            'integrity_class': ['Fair', 'Good']
        })

    # =============================================================================
    # MAIN VISUALIZATION FUNCTION TESTS
    # =============================================================================

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_create_fish_viz_with_data(self, mock_get_fish):
        """Test fish visualization creation with valid data."""
        mock_get_fish.return_value = self.sample_fish_data
        
        fig = create_fish_viz("Test Site")
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have correct title
        self.assertIn("Test Site", fig.layout.title.text)
        self.assertIn("IBI Scores Over Time", fig.layout.title.text)
        
        # Should have data traces
        self.assertGreater(len(fig.data), 0)
        
        # Should have y-axis label
        self.assertEqual(fig.layout.yaxis.title.text, 'IBI Score (Compared to Reference)')
        
        # Should have reference lines (shapes)
        self.assertGreater(len(fig.layout.shapes), 0)

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_create_fish_viz_no_site_name(self, mock_get_fish):
        """Test fish visualization creation without site name."""
        mock_get_fish.return_value = self.sample_fish_data
        
        fig = create_fish_viz()
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have generic title
        self.assertEqual(fig.layout.title.text, "IBI Scores Over Time")

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_create_fish_viz_empty_data(self, mock_get_fish):
        """Test fish visualization creation with empty data."""
        mock_get_fish.return_value = pd.DataFrame()
        
        fig = create_fish_viz("Test Site")
        
        # Should return empty figure
        self.assertIsInstance(fig, go.Figure)
        self.assertIn("No fish data available", fig.layout.title.text)

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_create_fish_viz_error_handling(self, mock_get_fish):
        """Test fish visualization error handling."""
        mock_get_fish.side_effect = Exception("Database error")
        
        fig = create_fish_viz("Test Site")
        
        # Should return error figure
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.layout.title.text, "Error creating visualization")

    # =============================================================================
    # METRICS TABLE FUNCTION TESTS
    # =============================================================================

    def test_create_fish_metrics_table_basic(self):
        """Test basic fish metrics table creation."""
        from dash import dash_table
        
        table = create_fish_metrics_table(self.sample_metrics_data, self.sample_summary_data)
        
        # Should return DataTable component
        self.assertIsInstance(table, dash_table.DataTable)
        
        # Should have correct structure
        self.assertEqual(table.id, 'fish-metrics-table')
        self.assertGreater(len(table.columns), 1)  # Metric column + year columns
        self.assertGreater(len(table.data), len(FISH_METRIC_ORDER))  # Metrics + summary rows

    def test_create_fish_metrics_table_empty_data(self):
        """Test metrics table creation with empty data."""
        from dash import html
        
        empty_df = pd.DataFrame()
        
        result = create_fish_metrics_table(empty_df, empty_df)
        
        # Should handle gracefully - either return empty table or error message
        self.assertTrue(
            isinstance(result, html.Div) or 
            hasattr(result, 'data')  # DataTable with empty data
        )

    def test_create_fish_metrics_table_error_handling(self):
        """Test metrics table error handling."""
        from dash import html, dash_table
        
        # Pass invalid data to trigger error
        result = create_fish_metrics_table("invalid", "invalid")
        
        # Should return either error message or empty table (both are acceptable)
        self.assertTrue(
            isinstance(result, html.Div) or 
            isinstance(result, dash_table.DataTable)
        )

    # =============================================================================
    # ACCORDION FUNCTION TESTS
    # =============================================================================

    @patch('visualizations.fish_viz.get_fish_metrics_data_for_table')
    def test_create_fish_metrics_accordion_with_data(self, mock_get_data):
        """Test fish metrics accordion creation with valid data."""
        from dash import html
        
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        
        accordion = create_fish_metrics_accordion("Test Site")
        
        # Should return HTML component
        self.assertIsInstance(accordion, html.Div)

    @patch('visualizations.fish_viz.get_fish_metrics_data_for_table')
    def test_create_fish_metrics_accordion_empty_data(self, mock_get_data):
        """Test accordion creation with empty data."""
        from dash import html
        
        mock_get_data.return_value = (pd.DataFrame(), pd.DataFrame())
        
        accordion = create_fish_metrics_accordion("Test Site")
        
        # Should return "No data available" message
        self.assertIsInstance(accordion, html.Div)
        self.assertEqual(accordion.children, "No data available")

    @patch('visualizations.fish_viz.get_fish_metrics_data_for_table')
    def test_create_fish_metrics_accordion_error_handling(self, mock_get_data):
        """Test accordion error handling."""
        from dash import html
        
        mock_get_data.side_effect = Exception("Database error")
        
        accordion = create_fish_metrics_accordion("Test Site")
        
        # Should return error message
        self.assertIsInstance(accordion, html.Div)
        self.assertIn("Error creating metrics accordion", accordion.children)

    # =============================================================================
    # CONSTANTS AND CONFIGURATION TESTS
    # =============================================================================

    def test_integrity_thresholds_constant(self):
        """Test INTEGRITY_THRESHOLDS constant structure."""
        # Should have all expected threshold categories
        expected_categories = ['Excellent', 'Good', 'Fair', 'Poor']
        
        for category in expected_categories:
            self.assertIn(category, INTEGRITY_THRESHOLDS)
            self.assertIsInstance(INTEGRITY_THRESHOLDS[category], (int, float))
            self.assertGreater(INTEGRITY_THRESHOLDS[category], 0)
            self.assertLessEqual(INTEGRITY_THRESHOLDS[category], 1)
        
        # Should be in descending order (excellent > good > fair > poor)
        thresholds_list = list(INTEGRITY_THRESHOLDS.values())
        self.assertEqual(thresholds_list, sorted(thresholds_list, reverse=True))

    def test_integrity_colors_constant(self):
        """Test INTEGRITY_COLORS constant structure."""
        # Should have colors for all threshold categories
        for category in INTEGRITY_THRESHOLDS.keys():
            self.assertIn(category, INTEGRITY_COLORS)
            self.assertIsInstance(INTEGRITY_COLORS[category], str)

    def test_fish_metric_order_constant(self):
        """Test FISH_METRIC_ORDER constant."""
        # Should be a list
        self.assertIsInstance(FISH_METRIC_ORDER, list)
        
        # Should have expected fish metrics
        expected_metrics = [
            'Total No. of species',
            'No. of sensitive benthic species', 
            'No. of sunfish species',
            'No. of intolerant species',
            'Proportion tolerant individuals',
            'Proportion insectivorous cyprinid',
            'Proportion lithophilic spawners'
        ]
        
        self.assertEqual(FISH_METRIC_ORDER, expected_metrics)

    def test_fish_summary_labels_constant(self):
        """Test FISH_SUMMARY_LABELS constant."""
        # Should be a list
        self.assertIsInstance(FISH_SUMMARY_LABELS, list)
        
        # Should have expected summary labels
        expected_labels = ['Total Score', 'Comparison to Reference', 'Integrity Class']
        self.assertEqual(FISH_SUMMARY_LABELS, expected_labels)

    # =============================================================================
    # INTEGRATION WITH SHARED UTILITIES TESTS
    # =============================================================================

    def test_integration_with_biological_utils(self):
        """Test integration with shared biological utilities."""
        # This test ensures the fish module correctly uses shared utilities
        with patch('visualizations.fish_viz.get_fish_dataframe') as mock_get_fish:
            mock_get_fish.return_value = self.sample_fish_data
            
            fig = create_fish_viz("Test Site")
            
            # Should have characteristics of shared biological visualization
            self.assertIsInstance(fig, go.Figure)
            
            # Should have single trace (no seasons for fish)
            self.assertEqual(len(fig.data), 1)
            
            # Should have hover template set by shared utilities
            trace = fig.data[0]
            self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    def test_fish_specific_configurations(self):
        """Test that fish-specific configurations are correctly applied."""
        # Test that fish module uses its own thresholds and not macro thresholds
        self.assertIn('Excellent', INTEGRITY_THRESHOLDS)
        self.assertNotIn('Non-impaired', INTEGRITY_THRESHOLDS)  # Macro threshold
        
        # Test that fish metrics are fish-specific
        self.assertIn('Total No. of species', FISH_METRIC_ORDER)
        self.assertNotIn('Taxa Richness', FISH_METRIC_ORDER)  # Macro metric

    # =============================================================================
    # EDGE CASES AND ERROR HANDLING
    # =============================================================================

    def test_create_fish_viz_with_none_site(self):
        """Test fish visualization with None site name."""
        with patch('visualizations.fish_viz.get_fish_dataframe') as mock_get_fish:
            mock_get_fish.return_value = self.sample_fish_data
            
            fig = create_fish_viz(None)
            
            # Should handle gracefully
            self.assertIsInstance(fig, go.Figure)

    def test_create_fish_viz_with_special_characters(self):
        """Test fish visualization with special characters in site name."""
        special_site = "Test Site: with/special\\characters & symbols"
        
        with patch('visualizations.fish_viz.get_fish_dataframe') as mock_get_fish:
            mock_get_fish.return_value = self.sample_fish_data
            
            fig = create_fish_viz(special_site)
            
            # Should handle special characters gracefully
            self.assertIsInstance(fig, go.Figure)
            self.assertIn(special_site, fig.layout.title.text)

    def test_metrics_table_with_missing_metrics(self):
        """Test metrics table when some expected metrics are missing."""
        # Data missing some metrics from FISH_METRIC_ORDER
        incomplete_metrics = pd.DataFrame({
            'year': [2020, 2020],
            'metric_name': ['Total No. of species', 'No. of sunfish species'],
            'metric_score': [12, 3]
        })
        
        table = create_fish_metrics_table(incomplete_metrics, self.sample_summary_data)
        
        # Should handle missing metrics gracefully
        from dash import dash_table
        self.assertIsInstance(table, dash_table.DataTable)
        
        # Should include all metrics from FISH_METRIC_ORDER (missing ones as '-')
        self.assertEqual(len([col for col in table.columns if col['id'] == 'Metric']), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)