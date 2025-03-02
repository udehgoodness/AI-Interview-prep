"""
Pytest configuration file for backend tests.
"""
import pytest
import os
import sys

# Add the parent directory to the path so we can import modules from the backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define fixtures that can be used across tests
@pytest.fixture
def api_base_url():
    """Return the base URL for the API"""
    return "http://localhost:8000" 