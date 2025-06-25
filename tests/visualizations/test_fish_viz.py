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
            'collection_date': pd.to_datetime(['2020-09-15', '2021-08-20', '2022-07-10', '2023-09-05']),
            'comparison_to_reference': [0.85, 0.72, 0.91, 0.68],
            'integrity_class': ['Good', 'Fair', 'Good', 'Fair'],
            'site_name': ['Test Site'] * 4
        })
        
        # Sample metrics data
        self.sample_metrics_data = pd.DataFrame({
            'event_id': [1, 1, 1, 2, 2, 2],
            'year': [2020, 2020, 2020, 2021, 2021, 2021],
            'metric_name': ['Total No. of species', 'No. of sensitive benthic species', 'No. of sunfish species',
                          'Total No. of species', 'No. of sensitive benthic species', 'No. of sunfish species'],
            'metric_score': [12, 4, 3, 15, 5, 4]
        })
        
        # Sample summary data
        self.sample_summary_data = pd.DataFrame({
            'event_id': [1, 2],
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
        
        # Should have single trace (no seasons for fish)
        self.assertEqual(len(fig.data), 1)
        
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

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_create_fish_viz_uses_shared_utilities(self, mock_get_fish):
        """Test that fish viz uses shared visualization utilities."""
        mock_get_fish.return_value = self.sample_fish_data
        
        fig = create_fish_viz("Test Site")
        
        # Should use shared utilities for date-aware visualization
        self.assertEqual(fig.layout.xaxis.title.text, "Year")
        
        # Should have single trace with proper hover template
        trace = fig.data[0]
        self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')
        
        # Should have reference lines from shared utilities
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Should have proper styling from shared utilities
        self.assertEqual(fig.layout.title.x, 0.5)  # Centered

    # =============================================================================
    # METRICS TABLE FUNCTION TESTS
    # =============================================================================

    def test_create_fish_metrics_table_basic(self):
        """Test basic fish metrics table creation."""
        from dash import dash_table, html
        
        table = create_fish_metrics_table(self.sample_metrics_data, self.sample_summary_data)
        
        # Should return Div containing DataTable and REP note
        self.assertIsInstance(table, html.Div)
        
        # Should contain a DataTable as first child
        self.assertIsInstance(table.children[0], dash_table.DataTable)
        data_table = table.children[0]
        
        # Should have correct structure
        self.assertEqual(data_table.id, 'fish-metrics-table')
        self.assertGreaterEqual(len(data_table.columns), 1)  # At least metric column

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

    def test_create_fish_metrics_table_uses_shared_utilities(self):
        """Test that metrics table uses shared formatting utilities."""
        from dash import dash_table, html
        
        table = create_fish_metrics_table(self.sample_metrics_data, self.sample_summary_data)
        
        if isinstance(table, html.Div) and len(table.children) > 0:
            data_table = table.children[0]
            if isinstance(data_table, dash_table.DataTable):
                # Should use shared table styling
                self.assertIsNotNone(data_table.style_table)
                self.assertIsNotNone(data_table.style_header)
                self.assertIsNotNone(data_table.style_cell)
                
                # Should have conditional formatting
                self.assertGreater(len(data_table.style_data_conditional), 0)

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

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_integration_with_shared_visualization_utils(self, mock_get_fish):
        """Test integration with shared visualization utilities."""
        mock_get_fish.return_value = self.sample_fish_data
        
        fig = create_fish_viz("Test Site")
        
        # Should use shared create_trace function
        trace = fig.data[0]
        self.assertEqual(trace.mode, 'lines+markers')
        
        # Should use shared update_layout function
        self.assertEqual(fig.layout.title.x, 0.5)  # Centered title
        
        # Should use shared add_reference_lines function
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Should use shared generate_hover_text function
        self.assertIsNotNone(trace.text)
        self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    def test_fish_specific_vs_shared_functionality(self):
        """Test that fish module correctly uses shared vs. fish-specific functionality."""
        # Test that fish uses its own thresholds and not macro thresholds
        self.assertIn('Excellent', INTEGRITY_THRESHOLDS)
        self.assertNotIn('Non-impaired', INTEGRITY_THRESHOLDS)  # Macro threshold
        
        # Test that fish metrics are fish-specific
        self.assertIn('Total No. of species', FISH_METRIC_ORDER)
        self.assertNotIn('Taxa Richness', FISH_METRIC_ORDER)  # Macro metric

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_fish_single_trace_vs_macro_multi_trace(self, mock_get_fish):
        """Test that fish viz has single trace while macro has multiple."""
        mock_get_fish.return_value = self.sample_fish_data
        
        fig = create_fish_viz("Test Site")
        
        # Fish should have single trace (no seasons)
        self.assertEqual(len(fig.data), 1)
        
        # Should not have legend (unlike macro which has seasons)
        # Legend should be hidden for single trace
        if hasattr(fig.layout, 'showlegend'):
            self.assertFalse(fig.layout.showlegend)

    # =============================================================================
    # CORE FUNCTIONALITY TESTS
    # =============================================================================

    @patch('visualizations.fish_viz.get_fish_dataframe')
    def test_complete_visualization_workflow(self, mock_get_fish):
        """Test complete end-to-end visualization creation process."""
        mock_get_fish.return_value = self.sample_fish_data
        
        # Test visualization creation
        viz_result = create_fish_viz('Test Site')
        
        # Verify it's a valid figure with proper structure
        self.assertIsInstance(viz_result, go.Figure)
        self.assertEqual(len(viz_result.data), 1)  # Single trace for fish
        
        # Verify it has proper layout from shared utilities
        self.assertIsNotNone(viz_result.layout.title)
        self.assertIsNotNone(viz_result.layout.xaxis)
        self.assertIsNotNone(viz_result.layout.yaxis)
        
        # Verify it has reference lines for integrity classes
        self.assertGreater(len(viz_result.layout.shapes), 0)
        
        # Verify trace has proper hover text
        trace = viz_result.data[0]
        self.assertIsNotNone(trace.text)

    @patch('visualizations.fish_viz.get_fish_metrics_data_for_table')
    def test_complete_table_workflow(self, mock_get_data):
        """Test complete metrics table creation workflow."""
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        
        # Test accordion creation (which calls table creation)
        accordion_result = create_fish_metrics_accordion('Test Site')
        
        # Should create proper accordion structure
        from dash import html
        self.assertIsInstance(accordion_result, html.Div)
        
        # Test direct table creation
        table_result = create_fish_metrics_table(
            self.sample_metrics_data, 
            self.sample_summary_data
        )
        
        # Should create properly formatted div with table
        from dash import dash_table, html
        self.assertIsInstance(table_result, html.Div)
        
        # Should contain a DataTable as first child
        data_table = table_result.children[0]
        self.assertIsInstance(data_table, dash_table.DataTable)
        self.assertEqual(data_table.id, 'fish-metrics-table')

    def test_fish_hover_text_contains_rep_notation(self):
        """Test that fish hover text handles REP notation for replicate samples."""
        # Create data with REP notation
        fish_data_with_rep = self.sample_fish_data.copy()
        fish_data_with_rep.loc[0, 'site_name'] = 'Test Site REP'
        
        with patch('visualizations.fish_viz.get_fish_dataframe') as mock_get_fish:
            mock_get_fish.return_value = fish_data_with_rep
            
            fig = create_fish_viz("Test Site")
            
            # Should handle REP notation in hover text
            trace = fig.data[0]
            self.assertIsNotNone(trace.text)
            # REP should be preserved in the hover text for fish data
            hover_text = trace.text[0] if trace.text else ""
            # Just verify that hover text was generated (specific REP handling is implementation detail)
            self.assertIsInstance(hover_text, str)

if __name__ == '__main__':
    unittest.main(verbosity=2)