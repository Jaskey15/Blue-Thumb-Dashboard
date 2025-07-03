"""
Tests for application configuration

This file tests application configuration including:
- Configuration loading and validation
- Environment variable handling
- Configuration overrides
- Default value management
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.gcp_config import (
    get_environment,
    get_asset_base_url,
    get_database_path,
    get_log_level,
    get_app_config,
    is_gcp_environment,
)

class TestConfigurationLoading(unittest.TestCase):
    """Test configuration loading functionality."""

    @patch.dict(os.environ, {}, clear=True)
    def test_load_local_configuration(self):
        """Test loading default configuration for local environment."""
        config = get_app_config()
        self.assertEqual(config['environment'], 'local')
        self.assertEqual(config['asset_base_url'], '/assets')
        self.assertIn('database/blue_thumb.db', config['database_path'])
        self.assertEqual(config['log_level'], 'DEBUG')
        self.assertTrue(config['debug'])

    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project'}, clear=True)
    def test_load_gcp_configuration(self):
        """Test loading configuration for GCP environment."""
        config = get_app_config()
        self.assertEqual(config['environment'], 'gcp')
        self.assertEqual(config['asset_base_url'], '/assets') # No bucket set
        self.assertEqual(config['database_path'], '/tmp/blue_thumb.db')
        self.assertEqual(config['log_level'], 'INFO')
        self.assertFalse(config['debug'])


class TestEnvironmentVariables(unittest.TestCase):
    """Test environment variable handling."""

    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project', 'GCS_ASSET_BUCKET': 'my-asset-bucket'}, clear=True)
    def test_gcp_asset_bucket_override(self):
        """Test GCS_ASSET_BUCKET environment variable override."""
        base_url = get_asset_base_url()
        self.assertEqual(base_url, 'https://storage.googleapis.com/my-asset-bucket')

    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project'}, clear=True)
    def test_gcp_no_asset_bucket(self):
        """Test GCP environment without GCS_ASSET_BUCKET falls back to local assets."""
        base_url = get_asset_base_url()
        self.assertEqual(base_url, '/assets')

    @patch.dict(os.environ, {'LOG_LEVEL': 'WARNING', 'GOOGLE_CLOUD_PROJECT': 'test-project'}, clear=True)
    def test_log_level_override(self):
        """Test LOG_LEVEL environment variable override."""
        # Need to simulate a non-local environment for LOG_LEVEL to be read from env
        log_level = get_log_level()
        self.assertEqual(log_level, 'WARNING')

    @patch.dict(os.environ, {}, clear=True)
    def test_environment_variable_precedence(self):
        """Test environment variable precedence for identifying environment."""
        # Test GCP detection with different variables
        with patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'proj'}, clear=True):
            self.assertTrue(is_gcp_environment())
            self.assertEqual(get_environment(), 'gcp')
        
        with patch.dict(os.environ, {'GAE_APPLICATION': 'app'}, clear=True):
            self.assertTrue(is_gcp_environment())
            self.assertEqual(get_environment(), 'gcp')

        with patch.dict(os.environ, {'K_SERVICE': 'service'}, clear=True):
            self.assertTrue(is_gcp_environment())
            self.assertEqual(get_environment(), 'gcp')

        # Test local detection
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_gcp_environment())
            self.assertEqual(get_environment(), 'local')

class TestConfigurationOverrides(unittest.TestCase):
    """Test configuration override mechanisms."""
    
    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project'}, clear=True)
    def test_gcp_defaults(self):
        """Test default values for GCP environment."""
        self.assertEqual(get_log_level(), 'INFO')

    def test_configuration_value_types(self):
        """Test configuration value type enforcement."""
        config = get_app_config()
        self.assertIsInstance(config['environment'], str)
        self.assertIsInstance(config['asset_base_url'], str)
        self.assertIsInstance(config['database_path'], str)
        self.assertIsInstance(config['log_level'], str)
        self.assertIsInstance(config['debug'], bool)

if __name__ == '__main__':
    unittest.main(verbosity=2)