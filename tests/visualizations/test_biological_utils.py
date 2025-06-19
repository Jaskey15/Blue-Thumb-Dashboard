"""
Test suite for biological visualization utilities.
Tests the shared functions in visualizations.biological_utils module.
"""

import unittest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from visualizations.biological_utils import (
    # Core visualization functions
    create_biological_line_plot,
    calculate_dynamic_y_range,
    update_biological_figure_layout,
    add_reference_lines,
    
    # Table formatting functions
    format_biological_metrics_table,
    create_biological_table_styles,
    create_biological_data_table,
    
    # Hover and interaction functions
    create_hover_text,
    update_hover_data,
    
    # Error handling functions
    create_empty_biological_figure,
    create_error_biological_figure,
    
    # Constants
    BIOLOGICAL_COLORS,
    FONT_SIZES
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_biological_utils", category="testing")


class TestBiologicalUtils(unittest.TestCase):
    """Test biological visualization utility functions."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample biological data without seasons (fish-like)
        self.sample_fish_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023],
            'comparison_to_reference': [0.85, 0.72, 0.91, 0.68],
            'integrity_class': ['Good', 'Fair', 'Good', 'Fair'],
            'site_name': ['Test Site'] * 4
        })
        
        # Sample biological data with seasons (macro-like)
        self.sample_macro_data = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021, 2022, 2022],
            'season': ['Summer', 'Winter', 'Summer', 'Winter', 'Summer', 'Winter'],
            'comparison_to_reference': [0.75, 0.68, 0.82, 0.71, 0.69, 0.73],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired', 
                                   'Non-impaired', 'Slightly Impaired',
                                   'Moderately Impaired', 'Slightly Impaired'],
            'site_name': ['Test Site'] * 6
        })
        
        # Sample metrics data
        self.sample_metrics_data = pd.DataFrame({
            'year': [2020, 2020, 2020, 2021, 2021, 2021],
            'metric_name': ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score', 
                          'Taxa Richness', 'EPT Taxa Richness', 'HBI Score'],
            'metric_score': [8, 5, 3.2, 9, 6, 3.0],
            'season': ['Summer', 'Summer', 'Summer', 'Summer', 'Summer', 'Summer']
        })
        
        # Sample summary data
        self.sample_summary_data = pd.DataFrame({
            'year': [2020, 2021],
            'total_score': [42, 48],
            'comparison_to_reference': [0.75, 0.82],
            'biological_condition': ['Slightly Impaired', 'Non-impaired'],
            'season': ['Summer', 'Summer']
        })
        
        # Sample thresholds
        self.sample_thresholds = {
            'Excellent': 0.90,
            'Good': 0.75,
            'Fair': 0.60,
            'Poor': 0.45
        }
        
        self.sample_threshold_colors = {
            'Excellent': 'green',
            'Good': 'lightgreen',
            'Fair': 'orange',
            'Poor': 'red'
        }

    # =============================================================================
    # CORE VISUALIZATION FUNCTION TESTS
    # =============================================================================

    def test_create_biological_line_plot_single_line(self):
        """Test creating line plot without seasons (fish-style)."""
        fig = create_biological_line_plot(
            self.sample_fish_data,
            "Test Fish Plot",
            y_column='comparison_to_reference',
            has_seasons=False
        )
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have one trace (no seasons)
        self.assertEqual(len(fig.data), 1)
        
        # Should have the correct title
        self.assertEqual(fig.layout.title.text, "Test Fish Plot")
        
        # Should use the correct data
        trace = fig.data[0]
        self.assertEqual(list(trace.x), [2020, 2021, 2022, 2023])
        self.assertAlmostEqual(list(trace.y), [0.85, 0.72, 0.91, 0.68])

    def test_create_biological_line_plot_multi_line(self):
        """Test creating line plot with seasons (macro-style)."""
        fig = create_biological_line_plot(
            self.sample_macro_data,
            "Test Macro Plot",
            y_column='comparison_to_reference',
            has_seasons=True,
            color_map=BIOLOGICAL_COLORS
        )
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have two traces (Summer and Winter)
        self.assertEqual(len(fig.data), 2)
        
        # Should have the correct title
        self.assertEqual(fig.layout.title.text, "Test Macro Plot")
        
        # Check that both seasons are represented
        trace_names = [trace.name for trace in fig.data]
        self.assertIn('Summer', trace_names)
        self.assertIn('Winter', trace_names)

    def test_create_biological_line_plot_empty_data(self):
        """Test line plot creation with empty data."""
        empty_df = pd.DataFrame()
        
        fig = create_biological_line_plot(
            empty_df,
            "Empty Plot",
            has_seasons=False
        )
        
        # Should handle gracefully and return error figure
        self.assertIsInstance(fig, go.Figure)

    def test_calculate_dynamic_y_range_normal_data(self):
        """Test y-range calculation with normal data."""
        y_min, y_max = calculate_dynamic_y_range(
            self.sample_fish_data, 
            'comparison_to_reference'
        )
        
        # Should return appropriate range
        self.assertEqual(y_min, 0)
        # Max should be greater than data max (0.91) with padding
        self.assertGreater(y_max, 0.91)
        self.assertLessEqual(y_max, 1.1)  # But not exceed default max when data < 1

    def test_calculate_dynamic_y_range_empty_data(self):
        """Test y-range calculation with empty data."""
        empty_df = pd.DataFrame()
        
        y_min, y_max = calculate_dynamic_y_range(empty_df)
        
        # Should return default range
        self.assertEqual(y_min, 0)
        self.assertEqual(y_max, 1.1)

    def test_calculate_dynamic_y_range_missing_column(self):
        """Test y-range calculation with missing column."""
        y_min, y_max = calculate_dynamic_y_range(
            self.sample_fish_data, 
            'nonexistent_column'
        )
        
        # Should return default range
        self.assertEqual(y_min, 0)
        self.assertEqual(y_max, 1.1)

    def test_update_biological_figure_layout_basic(self):
        """Test basic figure layout update."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))
        
        updated_fig = update_biological_figure_layout(
            fig, 
            self.sample_fish_data, 
            "Test Title",
            y_label="Test Y Label"
        )
        
        # Should return the same figure object
        self.assertIs(updated_fig, fig)
        
        # Should have correct y-axis settings
        self.assertEqual(fig.layout.yaxis.title.text, "Test Y Label")
        self.assertEqual(fig.layout.yaxis.tickformat, '.2f')
        
        # Should have correct x-axis settings
        self.assertEqual(fig.layout.xaxis.tickmode, 'array')
        expected_years = sorted(self.sample_fish_data['year'].unique())
        self.assertEqual(list(fig.layout.xaxis.tickvals), expected_years)
        
        # Should center title
        self.assertEqual(fig.layout.title.x, 0.5)

    def test_update_biological_figure_layout_empty_data(self):
        """Test figure layout update with empty data."""
        fig = go.Figure()
        empty_df = pd.DataFrame()
        
        updated_fig = update_biological_figure_layout(fig, empty_df, "Test Title")
        
        # Should handle gracefully
        self.assertIs(updated_fig, fig)

    def test_add_reference_lines_basic(self):
        """Test adding reference lines to figure."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[2020, 2021, 2022], y=[0.8, 0.7, 0.9]))
        
        updated_fig = add_reference_lines(
            fig, 
            self.sample_fish_data, 
            self.sample_thresholds,
            self.sample_threshold_colors
        )
        
        # Should return the same figure
        self.assertIs(updated_fig, fig)
        
        # Should add shapes for reference lines
        self.assertGreater(len(fig.layout.shapes), 0)
        self.assertEqual(len(fig.layout.shapes), len(self.sample_thresholds))
        
        # Should add annotations for labels
        self.assertGreater(len(fig.layout.annotations), 0)

    def test_add_reference_lines_empty_thresholds(self):
        """Test adding reference lines with empty thresholds."""
        fig = go.Figure()
        
        updated_fig = add_reference_lines(fig, self.sample_fish_data, {})
        
        # Should handle gracefully
        self.assertIs(updated_fig, fig)
        self.assertEqual(len(fig.layout.shapes), 0)

    def test_add_reference_lines_empty_data(self):
        """Test adding reference lines with empty data."""
        fig = go.Figure()
        empty_df = pd.DataFrame()
        
        updated_fig = add_reference_lines(fig, empty_df, self.sample_thresholds)
        
        # Should handle gracefully
        self.assertIs(updated_fig, fig)

    # =============================================================================
    # TABLE FORMATTING FUNCTION TESTS
    # =============================================================================

    def test_format_biological_metrics_table_basic(self):
        """Test basic metrics table formatting."""
        metric_order = ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score']
        summary_labels = ['Total Score', 'Comparison to Reference', 'Biological Condition']
        
        metrics_table, summary_rows = format_biological_metrics_table(
            self.sample_metrics_data,
            self.sample_summary_data,
            metric_order,
            summary_labels
        )
        
        # Should return DataFrames
        self.assertIsInstance(metrics_table, pd.DataFrame)
        self.assertIsInstance(summary_rows, pd.DataFrame)
        
        # Metrics table should have correct structure
        self.assertEqual(metrics_table['Metric'].tolist(), metric_order)
        self.assertIn('2020', metrics_table.columns)
        self.assertIn('2021', metrics_table.columns)
        
        # Summary table should have correct structure
        self.assertEqual(summary_rows['Metric'].tolist(), summary_labels)

    def test_format_biological_metrics_table_with_season(self):
        """Test metrics table formatting with season filter."""
        metric_order = ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score']
        
        metrics_table, summary_rows = format_biological_metrics_table(
            self.sample_metrics_data,
            self.sample_summary_data,
            metric_order,
            season='Summer'
        )
        
        # Should filter to Summer data only
        self.assertIsInstance(metrics_table, pd.DataFrame)
        self.assertIsInstance(summary_rows, pd.DataFrame)

    def test_format_biological_metrics_table_empty_data(self):
        """Test metrics table formatting with empty data."""
        metric_order = ['Taxa Richness', 'EPT Taxa Richness']
        empty_df = pd.DataFrame()
        
        metrics_table, summary_rows = format_biological_metrics_table(
            empty_df, empty_df, metric_order
        )
        
        # Should handle gracefully
        self.assertIsInstance(metrics_table, pd.DataFrame)
        self.assertIsInstance(summary_rows, pd.DataFrame)
        self.assertEqual(metrics_table['Metric'].tolist(), metric_order)

    def test_create_biological_table_styles(self):
        """Test table styling creation."""
        mock_metrics_table = pd.DataFrame({'Metric': ['A', 'B', 'C']})
        
        styles = create_biological_table_styles(mock_metrics_table)
        
        # Should return dictionary with expected keys
        expected_keys = ['style_table', 'style_header', 'style_cell', 
                        'style_cell_conditional', 'style_data_conditional']
        for key in expected_keys:
            self.assertIn(key, styles)
        
        # Should have appropriate header styling
        self.assertEqual(styles['style_header']['backgroundColor'], 'rgb(230, 230, 230)')
        self.assertTrue(styles['style_header']['fontWeight'], 'bold')
        
        # Should have conditional styling for summary rows
        self.assertGreater(len(styles['style_data_conditional']), 0)

    def test_create_biological_data_table(self):
        """Test data table component creation."""
        from dash import dash_table
        
        test_data = pd.DataFrame({
            'Metric': ['A', 'B'],
            '2020': [1, 2],
            '2021': [3, 4]
        })
        
        styles = {
            'style_table': {},
            'style_header': {},
            'style_cell': {},
            'style_cell_conditional': [],
            'style_data_conditional': []
        }
        
        table = create_biological_data_table(test_data, 'test-table', styles)
        
        # Should return DataTable component
        self.assertIsInstance(table, dash_table.DataTable)
        self.assertEqual(table.id, 'test-table')
        self.assertEqual(len(table.columns), 3)

    # =============================================================================
    # HOVER AND INTERACTION FUNCTION TESTS
    # =============================================================================

    def test_create_hover_text_without_seasons(self):
        """Test hover text creation for data without seasons."""
        hover_text = create_hover_text(
            self.sample_fish_data,
            has_seasons=False,
            condition_column='integrity_class'
        )
        
        # Should return list of strings
        self.assertIsInstance(hover_text, list)
        self.assertEqual(len(hover_text), len(self.sample_fish_data))
        
        # Each hover text should contain expected elements
        for i, text in enumerate(hover_text):
            self.assertIn('Year', text)
            self.assertIn('Score', text)
            self.assertIn('Condition', text)
            self.assertIn(str(self.sample_fish_data.iloc[i]['year']), text)

    def test_create_hover_text_with_seasons(self):
        """Test hover text creation for data with seasons."""
        hover_text = create_hover_text(
            self.sample_macro_data,
            has_seasons=True,
            condition_column='biological_condition'
        )
        
        # Should return list of strings
        self.assertIsInstance(hover_text, list)
        self.assertEqual(len(hover_text), len(self.sample_macro_data))
        
        # Each hover text should contain season information
        for i, text in enumerate(hover_text):
            self.assertIn('Year', text)
            self.assertIn('Season', text)
            self.assertIn('Score', text)
            self.assertIn(str(self.sample_macro_data.iloc[i]['season']), text)

    def test_update_hover_data_single_trace(self):
        """Test updating hover data for single trace."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))
        
        hover_text = ['Text 1', 'Text 2', 'Text 3']
        
        updated_fig = update_hover_data(fig, hover_text)
        
        # Should return the same figure
        self.assertIs(updated_fig, fig)
        
        # Should update trace with hover text
        trace = fig.data[0]
        self.assertEqual(list(trace.text), hover_text)
        self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    # =============================================================================
    # ERROR HANDLING FUNCTION TESTS
    # =============================================================================

    def test_create_empty_biological_figure_with_site(self):
        """Test empty figure creation with site name."""
        fig = create_empty_biological_figure(site_name="Test Site", data_type="fish")
        
        # Should return plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have appropriate title
        self.assertIn("Test Site", fig.layout.title.text)
        self.assertIn("fish", fig.layout.title.text)
        
        # Should have annotation
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertEqual(fig.layout.annotations[0].text, "No data available")

    def test_create_error_biological_figure(self):
        """Test error figure creation."""
        error_message = "Test error message"
        fig = create_error_biological_figure(error_message)
        
        # Should return plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have error title
        self.assertEqual(fig.layout.title.text, "Error creating visualization")
        
        # Should have error annotation
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertIn(error_message, fig.layout.annotations[0].text)

    # =============================================================================
    # CONSTANTS TESTS
    # =============================================================================

    def test_biological_colors_constant(self):
        """Test BIOLOGICAL_COLORS constant structure."""
        # Should have seasonal colors
        self.assertIn('Winter', BIOLOGICAL_COLORS)
        self.assertIn('Summer', BIOLOGICAL_COLORS)
        
        # Should have condition colors
        self.assertIn('excellent', BIOLOGICAL_COLORS)
        self.assertIn('good', BIOLOGICAL_COLORS)
        self.assertIn('fair', BIOLOGICAL_COLORS)
        self.assertIn('poor', BIOLOGICAL_COLORS)
        
        # Should have default color
        self.assertIn('default', BIOLOGICAL_COLORS)
        
        # All values should be strings (color names/codes)
        for color in BIOLOGICAL_COLORS.values():
            self.assertIsInstance(color, str)

    def test_font_sizes_constant(self):
        """Test FONT_SIZES constant structure."""
        expected_sizes = ['title', 'axis_title', 'header', 'cell']
        
        for size_key in expected_sizes:
            self.assertIn(size_key, FONT_SIZES)
            self.assertIsInstance(FONT_SIZES[size_key], int)
            self.assertGreater(FONT_SIZES[size_key], 0)
        
        # Title should be largest
        self.assertGreaterEqual(FONT_SIZES['title'], FONT_SIZES['axis_title'])
        self.assertGreaterEqual(FONT_SIZES['axis_title'], FONT_SIZES['header'])


if __name__ == '__main__':
    unittest.main(verbosity=2) 