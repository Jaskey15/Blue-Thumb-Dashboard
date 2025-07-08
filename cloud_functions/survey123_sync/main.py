"""
Survey123 Daily Sync Cloud Function

This Cloud Function runs daily to sync new Survey123 submissions with the Blue Thumb Dashboard.
It downloads new chemical data submissions via ArcGIS REST API, processes them using existing
logic, and updates the SQLite database stored in Cloud Storage.

Trigger: Cloud Scheduler (daily at 6 AM Central)
Runtime: Python 3.12
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
DATABASE_BUCKET = os.environ.get('GCS_BUCKET_DATABASE', 'blue-thumb-database')
ARCGIS_CLIENT_ID = os.environ.get('ARCGIS_CLIENT_ID')
ARCGIS_CLIENT_SECRET = os.environ.get('ARCGIS_CLIENT_SECRET')
SURVEY123_FORM_ID = os.environ.get('SURVEY123_FORM_ID')

# ArcGIS endpoints
ARCGIS_TOKEN_URL = "https://www.arcgis.com/sharing/rest/oauth2/token"
SURVEY123_API_BASE = "https://survey123.arcgis.com/api/featureServices"

class ArcGISAuthenticator:
    """Handle ArcGIS authentication using service account credentials."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = None
    
    def get_access_token(self) -> str:
        """Get or refresh the ArcGIS access token."""
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
        # Token expires in seconds, add buffer
        expires_in = token_data.get('expires_in', 3600) - 300  # 5 minute buffer
        self.token_expires = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info("Successfully obtained ArcGIS access token")
        return self.access_token

class Survey123DataFetcher:
    """Fetch Survey123 data using ArcGIS REST API."""
    
    def __init__(self, authenticator: ArcGISAuthenticator, form_id: str):
        self.authenticator = authenticator
        self.form_id = form_id
    
    def get_submissions_since(self, since_date: datetime) -> pd.DataFrame:
        """Fetch Survey123 submissions since the specified date."""
        logger.info(f"Fetching Survey123 submissions since {since_date}")
        
        # Convert datetime to epoch milliseconds for ArcGIS query
        since_epoch = int(since_date.timestamp() * 1000)
        
        # Build query URL
        query_url = f"{SURVEY123_API_BASE}/{self.form_id}/0/query"
        
        params = {
            'token': self.authenticator.get_access_token(),
            'where': f"CreationDate > {since_epoch}",
            'outFields': '*',
            'f': 'json',
            'resultRecordCount': 1000  # Adjust as needed
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
            
            # Convert to DataFrame
            records = []
            for feature in features:
                attributes = feature.get('attributes', {})
                records.append(attributes)
            
            df = pd.DataFrame(records)
            logger.info(f"Converted to DataFrame with {len(df)} rows and {len(df.columns)} columns")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Survey123 data: {e}")
            raise

class DatabaseManager:
    """Manage SQLite database operations in Cloud Storage."""
    
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.db_blob_name = 'blue_thumb.db'
    
    def download_database(self, local_path: str) -> bool:
        """Download database from Cloud Storage to local file."""
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
        """Upload database from local file to Cloud Storage."""
        try:
            # Create backup first
            backup_name = f"backups/blue_thumb_backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db"
            blob = self.bucket.blob(self.db_blob_name)
            if blob.exists():
                backup_blob = self.bucket.blob(backup_name)
                backup_blob.upload_from_string(blob.download_as_string())
                logger.info(f"Created backup: {backup_name}")
            
            # Upload updated database
            new_blob = self.bucket.blob(self.db_blob_name)
            new_blob.upload_from_filename(local_path)
            logger.info(f"Uploaded updated database to {self.db_blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database: {e}")
            return False
    
    def get_last_sync_timestamp(self) -> datetime:
        """Get the timestamp of the last successful sync."""
        try:
            blob = self.bucket.blob('sync_metadata/last_sync.json')
            if blob.exists():
                metadata = json.loads(blob.download_as_string())
                return datetime.fromisoformat(metadata['last_sync_timestamp'])
            else:
                # Default to 7 days ago for first run
                return datetime.now() - timedelta(days=7)
                
        except Exception as e:
            logger.warning(f"Error reading last sync timestamp: {e}")
            return datetime.now() - timedelta(days=7)
    
    def update_sync_timestamp(self, timestamp: datetime) -> bool:
        """Update the last successful sync timestamp."""
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
    Process Survey123 data using existing chemical processing logic.
    This function uses the chemical_processor module to handle all processing.
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
    Main Cloud Function entry point for daily Survey123 sync.
    
    This function:
    1. Authenticates with ArcGIS
    2. Fetches new Survey123 submissions
    3. Processes the data using existing logic
    4. Updates the SQLite database
    5. Returns sync status
    """
    
    start_time = datetime.now()
    logger.info(f"Starting Survey123 daily sync at {start_time}")
    
    # Validate environment variables
    if not all([ARCGIS_CLIENT_ID, ARCGIS_CLIENT_SECRET, SURVEY123_FORM_ID]):
        error_msg = "Missing required environment variables"
        logger.error(error_msg)
        return {'error': error_msg, 'status': 'failed'}, 500
    
    try:
        # Initialize components
        authenticator = ArcGISAuthenticator(ARCGIS_CLIENT_ID, ARCGIS_CLIENT_SECRET)
        fetcher = Survey123DataFetcher(authenticator, SURVEY123_FORM_ID)
        db_manager = DatabaseManager(DATABASE_BUCKET)
        
        # Get last sync timestamp
        last_sync = db_manager.get_last_sync_timestamp()
        logger.info(f"Last sync was at: {last_sync}")
        
        # Fetch new submissions
        new_data = fetcher.get_submissions_since(last_sync)
        
        if new_data.empty:
            logger.info("No new Survey123 submissions found")
            return {
                'status': 'success',
                'message': 'No new data to process',
                'records_processed': 0,
                'execution_time': str(datetime.now() - start_time)
            }
        
        # Process the data
        processed_data = process_survey123_data(new_data)
        
        # Update database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            if not db_manager.download_database(temp_db.name):
                raise Exception("Failed to download database")
            
            # Insert processed data into SQLite database
            from chemical_processor import insert_processed_data_to_db
            insert_result = insert_processed_data_to_db(processed_data, temp_db.name)
            
            if 'error' in insert_result:
                raise Exception(f"Database insertion failed: {insert_result['error']}")
            
            # Upload updated database
            if not db_manager.upload_database(temp_db.name):
                raise Exception("Failed to upload updated database")
        
        # Update sync timestamp
        db_manager.update_sync_timestamp(start_time)
        
        # Return success response
        result = {
            'status': 'success',
            'message': f'Successfully processed {len(processed_data)} new records',
            'records_processed': len(processed_data),
            'records_inserted': insert_result.get('records_inserted', 0),
            'execution_time': str(datetime.now() - start_time),
            'last_sync': last_sync.isoformat(),
            'current_sync': start_time.isoformat()
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
    # For local testing
    class MockRequest:
        pass
    
    result = survey123_daily_sync(MockRequest())
    print(json.dumps(result, indent=2)) 