"""
Data Processing Package

This package handles all data processing operations including CSV cleaning,
biological data processing, and database operations.
"""

import os
import sys

# Add project root to Python path so all modules can import from project root
_current_dir = os.path.dirname(__file__)
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from utils import setup_logging

# Re-export for easy access
__all__ = ['setup_logging']
