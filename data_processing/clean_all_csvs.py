"""
clean_all_csvs.py - CSV Cleaning Pipeline

This script processes all raw CSV files to create cleaned versions with standardized site names.
The cleaned CSVs will be used for site consolidation and all subsequent data processing.

Usage: python clean_all_csvs.py
"""

import os
import sys
import pandas as pd
import re

# Add the parent directory to Python path so we can import utils
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from utils import setup_logging

# Set up logging
logger = setup_logging("clean_all_csvs", category="preprocessing")

# Define directories 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')

# Ensure processed directory exists
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# CSV file configurations
CSV_CONFIGS = {
    'site_data': {
        'input_file': 'site_data.csv',
        'output_file': 'cleaned_site_data.csv',
        'site_column': 'SiteName',
        'encoding': None,
        'description': 'Master site data with full metadata'
    },
    'chemical_data': {
        'input_file': 'chemical_data.csv',
        'output_file': 'cleaned_chemical_data.csv',
        'site_column': 'SiteName',
        'encoding': None,
        'description': 'Original chemical monitoring data'
    },
    'updated_chemical_data': {
        'input_file': 'updated_chemical_data.csv',
        'output_file': 'cleaned_updated_chemical_data.csv',
        'site_column': 'Site Name',
        'encoding': 'cp1252',
        'description': 'Updated chemical monitoring data'
    },
    'fish_data': {
        'input_file': 'fish_data.csv',
        'output_file': 'cleaned_fish_data.csv',
        'site_column': 'SiteName',
        'encoding': None,
        'description': 'Fish community monitoring data'
    },
    'macro_data': {
        'input_file': 'macro_data.csv',
        'output_file': 'cleaned_macro_data.csv',
        'site_column': 'SiteName',
        'encoding': None,
        'description': 'Macroinvertebrate monitoring data'
    },
    'habitat_data': {
        'input_file': 'habitat_data.csv',
        'output_file': 'cleaned_habitat_data.csv',
        'site_column': 'SiteName',
        'encoding': None,
        'description': 'Habitat assessment data'
    }
}

def clean_site_name(site_name):
    """
    Clean and standardize site names.
    
    Args:
        site_name: Raw site name string
    
    Returns:
        str: Cleaned site name
    """
    if pd.isna(site_name):
        return site_name
    
    # Convert to string and strip leading/trailing whitespace
    cleaned = str(site_name).strip()
    
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned

def clean_csv_file(config_key, config):
    """
    Clean a single CSV file and save the cleaned version.
    
    Args:
        config_key: Key identifying the CSV configuration
        config: Configuration dictionary for this CSV
    
    Returns:
        dict: Results of the cleaning process
    """
    input_path = os.path.join(RAW_DATA_DIR, config['input_file'])
    output_path = os.path.join(PROCESSED_DATA_DIR, config['output_file'])
    
    logger.info(f"Processing {config['description']}: {config['input_file']}")
    
    # Load the CSV with appropriate encoding
    if config['encoding']:
        df = pd.read_csv(input_path, encoding=config['encoding'], low_memory=False)
    else:
        df = pd.read_csv(input_path, low_memory=False)
    
    # Clean site names and count changes
    original_sites = df[config['site_column']].copy()
    df[config['site_column']] = df[config['site_column']].apply(clean_site_name)
    
    # Count changes made
    changes_mask = (original_sites != df[config['site_column']]) & original_sites.notna()
    site_changes = changes_mask.sum()
    
    # Save cleaned CSV
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    # Log results
    unique_sites = df[config['site_column']].nunique()
    logger.info(f"  ✓ {len(df)} rows, {site_changes} names cleaned, {unique_sites} unique sites")
    
    return {
        'config_key': config_key,
        'success': True,
        'rows': len(df),
        'site_changes': site_changes,
        'unique_sites': unique_sites,
        'output_file': config['output_file']
    }

def clean_all_csvs():
    """
    Main function to clean all CSV files.
    
    Returns:
        bool: True if all files processed successfully
    """
    logger.info("Starting CSV cleaning pipeline...")
    logger.info(f"Input: {RAW_DATA_DIR}")
    logger.info(f"Output: {PROCESSED_DATA_DIR}")
    
    results = []
    
    # Process each CSV file
    for config_key, config in CSV_CONFIGS.items():
        try:
            result = clean_csv_file(config_key, config)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {config['input_file']}: {e}")
            return False
    
    # Generate summary
    total_changes = sum(r['site_changes'] for r in results)
    total_sites = sum(r['unique_sites'] for r in results)
    
    logger.info(f"\n🎉 Successfully cleaned all {len(results)} CSV files!")
    logger.info(f"Total: {total_changes} site name changes, {total_sites} unique sites across all files")
    
    # List output files
    logger.info("\nCleaned files created:")
    for result in results:
        logger.info(f"  - {result['output_file']}")
    
    return True

if __name__ == "__main__":
    success = clean_all_csvs()
    if not success:
        sys.exit(1)