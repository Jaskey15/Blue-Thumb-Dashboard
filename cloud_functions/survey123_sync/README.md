# Survey123 Daily Sync Cloud Function

This Cloud Function provides automated daily synchronization of Survey123 form submissions with the Blue Thumb Dashboard database.

## Overview

The Survey123 sync function:
- **Runs daily at 6 AM Central Time** via Cloud Scheduler
- **Fetches new submissions** from Survey123 via ArcGIS REST API
- **Processes chemical data** using existing Blue Thumb logic
- **Updates SQLite database** stored in Cloud Storage
- **Creates automatic backups** before each update
- **Provides comprehensive logging** for monitoring and debugging

## Architecture

```
Survey123 Form ➜ ArcGIS API ➜ Cloud Function ➜ Cloud Storage ➜ Dashboard
                                     ↓
                              Processing Logic
                            (Chemical Analysis)
```

## Files

- **`main.py`**: Core Cloud Function with authentication and orchestration
- **`chemical_processor.py`**: Adapted chemical data processing logic
- **`requirements.txt`**: Python dependencies
- **`deploy.sh`**: Automated deployment script
- **`README.md`**: This documentation

## Setup Instructions

### 1. ArcGIS Configuration

First, you'll need to set up ArcGIS authentication:

1.  **Find or Create an App Registration**:
    *   Log into your ArcGIS Online organization.
    *   Go to **Organization** → **Settings** → **App Registrations**.
    *   **Check for an existing registration** that is used for the Blue Thumb project. Using an existing registration is preferred.
    *   If no suitable registration exists, **Create a new app registration**.
    *   Note the `Client ID` and `Client Secret` that are generated.

2.  **Ensure Permissions**:
    *   The App Registration (identified by the `Client ID`) must have permission to view the data from your Survey123 form.
    *   If you are reusing an existing app registration, these permissions are likely already in place.
    *   If you created a new one, you must **share the Survey123 form with the new App Registration** within ArcGIS Online to grant it access.

3.  **Get Survey123 Form ID**:
   - Open your Survey123 form in the web designer
   - The form ID is in the URL: `survey123.arcgis.com/share/{FORM_ID}`

### 2. Deploy Cloud Function

1. **Navigate to function directory**:
   ```bash
   cd cloud_functions/survey123_sync
   ```

2. **Make deployment script executable**:
   ```bash
   chmod +x deploy.sh
   ```

3. **Deploy the function**:
   ```bash
   ./deploy.sh
   ```

### 3. Set Environment Variables

Set the required environment variables using Google Cloud Secret Manager or environment variables:

```bash
# Set ArcGIS credentials
gcloud functions deploy survey123-daily-sync \
    --update-env-vars ARCGIS_CLIENT_ID="your_client_id" \
    --update-env-vars ARCGIS_CLIENT_SECRET="your_client_secret" \
    --update-env-vars SURVEY123_FORM_ID="your_form_id" \
    --region=us-central1
```

### 4. Create Daily Schedule

Create a Cloud Scheduler job for daily execution:

```bash
gcloud scheduler jobs create http survey123-daily-sync \
    --schedule="0 6 * * *" \
    --uri="https://us-central1-blue-thumb-dashboard.cloudfunctions.net/survey123-daily-sync" \
    --http-method=POST \
    --time-zone="America/Chicago"
```

### 5. Upload Database

Ensure your SQLite database is uploaded to Cloud Storage:

