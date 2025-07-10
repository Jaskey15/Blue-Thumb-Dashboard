"""
Survey123 Daily Sync Cloud Function

Automated daily synchronization of Survey123 submissions with Blue Thumb Dashboard.
Downloads new chemical data via ArcGIS REST API and updates SQLite database in Cloud Storage.

Environment Variables:
- GOOGLE_CLOUD_PROJECT: GCP project ID
- GCS_BUCKET_DATABASE: Cloud Storage bucket for database
- ARCGIS_CLIENT_ID: ArcGIS service account client ID
- ARCGIS_CLIENT_SECRET: ArcGIS service account secret
- SURVEY123_FORM_ID: Survey123 form identifier
"""

import os
import json
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import requests
from google.cloud import storage
import functions_framework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
DATABASE_BUCKET = os.environ.get('GCS_BUCKET_DATABASE', 'blue-thumb-database')
ARCGIS_CLIENT_ID = os.environ.get('ARCGIS_CLIENT_ID')
ARCGIS_CLIENT_SECRET = os.environ.get('ARCGIS_CLIENT_SECRET')
SURVEY123_FORM_ID = os.environ.get('SURVEY123_FORM_ID')

# ArcGIS endpoints
ARCGIS_TOKEN_URL = "https://www.arcgis.com/sharing/rest/oauth2/token"
SURVEY123_API_BASE = "https://survey123.arcgis.com/api/featureServices"

class ArcGISAuthenticator:
    """Handle ArcGIS authentication with automatic token refresh."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = None
    
    def get_access_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        logger.info("Requesting new ArcGIS access token...")
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(ARCGIS_TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600) - 300  # 5 minute buffer for safety
        self.token_expires = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info("Successfully obtained ArcGIS access token")
        return self.access_token

class Survey123DataFetcher:
    """Fetch Survey123 submissions using ArcGIS REST API."""
    
    def __init__(self, authenticator: ArcGISAuthenticator, form_id: str):
        self.authenticator = authenticator
        self.form_id = form_id
    
    def get_submissions_since(self, since_date: datetime) -> pd.DataFrame:
        """Fetch new Survey123 submissions since specified date."""
        logger.info(f"Fetching Survey123 submissions since {since_date}")
        
        since_epoch = int(since_date.timestamp() * 1000)  # ArcGIS expects epoch milliseconds
        
        query_url = f"{SURVEY123_API_BASE}/{self.form_id}/0/query"
        
        params = {
            'token': self.authenticator.get_access_token(),
            'where': f"CreationDate > {since_epoch}",
            'outFields': '*',
            'f': 'json',
            'resultRecordCount': 1000
        }
        
        try:
            response = requests.get(query_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"ArcGIS API error: {data['error']}")
            
            features = data.get('features', [])
            logger.info(f"Retrieved {len(features)} Survey123 submissions")
            
            if not features:
                return pd.DataFrame()
            
            # Convert feature attributes to DataFrame
            records = []
            for feature in features:
                attributes = feature.get('attributes', {})
                # Skip features with None or invalid attributes
                if attributes is not None and isinstance(attributes, dict):
                    records.append(attributes)
                else:
                    logger.warning(f"Skipping feature with invalid attributes: {feature}")
            
            df = pd.DataFrame(records)
            logger.info(f"Converted to DataFrame with {len(df)} rows and {len(df.columns)} columns")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Survey123 data: {e}")
            raise

class DatabaseManager:
    """Manage SQLite database operations in Cloud Storage with backup handling."""
    
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.db_blob_name = 'blue_thumb.db'
    
    def download_database(self, local_path: str) -> bool:
        """Download database from Cloud Storage for local processing."""
        try:
            blob = self.bucket.blob(self.db_blob_name)
            if not blob.exists():
                logger.error(f"Database {self.db_blob_name} not found in bucket {self.bucket.name}")
                return False
            
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded database to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading database: {e}")
            return False
    
    def upload_database(self, local_path: str) -> bool:
        """Upload updated database with automatic backup creation."""
        try:
            # Create timestamped backup before updating
            backup_name = f"backups/blue_thumb_backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db"
            blob = self.bucket.blob(self.db_blob_name)
            if blob.exists():
                backup_blob = self.bucket.blob(backup_name)
                backup_blob.upload_from_string(blob.download_as_string())
                logger.info(f"Created backup: {backup_name}")
            
            new_blob = self.bucket.blob(self.db_blob_name)
            new_blob.upload_from_filename(local_path)
            logger.info(f"Uploaded updated database to {self.db_blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database: {e}")
            return False
    
    def get_last_sync_timestamp(self) -> datetime:
        """Get timestamp of last successful sync for incremental updates."""
        try:
            blob = self.bucket.blob('sync_metadata/last_sync.json')
            if blob.exists():
                metadata = json.loads(blob.download_as_string())
                return datetime.fromisoformat(metadata['last_sync_timestamp'])
            else:
                return datetime.now() - timedelta(days=7)  # Default lookback for first run
                
        except Exception as e:
            logger.warning(f"Error reading last sync timestamp: {e}")
            return datetime.now() - timedelta(days=7)
    
    def update_sync_timestamp(self, timestamp: datetime) -> bool:
        """Record successful sync timestamp for next incremental run."""
        try:
            metadata = {
                'last_sync_timestamp': timestamp.isoformat(),
                'last_sync_status': 'success'
            }
            
            blob = self.bucket.blob('sync_metadata/last_sync.json')
            blob.upload_from_string(json.dumps(metadata))
            logger.info(f"Updated sync timestamp to {timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating sync timestamp: {e}")
            return False

def process_survey123_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process Survey123 data using existing chemical processing pipeline.
    """
    if df.empty:
        return pd.DataFrame()
    
    logger.info(f"Processing {len(df)} Survey123 records...")
    
    try:
        from chemical_processor import process_survey123_chemical_data
        return process_survey123_chemical_data(df)
        
    except Exception as e:
        logger.error(f"Error processing Survey123 data: {e}")
        raise

