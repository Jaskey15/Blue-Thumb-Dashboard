import logging
import os
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tenmile_creek.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_chemical_data(file_path=None):
    """Process chemical data from CSV file and return cleaned dataframe.""" 
    # Default file path if none provided
    if file_path is None:
        file_path = '/Users/jacobaskey/Desktop/MyProjects/Tenmile Creek Project/VsCode/venv/dashboard/data/raw/Tenmile_chemical.csv'
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Chemical data file not found at: {file_path}")
    
    # Load the data
    try:
        tenmile_data = pd.read_csv(file_path)
        logger.info(f"Successfully loaded data with {len(tenmile_data)} rows")
    except Exception as e:
        logger.error(f"Error loading chemical data: {e}")
        raise Exception(f"Error loading chemical data: {e}")

    # Clean column names
    tenmile_data.columns = [    
        col.replace(' \n', '_')
            .replace('\n', '_')
            .replace(' ', '_')
            .replace('-', '_')
            .replace('/', '_')
            .replace('.', '')
        for col in tenmile_data.columns
    ]
    logger.debug("Column names cleaned")
       
    # Rename columns for clarity
    renamed_columns = {
        'DO_mg_L': 'Dissolved_Oxygen',
        '%_Oxygen_Saturation': 'DO_Percent',
        'Nitrate_mg_L': 'Nitrate',
        'Nitrite_mg_L': 'Nitrite',
        'Ammonia_mg_L_NH3_N': 'Ammonia',
        'Orthophosphate_mg_L_P': 'Phosphorus',
        'Chloride_mg_L_Cl': 'Chloride',
    }

    # Create a clean version for analysis and plotting
    df_clean = tenmile_data.rename(columns=renamed_columns)
    logger.debug(f"Columns renamed: {', '.join(renamed_columns.keys())} -> {', '.join(renamed_columns.values())}")
    
    # Convert 'Date' column to datetime format
    df_clean['Date'] = pd.to_datetime(tenmile_data['Date'])

    # Extract additional time components 
    df_clean['Year'] = df_clean['Date'].dt.year
    df_clean['Month'] = df_clean['Date'].dt.month
    logger.debug("Date columns processed and time components extracted")

    # Define values used for BDL in calculation (Values provided by Blue Thumb Coordinator)
    bdl_values = {
        'Nitrate': 0.3,    
        'Nitrite': 0.03,    
        'Ammonia': 0.03,
        'Phosphorus': 0.005,
    }

    # Check for missing BDL columns and log warnings
    missing_bdl_columns = [col for col in bdl_values.keys() if col not in df_clean.columns]
    if missing_bdl_columns:
        logger.warning(f"BDL conversion: Could not find these columns: {', '.join(missing_bdl_columns)}")

    # Create function to replace BDL with specific values
    def convert_bdl_value(value, bdl_replacement):
        if isinstance(value, (int, float)):
            return value
        elif isinstance(value, str) and value.upper() == 'BDL':
            return bdl_replacement # Use specified assumed values
        else:
            try: 
                return float(value)
            except:
                logger.warning(f"Could not convert value '{value}' to float")
                return None
    
    # Apply BDL conversions for specific columns
    bdl_conversion_count = 0
    for column, bdl_value in bdl_values.items():
        if column in df_clean.columns:
            df_clean[column] = df_clean[column].apply(
                lambda x: convert_bdl_value(x, bdl_value)
            )
            bdl_conversion_count += 1

    logger.debug(f"Applied BDL conversions to {bdl_conversion_count} columns")
 
    # Define numeric columns
    numeric_columns = [
        'Dissolved_Oxygen', 'DO_Percent', 'pH', 
        'Nitrite', 'Nitrate', 'Ammonia', 
        'Phosphorus', 'Chloride', 
        'E_coli', 'Total_Coliforms'
    ]

    # Check for missing numeric columns and log warnings
    missing_numeric_columns = [col for col in numeric_columns if col not in df_clean.columns]
    if missing_numeric_columns:
        logger.warning(f"Numeric conversion: Could not find these columns: {', '.join(missing_numeric_columns)}")
                    
    # Convert all numeric colums
    numeric_conversion_count = 0 
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            numeric_conversion_count += 1
    
    logger.debug(f"Converted {numeric_conversion_count} columns to numeric type")
        
    # Calculate total nitrogen using converted values
    required_nitrogen_cols = ['Nitrate', 'Nitrite', 'Ammonia']
    if all(col in df_clean.columns for col in required_nitrogen_cols):
        df_clean['Soluble_Nitrogen'] = (
            df_clean['Nitrate'].fillna(bdl_values['Nitrate']) +
            df_clean['Nitrite'].fillna(bdl_values['Nitrite']) +
            df_clean['Ammonia'].fillna(bdl_values['Ammonia'])
        )
        logger.debug("Calculated Soluble_Nitrogen from component values")
    else:   
        missing_nitrogen_cols = [col for col in required_nitrogen_cols if col not in df_clean.columns]
        logger.warning(f"Cannot calculate Soluble_Nitrogen: Missing columns: {', '.join(missing_nitrogen_cols)}")

    # List of key parameters
    key_parameters = [    
        'DO_Percent', 'pH', 'Soluble_Nitrogen', 
        'Phosphorus', 'Chloride', 
    ]

    # Define reference values (based on Blue Thumb documentation)
    reference_values = {
        'DO_Percent': {
            'normal min': 80, 
            'normal max': 130, 
            'caution min': 50,
            'caution max': 150,
            'description': 'Normal dissolved oxygen saturation range'
        },
        'pH': {
            'normal min': 6.5, 
            'normal max': 9.0, 
            'description': 'Normal range for Oklahoma streams'
        },
        'Soluble_Nitrogen': {
            'normal': 0.8, 
            'caution': 1.5, 
            'description': 'Normal nitrogen levels for this area'
        },
        'Phosphorus': {
            'normal': 0.05, 
            'caution': 0.1, 
            'description': 'Phosphorus levels for streams in Oklahoma'
        },
        'Chloride': {
            'poor': 250,
            'description': 'Maximum acceptable chloride level'
        }
    }

    # Check for missing values in final datafram
    missing_values = df_clean.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Final dataframe contains {missing_values} missing values")

    logger.info(f"Data processing complete. Output dataframe has {len(df_clean)} rows and {len(df_clean.columns)} columns")
    return df_clean, key_parameters, reference_values

if __name__ == "__main__":
    try:
        logger.info("Starting chemical data processing")
        df_clean, key_parameters, reference_values = process_chemical_data()

        # Save processed data
        output_path = '/Users/jacobaskey/Desktop/MyProjects/Tenmile Creek Project/VsCode/venv/data/processed/Tenmile_chemical_cleaned.csv'  

        # Make sure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df_clean.to_csv(output_path, index=False)
        logger.info(f"Cleaned data saved to {output_path}")

    except Exception as e:
        logger.error(f"Error in chemical data processing: {e}")
