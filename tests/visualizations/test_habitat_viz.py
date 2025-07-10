"""
test_habitat_viz.py - Unit tests for Habitat Assessment Data Visualization

This module contains comprehensive tests for the habitat_viz.py module,
testing visualization creation, data table formatting, and error handling.

Test Coverage:
- create_habitat_viz() function with various data scenarios
- create_habitat_metrics_table() function 
- create_habitat_metrics_accordion() function
- Error handling and core functionality
- Integration with shared utilities
"""

import unittest
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, html

# Import the module under test
from visualizations.habitat_viz import (
    HABITAT_GRADE_COLORS,
    HABITAT_GRADE_THRESHOLDS,
    HABITAT_METRIC_ORDER,
    HABITAT_SUMMARY_LABELS,
    create_habitat_metrics_accordion,
    create_habitat_metrics_table,
    create_habitat_viz,
)


class TestHabitatVisualization(unittest.TestCase):
    """Test cases for habitat visualization functions."""

    def setUp(self):
        """Set up test data and fixtures."""
        # Sample habitat data for testing
        self.sample_habitat_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023],
            'assessment_date': pd.to_datetime(['2020-06-15', '2021-07-20', '2022-08-10', '2023-06-25']),
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

    # =============================================================================
    # MAIN VISUALIZATION FUNCTION TESTS
    # =============================================================================

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
        
        # Should have title with site name
        self.assertIn('Test Site', result.layout.title.text)
        self.assertIn('Habitat Scores', result.layout.title.text)

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_create_habitat_viz_no_site_filter(self, mock_get_data):
        """Test create_habitat_viz without site filtering."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz()
        
        # Check that the data query was called with None
        mock_get_data.assert_called_once_with(None)
        
        # Verify it returns a figure
        self.assertIsInstance(result, go.Figure)
        
        # Should have generic title without site name
        self.assertEqual(result.layout.title.text, 'Habitat Scores Over Time')

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
        self.assertEqual(result.layout.title.text, "Error creating visualization")

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_create_habitat_viz_uses_shared_utilities(self, mock_get_data):
        """Test that habitat viz uses shared visualization utilities."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz('Test Site')
        
        # Should use shared utilities for date-aware visualization
        # Verify it has proper layout from shared utilities
        self.assertEqual(result.layout.xaxis.title.text, "Year")
        self.assertEqual(result.layout.yaxis.title.text, "Habitat Score")
        
        # Should have reference lines (shapes) from shared utilities
        self.assertGreater(len(result.layout.shapes), 0)
        
        # Should have hover template from shared utilities
        trace = result.data[0]
        self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    # =============================================================================
    # METRICS TABLE FUNCTION TESTS
    # =============================================================================

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
        
        # Should have Metric column
        metric_columns = [col for col in result.columns if col['id'] == 'Metric']
        self.assertEqual(len(metric_columns), 1)

    def test_create_habitat_metrics_table_empty_data(self):
        """Test create_habitat_metrics_table with empty data."""
        result = create_habitat_metrics_table(self.empty_df, self.empty_df)
        
        # Should handle empty data gracefully
        self.assertIsInstance(result, (dash_table.DataTable, html.Div))

    def test_create_habitat_metrics_table_uses_shared_utilities(self):
        """Test that metrics table uses shared formatting utilities."""
        result = create_habitat_metrics_table(
            self.sample_metrics_data, 
            self.sample_summary_data
        )
        
        if isinstance(result, dash_table.DataTable):
            # Should use shared table styling
            self.assertIsNotNone(result.style_table)
            self.assertIsNotNone(result.style_header)
            self.assertIsNotNone(result.style_cell)
            
            # Should have styled rows and conditional formatting
            self.assertGreater(len(result.style_data_conditional), 0)

    # =============================================================================
    # ACCORDION FUNCTION TESTS
    # =============================================================================

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

    # =============================================================================
    # CONSTANTS AND CONFIGURATION TESTS
    # =============================================================================

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

    # =============================================================================
    # INTEGRATION WITH SHARED UTILITIES TESTS
    # =============================================================================

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_integration_with_shared_visualization_utils(self, mock_get_data):
        """Test integration with shared visualization utilities."""
        mock_get_data.return_value = self.sample_habitat_data
        
        result = create_habitat_viz('Test Site')
        
        # Should use shared create_trace function
        trace = result.data[0]
        self.assertEqual(trace.mode, 'lines+markers')
        
        # Should use shared update_layout function
        self.assertEqual(result.layout.title.x, 0.5)  # Centered title
        
        # Should use shared add_reference_lines function
        self.assertGreater(len(result.layout.shapes), 0)
        
        # Should use shared generate_hover_text function
        self.assertIsNotNone(trace.text)
        self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    def test_habitat_specific_vs_shared_functionality(self):
        """Test that habitat module correctly uses shared vs. habitat-specific functionality."""
        # Test that habitat uses its own thresholds, not biological thresholds
        self.assertIn('A', HABITAT_GRADE_THRESHOLDS)
        self.assertNotIn('Excellent', HABITAT_GRADE_THRESHOLDS)  # Biological threshold
        
        # Test that habitat metrics are habitat-specific
        self.assertIn('Instream Cover', HABITAT_METRIC_ORDER)
        self.assertNotIn('Taxa Richness', HABITAT_METRIC_ORDER)  # Biological metric

    # =============================================================================
    # CORE FUNCTIONALITY INTEGRATION TESTS
    # =============================================================================

    @patch('visualizations.habitat_viz.get_habitat_dataframe')
    def test_complete_visualization_workflow(self, mock_get_data):
        """Test complete end-to-end visualization creation process."""
        mock_get_data.return_value = self.sample_habitat_data
        
        # Test visualization creation
        viz_result = create_habitat_viz('Test Site')
        
        # Verify it's a valid figure with proper structure
        self.assertIsInstance(viz_result, go.Figure)
        self.assertGreater(len(viz_result.data), 0)
        
        # Verify it has proper layout from shared utilities
        self.assertIsNotNone(viz_result.layout.title)
        self.assertIsNotNone(viz_result.layout.xaxis)
        self.assertIsNotNone(viz_result.layout.yaxis)
        
        # Verify it has reference lines for habitat grades
        self.assertGreater(len(viz_result.layout.shapes), 0)
        
        # Verify trace has proper hover text
        trace = viz_result.data[0]
        self.assertIsNotNone(trace.text)

    @patch('visualizations.habitat_viz.get_habitat_metrics_data_for_table')
    def test_complete_table_workflow(self, mock_get_data):
        """Test complete metrics table creation workflow."""
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        
        # Test accordion creation (which calls table creation)
        accordion_result = create_habitat_metrics_accordion('Test Site')
        
        # Should create proper accordion structure
        self.assertIsInstance(accordion_result, html.Div)
        
        # Test direct table creation
        table_result = create_habitat_metrics_table(
            self.sample_metrics_data, 
            self.sample_summary_data
        )
        
        # Should create properly formatted table
        self.assertIsInstance(table_result, dash_table.DataTable)
        self.assertEqual(table_result.id, 'habitat-metrics-table')

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2) 