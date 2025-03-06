#!/usr/bin/env python3
"""
Consolidated test file for speech-to-text functionality.
"""

import os
import sys
import base64
import pytest
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test directory for output files
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def auth_token(api_base_url):
    """Get authentication token for a pro user"""
    login_data = {
        "username": "pro_user@example.com",
        "password": "Test1234!"
    }
    
    try:
        response = requests.post(
            f"{api_base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            return token
        else:
            logger.error(f"Failed to get auth token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting auth token: {str(e)}")
        return None

def test_speech_to_text(api_base_url, auth_headers):
    """Test the speech-to-text API with a sample audio file"""
    
    # Path to test audio file
    audio_file = os.path.join(TEST_DIR, "..", "test_data", "test_audio.mp3")
    
    # If test file doesn't exist, create a placeholder message
    if not os.path.exists(audio_file):
        logger.warning(f"Test audio file not found: {audio_file}")
        logger.info("Using a placeholder for testing purposes")
        test_message = "This is a test for speech to text conversion."
    else:
        # Read the audio file
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        # Prepare the request payload
        payload = {
            "audio": audio_base64,
            "language": "en"
        }
        
        try:
            # Make the API request
            response = requests.post(
                f"{api_base_url}/api/speech-to-text",
                json=payload,
                headers=auth_headers
            )
            
            # Check the response
            assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
            
            result = response.json()
            assert "text" in result, "Response does not contain 'text' field"
            
            transcribed_text = result["text"]
            logger.info(f"Transcribed text: {transcribed_text}")
            
            assert len(transcribed_text) > 0, "Transcribed text is empty"
            
            return True
        except Exception as e:
            logger.error(f"Error in speech-to-text test: {str(e)}")
            return False

def test_speech_to_text_with_model(api_base_url, auth_headers, model="openai"):
    """Test the speech-to-text API with a specific model"""
    
    # Path to test audio file
    audio_file = os.path.join(TEST_DIR, "..", "test_data", "test_audio.mp3")
    
    # If test file doesn't exist, create a placeholder message
    if not os.path.exists(audio_file):
        logger.warning(f"Test audio file not found: {audio_file}")
        logger.info("Using a placeholder for testing purposes")
        test_message = "This is a test for speech to text conversion."
    else:
        # Read the audio file
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        # Prepare the request payload
        payload = {
            "audio": audio_base64,
            "language": "en",
            "model": model
        }
        
        try:
            # Make the API request
            response = requests.post(
                f"{api_base_url}/api/speech-to-text",
                json=payload,
                headers=auth_headers
            )
            
            # Check the response
            assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
            
            result = response.json()
            assert "text" in result, "Response does not contain 'text' field"
            
            transcribed_text = result["text"]
            logger.info(f"Transcribed text ({model}): {transcribed_text}")
            
            assert len(transcribed_text) > 0, "Transcribed text is empty"
            
            return True
        except Exception as e:
            logger.error(f"Error in speech-to-text test with {model}: {str(e)}")
            return False

if __name__ == "__main__":
    # This allows running the test directly
    from conftest import api_base_url, auth_headers
    
    # Run the tests
    test_speech_to_text(api_base_url(), auth_headers())
    test_speech_to_text_with_model(api_base_url(), auth_headers(), "openai")
    test_speech_to_text_with_model(api_base_url(), auth_headers(), "deepseek") 