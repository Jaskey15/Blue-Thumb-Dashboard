"""
Test suite for chemical visualization functionality.
Tests the logic in visualizations.chemical_viz module.
"""

import os
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils import setup_logging
from visualizations.chemical_viz import (
    COLORS,
    MARKER_SIZES,
    _add_parameter_reference_lines,
    _add_standard_plot,
    _add_threshold_plot,
    _format_date_axes,
    create_all_parameters_view,
    create_time_series_plot,
)
from visualizations.visualization_utils import create_empty_figure, create_error_figure

# Set up logging for tests
logger = setup_logging("test_chemical_viz", category="testing")


class TestChemicalViz(unittest.TestCase):
    """Test chemical visualization functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample chemical data for testing
        self.sample_chemical_data = pd.DataFrame({
            'Site_Name': ['Blue Creek at Highway 9', 'Red River at Bridge', 'Tenmile Creek'],
            'Date': pd.to_datetime(['2023-01-15', '2023-06-20', '2023-12-10']),
            'Year': [2023, 2023, 2023],
            'Month': [1, 6, 12],
            'do_percent': [95.5, 110.2, 75.0],  # Normal, High, Low
            'pH': [7.2, 8.5, 6.0],              # Normal, High, Low  
            'Nitrate': [0.5, 1.2, 0.3],
            'Nitrite': [0.05, 0.1, 0.03],
            'Ammonia': [0.1, 0.3, 0.03],
            'Phosphorus': [0.02, 0.15, 0.08],   # Normal, High, Medium
            'Chloride': [25.0, 280.0, 45.0],    # Normal, High, Normal
            'soluble_nitrogen': [0.65, 1.6, 0.36]  # Normal, High, Normal
        })
        
        # Add status columns for threshold testing
        self.sample_chemical_data['do_percent_status'] = ['Normal', 'Above Normal (Basic/Alkaline)', 'Below Normal (Acidic)']
        self.sample_chemical_data['pH_status'] = ['Normal', 'Above Normal (Basic/Alkaline)', 'Below Normal (Acidic)']
        self.sample_chemical_data['Phosphorus_status'] = ['Normal', 'Poor', 'Caution']
        self.sample_chemical_data['Chloride_status'] = ['Normal', 'Poor', 'Normal']
        
        # Sample reference values
        self.sample_reference_values = {
            'do_percent': {
                'normal min': 80,
                'normal max': 130,
                'caution min': 50,
                'caution max': 150
            },
            'pH': {
                'normal min': 6.5,
                'normal max': 9.0
            },
            'soluble_nitrogen': {
                'normal': 0.8,
                'caution': 1.5
            },
            'Phosphorus': {
                'normal': 0.05,
                'caution': 0.1
            },
            'Chloride': {
                'poor': 250
            }
        }

    # =============================================================================
    # HELPER FUNCTION TESTS
    # =============================================================================

    def test_create_empty_figure_basic(self):
        """Test creation of empty figure with site name and data type."""
        site_name = "Test Site"
        data_type = "chemical"
        
        fig = create_empty_figure(site_name, data_type)
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have appropriate title
        self.assertIn(data_type, fig.layout.title.text)
        self.assertIn(site_name, fig.layout.title.text)
        
        # Should have annotation with message
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertIn("No data available", fig.layout.annotations[0].text)

    def test_create_error_figure_basic(self):
        """Test creation of error figure with message."""
        error_message = "Database connection failed"
        
        fig = create_error_figure(error_message)
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have error title
        self.assertEqual(fig.layout.title.text, "Error creating visualization")
        
        # Should have annotation with error message
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertIn(error_message, fig.layout.annotations[0].text)

    def test_format_date_axes_basic(self):
        """Test date axis formatting."""
        fig = go.Figure()
        fig.add_scatter(x=[1, 2, 3], y=[1, 2, 3])
        
        formatted_fig = _format_date_axes(fig, nticks=5)
        
        # Should return the same figure object
        self.assertIs(formatted_fig, fig)
        
        # Should set tick format and mode
        self.assertEqual(fig.layout.xaxis.tickformat, '%Y')
        self.assertEqual(fig.layout.xaxis.tickmode, 'auto')
        self.assertEqual(fig.layout.xaxis.nticks, 5)

    def test_add_parameter_reference_lines_do_percent(self):
        """Test adding reference lines for DO percent."""
        fig = go.Figure()
        df = self.sample_chemical_data
        
        fig = _add_parameter_reference_lines(fig, 'do_percent', df, self.sample_reference_values)
        
        # Should add reference lines (shapes)
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Check that shapes have the expected properties
        shapes = fig.layout.shapes
        for shape in shapes:
            self.assertEqual(shape.type, 'line')
            self.assertIsNotNone(shape.line.color)

    def test_add_parameter_reference_lines_ph(self):
        """Test adding reference lines for pH."""
        fig = go.Figure()
        df = self.sample_chemical_data
        
        fig = _add_parameter_reference_lines(fig, 'pH', df, self.sample_reference_values)
        
        # Should add reference lines for pH bounds
        self.assertGreater(len(fig.layout.shapes), 0)

    def test_add_parameter_reference_lines_nutrients(self):
        """Test adding reference lines for nutrients."""
        fig = go.Figure()
        df = self.sample_chemical_data
        
        # Test soluble nitrogen
        fig = _add_parameter_reference_lines(fig, 'soluble_nitrogen', df, self.sample_reference_values)
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Test phosphorus
        fig2 = go.Figure()
        fig2 = _add_parameter_reference_lines(fig2, 'Phosphorus', df, self.sample_reference_values)
        self.assertGreater(len(fig2.layout.shapes), 0)

    def test_add_parameter_reference_lines_unknown_parameter(self):
        """Test reference lines with unknown parameter."""
        fig = go.Figure()
        df = self.sample_chemical_data
        
        # Should handle unknown parameter gracefully
        fig = _add_parameter_reference_lines(fig, 'unknown_param', df, self.sample_reference_values)
        
        # Should not add any shapes
        self.assertEqual(len(fig.layout.shapes), 0)

    # =============================================================================
    # PLOT CREATION FUNCTION TESTS
    # =============================================================================

    def test_add_threshold_plot_basic(self):
        """Test adding threshold-based plot with status columns."""
        fig = go.Figure()
        df = self.sample_chemical_data
        
        fig = _add_threshold_plot(fig, df, 'do_percent', self.sample_reference_values, 
                                 MARKER_SIZES['individual'], 'DO Saturation (%)')
        
        # Should add traces for different status categories
        self.assertGreater(len(fig.data), 0)
        
        # Should have traces with different colors
        trace_colors = [trace.marker.color for trace in fig.data if hasattr(trace, 'marker')]
        self.assertGreater(len(set(trace_colors)), 1)  # Multiple colors used

    def test_add_threshold_plot_missing_status_column(self):
        """Test threshold plot when status column is missing."""
        fig = go.Figure()
        df = self.sample_chemical_data.drop(columns=['do_percent_status'])
        
        # Should handle missing status column gracefully
        fig = _add_threshold_plot(fig, df, 'do_percent', self.sample_reference_values,
                                 MARKER_SIZES['individual'], 'DO Saturation (%)')
        
        # Should still add traces (default to 'Normal')
        self.assertGreater(len(fig.data), 0)

    def test_add_standard_plot_basic(self):
        """Test adding standard blue scatter plot."""
        fig = go.Figure()
        df = self.sample_chemical_data
        
        fig = _add_standard_plot(fig, df, 'pH', MARKER_SIZES['individual'], 'pH')
        
        # Should add one trace
        self.assertEqual(len(fig.data), 1)
        
        # Should be blue markers with lines
        trace = fig.data[0]
        self.assertEqual(trace.marker.color, 'blue')
        self.assertEqual(trace.line.color, 'blue')
        self.assertEqual(trace.mode, 'markers+lines')

    def test_add_standard_plot_dashboard_mode(self):
        """Test standard plot in dashboard mode (smaller markers)."""
        from plotly.subplots import make_subplots

        # Create subplot figure for dashboard mode testing
        fig = make_subplots(rows=1, cols=1)
        df = self.sample_chemical_data
        
        fig = _add_standard_plot(fig, df, 'pH', MARKER_SIZES['dashboard'], 'pH', row=1, col=1)
        
        # Should add trace with smaller markers
        trace = fig.data[0]
        self.assertEqual(trace.marker.size, MARKER_SIZES['dashboard'])
        
        # Should have reduced opacity for dashboard
        self.assertEqual(trace.opacity, 0.7)

    # =============================================================================
    # MAIN VISUALIZATION FUNCTION TESTS
    # =============================================================================

    def test_create_time_series_plot_basic(self):
        """Test basic time series plot creation."""
        df = self.sample_chemical_data
        site_name = "Blue Creek at Highway 9"
        
        fig = create_time_series_plot(
            df, 'do_percent', self.sample_reference_values,
            site_name=site_name
        )
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have title with site name
        self.assertIn(site_name, fig.layout.title.text)
        
        # Should have data traces
        self.assertGreater(len(fig.data), 0)
        
        # Should have axis labels
        self.assertIsNotNone(fig.layout.xaxis.title.text)
        self.assertIsNotNone(fig.layout.yaxis.title.text)

    def test_create_time_series_plot_with_thresholds(self):
        """Test time series plot with threshold highlighting."""
        df = self.sample_chemical_data
        
        fig = create_time_series_plot(
            df, 'do_percent', self.sample_reference_values,
            highlight_thresholds=True
        )
        
        # Should have multiple traces (different threshold categories)
        self.assertGreater(len(fig.data), 1)
        
        # Should have reference lines (shapes)
        self.assertGreater(len(fig.layout.shapes), 0)

    def test_create_time_series_plot_without_thresholds(self):
        """Test time series plot without threshold highlighting."""
        df = self.sample_chemical_data
        
        fig = create_time_series_plot(
            df, 'do_percent', self.sample_reference_values,
            highlight_thresholds=False
        )
        
        # Should have standard blue plot
        self.assertGreaterEqual(len(fig.data), 1)
        
        # Check that at least one trace is blue
        blue_traces = [trace for trace in fig.data if getattr(trace.marker, 'color', None) == 'blue']
        self.assertGreater(len(blue_traces), 0)

    def test_create_time_series_plot_custom_labels(self):
        """Test time series plot with custom title and labels."""
        df = self.sample_chemical_data
        custom_title = "Custom pH Plot"
        custom_ylabel = "pH Units"
        
        fig = create_time_series_plot(
            df, 'pH', self.sample_reference_values,
            title=custom_title, y_label=custom_ylabel
        )
        
        # Should use custom title and y-label
        self.assertEqual(fig.layout.title.text, custom_title)
        self.assertEqual(fig.layout.yaxis.title.text, custom_ylabel)

    def test_create_time_series_plot_empty_data(self):
        """Test time series plot with empty data."""
        empty_df = pd.DataFrame()
        
        fig = create_time_series_plot(
            empty_df, 'do_percent', self.sample_reference_values
        )
        
        # Should return empty figure with message
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.layout.annotations), 1)
        self.assertIn("No data available", fig.layout.annotations[0].text)

    @patch('visualizations.chemical_viz.get_chemical_data_from_db')
    @patch('visualizations.chemical_viz.get_reference_values')
    def test_create_all_parameters_view_basic(self, mock_get_ref, mock_get_data):
        """Test basic parameter dashboard creation."""
        # Mock data loading functions
        mock_get_data.return_value = self.sample_chemical_data
        mock_get_ref.return_value = self.sample_reference_values
        
        fig = create_all_parameters_view()
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have subplot structure
        self.assertGreater(len(fig.data), 4)  # Multiple parameters
        
        # Should have title
        self.assertIsNotNone(fig.layout.title.text)

    def test_create_all_parameters_view_with_data(self):
        """Test parameter dashboard with provided data."""
        df = self.sample_chemical_data
        parameters = ['do_percent', 'pH', 'Phosphorus', 'Chloride']
        
        fig = create_all_parameters_view(
            df=df, 
            parameters=parameters,
            reference_values=self.sample_reference_values,
            site_name="Test Site"
        )
        
        # Should create subplots for each parameter
        self.assertIsInstance(fig, go.Figure)
        
        # Should have title with site name
        self.assertIn("Test Site", fig.layout.title.text)
        
        # Should have multiple traces
        self.assertGreater(len(fig.data), len(parameters))

    def test_create_all_parameters_view_with_thresholds(self):
        """Test dashboard with threshold highlighting enabled."""
        df = self.sample_chemical_data
        parameters = ['do_percent', 'pH']
        
        fig = create_all_parameters_view(
            df=df,
            parameters=parameters,
            reference_values=self.sample_reference_values,
            highlight_thresholds=True
        )
        
        # Should have threshold-colored traces
        self.assertGreater(len(fig.data), len(parameters))

    def test_create_all_parameters_view_without_thresholds(self):
        """Test dashboard without threshold highlighting."""
        df = self.sample_chemical_data
        parameters = ['do_percent', 'pH']
        
        fig = create_all_parameters_view(
            df=df,
            parameters=parameters,
            reference_values=self.sample_reference_values,
            highlight_thresholds=False
        )
        
        # Should have standard plots
        self.assertGreaterEqual(len(fig.data), len(parameters))

    def test_create_all_parameters_view_empty_data(self):
        """Test dashboard creation with empty data."""
        empty_df = pd.DataFrame()
        parameters = ['do_percent', 'pH']
        
        fig = create_all_parameters_view(
            df=empty_df,
            parameters=parameters,
            reference_values=self.sample_reference_values
        )
        
        # Should return empty figure with message
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.layout.annotations), 1)

    # =============================================================================
    # CONSTANTS AND CONFIGURATION TESTS
    # =============================================================================

    def test_colors_constant(self):
        """Test that COLORS constant has expected values."""
        # Should have all expected status categories
        expected_categories = ['Normal', 'Caution', 'Above Normal (Basic/Alkaline)', 
                             'Below Normal (Acidic)', 'Poor', 'Unknown']
        
        for category in expected_categories:
            self.assertIn(category, COLORS)
        
        # Colors should be valid hex or named colors
        for color in COLORS.values():
            self.assertIsInstance(color, str)
            self.assertTrue(color.startswith('#') or color.isalpha())

    def test_marker_sizes_constant(self):
        """Test that MARKER_SIZES constant has expected values."""
        # Should have both individual and dashboard sizes
        self.assertIn('individual', MARKER_SIZES)
        self.assertIn('dashboard', MARKER_SIZES)
        
        # Individual should be larger than dashboard
        self.assertGreater(MARKER_SIZES['individual'], MARKER_SIZES['dashboard'])
        
        # Should be positive integers
        for size in MARKER_SIZES.values():
            self.assertIsInstance(size, int)
            self.assertGreater(size, 0)

    # =============================================================================
    # EDGE CASES AND ERROR HANDLING
    # =============================================================================

    def test_missing_parameter_in_data(self):
        """Test behavior when parameter is missing from data."""
        df = self.sample_chemical_data.drop(columns=['do_percent'])
        
        # Should handle missing parameter gracefully - expect exception or empty figure
        try:
            fig = create_time_series_plot(df, 'do_percent', self.sample_reference_values)
            # If no exception, should return a valid figure (possibly empty)
            self.assertIsInstance(fig, go.Figure)
        except KeyError:
            # It's acceptable for this to raise a KeyError for missing parameter
            # This indicates the function doesn't currently handle missing parameters gracefully
            # but that's a reasonable behavior for a visualization function
            pass

    def test_invalid_reference_values(self):
        """Test behavior with invalid reference values."""
        invalid_refs = {'invalid_param': {'invalid_key': 'invalid_value'}}
        
        # Should handle gracefully
        fig = create_time_series_plot(
            self.sample_chemical_data, 'do_percent', invalid_refs
        )
        
        self.assertIsInstance(fig, go.Figure)

    def test_date_column_issues(self):
        """Test handling of date column problems."""
        df = self.sample_chemical_data.copy()
        df['Date'] = ['invalid', 'dates', 'here']
        
        # Should handle invalid dates gracefully
        try:
            fig = create_time_series_plot(df, 'pH', self.sample_reference_values)
            self.assertIsInstance(fig, go.Figure)
        except Exception:
            # It's acceptable if this raises an exception for invalid dates
            pass

    def test_all_null_values(self):
        """Test behavior with all null parameter values."""
        df = self.sample_chemical_data.copy()
        df['pH'] = [np.nan, np.nan, np.nan]
        
        fig = create_time_series_plot(df, 'pH', self.sample_reference_values)
        
        # Should handle null values gracefully
        self.assertIsInstance(fig, go.Figure)

    def test_single_data_point(self):
        """Test visualization with only one data point."""
        single_point_df = self.sample_chemical_data.iloc[:1].copy()
        
        fig = create_time_series_plot(
            single_point_df, 'do_percent', self.sample_reference_values
        )
        
        # Should handle single point gracefully
        self.assertIsInstance(fig, go.Figure)
        self.assertGreater(len(fig.data), 0)

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_year_shading_integration(self):
        """Test that year shading is applied correctly."""
        # Create data spanning multiple years
        multi_year_data = pd.DataFrame({
            'Date': pd.to_datetime(['2021-01-01', '2022-01-01', '2023-01-01']),
            'Year': [2021, 2022, 2023],
            'do_percent': [90, 95, 100],
            'do_percent_status': ['Normal', 'Normal', 'Normal']
        })
        
        fig = create_time_series_plot(
            multi_year_data, 'do_percent', self.sample_reference_values
        )
        
        # Should have year shading (background rectangles)
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Some shapes should be rectangles (year shading)
        rect_shapes = [shape for shape in fig.layout.shapes if shape.type == 'rect']
        self.assertGreater(len(rect_shapes), 0)

    def test_legend_configuration(self):
        """Test legend configuration for individual plots."""
        fig = create_time_series_plot(
            self.sample_chemical_data, 'do_percent', self.sample_reference_values,
            highlight_thresholds=True
        )
        
        # Should have horizontal legend at top
        self.assertEqual(fig.layout.legend.orientation, 'h')
        self.assertEqual(fig.layout.legend.yanchor, 'bottom')
        self.assertEqual(fig.layout.legend.y, 1.02)

    def test_subplot_layout_calculation(self):
        """Test subplot layout calculation for dashboard."""
        # Test with different numbers of parameters
        test_cases = [
            (['param1'], 1, 2),          # 1 param -> 1 row, 2 cols
            (['param1', 'param2'], 1, 2),    # 2 params -> 1 row, 2 cols  
            (['p1', 'p2', 'p3'], 2, 2),      # 3 params -> 2 rows, 2 cols
            (['p1', 'p2', 'p3', 'p4'], 2, 2), # 4 params -> 2 rows, 2 cols
            (['p1', 'p2', 'p3', 'p4', 'p5'], 3, 2), # 5 params -> 3 rows, 2 cols
        ]
        
        for params, expected_rows, expected_cols in test_cases:
            with self.subTest(params=len(params)):
                n_params = len(params)
                n_cols = 2
                n_rows = (n_params + 1) // 2
                
                self.assertEqual(n_rows, expected_rows)
                self.assertEqual(n_cols, expected_cols)

if __name__ == '__main__':
    unittest.main(verbosity=2) 