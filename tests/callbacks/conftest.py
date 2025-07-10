"""
Shared fixtures for callback testing.
"""

import os
import sys
from unittest.mock import patch

import dash
import pytest
from dash import html

# Add the project root to the Python path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def mock_app():
    """Create a minimal Dash app for testing callbacks."""
    app = dash.Dash(__name__)
    
    # Create a minimal layout with the required components for shared callbacks
    app.layout = html.Div([
        # Attribution modal components
        html.Div(id='attribution-modal'),
        html.Div(id='attribution-link'),
        html.Div(id='close-attribution'),
        html.Div(id='image-credits-modal'),
        html.Div(id='image-credits-link'),
        html.Div(id='close-image-credits'),
        
        # Navigation components
        html.Div(id='main-tabs'),
        html.Div(id='navigation-store'),
        html.Div(id='site-map-graph'),
        html.Div(id='parameter-dropdown'),
        html.Div(id='chemical-overview-link'),
        html.Div(id='biological-overview-link'),
        html.Div(id='habitat-overview-link'),
    ])
    
    return app

@pytest.fixture
def mock_callback_context():
    """Mock the dash.callback_context for testing."""
    with patch('dash.callback_context') as mock_ctx:
        yield mock_ctx

@pytest.fixture
def sample_click_data():
    """Sample click data that matches the expected format from the map."""
    return {
        'points': [{
            'text': '<b>Site:</b> Test Site<br>Parameter: 8.2 mg/L'
        }]
    }

@pytest.fixture
def sample_malformed_click_data():
    """Sample malformed click data for testing error handling."""
    return {
        'points': [{
            'text': 'Invalid format without site'
        }]
    } 