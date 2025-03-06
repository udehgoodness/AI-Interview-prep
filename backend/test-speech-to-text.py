#!/usr/bin/env python3
"""
Test script for the speech-to-text API.
"""

import requests
import json
import os
import sys
import base64
from datetime import datetime

# API configuration
API_BASE_URL = os.environ.get('API_URL', 'http://localhost:8000')

def get_auth_token():
    """Get authentication token for a pro user"""
    login_data = {
        "username": "pro_user@example.com",
        "password": "Test1234!"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/token", 
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        print(f"❌ Error getting auth token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def test_speech_to_text():
    """Test the speech-to-text API with a sample audio file"""
    print("\n🧪 Testing: Speech-to-Text API")
    print("--------------------------------------------------")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Cannot proceed with tests.")
        return False
    
    print("✅ Successfully authenticated as pro_user@example.com")
    
    # Check if we have a test audio file
    test_audio_file = "test_tts_output.mp3"
    if not os.path.exists(test_audio_file):
        print(f"❌ Error: No test audio file found at {test_audio_file}")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        # Read the audio file and convert to base64
        with open(test_audio_file, "rb") as f:
            audio_data = f.read()
        
        print(f"Audio file size: {len(audio_data) / 1024:.2f} KB")
        print(f"Audio file first 20 bytes: {audio_data[:20]}")
        
        # Convert to base64
        base64_audio = base64.b64encode(audio_data).decode("utf-8")
        print(f"Base64 audio length: {len(base64_audio)}")
        print(f"Base64 audio first 50 chars: {base64_audio[:50]}")
        
        # Create the payload
        payload = {
            "audio": base64_audio,  # No data URL prefix
            "language": "en"
        }
        
        print("Sending request...")
        print(f"Request URL: {API_BASE_URL}/api/speech-to-text")
        print(f"Request headers: {headers}")
        print(f"Request payload length: {len(json.dumps(payload))}")
        
        response = requests.post(
            f"{API_BASE_URL}/api/speech-to-text",
            headers=headers,
            json=payload
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        # Try to get the response text even if it's an error
        try:
            response_text = response.text
            print(f"Response text: {response_text[:500]}")
        except Exception as e:
            print(f"Error getting response text: {e}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Check if the response contains text
        if not data.get("text"):
            print("❌ Error: No text in response")
            return False
        
        print(f"✅ Success! Speech transcribed to text:")
        print(f"   Text: {data['text']}")
        return True
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

if __name__ == "__main__":
    print(f"Running test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = test_speech_to_text()
    if result:
        print("\n✅ Speech-to-text test passed!")
        sys.exit(0)
    else:
        print("\n❌ Speech-to-text test failed!")
        sys.exit(1) 