```bash
gsutil cp database/blue_thumb.db gs://blue-thumb-database/
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Yes (auto-set) |
| `GCS_BUCKET_DATABASE` | Cloud Storage bucket for database | Yes |
| `ARCGIS_CLIENT_ID` | ArcGIS service account client ID | Yes |
| `ARCGIS_CLIENT_SECRET` | ArcGIS service account secret | Yes |
| `SURVEY123_FORM_ID` | Survey123 form identifier | Yes |

## Data Processing Flow

### 1. Authentication
- Obtains ArcGIS access token using service account credentials
- Handles token refresh automatically

### 2. Data Fetching
- Queries Survey123 API for submissions since last sync
- Converts ArcGIS feature data to pandas DataFrame

### 3. Chemical Processing
- **Date parsing**: Extracts dates from Survey123 timestamp format
- **Nutrient processing**: Handles range-based measurements (Low/Mid/High)
- **BDL conversions**: Converts zeros to Below Detection Limit values
- **Data validation**: Removes invalid measurements
- **Schema formatting**: Converts to database-compatible format

### 4. Database Updates
- Downloads SQLite database from Cloud Storage
- Creates automatic backup with timestamp
- Inserts new chemical measurements
- Uploads updated database back to Cloud Storage

### 5. Sync Tracking
- Records last successful sync timestamp
- Provides detailed execution logs
- Returns comprehensive status information

## Chemical Parameters Processed

The function processes these chemical parameters from Survey123:

| Parameter | Survey123 Fields | Processing Logic |
|-----------|------------------|------------------|
| **pH** | `pH #1`, `pH #2` | Greater of two values |
| **Dissolved Oxygen** | `% Oxygen Saturation` | Direct mapping |
| **Nitrate** | `Nitrate #1`, `Nitrate #2` | Greater of two values |
| **Nitrite** | `Nitrite #1`, `Nitrite #2` | Greater of two values |
| **Ammonia** | Range selection + readings | Conditional based on range |
| **Phosphorus** | Range selection + readings | Conditional based on range |
| **Chloride** | Range selection + readings | Conditional based on range |

### Range-Based Processing

For Ammonia, Phosphorus, and Chloride, the function uses conditional logic:

```python
# Example for Ammonia
if range_selection == "Low":
    value = max(low_reading_1, low_reading_2)
elif range_selection == "Mid":  
    value = max(mid_reading_1, mid_reading_2)
elif range_selection == "High":
    value = max(high_reading_1, high_reading_2)
```

## Monitoring and Debugging

### View Function Logs

```bash
gcloud functions logs read survey123-daily-sync --region=us-central1
```

### Test Manual Execution

```bash
# Get function URL
FUNCTION_URL=$(gcloud functions describe survey123-daily-sync --region=us-central1 --format="value(serviceConfig.uri)")

# Trigger manually
curl -X POST $FUNCTION_URL
```

### Check Scheduler Status

```bash
gcloud scheduler jobs describe survey123-daily-sync --location=us-central1
```

## Response Format

### Successful Execution
```json
{
  "status": "success",
  "message": "Successfully processed 3 new records",
  "records_processed": 3,
  "records_inserted": 21,
  "execution_time": "0:00:45.123456",
  "last_sync": "2024-01-30T06:00:00",
  "current_sync": "2024-01-31T06:00:00"
}
```

### No New Data
```json
{
  "status": "success", 
  "message": "No new data to process",
  "records_processed": 0,
  "execution_time": "0:00:12.345678"
}
```

### Error Response
```json
{
  "status": "failed",
  "error": "ArcGIS authentication failed",
  "execution_time": "0:00:05.123456"
}
```

## Cost Estimation

**Daily execution costs** (very minimal):
- **Function invocations**: ~$0.0001/year (within free tier)
- **Compute time**: ~$0.30/year
- **Storage**: ~$0.36/year (database storage)
- **Total**: **<$1/year**

## Troubleshooting

### Common Issues

1. **ArcGIS Authentication Failed**
   - Verify `ARCGIS_CLIENT_ID` and `ARCGIS_CLIENT_SECRET`
   - Check service account permissions in ArcGIS

2. **Survey123 Form Not Found**
   - Verify `SURVEY123_FORM_ID` is correct
   - Ensure form is published and accessible

3. **Database Update Failed**
   - Check Cloud Storage bucket permissions
   - Verify database file exists in bucket

4. **No Data Processed**
   - Check if there are new Survey123 submissions
   - Verify date range logic (last sync timestamp)

### Debug Mode

To enable more detailed logging, update the function with debug environment variable:

```bash
gcloud functions deploy survey123-daily-sync \
    --update-env-vars DEBUG="true" \
    --region=us-central1
```

## Security Considerations

- **Service account credentials** are stored as environment variables
- **Database backups** are created before each update
- **Function access** can be restricted using IAM policies
- **HTTPS only** communication with ArcGIS API

## Future Enhancements

- **Real-time webhooks** for immediate processing
- **Email notifications** for sync failures
- **Dashboard integration** for sync status monitoring
- **Multi-form support** for different survey types
- **Data validation rules** specific to site conditions

## Support

For issues or questions:
1. Check function logs for detailed error information
2. Verify all environment variables are set correctly
3. Test ArcGIS API access manually using provided credentials
4. Review Cloud Storage bucket permissions and database file integrity 