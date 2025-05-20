import unittest
import os
import pandas as pd
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore", message="*scattermapbox* is deprecated")
from dash import html

# Import your modules
from utils import load_markdown_content, create_image_with_caption, safe_div, format_value
from visualizations.map_viz import create_site_map, determine_status
from visualizations.chemical_viz import get_parameter_label, get_parameter_name
from visualizations.fish_viz import create_fish_viz
from visualizations.macro_viz import create_macro_viz
from visualizations.habitat_viz import create_habitat_viz

class UtilityTests(unittest.TestCase):
    def test_load_markdown_content_valid_file(self):
        """Test loading a valid markdown file."""
        # Assuming overview.md exists
        result = load_markdown_content('overview/overview.md')
        # Check that it returns a dash component
        self.assertIsInstance(result, html.Div)
    
    def test_load_markdown_content_invalid_file(self):
        """Test loading a non-existent markdown file."""
        # Should handle gracefully with fallback message
        result = load_markdown_content('nonexistent_file.md')
        self.assertIsInstance(result, html.Div)
        # Could check for alert class or error message
    
    def test_create_image_with_caption(self):
        """Test creating an image with caption."""
        result = create_image_with_caption(
            src='/assets/images/healthy_stream_diagram.png',
            caption="Test caption"
        )
        self.assertIsInstance(result, html.Div)
        # Could check for figcaption content
    
    def test_safe_div_normal(self):
        """Test safe division with normal values."""
        result = safe_div(10, 2)
        self.assertEqual(result, 5)
    
    def test_safe_div_zero_denominator(self):
        """Test safe division with zero denominator."""
        result = safe_div(10, 0, default=99)
        self.assertEqual(result, 99)
    
    def test_format_value_normal(self):
        """Test value formatting with normal value."""
        result = format_value(12.3456, precision=2, unit="mg/L")
        self.assertEqual(result, "12.35 mg/L")
    
    def test_format_value_none(self):
        """Test value formatting with None."""
        result = format_value(None)
        self.assertEqual(result, "N/A")

class VisualizationTests(unittest.TestCase):
    def test_create_site_map(self):
        """Test creation of the site map."""
        fig = create_site_map()
        self.assertIsInstance(fig, go.Figure)
        # Check that the figure has at least some traces
        self.assertGreater(len(fig.data), 0)
    
    def test_create_site_map_with_parameter(self):
        """Test creation of the site map with a parameter."""
        fig = create_site_map('chem', 'do_percent')
        self.assertIsInstance(fig, go.Figure)
        # Check that colors are applied based on status
        self.assertGreater(len(fig.data), 0)
    
    def test_get_parameter_label(self):
        """Test getting parameter labels."""
        label = get_parameter_label('do_percent')
        self.assertEqual(label, 'DO Saturation (%)')
        
        # Test with unknown parameter
        unknown_label = get_parameter_label('unknown_param')
        self.assertEqual(unknown_label, 'unknown_param')
    
    def test_determine_status(self):
        """Test determination of status based on parameter value."""
        parameter = 'do_percent'
        reference_values = {'do_percent': {'normal min': 80, 'normal max': 130}}
        
        # Test normal value
        status, color = determine_status(parameter, 100, reference_values)
        self.assertEqual(status, 'Normal')
        
        # Test below normal value
        status, color = determine_status(parameter, 60, reference_values)
        self.assertEqual(status, 'Caution')
        
        # Test NaN value
        import numpy as np
        status, color = determine_status(parameter, np.nan, reference_values)
        self.assertEqual(status, 'Unknown')

class ComponentCreationTests(unittest.TestCase):
    def test_create_fish_viz(self):
        """Test creation of fish visualization."""
        fig = create_fish_viz()
        self.assertIsInstance(fig, go.Figure)
    
    def test_create_macro_viz(self):
        """Test creation of macroinvertebrate visualization."""
        fig = create_macro_viz()
        self.assertIsInstance(fig, go.Figure)
    
    def test_create_habitat_viz(self):
        """Test creation of habitat visualization."""
        fig = create_habitat_viz()
        self.assertIsInstance(fig, go.Figure)
    
    def test_chemical_parameter_names(self):
        """Test parameter name mapping."""
        self.assertEqual(get_parameter_name('do_percent'), 'Dissolved Oxygen')
        self.assertEqual(get_parameter_name('pH'), 'pH')
        self.assertEqual(get_parameter_name('soluble_nitrogen'), 'Nitrogen')
        self.assertEqual(get_parameter_name('unknown'), 'unknown')  # Default case

if __name__ == '__main__':
    unittest.main()