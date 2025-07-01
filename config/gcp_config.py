"""
GCP-specific configuration for the Blue Thumb Dashboard.

This module handles configuration differences between local development,
Heroku deployment, and Google Cloud Platform deployment.
"""

import os
from utils import setup_logging

# Set up logging
logger = setup_logging("gcp_config", category="general")

# Environment detection
def is_gcp_environment():
    """Check if running in Google Cloud Platform environment."""
    return bool(os.environ.get('GOOGLE_CLOUD_PROJECT') or 
                os.environ.get('GAE_APPLICATION') or
                os.environ.get('K_SERVICE'))  # Cloud Run service name

def is_heroku_environment():
    """Check if running in Heroku environment."""
    return bool(os.environ.get('DYNO'))

def get_environment():
    """Get the current deployment environment."""
    if is_gcp_environment():
        return 'gcp'
    elif is_heroku_environment():
        return 'heroku'
    else:
        return 'local'

# Asset URL configuration
def get_asset_base_url():
    """
    Get the base URL for static assets based on environment.
    
    Returns:
        str: Base URL for assets
    """
    environment = get_environment()
    
    if environment == 'gcp':
        # Use Cloud Storage bucket for assets in GCP
        bucket_name = os.environ.get('GCS_ASSET_BUCKET')
        if bucket_name:
            return f"https://storage.googleapis.com/{bucket_name}"
        else:
            logger.warning("GCS_ASSET_BUCKET not set, falling back to local assets")
            return "/assets"
    else:
        # Use local assets for Heroku and local development
        return "/assets"

# Database configuration
def get_database_path():
    """
    Get the database path based on environment.
    
    Returns:
        str: Path to database file
    """
    environment = get_environment()
    
    if environment == 'gcp':
        # For GCP, we might use Cloud SQL later, but for now use local SQLite
        # Store in /tmp for Cloud Run (ephemeral storage)
        return '/tmp/blue_thumb.db'
    else:
        # Use relative path for Heroku and local development
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'blue_thumb.db')

# Logging configuration
def get_log_level():
    """Get appropriate log level for environment."""
    environment = get_environment()
    
    if environment == 'gcp':
        return os.environ.get('LOG_LEVEL', 'INFO')
    elif environment == 'heroku':
        return os.environ.get('LOG_LEVEL', 'INFO')
    else:
        return 'DEBUG'

# Application configuration
def get_app_config():
    """
    Get application configuration for the current environment.
    
    Returns:
        dict: Configuration dictionary
    """
    environment = get_environment()
    
    config = {
        'environment': environment,
        'asset_base_url': get_asset_base_url(),
        'database_path': get_database_path(),
        'log_level': get_log_level(),
        'debug': environment == 'local'
    }
    
    logger.info(f"Application configuration for {environment} environment:")
    logger.info(f"  - Asset base URL: {config['asset_base_url']}")
    logger.info(f"  - Database path: {config['database_path']}")
    logger.info(f"  - Log level: {config['log_level']}")
    
    return config 