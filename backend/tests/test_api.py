#!/usr/bin/env python3
"""
Test script for API health check.
"""

import requests
import sys
import pytest

def test_api_health():
    """Test if the API health endpoint is responding."""
    try:
        response = requests.get("http://localhost:8000/api/health")
        assert response.status_code == 200, f"API health check failed with status {response.status_code}"
        print(f"API health check passed: {response.text}")
    except Exception as e:
        pytest.fail(f"API health check failed with error: {str(e)}")

if __name__ == "__main__":
    print("Testing API...")
    try:
        r = requests.get("http://localhost:8000/api/health")
        print(f"Status: {r.status_code}, Response: {r.text}")
        sys.exit(0 if r.status_code == 200 else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
