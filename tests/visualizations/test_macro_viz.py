"""
Test suite for macroinvertebrate visualization functionality.
Tests the logic in visualizations.macro_viz module.
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

from visualizations.macro_viz import (
    create_macro_viz,
    create_macro_metrics_table_for_season,
    create_macro_metrics_accordion,
    CONDITION_THRESHOLDS,
    CONDITION_COLORS,
    MACRO_METRIC_ORDER,
    MACRO_SUMMARY_LABELS
)
from data_processing.data_queries import (
    get_macroinvertebrate_dataframe,
    get_macro_metrics_data_for_table
)
from utils import setup_logging

# Set up logging for tests
logger = setup_logging("test_macro_viz", category="testing")


class TestMacroViz(unittest.TestCase):
    """Test macroinvertebrate visualization functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample macro data with seasons
        self.sample_macro_data = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021, 2022, 2022],
            'season': ['Summer', 'Winter', 'Summer', 'Winter', 'Summer', 'Winter'],
            'comparison_to_reference': [0.75, 0.68, 0.82, 0.71, 0.69, 0.73],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired', 
                                   'Non-impaired', 'Slightly Impaired',
                                   'Moderately Impaired', 'Slightly Impaired'],
            'site_name': ['Test Site'] * 6
        })
        
        # Sample metrics data for both seasons
        self.sample_metrics_data = pd.DataFrame({
            'year': [2020, 2020, 2020, 2020, 2020, 2020, 2021, 2021, 2021, 2021, 2021, 2021],
            'season': ['Summer', 'Summer', 'Summer', 'Winter', 'Winter', 'Winter'] * 2,
            'metric_name': ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score'] * 4,
            'metric_score': [15, 8, 3.2, 12, 6, 3.8, 18, 10, 2.9, 14, 7, 3.5]
        })
        
        # Sample summary data for both seasons
        self.sample_summary_data = pd.DataFrame({
            'year': [2020, 2020, 2021, 2021],
            'season': ['Summer', 'Winter', 'Summer', 'Winter'],
            'total_score': [42, 38, 48, 41],
            'comparison_to_reference': [0.75, 0.68, 0.82, 0.71],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired', 
                                   'Non-impaired', 'Slightly Impaired']
        })

    # =============================================================================
    # MAIN VISUALIZATION FUNCTION TESTS
    # =============================================================================

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_create_macro_viz_with_data(self, mock_get_macro):
        """Test macro visualization creation with valid data."""
        mock_get_macro.return_value = self.sample_macro_data
        
        fig = create_macro_viz("Test Site")
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have correct title
        self.assertIn("Test Site", fig.layout.title.text)
        self.assertIn("Bioassessment Scores Over Time", fig.layout.title.text)
        
        # Should have two traces (Summer and Winter)
        self.assertEqual(len(fig.data), 2)
        
        # Should have y-axis label
        self.assertEqual(fig.layout.yaxis.title.text, 'Bioassessment Score<br>(Compared to Reference)')
        
        # Should have reference lines (shapes)
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Check that both seasons are represented
        trace_names = [trace.name for trace in fig.data]
        self.assertIn('Summer', trace_names)
        self.assertIn('Winter', trace_names)

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_create_macro_viz_no_site_name(self, mock_get_macro):
        """Test macro visualization creation without site name."""
        mock_get_macro.return_value = self.sample_macro_data
        
        fig = create_macro_viz()
        
        # Should return a plotly Figure
        self.assertIsInstance(fig, go.Figure)
        
        # Should have generic title
        self.assertEqual(fig.layout.title.text, "Bioassessment Scores Over Time")

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_create_macro_viz_filtered_by_site(self, mock_get_macro):
        """Test macro visualization creation with site filtering."""
        # Data with multiple sites
        multi_site_data = self.sample_macro_data.copy()
        multi_site_data.loc[3:, 'site_name'] = 'Other Site'
        
        mock_get_macro.return_value = multi_site_data
        
        fig = create_macro_viz("Test Site")
        
        # Should filter data for the specified site
        mock_get_macro.assert_called_once()
        self.assertIsInstance(fig, go.Figure)

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_create_macro_viz_empty_data(self, mock_get_macro):
        """Test macro visualization creation with empty data."""
        mock_get_macro.return_value = pd.DataFrame()
        
        fig = create_macro_viz("Test Site")
        
        # Should return a figure (either empty or error)
        self.assertIsInstance(fig, go.Figure)
        # The title should indicate either no data or an error
        title_text = fig.layout.title.text
        self.assertTrue(
            "No macroinvertebrate data available" in title_text or
            "Error creating visualization" in title_text
        )

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_create_macro_viz_error_handling(self, mock_get_macro):
        """Test macro visualization error handling."""
        mock_get_macro.side_effect = Exception("Database error")
        
        fig = create_macro_viz("Test Site")
        
        # Should return error figure
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.layout.title.text, "Error creating visualization")

    # =============================================================================
    # SEASONAL METRICS TABLE FUNCTION TESTS
    # =============================================================================

    def test_create_macro_metrics_table_for_season_summer(self):
        """Test macro metrics table creation for Summer season."""
        from dash import dash_table
        
        table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, 
            self.sample_summary_data, 
            'Summer'
        )
        
        # Should return DataTable component
        self.assertIsInstance(table, dash_table.DataTable)
        
        # Should have correct ID for Summer
        self.assertEqual(table.id, 'summer-macro-metrics-table')
        
        # Should have correct structure
        self.assertGreater(len(table.columns), 1)  # Metric column + year columns
        self.assertGreater(len(table.data), len(MACRO_METRIC_ORDER))  # Metrics + summary rows

    def test_create_macro_metrics_table_for_season_winter(self):
        """Test macro metrics table creation for Winter season."""
        from dash import dash_table
        
        table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, 
            self.sample_summary_data, 
            'Winter'
        )
        
        # Should return DataTable component
        self.assertIsInstance(table, dash_table.DataTable)
        
        # Should have correct ID for Winter
        self.assertEqual(table.id, 'winter-macro-metrics-table')

    def test_create_macro_metrics_table_for_season_empty_data(self):
        """Test seasonal metrics table creation with empty data."""
        from dash import html
        
        empty_df = pd.DataFrame()
        
        result = create_macro_metrics_table_for_season(empty_df, empty_df, 'Summer')
        
        # Should handle gracefully
        self.assertTrue(
            isinstance(result, html.Div) or 
            hasattr(result, 'data')  # DataTable with empty data
        )

    def test_create_macro_metrics_table_for_season_error_handling(self):
        """Test seasonal metrics table error handling."""
        from dash import html, dash_table
        
        # Pass invalid data to trigger error
        result = create_macro_metrics_table_for_season("invalid", "invalid", "Summer")
        
        # Should return either error message or empty table (both are acceptable)
        self.assertTrue(
            isinstance(result, html.Div) or 
            isinstance(result, dash_table.DataTable)
        )

    # =============================================================================
    # ACCORDION FUNCTION TESTS
    # =============================================================================

    @patch('visualizations.macro_viz.get_macro_metrics_data_for_table')
    def test_create_macro_metrics_accordion_with_data(self, mock_get_data):
        """Test macro metrics accordion creation with valid data."""
        from dash import html
        
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        
        accordion = create_macro_metrics_accordion("Test Site")
        
        # Should return HTML component containing two accordions
        self.assertIsInstance(accordion, html.Div)
        
        # Should have two children (Summer and Winter accordions)
        self.assertEqual(len(accordion.children), 2)

    @patch('visualizations.macro_viz.get_macro_metrics_data_for_table')
    def test_create_macro_metrics_accordion_with_site_filtering(self, mock_get_data):
        """Test accordion creation with site filtering."""
        from dash import html
        
        # Data with multiple sites
        multi_site_metrics = self.sample_metrics_data.copy()
        multi_site_metrics['site_name'] = ['Test Site'] * 6 + ['Other Site'] * 6
        
        multi_site_summary = self.sample_summary_data.copy()
        multi_site_summary['site_name'] = ['Test Site'] * 2 + ['Other Site'] * 2
        
        mock_get_data.return_value = (multi_site_metrics, multi_site_summary)
        
        accordion = create_macro_metrics_accordion("Test Site")
        
        # Should return HTML component
        self.assertIsInstance(accordion, html.Div)
        mock_get_data.assert_called_once()

    @patch('visualizations.macro_viz.get_macro_metrics_data_for_table')
    def test_create_macro_metrics_accordion_empty_data(self, mock_get_data):
        """Test accordion creation with empty data."""
        from dash import html
        
        mock_get_data.return_value = (pd.DataFrame(), pd.DataFrame())
        
        accordion = create_macro_metrics_accordion("Test Site")
        
        # Should return "No data available" message
        self.assertIsInstance(accordion, html.Div)
        self.assertEqual(accordion.children, "No data available")

    @patch('visualizations.macro_viz.get_macro_metrics_data_for_table')
    def test_create_macro_metrics_accordion_error_handling(self, mock_get_data):
        """Test accordion error handling."""
        from dash import html
        
        mock_get_data.side_effect = Exception("Database error")
        
        accordion = create_macro_metrics_accordion("Test Site")
        
        # Should return error message
        self.assertIsInstance(accordion, html.Div)
        self.assertIn("Error creating metrics accordion", accordion.children)

    # =============================================================================
    # CONSTANTS AND CONFIGURATION TESTS
    # =============================================================================

    def test_condition_thresholds_constant(self):
        """Test CONDITION_THRESHOLDS constant structure."""
        # Should have all expected threshold categories
        expected_categories = ['Non-impaired', 'Slightly Impaired', 'Moderately Impaired']
        
        for category in expected_categories:
            self.assertIn(category, CONDITION_THRESHOLDS)
            self.assertIsInstance(CONDITION_THRESHOLDS[category], (int, float))
            self.assertGreater(CONDITION_THRESHOLDS[category], 0)
            self.assertLessEqual(CONDITION_THRESHOLDS[category], 1)
        
        # Should be in descending order (non-impaired > slightly > moderately)
        thresholds_list = list(CONDITION_THRESHOLDS.values())
        self.assertEqual(thresholds_list, sorted(thresholds_list, reverse=True))

    def test_condition_colors_constant(self):
        """Test CONDITION_COLORS constant structure."""
        # Should have colors for all threshold categories
        for category in CONDITION_THRESHOLDS.keys():
            self.assertIn(category, CONDITION_COLORS)
            self.assertIsInstance(CONDITION_COLORS[category], str)

    def test_macro_metric_order_constant(self):
        """Test MACRO_METRIC_ORDER constant."""
        # Should be a list
        self.assertIsInstance(MACRO_METRIC_ORDER, list)
        
        # Should have expected macro metrics
        expected_metrics = [
            'Taxa Richness',
            'EPT Taxa Richness',
            'EPT Abundance',
            'HBI Score',
            '% Contribution Dominants',
            'Shannon-Weaver'
        ]
        
        self.assertEqual(MACRO_METRIC_ORDER, expected_metrics)

    def test_macro_summary_labels_constant(self):
        """Test MACRO_SUMMARY_LABELS constant."""
        # Should be a list
        self.assertIsInstance(MACRO_SUMMARY_LABELS, list)
        
        # Should have expected summary labels
        expected_labels = ['Total Score', 'Comparison to Reference', 'Biological Condition']
        self.assertEqual(MACRO_SUMMARY_LABELS, expected_labels)

    # =============================================================================
    # INTEGRATION WITH SHARED UTILITIES TESTS
    # =============================================================================

    def test_integration_with_biological_utils(self):
        """Test integration with shared biological utilities."""
        # This test ensures the macro module correctly uses shared utilities
        with patch('visualizations.macro_viz.get_macroinvertebrate_dataframe') as mock_get_macro:
            mock_get_macro.return_value = self.sample_macro_data
            
            fig = create_macro_viz("Test Site")
            
            # Should have characteristics of shared biological visualization
            self.assertIsInstance(fig, go.Figure)
            
            # Should have multiple traces (seasons for macro)
            self.assertEqual(len(fig.data), 2)
            
            # Should have hover template set by shared utilities
            for trace in fig.data:
                self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    def test_macro_specific_configurations(self):
        """Test that macro-specific configurations are correctly applied."""
        # Test that macro module uses its own thresholds and not fish thresholds
        self.assertIn('Non-impaired', CONDITION_THRESHOLDS)
        self.assertNotIn('Excellent', CONDITION_THRESHOLDS)  # Fish threshold
        
        # Test that macro metrics are macro-specific
        self.assertIn('Taxa Richness', MACRO_METRIC_ORDER)
        self.assertIn('EPT Taxa Richness', MACRO_METRIC_ORDER)
        self.assertNotIn('Total No. of species', MACRO_METRIC_ORDER)  # Fish metric

    def test_seasonal_handling_specificity(self):
        """Test that macro module correctly handles seasonal data."""
        # Macro should handle seasons while fish does not
        self.assertIn('Summer', self.sample_macro_data['season'].values)
        self.assertIn('Winter', self.sample_macro_data['season'].values)
        
        # Test that both seasons are handled in table creation
        summer_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Summer'
        )
        winter_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Winter'
        )
        
        # Both should be valid tables with different IDs
        from dash import dash_table
        self.assertIsInstance(summer_table, dash_table.DataTable)
        self.assertIsInstance(winter_table, dash_table.DataTable)
        self.assertNotEqual(summer_table.id, winter_table.id)

    # =============================================================================
    # SEASONAL DATA HANDLING TESTS
    # =============================================================================

    def test_seasonal_data_filtering(self):
        """Test that seasonal data is properly filtered."""
        # Test Summer filtering
        summer_metrics = self.sample_metrics_data[self.sample_metrics_data['season'] == 'Summer']
        summer_summary = self.sample_summary_data[self.sample_summary_data['season'] == 'Summer']
        
        summer_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Summer'
        )
        
        # Should create valid table
        from dash import dash_table
        self.assertIsInstance(summer_table, dash_table.DataTable)
        
        # Test Winter filtering
        winter_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Winter'
        )
        
        self.assertIsInstance(winter_table, dash_table.DataTable)

    def test_multi_season_hover_text_handling(self):
        """Test that hover text is correctly handled for multiple seasons."""
        with patch('visualizations.macro_viz.get_macroinvertebrate_dataframe') as mock_get_macro:
            mock_get_macro.return_value = self.sample_macro_data
            
            fig = create_macro_viz("Test Site")
            
            # Should have hover data for both seasons
            self.assertEqual(len(fig.data), 2)
            
            # Each trace should have hover template
            for trace in fig.data:
                self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')
                self.assertIsNotNone(trace.text)

    # =============================================================================
    # EDGE CASES AND ERROR HANDLING
    # =============================================================================

    def test_create_macro_viz_with_none_site(self):
        """Test macro visualization with None site name."""
        with patch('visualizations.macro_viz.get_macroinvertebrate_dataframe') as mock_get_macro:
            mock_get_macro.return_value = self.sample_macro_data
            
            fig = create_macro_viz(None)
            
            # Should handle gracefully
            self.assertIsInstance(fig, go.Figure)

    def test_create_macro_viz_single_season_data(self):
        """Test macro visualization with data from only one season."""
        single_season_data = self.sample_macro_data[self.sample_macro_data['season'] == 'Summer'].copy()
        
        with patch('visualizations.macro_viz.get_macroinvertebrate_dataframe') as mock_get_macro:
            mock_get_macro.return_value = single_season_data
            
            fig = create_macro_viz("Test Site")
            
            # Should handle single season gracefully
            self.assertIsInstance(fig, go.Figure)
            # Should have only one trace for single season
            self.assertEqual(len(fig.data), 1)

    def test_metrics_table_missing_season_data(self):
        """Test metrics table when one season has no data."""
        # Data with only Summer metrics
        summer_only_metrics = self.sample_metrics_data[
            self.sample_metrics_data['season'] == 'Summer'
        ].copy()
        
        summer_only_summary = self.sample_summary_data[
            self.sample_summary_data['season'] == 'Summer'
        ].copy()
        
        # Test Winter table creation with Summer-only data
        winter_table = create_macro_metrics_table_for_season(
            summer_only_metrics, summer_only_summary, 'Winter'
        )
        
        # Should handle gracefully
        from dash import dash_table, html
        self.assertTrue(
            isinstance(winter_table, dash_table.DataTable) or 
            isinstance(winter_table, html.Div)
        )

    def test_accordion_with_site_name_filtering(self):
        """Test accordion creation with site name that has no data."""
        with patch('visualizations.macro_viz.get_macro_metrics_data_for_table') as mock_get_data:
            # Return data that would be filtered out by site name
            mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
            
            accordion = create_macro_metrics_accordion("Nonexistent Site")
            
            # Should handle gracefully
            from dash import html
            self.assertIsInstance(accordion, html.Div)

    def test_invalid_season_parameter(self):
        """Test table creation with invalid season parameter."""
        # Test with invalid season
        result = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'InvalidSeason'
        )
        
        # Should handle gracefully
        from dash import dash_table, html
        self.assertTrue(
            isinstance(result, dash_table.DataTable) or 
            isinstance(result, html.Div)
        )


if __name__ == '__main__':
    unittest.main(verbosity=2) 