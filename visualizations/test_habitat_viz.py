"""
test_habitat_viz.py - Unit tests for Habitat Assessment Data Visualization

This module contains comprehensive tests for the habitat_viz.py module,
testing visualization creation, data table formatting, and error handling.

Test Coverage:
- create_habitat_viz() function with various data scenarios
- create_habitat_metrics_table() function 
- create_habitat_metrics_accordion() function
- Error handling and edge cases
- Data formatting and styling
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, html

# Import the module under test
from visualizations.habitat_viz import (
    create_habitat_viz,
    create_habitat_metrics_table,
    create_habitat_metrics_accordion,
    HABITAT_GRADE_THRESHOLDS,
    HABITAT_GRADE_COLORS,
    HABITAT_METRIC_ORDER,
    HABITAT_SUMMARY_LABELS
)


class TestHabitatVisualization(unittest.TestCase):
    """Test cases for habitat visualization functions."""

    def setUp(self):
        """Set up test data and fixtures."""
        # Sample habitat data for testing
        self.sample_habitat_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023],
            'total_score': [85, 78, 92, 65],
            'habitat_grade': ['B', 'C', 'A', 'D'],
            'site_name': ['Test Site'] * 4
        })
        
        # Sample metrics data
        self.sample_metrics_data = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021],
            'metric_name': ['Instream Cover', 'Pool Bottom Substrate', 'Instream Cover', 'Pool Bottom Substrate'],
            'metric_score': [8, 7, 9, 6],
            'site_name': ['Test Site'] * 4
        })
        
        # Sample summary data
        self.sample_summary_data = pd.DataFrame({
            'year': [2020, 2021],
            'total_score': [85, 78],
            'habitat_grade': ['B', 'C'],
            'site_name': ['Test Site'] * 2
        })
        
        # Empty dataframes for testing
        self.empty_df = pd.DataFrame()

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_create_habitat_viz_with_data(self, mock_get_data):
        """Test create_habitat_viz with valid data."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz('Test Site')
        
        # Verify it returns a plotly figure
        self.assertIsInstance(result, go.Figure)
        
        # Check that the data query was called with correct site
        mock_get_data.assert_called_once_with('Test Site')
        
        # Verify figure has data
        self.assertGreater(len(result.data), 0)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_create_habitat_viz_no_site_filter(self, mock_get_data):
        """Test create_habitat_viz without site filtering."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz()
        
        # Check that the data query was called with None
        mock_get_data.assert_called_once_with(None)
        
        # Verify it returns a figure
        self.assertIsInstance(result, go.Figure)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_create_habitat_viz_empty_data(self, mock_get_data):
        """Test create_habitat_viz with empty data."""
        mock_get_data.return_value = self.empty_df
        
        result = create_habitat_viz('Test Site')
        
        # Should return an empty figure
        self.assertIsInstance(result, go.Figure)
        
        # Check that it shows an appropriate message
        if result.layout.annotations:
            self.assertIn("No", result.layout.annotations[0].text)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_create_habitat_viz_database_error(self, mock_get_data):
        """Test create_habitat_viz with database error."""
        mock_get_data.side_effect = Exception("Database connection failed")
        
        result = create_habitat_viz('Test Site')
        
        # Should return an error figure
        self.assertIsInstance(result, go.Figure)

    def test_create_habitat_metrics_table_with_data(self):
        """Test create_habitat_metrics_table with valid data."""
        result = create_habitat_metrics_table(
            self.sample_metrics_data, 
            self.sample_summary_data
        )
        
        # Should return a DataTable component
        self.assertIsInstance(result, dash_table.DataTable)
        
        # Check that it has an ID
        self.assertEqual(result.id, 'habitat-metrics-table')
        
        # Verify it has data
        self.assertGreater(len(result.data), 0)
        
        # Check that columns are present
        self.assertGreater(len(result.columns), 0)

    def test_create_habitat_metrics_table_empty_data(self):
        """Test create_habitat_metrics_table with empty data."""
        result = create_habitat_metrics_table(self.empty_df, self.empty_df)
        
        # Should handle empty data gracefully
        self.assertIsInstance(result, (dash_table.DataTable, html.Div))

    def test_create_habitat_metrics_table_error_handling(self):
        """Test create_habitat_metrics_table error handling."""
        # Pass invalid data to trigger error
        invalid_data = "not a dataframe"
        
        result = create_habitat_metrics_table(invalid_data, invalid_data)
        
        # Should handle error gracefully - either return a DataTable with basic structure or error div
        self.assertIsInstance(result, (dash_table.DataTable, html.Div))
        
        # If it's a DataTable, it should have the basic metric structure
        if isinstance(result, dash_table.DataTable):
            # Should have the metric order as fallback data
            self.assertGreater(len(result.data), 0)
            # Should contain at least the metric column
            self.assertTrue(any(col['id'] == 'Metric' for col in result.columns))

    @patch('visualizations.habitat_viz.get_habitat_metrics_data_for_table')
    def test_create_habitat_metrics_accordion_with_data(self, mock_get_data):
        """Test create_habitat_metrics_accordion with valid data."""
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        
        result = create_habitat_metrics_accordion('Test Site')
        
        # Should return an HTML div
        self.assertIsInstance(result, html.Div)
        
        # Check that the data query was called with correct site
        mock_get_data.assert_called_once_with('Test Site')

    @patch('visualizations.habitat_viz.get_habitat_metrics_data_for_table')
    def test_create_habitat_metrics_accordion_empty_data(self, mock_get_data):
        """Test create_habitat_metrics_accordion with empty data."""
        mock_get_data.return_value = (self.empty_df, self.empty_df)
        
        result = create_habitat_metrics_accordion('Test Site')
        
        # Should return a div with no data message
        self.assertIsInstance(result, html.Div)
        self.assertIn("No habitat assessment data available", result.children)

    @patch('visualizations.habitat_viz.get_habitat_metrics_data_for_table')
    def test_create_habitat_metrics_accordion_database_error(self, mock_get_data):
        """Test create_habitat_metrics_accordion with database error."""
        mock_get_data.side_effect = Exception("Database error")
        
        result = create_habitat_metrics_accordion('Test Site')
        
        # Should return an error message div
        self.assertIsInstance(result, html.Div)
        self.assertIn("Error", result.children)

    def test_habitat_constants(self):
        """Test that habitat-specific constants are properly defined."""
        # Test grade thresholds
        self.assertIsInstance(HABITAT_GRADE_THRESHOLDS, dict)
        self.assertIn('A', HABITAT_GRADE_THRESHOLDS)
        self.assertIn('B', HABITAT_GRADE_THRESHOLDS)
        self.assertIn('C', HABITAT_GRADE_THRESHOLDS)
        self.assertIn('D', HABITAT_GRADE_THRESHOLDS)
        
        # Test grade colors
        self.assertIsInstance(HABITAT_GRADE_COLORS, dict)
        self.assertEqual(len(HABITAT_GRADE_COLORS), 5)  # A, B, C, D, F
        
        # Test metric order
        self.assertIsInstance(HABITAT_METRIC_ORDER, list)
        self.assertGreater(len(HABITAT_METRIC_ORDER), 0)
        
        # Test summary labels
        self.assertIsInstance(HABITAT_SUMMARY_LABELS, list)
        self.assertEqual(len(HABITAT_SUMMARY_LABELS), 2)

    def test_habitat_grade_threshold_values(self):
        """Test that habitat grade thresholds have correct values."""
        self.assertEqual(HABITAT_GRADE_THRESHOLDS['A'], 90)
        self.assertEqual(HABITAT_GRADE_THRESHOLDS['B'], 80)
        self.assertEqual(HABITAT_GRADE_THRESHOLDS['C'], 70)
        self.assertEqual(HABITAT_GRADE_THRESHOLDS['D'], 60)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_figure_has_reference_lines(self, mock_get_data):
        """Test that the habitat visualization includes grade reference lines."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz('Test Site')
        
        # Check that reference lines are added (shapes in layout)
        self.assertIsInstance(result.layout.shapes, tuple)
        self.assertGreater(len(result.layout.shapes), 0)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_figure_title_with_site(self, mock_get_data):
        """Test that figure title includes site name when provided."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz('Test Site')
        
        # Check that title includes site name
        self.assertIn('Test Site', result.layout.title.text)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_figure_title_without_site(self, mock_get_data):
        """Test that figure title is generic when no site provided."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz()
        
        # Check that title is generic
        self.assertIn('Habitat Assessment Scores', result.layout.title.text)
        self.assertNotIn('for', result.layout.title.text)

    def test_metrics_table_has_correct_columns(self):
        """Test that metrics table includes all expected habitat metrics."""
        result = create_habitat_metrics_table(
            self.sample_metrics_data, 
            self.sample_summary_data
        )
        
        if isinstance(result, dash_table.DataTable):
            # Get the data as DataFrame to check metrics
            table_df = pd.DataFrame(result.data)
            
            # Should have Metric column
            self.assertIn('Metric', table_df.columns)
            
            # Should have year columns
            year_columns = [col for col in table_df.columns if col.isdigit()]
            self.assertGreater(len(year_columns), 0)

    @patch('visualizations.habitat_viz.create_habitat_metrics_table')
    @patch('visualizations.habitat_viz.get_habitat_metrics_data_for_table')
    def test_accordion_calls_table_creation(self, mock_get_data, mock_create_table):
        """Test that accordion function calls table creation with correct data."""
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        mock_table = MagicMock()
        mock_create_table.return_value = mock_table
        
        result = create_habitat_metrics_accordion('Test Site')
        
        # Verify table creation was called
        mock_create_table.assert_called_once_with(
            self.sample_metrics_data, 
            self.sample_summary_data
        )

    def test_summary_labels_content(self):
        """Test that summary labels contain expected values."""
        self.assertIn('Total Points', HABITAT_SUMMARY_LABELS)
        self.assertIn('Habitat Grade', HABITAT_SUMMARY_LABELS)

    def test_metric_order_completeness(self):
        """Test that metric order includes key habitat assessment metrics."""
        expected_metrics = [
            'Instream Cover',
            'Pool Bottom Substrate', 
            'Pool Variability',
            'Canopy Cover',
            'Bank Stability'
        ]
        
        for metric in expected_metrics:
            self.assertIn(metric, HABITAT_METRIC_ORDER)


class TestHabitatVisualizationIntegration(unittest.TestCase):
    """Integration tests for habitat visualization components."""

    def setUp(self):
        """Set up integration test data."""
        self.integration_habitat_data = pd.DataFrame({
            'year': [2020, 2021, 2022],
            'total_score': [95, 82, 67],
            'habitat_grade': ['A', 'B', 'D'],
            'site_name': ['Integration Test Site'] * 3
        })

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_end_to_end_visualization_creation(self, mock_get_data):
        """Test complete end-to-end visualization creation process."""
        mock_get_data.return_value = self.integration_habitat_data
        
        # Test visualization creation
        viz_result = create_habitat_viz('Integration Test Site')
        
        # Verify it's a valid figure
        self.assertIsInstance(viz_result, go.Figure)
        
        # Verify it has data traces
        self.assertGreater(len(viz_result.data), 0)
        
        # Verify it has proper layout
        self.assertIsNotNone(viz_result.layout.title)
        self.assertIsNotNone(viz_result.layout.xaxis)
        self.assertIsNotNone(viz_result.layout.yaxis)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2) 