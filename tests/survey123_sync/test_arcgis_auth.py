"""
Tests for ArcGIS authentication functionality.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import requests

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'cloud_functions', 'survey123_sync'))

# Mock Cloud Function specific modules before importing
sys.modules['functions_framework'] = MagicMock()
sys.modules['google.cloud'] = MagicMock() 
sys.modules['google.cloud.storage'] = MagicMock()

from main import ArcGISAuthenticator


class TestArcGISAuthenticator(unittest.TestCase):
    """Test ArcGIS authentication logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.authenticator = ArcGISAuthenticator(self.client_id, self.client_secret)
    
    @patch('main.requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful token acquisition."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test_token_123',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        token = self.authenticator.get_access_token()
        
        # Verify token was returned
        self.assertEqual(token, 'test_token_123')
        self.assertEqual(self.authenticator.access_token, 'test_token_123')
        
        # Verify request was made correctly
        mock_post.assert_called_once_with(
            'https://www.arcgis.com/sharing/rest/oauth2/token',
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
        )
        
        # Verify expiration was set with buffer
        self.assertIsNotNone(self.authenticator.token_expires)
        self.assertTrue(self.authenticator.token_expires > datetime.now())
    
    @patch('main.requests.post')
    def test_get_access_token_reuse_valid_token(self, mock_post):
        """Test that valid tokens are reused without new requests."""
        # Set up existing valid token
        self.authenticator.access_token = 'existing_token'
        self.authenticator.token_expires = datetime.now() + timedelta(minutes=30)
        
        token = self.authenticator.get_access_token()
        
        # Should return existing token without making request
        self.assertEqual(token, 'existing_token')
        mock_post.assert_not_called()
    
    @patch('main.requests.post')
    def test_get_access_token_refresh_expired_token(self, mock_post):
        """Test that expired tokens trigger new requests."""
        # Set up expired token
        self.authenticator.access_token = 'expired_token'
        self.authenticator.token_expires = datetime.now() - timedelta(minutes=5)
        
        # Mock new token response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'new_token_456',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        token = self.authenticator.get_access_token()
        
        # Should get new token
        self.assertEqual(token, 'new_token_456')
        mock_post.assert_called_once()
    
    @patch('main.requests.post')
    def test_get_access_token_http_error(self, mock_post):
        """Test handling of HTTP errors during token request."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response
        
        with self.assertRaises(requests.HTTPError):
            self.authenticator.get_access_token()
    
    @patch('main.requests.post')
    def test_get_access_token_missing_expires_in(self, mock_post):
        """Test handling when expires_in is missing from response."""
        # Mock response without expires_in
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test_token_no_expiry'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        token = self.authenticator.get_access_token()
        
        # Should still work with default expiry
        self.assertEqual(token, 'test_token_no_expiry')
        self.assertIsNotNone(self.authenticator.token_expires)
    
    @patch('main.requests.post')
    def test_get_access_token_json_error(self, mock_post):
        """Test handling of malformed JSON response."""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError):
            self.authenticator.get_access_token()


if __name__ == '__main__':
    unittest.main() 