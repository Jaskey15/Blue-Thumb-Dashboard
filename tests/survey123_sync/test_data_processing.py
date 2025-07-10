"""
Tests for Survey123 data processing functions.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

import pandas as pd

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'cloud_functions', 'survey123_sync'))

# Mock Cloud Function specific modules before importing
sys.modules['functions_framework'] = MagicMock()
sys.modules['google.cloud'] = MagicMock() 
sys.modules['google.cloud.storage'] = MagicMock()

from main import process_survey123_data


class TestSurvey123DataProcessing(unittest.TestCase):
    """Test Survey123 data processing wrapper functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample Survey123 data
        self.sample_survey123_data = pd.DataFrame({
            'Site Name': ['Test Site 1'],
            'Sampling Date': ['5/15/2023, 10:30 AM'],
            '% Oxygen Saturation': [95.5],
            'pH #1': [7.2],
            'pH #2': [7.5],
            'Nitrate #1': [0.5],
            'Nitrate #2': [0.6],
            'Nitrite #1': [0.05],
            'Nitrite #2': [0.04],
            'Ammonia Nitrogen Range Selection': ['Low'],
            'Ammonia Nitrogen Low Reading #1': [0.1],
            'Ammonia Nitrogen Low Reading #2': [0.12],
            'Orthophosphate Range Selection': ['Low'],
            'Orthophosphate_Low1_Final': [0.02],
            'Orthophosphate_Low2_Final': [0.03],
            'Chloride Range Selection': ['Low'],
            'Chloride_Low1_Final': [25.0],
            'Chloride_Low2_Final': [26.0]
        })
    
    def test_process_survey123_data_function(self):
        """Test the data processing function wrapper."""
        # Test with valid data
        result = process_survey123_data(self.sample_survey123_data.copy())
        
        # Should process successfully
        self.assertFalse(result.empty)
        self.assertIn('Site_Name', result.columns)
        
        # Test with empty data
        empty_result = process_survey123_data(pd.DataFrame())
        self.assertTrue(empty_result.empty)
    
    def test_process_survey123_data_error_handling(self):
        """Test error handling in data processing function."""
        # Create invalid data that should cause processing errors
        invalid_df = pd.DataFrame({'Invalid': ['Data']})
        
        result = process_survey123_data(invalid_df)
        
        # Should handle errors gracefully and return empty DataFrame
        self.assertTrue(result.empty)


if __name__ == '__main__':
    unittest.main() 