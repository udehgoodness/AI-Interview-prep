#!/usr/bin/env python3
"""
Test script for the audio API to verify text-to-speech functionality.
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

def test_text_to_speech(token):
    """Test the text-to-speech API"""
    print("\n🧪 Testing: Text-to-Speech API")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "text": "Hello, this is a test of the text to speech API for the AI Interview Prep platform.",
        "voice": "alloy"  # Using OpenAI's alloy voice
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/text-to-speech",
            headers=headers,
            json=payload
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Save the audio to a file
        output_file = "test_tts_output.mp3"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Success! Audio generated and saved to {output_file}")
        print(f"   File size: {len(response.content) / 1024:.2f} KB")
        return True
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def run_all_tests():
    """Run all test cases"""
    print(f"Running tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 Starting Audio API Tests")
    print("==================================================")
    
    # Get authentication token for pro user
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Cannot proceed with tests.")
        sys.exit(1)
    
    print("✅ Successfully authenticated as pro_user@example.com")
    
    # Run the text-to-speech test
    if test_text_to_speech(token):
        print("\n==================================================")
        print("✅ Text-to-speech API test passed!")
        print("   Audio file saved to test_tts_output.mp3")
        return 0
    else:
        print("\n==================================================")
        print("❌ Text-to-speech API test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests()) 