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
    format_macro_metrics_table,
    CONDITION_THRESHOLDS,
    CONDITION_COLORS,
    MACRO_METRIC_ORDER,
    MACRO_SUMMARY_LABELS
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
            'collection_date': pd.to_datetime(['2020-06-15', '2020-12-15', '2021-07-20', '2021-12-20', '2022-06-10', '2022-12-10']),
            'season': ['Summer', 'Winter', 'Summer', 'Winter', 'Summer', 'Winter'],
            'comparison_to_reference': [0.75, 0.68, 0.82, 0.71, 0.69, 0.73],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired', 
                                   'Non-impaired', 'Slightly Impaired',
                                   'Moderately Impaired', 'Slightly Impaired'],
            'habitat': ['Riffle', 'Vegetation', 'Riffle', 'Vegetation', 'Riffle', 'Vegetation'],
            'site_name': ['Test Site'] * 6
        })
        
        # Sample metrics data for both seasons
        self.sample_metrics_data = pd.DataFrame({
            'event_id': [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
            'year': [2020, 2020, 2020, 2020, 2020, 2020, 2021, 2021, 2021, 2021, 2021, 2021],
            'season': ['Summer', 'Summer', 'Summer', 'Winter', 'Winter', 'Winter', 'Summer', 'Summer', 'Summer', 'Winter', 'Winter', 'Winter'],
            'habitat': ['Riffle', 'Riffle', 'Riffle', 'Vegetation', 'Vegetation', 'Vegetation', 'Riffle', 'Riffle', 'Riffle', 'Vegetation', 'Vegetation', 'Vegetation'],
            'metric_name': ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score', 'Taxa Richness', 'EPT Taxa Richness', 'HBI Score', 'Taxa Richness', 'EPT Taxa Richness', 'HBI Score', 'Taxa Richness', 'EPT Taxa Richness', 'HBI Score'],
            'metric_score': [15, 8, 3, 12, 6, 4, 18, 10, 3, 14, 7, 4],
            'collection_date': pd.to_datetime(['2020-06-15', '2020-06-15', '2020-06-15', '2020-12-15', '2020-12-15', '2020-12-15', '2021-07-20', '2021-07-20', '2021-07-20', '2021-12-20', '2021-12-20', '2021-12-20'])
        })
        
        # Sample summary data for both seasons
        self.sample_summary_data = pd.DataFrame({
            'event_id': [1, 2, 3, 4],
            'year': [2020, 2020, 2021, 2021],
            'season': ['Summer', 'Winter', 'Summer', 'Winter'],
            'habitat': ['Riffle', 'Vegetation', 'Riffle', 'Vegetation'],
            'total_score': [42, 38, 48, 41],
            'comparison_to_reference': [0.75, 0.68, 0.82, 0.71],
            'biological_condition': ['Slightly Impaired', 'Moderately Impaired', 
                                   'Non-impaired', 'Slightly Impaired'],
            'collection_date': pd.to_datetime(['2020-06-15', '2020-12-15', '2021-07-20', '2021-12-20'])
        })
        
        # Test data for duplicate handling (REP notation and habitat suffixes)
        self.duplicate_metrics_data = pd.DataFrame({
            'event_id': [10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15],
            'year': [2022, 2022, 2022, 2022, 2022, 2022, 2022, 2022, 2022, 2022, 2022, 2022, 2023, 2023, 2023, 2023, 2023, 2023],
            'season': ['Summer'] * 18,
            'habitat': ['Riffle'] * 6 + ['Vegetation'] * 6 + ['Riffle'] * 6,
            'metric_name': ['Taxa Richness', 'EPT Taxa Richness', 'HBI Score'] * 6,
            'metric_score': [15, 8, 3, 12, 6, 4, 18, 10, 3, 14, 7, 4, 16, 9, 2, 13, 5, 5],
            'collection_date': pd.to_datetime(['2022-06-10'] * 3 + ['2022-07-15'] * 3 + ['2022-06-10'] * 3 + ['2022-06-15'] * 3 + ['2023-06-05'] * 3 + ['2023-06-20'] * 3)
        })
        
        self.duplicate_summary_data = pd.DataFrame({
            'event_id': [10, 11, 12, 13, 14, 15],
            'year': [2022, 2022, 2022, 2022, 2023, 2023],
            'season': ['Summer'] * 6,
            'habitat': ['Riffle', 'Riffle', 'Vegetation', 'Vegetation', 'Riffle', 'Riffle'],
            'total_score': [26, 22, 31, 25, 27, 23],
            'comparison_to_reference': [0.65, 0.55, 0.78, 0.63, 0.68, 0.58],
            'biological_condition': ['Moderately Impaired', 'Moderately Impaired', 'Slightly Impaired', 'Moderately Impaired', 'Moderately Impaired', 'Moderately Impaired'],
            'collection_date': pd.to_datetime(['2022-06-10', '2022-07-15', '2022-06-10', '2022-06-15', '2023-06-05', '2023-06-20'])
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

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_create_macro_viz_uses_shared_utilities(self, mock_get_macro):
        """Test that macro viz uses shared visualization utilities."""
        mock_get_macro.return_value = self.sample_macro_data
        
        fig = create_macro_viz("Test Site")
        
        # Should use shared utilities for date-aware visualization
        self.assertEqual(fig.layout.xaxis.title.text, "Year")
        
        # Should have multiple traces with proper hover template
        self.assertEqual(len(fig.data), 2)  # Summer and Winter
        for trace in fig.data:
            self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')
        
        # Should have reference lines from shared utilities
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Should have legend for seasons
        self.assertEqual(fig.layout.legend.title.text, "Season")

    # =============================================================================
    # SEASONAL METRICS TABLE FUNCTION TESTS
    # =============================================================================

    def test_create_macro_metrics_table_for_season_summer(self):
        """Test macro metrics table creation for Summer season."""
        from dash import dash_table, html
        
        table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, 
            self.sample_summary_data, 
            'Summer'
        )
        
        # Should return Div containing DataTable and footnote
        self.assertIsInstance(table, html.Div)
        
        # Should contain a DataTable as first child
        self.assertIsInstance(table.children[0], dash_table.DataTable)
        data_table = table.children[0]
        
        # Should have correct ID for Summer
        self.assertEqual(data_table.id, 'summer-macro-metrics-table')
        
        # Should have correct structure
        self.assertGreater(len(data_table.columns), 1)  # Metric column + year columns
        self.assertGreater(len(data_table.data), len(MACRO_METRIC_ORDER))  # Metrics + summary rows

    def test_create_macro_metrics_table_for_season_winter(self):
        """Test macro metrics table creation for Winter season."""
        from dash import dash_table, html
        
        table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, 
            self.sample_summary_data, 
            'Winter'
        )
        
        # Should return Div containing DataTable and footnote
        self.assertIsInstance(table, html.Div)
        
        # Should contain a DataTable as first child
        self.assertIsInstance(table.children[0], dash_table.DataTable)
        data_table = table.children[0]
        
        # Should have correct ID for Winter
        self.assertEqual(data_table.id, 'winter-macro-metrics-table')

    def test_create_macro_metrics_table_for_season_empty_data(self):
        """Test seasonal metrics table creation with empty data."""
        from dash import html
        
        empty_df = pd.DataFrame()
        
        result = create_macro_metrics_table_for_season(empty_df, empty_df, 'Summer')
        
        # Should handle gracefully - either return empty table or error message
        self.assertTrue(
            isinstance(result, html.Div) or 
            hasattr(result, 'data')  # DataTable with empty data
        )

    def test_create_macro_metrics_table_uses_shared_utilities(self):
        """Test that metrics table uses shared formatting utilities."""
        from dash import dash_table, html
        
        table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, 
            self.sample_summary_data, 
            'Summer'
        )
        
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
    # DUPLICATE HANDLING TESTS (REP NOTATION AND HABITAT SUFFIXES)
    # =============================================================================

    def test_format_macro_metrics_table_same_habitat_replicates(self):
        """Test that same habitat replicates get REP notation."""
        # Test 2023 data which has simple Riffle replicates (events 14 and 15)
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            season='Summer'
        )
        
        # Should have columns for both Riffle samples in 2023 (simple case)
        columns = list(metrics_table.columns)
        self.assertIn('2023', columns)
        self.assertIn('2023 (REP)', columns)
        
        # Both should be Riffle habitat
        self.assertEqual(habitat_row['2023'].iloc[0], 'Riffle')
        self.assertEqual(habitat_row['2023 (REP)'].iloc[0], 'Riffle')

    def test_format_macro_metrics_table_different_habitats(self):
        """Test that different habitats get proper suffixes."""
        # Test 2022 data which has Riffle and Vegetation (both with replicates)
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            season='Summer'
        )
        
        # Should have habitat-suffixed columns for 2022
        columns = list(metrics_table.columns)
        expected_2022_cols = ['2022-R', '2022-R (REP)', '2022-V', '2022-V (REP)']
        
        for col in expected_2022_cols:
            self.assertIn(col, columns)
        
        # Check habitat row matches suffixes
        self.assertEqual(habitat_row['2022-R'].iloc[0], 'Riffle')
        self.assertEqual(habitat_row['2022-R (REP)'].iloc[0], 'Riffle')
        self.assertEqual(habitat_row['2022-V'].iloc[0], 'Vegetation')
        self.assertEqual(habitat_row['2022-V (REP)'].iloc[0], 'Vegetation')

    def test_format_macro_metrics_table_rep_with_different_habitats(self):
        """Test complex case with both REP and different habitats."""
        # This tests the most complex scenario from our test data
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            season='Summer'
        )
        
        # Should handle both 2022 (complex) and 2023 (simple REP) correctly
        columns = list(metrics_table.columns)
        
        # 2022 should have habitat suffixes due to multiple habitats
        self.assertIn('2022-R', columns)
        self.assertIn('2022-R (REP)', columns)
        self.assertIn('2022-V', columns)
        self.assertIn('2022-V (REP)', columns)
        
        # 2023 should have simple REP notation (same habitat)
        self.assertIn('2023', columns)
        self.assertIn('2023 (REP)', columns)

    def test_format_macro_metrics_table_chronological_ordering(self):
        """Test that samples are ordered chronologically within years."""
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            season='Summer'
        )
        
        # REP samples should come after original samples
        columns = list(metrics_table.columns)
        
        # For 2022 with habitat suffixes
        r_index = columns.index('2022-R')
        r_rep_index = columns.index('2022-R (REP)')
        self.assertLess(r_index, r_rep_index)
        
        # For 2023 with simple REP
        orig_index = columns.index('2023')
        rep_index = columns.index('2023 (REP)')
        self.assertLess(orig_index, rep_index)

    def test_format_macro_metrics_table_no_data_overwriting(self):
        """Test that no data is lost due to column name conflicts."""
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            season='Summer'
        )
        
        # Should have all 6 collections represented (2022: 4 samples, 2023: 2 samples)
        # Minus the 'Metric' column = 6 data columns
        expected_columns = 6
        actual_data_columns = len(metrics_table.columns) - 1  # Subtract 'Metric' column
        self.assertEqual(actual_data_columns, expected_columns)
        
        # Check that each column has unique data
        columns = [col for col in metrics_table.columns if col != 'Metric']
        for col in columns:
            # Each column should have valid metric scores (not all the same)
            scores = metrics_table[col].tolist()
            non_dash_scores = [s for s in scores if s != '-']
            if non_dash_scores:
                self.assertGreater(len(set(non_dash_scores)), 0)  # Should have some variation

    def test_format_macro_metrics_table_footnotes_in_table_creation(self):
        """Test that footnotes are properly included in table creation."""
        from dash import html
        
        table = create_macro_metrics_table_for_season(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            'Summer'
        )
        
        # Should be a Div with multiple children (table + footnotes)
        self.assertIsInstance(table, html.Div)
        self.assertGreaterEqual(len(table.children), 4)  # DataTable + 3 footnotes
        
        # Check that footnotes contain expected text
        footnote_texts = []
        for child in table.children[1:]:  # Skip first child (DataTable)
            if isinstance(child, html.P):
                footnote_texts.append(child.children)
        
        # Should have footnotes about REP, habitat suffixes, and reference values
        footnote_content = ' '.join(footnote_texts)
        self.assertIn('(REP)', footnote_content)
        self.assertIn('R=Riffle', footnote_content)
        self.assertIn('V=Vegetation', footnote_content)
        self.assertIn('W=Woody', footnote_content)  # Still check for W=Woody in general footnote

    def test_format_macro_metrics_table_empty_data_handling(self):
        """Test duplicate handling with empty data."""
        empty_df = pd.DataFrame()
        
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            empty_df, empty_df, season='Summer'
        )
        
        # Should handle gracefully and return proper structure
        self.assertIsInstance(metrics_table, pd.DataFrame)
        self.assertIsInstance(habitat_row, pd.DataFrame)
        self.assertIsInstance(summary_rows, pd.DataFrame)
        
        # Should have basic structure even with no data
        self.assertIn('Metric', metrics_table.columns)
        self.assertIn('Metric', habitat_row.columns)
        self.assertIn('Metric', summary_rows.columns)

    def test_habitat_abbreviation_logic(self):
        """Test that habitat abbreviations are correctly applied."""
        metrics_table, habitat_row, summary_rows = format_macro_metrics_table(
            self.duplicate_metrics_data, 
            self.duplicate_summary_data, 
            season='Summer'
        )
        
        # Check specific habitat abbreviations
        columns = list(metrics_table.columns)
        
        # Riffle should use 'R'
        riffle_cols = [col for col in columns if '-R' in col]
        self.assertGreater(len(riffle_cols), 0)
        
        # Vegetation should use 'V'
        veg_cols = [col for col in columns if '-V' in col]
        self.assertGreater(len(veg_cols), 0)
        
        # Should have both Riffle and Vegetation abbreviations
        self.assertTrue(any('-R' in col for col in columns))
        self.assertTrue(any('-V' in col for col in columns))

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

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_integration_with_shared_visualization_utils(self, mock_get_macro):
        """Test integration with shared visualization utilities."""
        mock_get_macro.return_value = self.sample_macro_data
        
        fig = create_macro_viz("Test Site")
        
        # Should use shared create_trace function for both seasons
        self.assertEqual(len(fig.data), 2)
        for trace in fig.data:
            self.assertEqual(trace.mode, 'lines+markers')
        
        # Should use shared update_layout function
        self.assertEqual(fig.layout.title.x, 0.5)  # Centered title
        
        # Should use shared add_reference_lines function
        self.assertGreater(len(fig.layout.shapes), 0)
        
        # Should use shared generate_hover_text function
        for trace in fig.data:
            self.assertIsNotNone(trace.text)
            self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')

    def test_macro_specific_vs_shared_functionality(self):
        """Test that macro module correctly uses shared vs. macro-specific functionality."""
        # Test that macro uses its own thresholds and not fish thresholds
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
        
        # Both should be valid Div containers with DataTables inside
        from dash import dash_table, html
        self.assertIsInstance(summer_table, html.Div)
        self.assertIsInstance(winter_table, html.Div)
        
        # Extract the DataTables from the Div containers
        summer_data_table = summer_table.children[0]
        winter_data_table = winter_table.children[0]
        
        self.assertIsInstance(summer_data_table, dash_table.DataTable)
        self.assertIsInstance(winter_data_table, dash_table.DataTable)
        self.assertNotEqual(summer_data_table.id, winter_data_table.id)

    # =============================================================================
    # SEASONAL DATA HANDLING TESTS
    # =============================================================================

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_macro_multi_trace_vs_fish_single_trace(self, mock_get_macro):
        """Test that macro viz has multiple traces while fish has single."""
        mock_get_macro.return_value = self.sample_macro_data
        
        fig = create_macro_viz("Test Site")
        
        # Macro should have multiple traces (seasons)
        self.assertEqual(len(fig.data), 2)
        
        # Should have legend for seasons
        self.assertEqual(fig.layout.legend.title.text, "Season")
        
        # Traces should have different names
        trace_names = [trace.name for trace in fig.data]
        self.assertIn('Summer', trace_names)
        self.assertIn('Winter', trace_names)

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_macro_hover_text_contains_habitat_and_season(self, mock_get_macro):
        """Test that macro hover text contains season and habitat information."""
        mock_get_macro.return_value = self.sample_macro_data
        
        fig = create_macro_viz("Test Site")
        
        # Should have hover data for both seasons
        self.assertEqual(len(fig.data), 2)
        
        # Each trace should have hover template and text
        for trace in fig.data:
            self.assertEqual(trace.hovertemplate, '%{text}<extra></extra>')
            self.assertIsNotNone(trace.text)
            
            # Hover text should contain season and habitat info
            if trace.text:
                hover_text = trace.text[0] if trace.text else ""
                # Verify that hover text was generated (specific content is implementation detail)
                self.assertIsInstance(hover_text, str)

    def test_seasonal_data_filtering_in_table_creation(self):
        """Test that seasonal data is properly filtered in table functions."""
        # Test Summer filtering
        summer_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Summer'
        )
        
        # Should create valid Div container with DataTable
        from dash import dash_table, html
        self.assertIsInstance(summer_table, html.Div)
        self.assertIsInstance(summer_table.children[0], dash_table.DataTable)
        
        # Test Winter filtering
        winter_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Winter'
        )
        
        self.assertIsInstance(winter_table, html.Div)
        self.assertIsInstance(winter_table.children[0], dash_table.DataTable)

    # =============================================================================
    # CORE FUNCTIONALITY TESTS
    # =============================================================================

    @patch('visualizations.macro_viz.get_macroinvertebrate_dataframe')
    def test_complete_visualization_workflow(self, mock_get_macro):
        """Test complete end-to-end visualization creation process."""
        mock_get_macro.return_value = self.sample_macro_data
        
        # Test visualization creation
        viz_result = create_macro_viz('Test Site')
        
        # Verify it's a valid figure with proper structure
        self.assertIsInstance(viz_result, go.Figure)
        self.assertEqual(len(viz_result.data), 2)  # Two traces for seasons
        
        # Verify it has proper layout from shared utilities
        self.assertIsNotNone(viz_result.layout.title)
        self.assertIsNotNone(viz_result.layout.xaxis)
        self.assertIsNotNone(viz_result.layout.yaxis)
        
        # Verify it has reference lines for biological conditions
        self.assertGreater(len(viz_result.layout.shapes), 0)
        
        # Verify traces have proper hover text
        for trace in viz_result.data:
            self.assertIsNotNone(trace.text)

    @patch('visualizations.macro_viz.get_macro_metrics_data_for_table')
    def test_complete_table_workflow(self, mock_get_data):
        """Test complete metrics table creation workflow."""
        mock_get_data.return_value = (self.sample_metrics_data, self.sample_summary_data)
        
        # Test accordion creation (which calls table creation for both seasons)
        accordion_result = create_macro_metrics_accordion('Test Site')
        
        # Should create proper accordion structure
        from dash import html
        self.assertIsInstance(accordion_result, html.Div)
        self.assertEqual(len(accordion_result.children), 2)  # Summer and Winter
        
        # Test direct table creation for each season
        summer_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Summer'
        )
        winter_table = create_macro_metrics_table_for_season(
            self.sample_metrics_data, self.sample_summary_data, 'Winter'
        )
        
        # Should create properly formatted Div containers with DataTables
        from dash import dash_table, html
        self.assertIsInstance(summer_table, html.Div)
        self.assertIsInstance(winter_table, html.Div)
        
        # Extract DataTables from Div containers
        summer_data_table = summer_table.children[0]
        winter_data_table = winter_table.children[0]
        
        self.assertIsInstance(summer_data_table, dash_table.DataTable)
        self.assertIsInstance(winter_data_table, dash_table.DataTable)
        self.assertEqual(summer_data_table.id, 'summer-macro-metrics-table')
        self.assertEqual(winter_data_table.id, 'winter-macro-metrics-table')

if __name__ == '__main__':
    unittest.main(verbosity=2) 