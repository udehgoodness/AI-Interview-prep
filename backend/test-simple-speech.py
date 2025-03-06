#!/usr/bin/env python3
import os
import sys
import json
import base64
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API URL
API_URL = "http://localhost:8000"

def get_auth_token():
    """Get authentication token"""
    try:
        auth_url = f"{API_URL}/api/auth/token"
        auth_data = {
            "username": "pro_user@example.com",
            "password": "Test1234!"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(auth_url, data=auth_data, headers=headers)
        response.raise_for_status()
        
        token_data = response.json()
        logger.info(f"Successfully authenticated as {auth_data['username']}")
        return token_data["access_token"]
    except Exception as e:
        logger.error(f"Error getting auth token: {str(e)}")
        return None

def test_speech_to_text(token):
    """Test the speech-to-text API"""
    try:
        # Check if test audio file exists
        audio_file = "test_conversation_audio.mp3"
        if not os.path.exists(audio_file):
            logger.error(f"No test audio file found at {audio_file}")
            return False
        
        # Read audio file
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Log audio info
        logger.info(f"Audio file size: {len(audio_bytes) / 1024:.2f} KB")
        logger.info(f"Audio file first 20 bytes: {audio_bytes[:20]}")
        logger.info(f"Base64 audio length: {len(audio_base64)}")
        logger.info(f"Base64 audio first 50 chars: {audio_base64[:50]}")
        
        # Prepare request
        url = f"{API_URL}/api/test-speech-to-text"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "audio": audio_base64,
            "language": "en"
        }
        
        # Send request
        logger.info("Sending request...")
        logger.info(f"Request URL: {url}")
        logger.info(f"Request headers: {headers}")
        logger.info(f"Request payload length: {len(json.dumps(payload))}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        # Log response
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        logger.info(f"Response text: {response.text}")
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Speech transcribed to text: {result['text']}")
            return True
        else:
            logger.error(f"Error: {response.status_code} {response.reason}")
            return False
    except Exception as e:
        logger.error(f"Error in test_speech_to_text: {str(e)}")
        return False

def main():
    """Run the test"""
    logger.info(f"Running test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        logger.error("Failed to get authentication token. Cannot proceed with tests.")
        return False
    
    logger.info("Successfully authenticated")
    
    # Test speech-to-text
    result = test_speech_to_text(token)
    
    if result:
        logger.info("Speech-to-text test passed!")
    else:
        logger.error("Speech-to-text test failed!")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 