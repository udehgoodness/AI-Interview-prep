"""
Pytest configuration file for backend tests.
"""
import pytest
import os
import sys
import requests
from .test_auth import get_access_token

# Add the parent directory to the path so we can import modules from the backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define fixtures that can be used across tests
@pytest.fixture
def api_base_url():
    """Return the base URL for the API"""
    return "http://localhost:8000"

@pytest.fixture
def auth_headers():
    """Return headers with a test token for authentication"""
    # Get a fresh token for each test run
    api_base_url = "http://localhost:8000"
    token = get_access_token(api_base_url)
    
    if not token:
        # If we can't get a token, register a new user and get a token
        register_data = {
            "email": "test_user@example.com",
            "password": "Password123!",
            "full_name": "Test User"
        }
        
        response = requests.post(
            f"{api_base_url}/api/auth/register",
            json=register_data
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token")
    
    return {
        "Authorization": f"Bearer {token}" if token else ""
    } 