@functions_framework.http
def survey123_daily_sync(request):
    """
    Main Cloud Function entry point for daily Survey123 synchronization.
    
    Workflow:
    1. Authenticate with ArcGIS and fetch new submissions
    2. Process data using existing chemical pipeline
    3. Update SQLite database with automatic backup
    4. Record sync timestamp for next incremental run
    """
    
    start_time = datetime.now()
    logger.info(f"Starting Survey123 daily sync at {start_time}")
    
    if not all([ARCGIS_CLIENT_ID, ARCGIS_CLIENT_SECRET, SURVEY123_FORM_ID]):
        error_msg = "Missing required environment variables"
        logger.error(error_msg)
        return {'error': error_msg, 'status': 'failed'}, 500
    
    try:
        # Initialize service components
        authenticator = ArcGISAuthenticator(ARCGIS_CLIENT_ID, ARCGIS_CLIENT_SECRET)
        fetcher = Survey123DataFetcher(authenticator, SURVEY123_FORM_ID)
        db_manager = DatabaseManager(DATABASE_BUCKET)
        
        last_sync = db_manager.get_last_sync_timestamp()
        logger.info(f"Last sync was at: {last_sync}")
        
        # Fetch and process new data
        new_data = fetcher.get_submissions_since(last_sync)
        
        if new_data.empty:
            logger.info("No new Survey123 submissions found")
            return {
                'status': 'success',
                'message': 'No new data to process',
                'records_processed': 0,
                'execution_time': str(datetime.now() - start_time)
            }
        
        processed_data = process_survey123_data(new_data)
        
        # Database update with temporary file handling
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            if not db_manager.download_database(temp_db.name):
                raise Exception("Failed to download database")
            
            from chemical_processor import insert_processed_data_to_db, classify_active_sites_in_db
            insert_result = insert_processed_data_to_db(processed_data, temp_db.name)
            
            if 'error' in insert_result:
                raise Exception(f"Database insertion failed: {insert_result['error']}")
            
            # Reclassify active/historic sites after inserting new data
            classification_result = classify_active_sites_in_db(temp_db.name)
            if 'error' in classification_result:
                logger.warning(f"Site classification failed: {classification_result['error']}")
            else:
                logger.info(f"Site classification updated: {classification_result['active_count']} active, {classification_result['historic_count']} historic")
            
            if not db_manager.upload_database(temp_db.name):
                raise Exception("Failed to upload updated database")
        
        db_manager.update_sync_timestamp(start_time)
        
        # Success response with execution metrics
        result = {
            'status': 'success',
            'message': f'Successfully processed {len(processed_data)} new records',
            'records_processed': len(processed_data),
            'records_inserted': insert_result.get('records_inserted', 0),
            'execution_time': str(datetime.now() - start_time),
            'last_sync': last_sync.isoformat(),
            'current_sync': start_time.isoformat()
        }
        
        # Add site classification results if available
        if 'error' not in classification_result:
            result['site_classification'] = {
                'sites_classified': classification_result.get('sites_classified', 0),
                'active_count': classification_result.get('active_count', 0),
                'historic_count': classification_result.get('historic_count', 0)
            }
        
        logger.info(f"Sync completed successfully: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Sync failed: {str(e)}"
        logger.error(error_msg)
        
        return {
            'status': 'failed',
            'error': error_msg,
            'execution_time': str(datetime.now() - start_time)
        }, 500

if __name__ == "__main__":
    # Local testing support
    class MockRequest:
        pass
    
    result = survey123_daily_sync(MockRequest())
    print(json.dumps(result, indent=2)) 