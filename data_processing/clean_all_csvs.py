"""
clean_all_csvs.py - CSV Cleaning Pipeline

This script processes all raw CSV files to create cleaned versions with standardized site names.
The cleaned CSVs will be used for site consolidation and all subsequent data processing.

Usage: python clean_all_csvs.py
"""

import os
import pandas as pd
from data_processing import setup_logging

# Set up logging
logger = setup_logging("clean_all_csvs", category="preprocessing")

# Define data directories 
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
INTERIM_DATA_DIR = os.path.join(BASE_DIR, 'data', 'interim')

# Ensure interim directory exists
os.makedirs(INTERIM_DATA_DIR, exist_ok=True)

def clean_all_csvs():
    """
    Clean all CSV files by standardizing site names.
    
    This function processes all raw CSV files, cleans site names by stripping
    whitespace and normalizing spaces, then saves cleaned versions to the interim folder.
    
    Returns:
        bool: True if all files processed successfully
    """
    logger.info("Starting CSV cleaning pipeline...")
    logger.info(f"Input: {RAW_DATA_DIR}")
    logger.info(f"Output: {INTERIM_DATA_DIR}")
    
    # List of CSV files to process
    csv_files = [
        'site_data.csv',
        'chemical_data.csv', 
        'updated_chemical_data.csv',
        'fish_data.csv',
        'macro_data.csv',
        'habitat_data.csv',
    ]
    
    # Initialize summary counters
    total_changes = 0
    total_sites = 0
    processed_files = []
    
    # Process each CSV file
    for input_file in csv_files:
        try:
            # Handle special cases
            if input_file == 'updated_chemical_data.csv':
                site_column = 'Site Name'
                encoding = 'cp1252'
            else:
                site_column = 'SiteName'
                encoding = None
            
            # Auto-generate output filename and description
            output_file = f'cleaned_{input_file}'
            description = input_file.replace('_', ' ').replace('.csv', ' data')
            
            input_path = os.path.join(RAW_DATA_DIR, input_file)
            output_path = os.path.join(INTERIM_DATA_DIR, output_file)
            
            logger.info(f"Processing {description}: {input_file}")
            
            # Load the CSV with appropriate encoding
            if encoding:
                df = pd.read_csv(input_path, encoding=encoding, low_memory=False)
            else:
                df = pd.read_csv(input_path, low_memory=False)
            
            # Clean site names and count changes
            original_sites = df[site_column].copy()
            df[site_column] = df[site_column].str.strip().str.replace(r'\s+', ' ', regex=True)
            
            # Count changes made
            changes_mask = (original_sites != df[site_column]) & original_sites.notna()
            site_changes = changes_mask.sum()
            
            # Save cleaned CSV
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            # Log results and update counters
            unique_sites = df[site_column].nunique()
            logger.info(f"  ✓ {len(df)} rows, {site_changes} names cleaned, {unique_sites} unique sites")
            
            total_changes += site_changes
            total_sites += unique_sites
            processed_files.append(output_file)
            
        except Exception as e:
            logger.error(f"Failed to process {input_file}: {e}")
            return False
    
    # Generate summary
    logger.info(f"\n🎉 Successfully cleaned all {len(processed_files)} CSV files!")
    logger.info(f"Total: {total_changes} site name changes, {total_sites} unique sites across all files")
    
    # List output files
    logger.info("\nCleaned files created:")
    for filename in processed_files:
        logger.info(f"  - {filename}")
    
    return True

if __name__ == "__main__":
    success = clean_all_csvs()
    if not success:
        sys.exit(1)