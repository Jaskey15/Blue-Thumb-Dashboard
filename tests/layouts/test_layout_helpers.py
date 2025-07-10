"""
Tests for layouts.helpers module

This file tests the layout helper functions including:
- UI component generation
- Layout structure validation
- Helper function logic
- Component styling and configuration

TODO: Implement the following test classes:
- TestUIComponentGeneration
- TestLayoutStructure
- TestHelperFunctions
- TestComponentStyling
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

from layouts.helpers import (
    create_species_gallery,
    create_action_card,
    create_dropdown_row,
    create_season_month_selectors
)


class TestUIComponentGeneration(unittest.TestCase):
    """Test UI component generation functions."""
    
    def test_create_species_gallery_fish(self):
        """Test species gallery creation for fish."""
        gallery = create_species_gallery('fish')
        
        # Check it's a Div component
        self.assertIsInstance(gallery, html.Div)
        
        # Check children structure
        children = gallery.children
        self.assertEqual(len(children), 4)  # title, container, buttons row, store
        
        # Check title
        title = children[0]
        self.assertIsInstance(title, html.H5)
        self.assertEqual(title.children, "Common Fish Found in Oklahoma Streams")
        
        # Check container has correct ID
        container = children[1]
        self.assertEqual(container.id, "fish-gallery-container")
        
        # Check navigation buttons exist
        buttons_row = children[2]
        self.assertIsInstance(buttons_row, dbc.Row)
        
        # Check store component
        store = children[3]
        self.assertIsInstance(store, dcc.Store)
        self.assertEqual(store.id, "current-fish-index")
    
    def test_create_species_gallery_macro(self):
        """Test species gallery creation for macroinvertebrates."""
        gallery = create_species_gallery('macro')
        
        # Check title for macro
        title = gallery.children[0]
        self.assertEqual(title.children, "Common Macroinvertebrates Found in Oklahoma Streams")
        
        # Check IDs are correct for macro
        container = gallery.children[1]
        self.assertEqual(container.id, "macro-gallery-container")
        
        store = gallery.children[3]
        self.assertEqual(store.id, "current-macro-index")
    
    def test_create_action_card_complete(self):
        """Test action card creation with all parameters."""
        icon = "test-icon"
        title = "TEST ACTION"
        why_text = "This is why it matters"
        tips_list = ["Tip 1", "Tip 2", "Tip 3"]
        category = "test-category"
        
        card = create_action_card(icon, title, why_text, tips_list, category)
        
        # Check it's a Card component
        self.assertIsInstance(card, dbc.Card)
        
        # Check card has correct class names
        self.assertIn("action-card", card.className)
        self.assertIn("test-category", card.className)
        
        # Check structure - header and body
        self.assertEqual(len(card.children), 2)
        
        # Check header structure
        header = card.children[0]
        self.assertIsInstance(header, dbc.CardHeader)
        
        # Check body structure
        body = card.children[1]
        self.assertIsInstance(body, dbc.CardBody)
    
    def test_create_action_card_without_category(self):
        """Test action card creation without category."""
        card = create_action_card("icon", "title", "why", ["tip"])
        
        # Should not have empty category in class
        self.assertNotIn("None", card.className)
        self.assertIn("action-card", card.className)


class TestLayoutStructure(unittest.TestCase):
    """Test layout structure validation."""
    
    def test_dropdown_row_structure(self):
        """Test dropdown row component hierarchy."""
        options = [{'label': 'Option 1', 'value': 'opt1'}]
        row = create_dropdown_row("test-id", "Test Label", options)
        
        # Check it's a Row component
        self.assertIsInstance(row, dbc.Row)
        
        # Check has mb-2 class
        self.assertIn("mb-2", row.className)
        
        # Check column structure
        self.assertEqual(len(row.children), 1)
        col = row.children[0]
        self.assertIsInstance(col, dbc.Col)
        self.assertEqual(col.width, 12)
        
        # Check column children (label and dropdown)
        self.assertEqual(len(col.children), 2)
        label = col.children[0]
        dropdown = col.children[1]
        
        self.assertIsInstance(label, html.Label)
        self.assertIsInstance(dropdown, dcc.Dropdown)
    
    def test_season_month_selectors_structure(self):
        """Test season/month selector component hierarchy."""
        selectors = create_season_month_selectors()
        
        # Check it's a Row component
        self.assertIsInstance(selectors, dbc.Row)
        
        # Check has correct class
        self.assertIn("mb-3", selectors.className)
        
        # Check has two columns
        self.assertEqual(len(selectors.children), 2)
        
        # Check first column (season)
        season_col = selectors.children[0]
        self.assertIsInstance(season_col, dbc.Col)
        self.assertEqual(season_col.width, 5)
        
        # Check second column (months)
        month_col = selectors.children[1]
        self.assertIsInstance(month_col, dbc.Col)
        self.assertEqual(month_col.width, 7)


class TestHelperFunctions(unittest.TestCase):
    """Test layout helper functions."""
    
    def test_dropdown_row_with_defaults(self):
        """Test dropdown row with default parameters."""
        options = [{'label': 'Test', 'value': 'test'}]
        row = create_dropdown_row("test-id", "Test Label", options)
        
        dropdown = row.children[0].children[1]
        
        # Check default values
        self.assertEqual(dropdown.id, "test-id")
        self.assertEqual(dropdown.options, options)
        self.assertIsNone(dropdown.value)
        self.assertFalse(dropdown.clearable)
        self.assertEqual(dropdown.placeholder, "Select an option...")
    
    def test_dropdown_row_with_custom_values(self):
        """Test dropdown row with custom parameters."""
        options = [{'label': 'Test', 'value': 'test'}]
        row = create_dropdown_row(
            "custom-id", 
            "Custom Label", 
            options,
            default_value="test",
            clearable=True,
            placeholder="Custom placeholder"
        )
        
        dropdown = row.children[0].children[1]
        
        # Check custom values
        self.assertEqual(dropdown.id, "custom-id")
        self.assertEqual(dropdown.value, "test")
        self.assertTrue(dropdown.clearable)
        self.assertEqual(dropdown.placeholder, "Custom placeholder")
    
    def test_season_month_selectors_defaults(self):
        """Test season/month selectors have correct defaults."""
        selectors = create_season_month_selectors()
        
        # Get month checklist from second column
        month_col = selectors.children[1]
        checklist = None
        for child in month_col.children:
            if isinstance(child, dcc.Checklist):
                checklist = child
                break
        
        self.assertIsNotNone(checklist)
        
        # Check default months (all selected)
        self.assertEqual(checklist.value, list(range(1, 13)))
        
        # Check inline display
        self.assertTrue(checklist.inline)
        
        # Check 12 month options
        self.assertEqual(len(checklist.options), 12)


class TestComponentStyling(unittest.TestCase):
    """Test component styling and configuration."""
    
    def test_species_gallery_styling(self):
        """Test species gallery component styling."""
        gallery = create_species_gallery('fish')
        
        # Check title styling
        title = gallery.children[0]
        self.assertIn("text-center", title.className)
        self.assertIn("mt-4", title.className)
        
        # Check container styling
        container = gallery.children[1]
        self.assertIn("text-center", container.className)
        self.assertEqual(container.style['min-height'], '400px')
        
        # Check navigation row styling
        nav_row = gallery.children[2]
        self.assertIn("mt-3", nav_row.className)
    
    def test_action_card_styling(self):
        """Test action card component styling."""
        card = create_action_card("icon", "title", "why", ["tip"], "custom-category")
        
        # Check card classes
        expected_classes = ["action-card", "mb-4", "h-100", "custom-category"]
        for cls in expected_classes:
            self.assertIn(cls, card.className)
    
    def test_dropdown_row_label_styling(self):
        """Test dropdown row label styling."""
        row = create_dropdown_row("id", "Label", [])
        
        label = row.children[0].children[0]
        self.assertEqual(label.style["margin-bottom"], "5px")
        
        dropdown = row.children[0].children[1]
        self.assertEqual(dropdown.style["width"], "100%")


class TestAccessibility(unittest.TestCase):
    """Test accessibility features in layouts."""
    
    def test_species_gallery_navigation_accessibility(self):
        """Test species gallery navigation has proper button structure."""
        gallery = create_species_gallery('fish')
        
        # Get navigation row
        nav_row = gallery.children[2]
        
        # Check button structure
        prev_col = nav_row.children[0]
        next_col = nav_row.children[1]
        
        # Buttons should be properly structured for accessibility
        self.assertIsInstance(prev_col, dbc.Col)
        self.assertIsInstance(next_col, dbc.Col)
        
        # Check column widths for proper layout
        self.assertEqual(prev_col.width["size"], 2)
        self.assertEqual(prev_col.width["offset"], 4)
        self.assertEqual(next_col.width, 2)
    
    def test_dropdown_labels_for_accessibility(self):
        """Test dropdown labels are properly associated."""
        row = create_dropdown_row("test-dropdown", "Test Label", [])
        
        label = row.children[0].children[0]
        dropdown = row.children[0].children[1]
        
        # Label should contain text
        self.assertEqual(label.children, "Test Label")
        
        # Dropdown should have proper ID for association
        self.assertEqual(dropdown.id, "test-dropdown")
    
    def test_action_card_structure_accessibility(self):
        """Test action card has proper heading structure."""
        card = create_action_card("icon", "MAIN TITLE", "explanation", ["tip1", "tip2"])
        
        # Should have header and body
        header = card.children[0]
        body = card.children[1]
        
        self.assertIsInstance(header, dbc.CardHeader)
        self.assertIsInstance(body, dbc.CardBody)
        
        # Header should contain proper heading element
        header_content = header.children[0]
        title_element = header_content.children[1]
        self.assertIsInstance(title_element, html.H5)


if __name__ == '__main__':
    unittest.main(verbosity=2) 