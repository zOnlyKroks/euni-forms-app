"""Pytest configuration for euniforms tests."""

import os
import sys

def pytest_configure():
    """Configure Django settings for testing."""
    # Add the current directory to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Configure Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'euniforms.tests.settings')