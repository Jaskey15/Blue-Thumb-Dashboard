"""
Test suite for visualization utilities.
Tests the shared functions in visualizations.visualization_utils module.
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

from visualizations.visualization_utils import (
    # Core visualization functions
    add_reference_lines,
    update_layout,
    create_trace,
    generate_hover_text,
    
    # Data processing functions
    calculate_dynamic_y_range,
    format_metrics_table,
    
    # Table and UI functions
    create_table_styles,
    create_data_table,
    
    # Error handling functions
    create_empty_figure,
    create_error_figure,
    
    # Constants
    DEFAULT_COLORS,
    FONT_SIZES
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_visualization_utils", category="testing")

class TestVisualizationUtils(unittest.TestCase):
    """Test visualization utility functions."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample data with dates for testing
        self.sample_habitat_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023],
            'assessment_date': pd.to_datetime(['2020-06-15', '2021-07-20', '2022-08-10', '2023-06-25']),
            'total_score': [85, 92, 78, 88],
            'habitat_grade': ['B', 'A', 'C', 'B']
        })
        
        self.sample_fish_data = pd.DataFrame({
            'year': [2020, 2021, 2022, 2023],
            'collection_date': pd.to_datetime(['2020-09-15', '2021-08-20', '2022-07-10', '2023-09-05']),
            'comparison_to_reference': [0.85, 0.72, 0.91, 0.68],
            'integrity_class': ['Good', 'Fair', 'Good', 'Fair']
        })
        
        self.sample_macro_data = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021],
            'collection_date': pd.to_datetime(['2020-06-15', '2020-12-15', '2021-07-20', '2021-12-20']),
            'season': ['Summer', 'Winter', 'Summer', 'Winter'],
            'comparison_to_reference': [0.75, 0.68, 0.82, 0.71],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired', 'Non-impaired', 'Slightly Impaired'],
            'habitat': ['Riffle', 'Vegetation', 'Riffle', 'Vegetation']
        })
        
        # Sample metrics and summary data
        self.sample_metrics_data = pd.DataFrame({
            'year': [2020, 2020, 2020, 2021, 2021, 2021],
            'metric_name': ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score', 
                          'Taxa Richness', 'EPT Taxa Richness', 'HBI Score'],
            'metric_score': [8, 5, 3.2, 9, 6, 3.0]
        })
        
        self.sample_summary_data = pd.DataFrame({
            'year': [2020, 2021],
            'total_score': [42, 48],
            'comparison_to_reference': [0.75, 0.82],
            'biological_condition': ['Slightly Impaired', 'Non-impaired']
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

    def test_add_reference_lines_empty_data(self):
        """Test adding reference lines with empty data."""
        fig = go.Figure()
        empty_df = pd.DataFrame()
        
        updated_fig = add_reference_lines(fig, empty_df, self.sample_thresholds)
        
        # Should handle gracefully
        self.assertIs(updated_fig, fig)

    def test_update_layout_basic(self):
        """Test basic figure layout update."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))
        
        updated_fig = update_layout(
            fig, 
            self.sample_fish_data, 
            "Test Title",
            y_label="Test Y Label",
            y_column='comparison_to_reference'
        )
        
        # Should return the same figure object
        self.assertIs(updated_fig, fig)
        
        # Should have correct layout settings
        self.assertEqual(fig.layout.title.text, "Test Title")
        self.assertEqual(fig.layout.yaxis.title.text, "Test Y Label")
        self.assertEqual(fig.layout.title.x, 0.5)  # Centered
        
        # Should have year-based x-axis
        self.assertEqual(fig.layout.xaxis.title.text, "Year")

    def test_update_layout_with_legend(self):
        """Test layout update with legend (for macro data)."""
        fig = go.Figure()
        
        updated_fig = update_layout(
            fig, 
            self.sample_macro_data, 
            "Macro Plot",
            y_label="Score",
            has_legend=True
        )
        
        # Should add legend title for seasons
        self.assertEqual(fig.layout.legend.title.text, "Season")

    def test_create_trace_basic(self):
        """Test creating a basic trace."""
        hover_fields = {
            'Collection Date': 'collection_date',
            'IBI Score': 'comparison_to_reference',
            'Integrity Class': 'integrity_class'
        }
        
        trace = create_trace(
            self.sample_fish_data,
            date_column='collection_date',
            y_column='comparison_to_reference',
            name='Fish IBI',
            color='blue',
            hover_fields=hover_fields
        )
        
        # Should return a Scatter trace
        self.assertIsInstance(trace, go.Scatter)
        self.assertEqual(trace.name, 'Fish IBI')
        self.assertEqual(trace.line.color, 'blue')
        self.assertEqual(trace.mode, 'lines+markers')
        
        # Should have hover text
        self.assertIsNotNone(trace.text)
        self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    def test_create_trace_empty_data(self):
        """Test creating trace with empty data."""
        empty_df = pd.DataFrame()
        
        trace = create_trace(
            empty_df,
            date_column='collection_date',
            y_column='comparison_to_reference',
            name='Empty Trace'
        )
        
        # Should return empty scatter trace
        self.assertIsInstance(trace, go.Scatter)

    def test_generate_hover_text_fish_data(self):
        """Test hover text generation for fish data."""
        hover_fields = {
            'Collection Date': 'collection_date',
            'IBI Score': 'comparison_to_reference',
            'Integrity Class': 'integrity_class'
        }
        
        hover_text = generate_hover_text(self.sample_fish_data, hover_fields)
        
        # Should return list of strings
        self.assertIsInstance(hover_text, list)
        self.assertEqual(len(hover_text), len(self.sample_fish_data))
        
        # First hover text should contain expected elements
        first_text = hover_text[0]
        self.assertIn('Collection Date', first_text)
        self.assertIn('IBI Score', first_text)
        self.assertIn('Integrity Class', first_text)
        self.assertIn('09-15-2020', first_text)  # Date formatting
        self.assertIn('0.85', first_text)  # Score formatting

    def test_generate_hover_text_habitat_data(self):
        """Test hover text generation for habitat data."""
        hover_fields = {
            'Assessment Date': 'assessment_date',
            'Habitat Score': 'total_score',
            'Grade': 'habitat_grade'
        }
        
        hover_text = generate_hover_text(self.sample_habitat_data, hover_fields)
        
        # Should return list of strings
        self.assertIsInstance(hover_text, list)
        
        # First hover text should contain expected elements
        first_text = hover_text[0]
        self.assertIn('Assessment Date', first_text)
        self.assertIn('Habitat Score', first_text)
        self.assertIn('Grade', first_text)
        self.assertIn('85', first_text)  # Integer score for habitat

    def test_generate_hover_text_macro_data(self):
        """Test hover text generation for macro data."""
        hover_fields = {
            'Collection Date': 'collection_date',
            'Season': 'season',
            'Habitat Type': 'habitat',
            'Bioassessment Score': 'comparison_to_reference',
            'Biological Condition': 'biological_condition'
        }
        
        hover_text = generate_hover_text(self.sample_macro_data, hover_fields)
        
        # Should return list of strings
        self.assertIsInstance(hover_text, list)
        
        # First hover text should contain expected elements
        first_text = hover_text[0]
        self.assertIn('Collection Date', first_text)
        self.assertIn('Season', first_text)
        self.assertIn('Habitat Type', first_text)
        self.assertIn('Summer', first_text)
        self.assertIn('0.75', first_text)  # Decimal score for biological

    # =============================================================================
    # DATA PROCESSING FUNCTION TESTS
    # =============================================================================

    def test_calculate_dynamic_y_range_biological_data(self):
        """Test y-range calculation for biological data."""
        y_min, y_max = calculate_dynamic_y_range(
            self.sample_fish_data, 
            'comparison_to_reference'
        )
        
        # Should return appropriate range for biological data
        self.assertEqual(y_min, 0)
        # Max should be at least 1.1 (default) since data max is 0.91
        self.assertGreaterEqual(y_max, 1.1)

    def test_calculate_dynamic_y_range_habitat_data(self):
        """Test y-range calculation for habitat data."""
        y_min, y_max = calculate_dynamic_y_range(
            self.sample_habitat_data, 
            'total_score'
        )
        
        # Should return appropriate range for habitat data
        self.assertEqual(y_min, 0)
        # Max should be at least 110 (default) since data max is 92
        self.assertGreaterEqual(y_max, 110)

    def test_calculate_dynamic_y_range_empty_data(self):
        """Test y-range calculation with empty data."""
        empty_df = pd.DataFrame()
        
        # Test biological default
        y_min, y_max = calculate_dynamic_y_range(empty_df, 'comparison_to_reference')
        self.assertEqual(y_min, 0)
        self.assertEqual(y_max, 1.1)
        
        # Test habitat default
        y_min, y_max = calculate_dynamic_y_range(empty_df, 'total_score')
        self.assertEqual(y_min, 0)
        self.assertEqual(y_max, 110)

    def test_format_metrics_table_basic(self):
        """Test basic metrics table formatting."""
        metric_order = ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score']
        summary_labels = ['Total Score', 'Comparison to Reference', 'Biological Condition']
        
        metrics_table, summary_rows = format_metrics_table(
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

    def test_format_metrics_table_empty_data(self):
        """Test metrics table formatting with empty data."""
        metric_order = ['Taxa Richness', 'EPT Taxa Richness']
        empty_df = pd.DataFrame()
        
        metrics_table, summary_rows = format_metrics_table(
            empty_df, empty_df, metric_order
        )
        
        # Should handle gracefully
        self.assertIsInstance(metrics_table, pd.DataFrame)
        self.assertIsInstance(summary_rows, pd.DataFrame)
        self.assertEqual(metrics_table['Metric'].tolist(), metric_order)

    # =============================================================================
    # TABLE AND UI FUNCTION TESTS
    # =============================================================================

    def test_create_table_styles(self):
        """Test table styling creation."""
        mock_metrics_table = pd.DataFrame({'Metric': ['A', 'B', 'C']})
        
        styles = create_table_styles(mock_metrics_table)
        
        # Should return dictionary with expected keys
        expected_keys = ['style_table', 'style_header', 'style_cell', 
                        'style_cell_conditional', 'style_data_conditional']
        for key in expected_keys:
            self.assertIn(key, styles)
        
        # Should have appropriate header styling
        self.assertEqual(styles['style_header']['backgroundColor'], 'rgb(230, 230, 230)')
        self.assertEqual(styles['style_header']['fontWeight'], 'bold')
        
        # Should have conditional styling for summary rows
        self.assertGreater(len(styles['style_data_conditional']), 0)

    def test_create_data_table(self):
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
        
        table = create_data_table(test_data, 'test-table', styles)
        
        # Should return DataTable component
        self.assertIsInstance(table, dash_table.DataTable)
        self.assertEqual(table.id, 'test-table')
        self.assertEqual(len(table.columns), 3)

    # =============================================================================
    # ERROR HANDLING FUNCTION TESTS
    # =============================================================================

    def test_create_empty_figure_with_site(self):
        """Test empty figure creation with site name."""
        fig = create_empty_figure(site_name="Test Site", data_type="fish")
        
        # Should return plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have appropriate title
        self.assertIn("Test Site", fig.layout.title.text)
        self.assertIn("fish", fig.layout.title.text)
        
        # Should have annotation
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertEqual(fig.layout.annotations[0].text, "No data available")

    def test_create_error_figure(self):
        """Test error figure creation."""
        error_message = "Test error message"
        fig = create_error_figure(error_message)
        
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

    def test_default_colors_constant(self):
        """Test DEFAULT_COLORS constant structure."""
        # Should have seasonal colors
        self.assertIn('Winter', DEFAULT_COLORS)
        self.assertIn('Summer', DEFAULT_COLORS)
        
        # Should have condition colors
        self.assertIn('excellent', DEFAULT_COLORS)
        self.assertIn('good', DEFAULT_COLORS)
        self.assertIn('fair', DEFAULT_COLORS)
        self.assertIn('poor', DEFAULT_COLORS)
        
        # Should have default color
        self.assertIn('default', DEFAULT_COLORS)
        
        # All values should be strings (color names/codes)
        for color in DEFAULT_COLORS.values():
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

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_full_visualization_workflow_fish(self):
        """Test complete workflow for fish visualization."""
        fig = go.Figure()
        
        # Create trace
        hover_fields = {
            'Collection Date': 'collection_date',
            'IBI Score': 'comparison_to_reference',
            'Integrity Class': 'integrity_class'
        }
        
        trace = create_trace(
            self.sample_fish_data,
            date_column='collection_date',
            y_column='comparison_to_reference',
            name='Fish IBI',
            hover_fields=hover_fields
        )
        fig.add_trace(trace)
        
        # Update layout
        fig = update_layout(
            fig,
            self.sample_fish_data,
            "Fish IBI Scores",
            y_label="IBI Score",
            y_column='comparison_to_reference'
        )
        
        # Add reference lines
        fig = add_reference_lines(
            fig,
            self.sample_fish_data,
            self.sample_thresholds,
            self.sample_threshold_colors
        )
        
        # Should have complete visualization
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 1)
        self.assertGreater(len(fig.layout.shapes), 0)
        self.assertEqual(fig.layout.title.text, "Fish IBI Scores")

    def test_full_table_workflow(self):
        """Test complete workflow for metrics table creation."""
        metric_order = ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score']
        summary_labels = ['Total Score', 'Comparison to Reference', 'Biological Condition']
        
        # Format table data
        metrics_table, summary_rows = format_metrics_table(
            self.sample_metrics_data,
            self.sample_summary_data,
            metric_order,
            summary_labels
        )
        
        # Combine tables
        full_table = pd.concat([metrics_table, summary_rows], ignore_index=True)
        
        # Create styles
        styles = create_table_styles(metrics_table)
        
        # Create table component
        table = create_data_table(full_table, 'test-metrics-table', styles)
        
        # Should have complete table
        from dash import dash_table
        self.assertIsInstance(table, dash_table.DataTable)
        self.assertEqual(table.id, 'test-metrics-table')
        self.assertGreater(len(table.data), len(metric_order))  # Includes summary rows

if __name__ == '__main__':
    unittest.main(verbosity=2) 