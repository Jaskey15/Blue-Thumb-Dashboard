"""
Tests for Survey123 data fetching functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import requests
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'cloud_functions', 'survey123_sync'))

# Mock Cloud Function specific modules before importing
sys.modules['functions_framework'] = MagicMock()
sys.modules['google.cloud'] = MagicMock() 
sys.modules['google.cloud.storage'] = MagicMock()

from main import Survey123DataFetcher, ArcGISAuthenticator


class TestSurvey123DataFetcher(unittest.TestCase):
    """Test Survey123 data fetching logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_authenticator = MagicMock(spec=ArcGISAuthenticator)
        self.mock_authenticator.get_access_token.return_value = "test_token"
        self.form_id = "test_form_123"
        self.fetcher = Survey123DataFetcher(self.mock_authenticator, self.form_id)
        self.since_date = datetime(2023, 1, 1, 12, 0, 0)
    
    @patch('main.requests.get')
    def test_get_submissions_success(self, mock_get):
        """Test successful submission fetching."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'features': [
                {
                    'attributes': {
                        'objectid': 1,
                        'site_name': 'Test Site 1',
                        'collection_date': '2023-01-15',
                        'ph': 7.2,
                        'do_percent': 95.5
                    }
                },
                {
                    'attributes': {
                        'objectid': 2,
                        'site_name': 'Test Site 2',
                        'collection_date': '2023-01-20',
                        'ph': 8.1,
                        'do_percent': 88.0
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result_df = self.fetcher.get_submissions_since(self.since_date)
        
        # Verify DataFrame was created correctly
        self.assertIsInstance(result_df, pd.DataFrame)
        self.assertEqual(len(result_df), 2)
        self.assertIn('site_name', result_df.columns)
        self.assertIn('ph', result_df.columns)
        self.assertEqual(result_df.iloc[0]['site_name'], 'Test Site 1')
        self.assertEqual(result_df.iloc[1]['ph'], 8.1)
        
        # Verify API was called correctly
        expected_since_epoch = int(self.since_date.timestamp() * 1000)
        expected_url = f"https://survey123.arcgis.com/api/featureServices/{self.form_id}/0/query"
        expected_params = {
            'token': 'test_token',
            'where': f"CreationDate > {expected_since_epoch}",
            'outFields': '*',
            'f': 'json',
            'resultRecordCount': 1000
        }
        
        mock_get.assert_called_once_with(expected_url, params=expected_params)
    
    @patch('main.requests.get')
    def test_get_submissions_empty_response(self, mock_get):
        """Test handling of empty API response."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = {'features': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result_df = self.fetcher.get_submissions_since(self.since_date)
        
        # Should return empty DataFrame
        self.assertIsInstance(result_df, pd.DataFrame)
        self.assertTrue(result_df.empty)
    
    @patch('main.requests.get')
    def test_get_submissions_api_error(self, mock_get):
        """Test handling of API error response."""
        # Mock API error response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'error': {
                'code': 400,
                'message': 'Invalid query parameters'
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            self.fetcher.get_submissions_since(self.since_date)
        
        self.assertIn('ArcGIS API error', str(context.exception))
    
    @patch('main.requests.get')
    def test_get_submissions_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response
        
        with self.assertRaises(Exception):
            self.fetcher.get_submissions_since(self.since_date)
    
    @patch('main.requests.get')
    def test_get_submissions_missing_features(self, mock_get):
        """Test handling when features key is missing."""
        # Mock response without features
        mock_response = MagicMock()
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result_df = self.fetcher.get_submissions_since(self.since_date)
        
        # Should return empty DataFrame
        self.assertIsInstance(result_df, pd.DataFrame)
        self.assertTrue(result_df.empty)
    
    @patch('main.requests.get')
    def test_get_submissions_malformed_features(self, mock_get):
        """Test handling of malformed feature data."""
        # Mock response with malformed features
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'features': [
                {'attributes': {'site_name': 'Valid Site'}},
                {'no_attributes': 'Invalid'},  # Missing attributes
                {'attributes': None}  # Null attributes
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result_df = self.fetcher.get_submissions_since(self.since_date)
        
        # Should handle malformed data gracefully
        self.assertIsInstance(result_df, pd.DataFrame)
        # Should have at least one valid record
        self.assertGreaterEqual(len(result_df), 1)
    
    def test_epoch_conversion(self):
        """Test that date is correctly converted to epoch milliseconds."""
        test_date = datetime(2023, 6, 15, 14, 30, 0)
        expected_epoch = int(test_date.timestamp() * 1000)
        
        with patch('main.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {'features': []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            self.fetcher.get_submissions_since(test_date)
            
            # Check that the where clause contains the correct epoch time
            call_params = mock_get.call_args[1]['params']
            self.assertEqual(call_params['where'], f"CreationDate > {expected_epoch}")
    
    @patch('main.requests.get')
    def test_authenticator_called(self, mock_get):
        """Test that authenticator is called to get token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'features': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        self.fetcher.get_submissions_since(self.since_date)
        
        # Verify authenticator was called
        self.mock_authenticator.get_access_token.assert_called_once()


if __name__ == '__main__':
    unittest.main() 