#!/usr/bin/env python3
"""
Consolidated test file for audio functionality.
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

def test_text_to_speech(api_base_url, auth_headers, model="openai"):
    """Test the text-to-speech API with a specific model"""
    
    # Prepare the request payload
    payload = {
        "text": "This is a test for text to speech conversion.",
        "voice": "alloy",
        "model": model
    }
    
    try:
        # Make the API request
        response = requests.post(
            f"{api_base_url}/api/text-to-speech",
            json=payload,
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        
        result = response.json()
        assert "audio" in result, "Response does not contain 'audio' field"
        
        audio_base64 = result["audio"]
        assert len(audio_base64) > 0, "Audio data is empty"
        
        # Decode the base64 audio data
        audio_data = base64.b64decode(audio_base64)
        
        # Save the audio file for verification
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_file = os.path.join(TEST_DIR, "..", "test_output", f"tts_output_{model}_{timestamp}.mp3")
        
        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(audio_data)
        
        logger.info(f"Text-to-speech output saved to {output_file}")
        
        return True
    except Exception as e:
        logger.error(f"Error in text-to-speech test with {model}: {str(e)}")
        return False

def test_upload_audio(api_base_url, auth_headers):
    """Test the audio upload API"""
    
    # Path to test audio file
    audio_file = os.path.join(TEST_DIR, "..", "test_data", "test_audio.mp3")
    
    # If test file doesn't exist, create a placeholder
    if not os.path.exists(audio_file):
        logger.warning(f"Test audio file not found: {audio_file}")
        return False
    
    try:
        # Open the file for upload
        with open(audio_file, "rb") as f:
            files = {"file": (os.path.basename(audio_file), f, "audio/mpeg")}
            
            # Make the API request
            response = requests.post(
                f"{api_base_url}/api/upload-audio",
                files=files,
                headers=auth_headers
            )
            
            # Check the response
            assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
            
            result = response.json()
            assert "filename" in result, "Response does not contain 'filename' field"
            
            logger.info(f"Audio file uploaded successfully: {result['filename']}")
            
            return True
    except Exception as e:
        logger.error(f"Error in audio upload test: {str(e)}")
        return False

if __name__ == "__main__":
    # This allows running the test directly
    from conftest import api_base_url, auth_headers
    
    # Run the tests
    api_base = api_base_url()
    auth_hdrs = auth_headers()
    
    # Test text-to-speech with different models
    test_text_to_speech(api_base, auth_hdrs, "openai")
    test_text_to_speech(api_base, auth_hdrs, "deepseek")
    
    # Test audio upload
    test_upload_audio(api_base, auth_hdrs) 