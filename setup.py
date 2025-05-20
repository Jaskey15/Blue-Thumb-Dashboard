"""
Setup script for Tenmile Creek Water Quality Dashboard.
This script initializes the database and processes all data.
"""
import sys
import logging
import importlib.util
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tenmile_creek_setup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define processing steps as a configuration list for better maintainability
SETUP_STEPS = [
    {
        "name": "database schema",
        "module": "database.db_schema",
        "function": "create_tables",
        "args": [],
        "critical": True  # If this fails, we should exit
    },
    {
        "name": "chemical data",
        "module": "data_processing.chemical_processing",
        "function": "run_initial_db_setup",  # Changed from process_chemical_data
        "args": [],
        "critical": True
    },
    # Rest of the steps remain the same
    {
        "name": "fish data",
        "module": "data_processing.fish_processing",
        "function": "load_fish_data",
        "args": [],
        "critical": True
    },
    {
        "name": "macroinvertebrate data",
        "module": "data_processing.macro_processing",
        "function": "load_macroinvertebrate_data",
        "args": [],
        "critical": True
    }
]

def check_prerequisites():
    """Check if all required packages and files are available."""
    logger.info("Checking prerequisites...")
    
    # Check for required Python packages
    required_packages = ["dash", "dash_bootstrap_components", "pandas", "plotly", "sqlite3"]
    missing_packages = []
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required Python packages: {', '.join(missing_packages)}")
        logger.info("Please install required packages with: pip install -r requirements.txt")
        return False
    
    # Check for required data files
    required_data_files = [
        "data/raw/Tenmile_chemical.csv",
        # Add more required files here if needed
    ]
    
    missing_files = []
    for file_path in required_data_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required data files: {', '.join(missing_files)}")
        return False
    
    logger.info("All prerequisites are met.")
    return True

def execute_step(step):
    """Execute a single setup step."""
    name = step["name"]
    module_name = step["module"]
    function_name = step["function"]
    args = step.get("args", [])
    critical = step.get("critical", False)
    
    logger.info(f"Processing {name}...")
    
    try:
        # Import the module
        module = __import__(module_name, fromlist=[function_name])
        function = getattr(module, function_name)
        
        # Execute the function with any provided arguments
        start_time = time.time()
        result = function(*args)
        elapsed_time = time.time() - start_time
        
        # Log success and return any results
        logger.info(f"{name.capitalize()} processed successfully in {elapsed_time:.2f} seconds")
        return True, result
    
    except Exception as e:
        logger.error(f"Error processing {name}: {e}")
        if critical:
            logger.critical("This is a critical step. Setup cannot continue.")
            sys.exit(1)
        return False, None

def main():
    """Run all setup tasks in the correct order."""
    logger.info("Starting Tenmile Creek Dashboard setup...")
    
    # Check prerequisites before proceeding
    if not check_prerequisites():
        logger.error("Setup cannot continue due to missing prerequisites.")
        sys.exit(1)
    
    # Process each setup step
    results = {}
    for step in SETUP_STEPS:
        success, result = execute_step(step)
        if success and result is not None:
            results[step["name"]] = result
    
    # All done!
    logger.info("Setup complete! Run 'python -m app' to start the dashboard.")
    logger.info("Dashboard will be available at http://127.0.0.1:8050/")
    
    # Ask if user wants to start the dashboard now
    response = input("Would you like to start the dashboard now? (y/n): ")
    if response.lower() in ['y', 'yes']:
        logger.info("Starting dashboard...")
        try:
            from app import app
            app.run(debug=True)
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}")
            sys.exit(1)
    else:
        logger.info("Dashboard not started. You can run it later with 'python -m app'")

if __name__ == "__main__":
    main()