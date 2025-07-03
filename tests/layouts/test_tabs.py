"""
Tests for layouts.tabs module

This file tests the tab layout creation functions including:
- Tab layout generation
- Component hierarchy validation
- Tab-specific functionality
- Content organization
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from dash import html, dcc
import dash_bootstrap_components as dbc

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from layouts.tabs import (
    create_overview_tab,
    create_chemical_tab,
    create_biological_tab,
    create_habitat_tab,
    create_protect_our_streams_tab,
    create_source_data_tab
)


class TestOverviewTab(unittest.TestCase):
    """Test overview tab layout creation."""
    
    @patch('layouts.tabs.overview.load_markdown_content')
    def test_create_overview_tab(self, mock_markdown):
        """Test overview tab creation."""
        # Mock markdown loading
        mock_markdown.return_value = html.Div("Mock markdown content")
        
        tab = create_overview_tab()
        
        # Check it's a Div component
        self.assertIsInstance(tab, html.Div)
        
        # Check has correct class
        self.assertIn("tab-content-wrapper", tab.className)
        
        # Check structure (should have multiple rows)
        children = tab.children
        self.assertGreater(len(children), 3)  # At least 4 rows expected
        
        # All children should be Row components
        for child in children:
            self.assertIsInstance(child, dbc.Row)
    
    @patch('layouts.tabs.overview.load_markdown_content')
    def test_overview_tab_parameter_dropdown(self, mock_markdown):
        """Test overview tab parameter dropdown component."""
        mock_markdown.return_value = html.Div("Mock content")
        
        tab = create_overview_tab()
        
        # Find the parameter dropdown in the structure
        dropdown = None
        for row in tab.children:
            for col in row.children:
                for child in col.children:
                    if isinstance(child, dcc.Dropdown) and hasattr(child, 'id') and child.id == 'parameter-dropdown':
                        dropdown = child
                        break
        
        self.assertIsNotNone(dropdown)
        self.assertEqual(dropdown.id, 'parameter-dropdown')
        self.assertTrue(dropdown.disabled)  # Should start disabled
        self.assertIsNone(dropdown.value)  # Should start with no value
    
    @patch('layouts.tabs.overview.load_markdown_content')
    def test_overview_tab_map_container(self, mock_markdown):
        """Test overview tab map container."""
        mock_markdown.return_value = html.Div("Mock content")
        
        tab = create_overview_tab()
        
        # Find the map graph
        map_graph = None
        for row in tab.children:
            for col in row.children:
                for child in col.children:
                    if isinstance(child, dcc.Graph) and hasattr(child, 'id') and child.id == 'site-map-graph':
                        map_graph = child
                        break
        
        self.assertIsNotNone(map_graph)
        self.assertEqual(map_graph.id, 'site-map-graph')
        
        # Check map configuration
        config = map_graph.config
        self.assertTrue(config['scrollZoom'])
        self.assertTrue(config['displayModeBar'])


class TestChemicalTab(unittest.TestCase):
    """Test chemical tab layout creation."""
    
    @patch('layouts.tabs.chemical.get_chemical_date_range')
    def test_create_chemical_tab(self, mock_date_range):
        """Test chemical tab creation."""
        # Mock date range function
        mock_date_range.return_value = (2020, 2024)
        tab = create_chemical_tab()
        
        # Check it's a Div component
        self.assertIsInstance(tab, html.Div)
        
        # Check has correct class
        self.assertIn("tab-content-wrapper", tab.className)
        
        # Check structure
        children = tab.children
        self.assertGreater(len(children), 2)  # Download, description, site selection, controls
    
    @patch('layouts.tabs.chemical.get_chemical_date_range')
    def test_chemical_tab_site_dropdown(self, mock_date_range):
        """Test chemical tab site dropdown component."""
        mock_date_range.return_value = (2020, 2024)
        tab = create_chemical_tab()
        
        # Find the site dropdown
        site_dropdown = None
        for child in tab.children:
            if isinstance(child, html.Div):
                for sub_child in child.children:
                    if isinstance(sub_child, dcc.Dropdown) and hasattr(sub_child, 'id') and sub_child.id == 'chemical-site-dropdown':
                        site_dropdown = sub_child
                        break
        
        self.assertIsNotNone(site_dropdown)
        self.assertEqual(site_dropdown.id, 'chemical-site-dropdown')
        self.assertTrue(site_dropdown.searchable)
        self.assertTrue(site_dropdown.clearable)
        self.assertEqual(site_dropdown.placeholder, "Search for a site...")
    
    @patch('layouts.tabs.chemical.get_chemical_date_range')
    def test_chemical_tab_parameter_dropdown(self, mock_date_range):
        """Test chemical tab parameter dropdown component."""
        mock_date_range.return_value = (2020, 2024)
        tab = create_chemical_tab()
        
        # Find the parameter dropdown in controls section
        param_dropdown = None
        controls_div = None
        
        # Find controls content div
        for child in tab.children:
            if isinstance(child, html.Div) and hasattr(child, 'id') and child.id == 'chemical-controls-content':
                controls_div = child
                break
        
        self.assertIsNotNone(controls_div)
        
        # Find parameter dropdown within controls
        for row in controls_div.children:
            if isinstance(row, dbc.Row):
                for col in row.children:
                    for item in col.children:
                        if isinstance(item, dcc.Dropdown) and hasattr(item, 'id') and item.id == 'chemical-parameter-dropdown':
                            param_dropdown = item
                            break
        
        self.assertIsNotNone(param_dropdown)
        
        # Check parameter options
        expected_values = ['do_percent', 'pH', 'soluble_nitrogen', 'Phosphorus', 'Chloride', 'all_parameters']
        actual_values = [opt['value'] for opt in param_dropdown.options]
        self.assertEqual(actual_values, expected_values)


class TestBiologicalTab(unittest.TestCase):
    """Test biological tab layout creation."""
    
    def test_create_biological_tab(self):
        """Test biological tab creation."""
        tab = create_biological_tab()
        
        # Check it's a Div component
        self.assertIsInstance(tab, html.Div)
        
        # Check has correct class
        self.assertIn("tab-content-wrapper", tab.className)
        
        # Check basic structure
        children = tab.children
        self.assertGreater(len(children), 3)  # Download, description, community selection, site selection, content
    
    def test_biological_tab_community_selector(self):
        """Test biological tab community selector."""
        tab = create_biological_tab()
        
        # Find community dropdown
        community_dropdown = None
        for child in tab.children:
            if isinstance(child, html.Div) and hasattr(child, 'children') and child.children is not None:
                for sub_child in child.children:
                    if isinstance(sub_child, dcc.Dropdown) and hasattr(sub_child, 'id') and sub_child.id == 'biological-community-dropdown':
                        community_dropdown = sub_child
                        break
        
        self.assertIsNotNone(community_dropdown)
        self.assertEqual(community_dropdown.id, 'biological-community-dropdown')
        
        # Check community options
        expected_values = ['fish', 'macro']
        actual_values = [opt['value'] for opt in community_dropdown.options]
        self.assertEqual(actual_values, expected_values)
        
        # Check default state
        self.assertEqual(community_dropdown.value, '')
    
    def test_biological_tab_site_selector(self):
        """Test biological tab site selector."""
        tab = create_biological_tab()
        
        # Find site dropdown
        site_dropdown = None
        for child in tab.children:
            if isinstance(child, html.Div) and hasattr(child, 'id') and child.id == 'biological-site-search-section':
                for sub_child in child.children:
                    if isinstance(sub_child, dcc.Dropdown) and hasattr(sub_child, 'id') and sub_child.id == 'biological-site-dropdown':
                        site_dropdown = sub_child
                        break
        
        self.assertIsNotNone(site_dropdown)
        self.assertEqual(site_dropdown.id, 'biological-site-dropdown')
        self.assertTrue(site_dropdown.searchable)
        self.assertTrue(site_dropdown.clearable)
        self.assertTrue(site_dropdown.disabled)  # Should start disabled


class TestHabitatTab(unittest.TestCase):
    """Test habitat tab layout creation."""
    
    @patch('layouts.tabs.habitat.load_markdown_content')
    @patch('layouts.tabs.habitat.create_image_with_caption')
    def test_create_habitat_tab(self, mock_image, mock_markdown):
        """Test habitat tab creation."""
        # Mock dependencies
        mock_markdown.return_value = html.Div("Mock markdown")
        mock_image.return_value = html.Img()
        
        tab = create_habitat_tab()
        
        # Check it's a Div component
        self.assertIsInstance(tab, html.Div)
        
        # Check has correct class
        self.assertIn("tab-content-wrapper", tab.className)
        
        # Check structure
        children = tab.children
        self.assertGreater(len(children), 2)  # Download, description, site selection, content
    
    @patch('layouts.tabs.habitat.load_markdown_content')
    @patch('layouts.tabs.habitat.create_image_with_caption')
    def test_habitat_tab_site_dropdown(self, mock_image, mock_markdown):
        """Test habitat tab site dropdown."""
        mock_markdown.return_value = html.Div("Mock markdown")
        mock_image.return_value = html.Img()
        
        tab = create_habitat_tab()
        
        # Find site dropdown
        site_dropdown = None
        for child in tab.children:
            if isinstance(child, html.Div):
                for sub_child in child.children:
                    if isinstance(sub_child, dcc.Dropdown) and hasattr(sub_child, 'id') and sub_child.id == 'habitat-site-dropdown':
                        site_dropdown = sub_child
                        break
        
        self.assertIsNotNone(site_dropdown)
        self.assertEqual(site_dropdown.id, 'habitat-site-dropdown')
        self.assertTrue(site_dropdown.searchable)
        self.assertTrue(site_dropdown.clearable)
        self.assertEqual(site_dropdown.placeholder, "Search for a site...")
    
    @patch('layouts.tabs.habitat.load_markdown_content')
    @patch('layouts.tabs.habitat.create_image_with_caption')
    def test_habitat_tab_content_container(self, mock_image, mock_markdown):
        """Test habitat tab content container."""
        mock_markdown.return_value = html.Div("Mock markdown")
        mock_image.return_value = html.Img()
        
        tab = create_habitat_tab()
        
        # Find controls content container
        controls_div = None
        for child in tab.children:
            if isinstance(child, html.Div) and hasattr(child, 'id') and child.id == 'habitat-controls-content':
                controls_div = child
                break
        
        self.assertIsNotNone(controls_div)
        
        # Should be initially hidden
        self.assertEqual(controls_div.style['display'], 'none')


class TestProtectStreamsTab(unittest.TestCase):
    """Test protect streams tab layout creation."""
    
    @patch('layouts.tabs.protect_streams.load_markdown_content')
    @patch('layouts.tabs.protect_streams.create_image_with_caption')
    def test_create_protect_streams_tab(self, mock_image, mock_markdown):
        """Test protect streams tab creation."""
        # Mock dependencies
        mock_markdown.return_value = html.Div("Mock markdown content")
        mock_image.return_value = html.Img()
        
        tab = create_protect_our_streams_tab()
        
        # Check it's a Div component
        self.assertIsInstance(tab, html.Div)
        
        # Check has correct class
        self.assertIn("tab-content-wrapper", tab.className)
        
        # Check structure - should have rows
        children = tab.children
        self.assertGreater(len(children), 1)  # At least intro row and actions row
        
        # Check all children are rows
        for child in children:
            self.assertIsInstance(child, dbc.Row)
    
    @patch('layouts.tabs.protect_streams.load_markdown_content')
    @patch('layouts.tabs.protect_streams.create_image_with_caption')
    def test_protect_streams_tab_tabs_structure(self, mock_image, mock_markdown):
        """Test protect streams tab has proper tabs structure."""
        mock_markdown.return_value = html.Div("Mock markdown content")
        mock_image.return_value = html.Img()
        
        tab = create_protect_our_streams_tab()
        
        # Find the tabs component
        tabs_component = None
        for row in tab.children:
            for col in row.children:
                for child in col.children:
                    if isinstance(child, dbc.Tabs):
                        tabs_component = child
                        break
        
        self.assertIsNotNone(tabs_component)
        
        # Should have 4 tabs (Home & Yard, Rural & Agricultural, Recreation, Community Action)
        self.assertEqual(len(tabs_component.children), 4)
        
        # Check tab labels
        expected_labels = ["Home & Yard", "Rural & Agricultural", "Recreation", "Community Action"]
        actual_labels = [tab_child.label for tab_child in tabs_component.children]
        self.assertEqual(actual_labels, expected_labels)


class TestSourceDataTab(unittest.TestCase):
    """Test source data tab layout creation."""
    
    def test_create_source_data_tab(self):
        """Test source data tab creation."""
        tab = create_source_data_tab()
        
        # Check it's a Div component
        self.assertIsInstance(tab, html.Div)
        
        # Check has correct class
        self.assertIn("tab-content-wrapper", tab.className)
        
        # Check structure
        children = tab.children
        self.assertGreater(len(children), 1)  # Title row and cards row
        
        # Check all children are rows
        for child in children:
            self.assertIsInstance(child, dbc.Row)
    
    def test_source_data_tab_cards(self):
        """Test source data tab has proper card structure."""
        tab = create_source_data_tab()
        
        # Find the cards row (should be second row)
        cards_row = None
        if len(tab.children) > 1:
            cards_row = tab.children[1]
        
        self.assertIsNotNone(cards_row)
        self.assertIsInstance(cards_row, dbc.Row)
        
        # Should have multiple card columns
        self.assertGreater(len(cards_row.children), 1)
        
        # Each column should contain a card
        for col in cards_row.children:
            self.assertIsInstance(col, dbc.Col)
            # Column should contain a card
            card = col.children[0]
            self.assertIsInstance(card, dbc.Card)
            
            # Card should have header and body
            self.assertEqual(len(card.children), 2)
            self.assertIsInstance(card.children[0], dbc.CardHeader)
            self.assertIsInstance(card.children[1], dbc.CardBody)


class TestTabIntegration(unittest.TestCase):
    """Test tab integration and consistency."""
    
    @patch('layouts.tabs.overview.load_markdown_content')
    @patch('layouts.tabs.chemical.get_chemical_date_range')
    @patch('layouts.tabs.habitat.load_markdown_content')
    @patch('layouts.tabs.habitat.create_image_with_caption')
    @patch('layouts.tabs.protect_streams.load_markdown_content')
    @patch('layouts.tabs.protect_streams.create_image_with_caption')
    def test_all_tabs_return_valid_components(self, mock_protect_image, mock_protect_markdown, 
                                               mock_habitat_image, mock_habitat_markdown, 
                                               mock_chemical_date_range, mock_overview_markdown):
        """Test that all tab creation functions return valid Dash components."""
        # Mock all dependencies
        mock_overview_markdown.return_value = html.Div("Mock content")
        mock_habitat_markdown.return_value = html.Div("Mock content")
        mock_protect_markdown.return_value = html.Div("Mock content")
        mock_habitat_image.return_value = html.Img()
        mock_protect_image.return_value = html.Img()
        mock_chemical_date_range.return_value = (2020, 2024)
        
        # Test all tab creation functions
        overview_tab = create_overview_tab()
        chemical_tab = create_chemical_tab()
        biological_tab = create_biological_tab()
        habitat_tab = create_habitat_tab()
        protect_tab = create_protect_our_streams_tab()
        source_tab = create_source_data_tab()
        
        # All should return Div components
        tabs = [overview_tab, chemical_tab, biological_tab, habitat_tab, protect_tab, source_tab]
        for tab in tabs:
            self.assertIsInstance(tab, html.Div)
    
    def test_tab_styling_consistency(self):
        """Test consistent styling across tabs."""
        # Test tabs that don't require mocking
        biological_tab = create_biological_tab()
        source_tab = create_source_data_tab()
        
        # Both should have tab-content-wrapper class
        self.assertIn("tab-content-wrapper", biological_tab.className)
        self.assertIn("tab-content-wrapper", source_tab.className)
    
    @patch('layouts.tabs.chemical.get_chemical_date_range')
    def test_tab_download_components_consistency(self, mock_date_range):
        """Test that tabs consistently include download components."""
        mock_date_range.return_value = (2020, 2024)
        chemical_tab = create_chemical_tab()
        
        biological_tab = create_biological_tab()
        
        # Find download components
        chemical_download = None
        biological_download = None
        
        for child in chemical_tab.children:
            if isinstance(child, dcc.Download) and child.id == 'chemical-download-component':
                chemical_download = child
                break
        
        for child in biological_tab.children:
            if isinstance(child, dcc.Download) and child.id == 'biological-download-component':
                biological_download = child
                break
        
        # Both should have download components
        self.assertIsNotNone(chemical_download)
        self.assertIsNotNone(biological_download)


if __name__ == '__main__':
    unittest.main(verbosity=2) 