#!/usr/bin/env python3
"""
Test script for the conversation API with voice mode.
This script tests the full voice interview flow:
1. Text-to-speech: Converting AI messages to speech
2. Speech-to-text: Converting user speech to text
3. Conversation: Handling the back-and-forth between user and AI
"""

import requests
import json
import os
import sys
import base64
from datetime import datetime
import time

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
        
        # Parse the response
        data = response.json()
        
        # Check if the response contains audio data
        if not data.get("audio"):
            print("❌ Error: No audio data in response")
            return False
        
        # Save the audio to a file
        audio_data = data["audio"].split(',')[1]  # Remove the data URL prefix
        audio_bytes = base64.b64decode(audio_data)
        
        output_file = "test_tts_output.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        
        print(f"✅ Success! Audio generated and saved to {output_file}")
        print(f"   File size: {len(audio_bytes) / 1024:.2f} KB")
        return True
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def test_speech_to_text(token):
    """Test the speech-to-text API with the audio file generated from text-to-speech"""
    print("\n🧪 Testing: Speech-to-Text API")
    print("--------------------------------------------------")
    
    # Check if we have a test audio file from the TTS test
    test_audio_file = "test_tts_output.mp3"
    if not os.path.exists(test_audio_file):
        print("❌ Error: No test audio file found. Run the text-to-speech test first.")
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
        
        base64_audio = base64.b64encode(audio_data).decode("utf-8")
        print(f"Base64 audio length: {len(base64_audio)}")
        print(f"Base64 audio first 50 chars: {base64_audio[:50]}")
        
        # Add the data URL prefix
        base64_audio_with_prefix = f"data:audio/mp3;base64,{base64_audio}"
        
        payload = {
            "audio": base64_audio_with_prefix,
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

def test_conversation_api(token):
    """Test the conversation API"""
    print("\n🧪 Testing: Conversation API")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Initial conversation history
    conversation_history = [
        {"role": "assistant", "content": "Hello! I'm your AI interviewer. Can you tell me about your experience with Python?"},
        {"role": "user", "content": "I've been using Python for about 5 years, mainly for web development with Django and data analysis with pandas."}
    ]
    
    payload = {
        "job_title": "Python Developer",
        "job_description": "We are looking for a Python developer with experience in web development and data analysis.",
        "conversation_history": conversation_history,
        "current_question_index": 0,
        "time_up": False,
        "time_running_low": False,
        "no_response_detected": False,
        "is_code_submission": False,
        "question_type": "general",
        "include_follow_up": True
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/interview/conversation",
            headers=headers,
            json=payload
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Check if the response contains text
        if not data.get("text"):
            print("❌ Error: No text in response")
            return False
        
        print(f"✅ Success! Conversation response:")
        print(f"   Text: {data['text'][:100]}...")
        
        # Check if the response contains audio
        if not data.get("audio"):
            print("⚠️ Warning: No audio in response")
        else:
            # Save the audio to a file
            audio_data = base64.b64decode(data["audio"])
            output_file = "test_conversation_audio.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"✅ Audio response saved to {output_file}")
            print(f"   File size: {len(audio_data) / 1024:.2f} KB")
        
        return True
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def test_full_voice_interview_flow(token):
    """Test the full voice interview flow"""
    print("\n🧪 Testing: Full Voice Interview Flow")
    print("--------------------------------------------------")
    
    # Step 1: Get an initial question from the conversation API
    print("Step 1: Getting initial question...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Initial empty conversation history
    conversation_history = []
    
    payload = {
        "job_title": "Python Developer",
        "job_description": "We are looking for a Python developer with experience in web development and data analysis.",
        "conversation_history": conversation_history,
        "current_question_index": 0,
        "time_up": False,
        "time_running_low": False,
        "no_response_detected": False,
        "is_code_submission": False,
        "question_type": "general",
        "include_follow_up": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/interview/conversation",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get("text"):
            print("❌ Error: No text in response")
            return False
        
        initial_question = data["text"]
        print(f"✅ Initial question: {initial_question[:100]}...")
        
        # Add the question to the conversation history
        conversation_history.append({"role": "assistant", "content": initial_question})
        
        # Step 2: Simulate user response
        print("\nStep 2: Simulating user response...")
        user_response = "I have 5 years of experience with Python, primarily working with Django for web development and pandas for data analysis. I've also worked with Flask and FastAPI for building RESTful APIs."
        
        # Add the user response to the conversation history
        conversation_history.append({"role": "user", "content": user_response})
        
        # Step 3: Get AI response to the user's answer
        print("\nStep 3: Getting AI response...")
        payload["conversation_history"] = conversation_history
        
        response = requests.post(
            f"{API_BASE_URL}/api/interview/conversation",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get("text"):
            print("❌ Error: No text in response")
            return False
        
        ai_response = data["text"]
        print(f"✅ AI response: {ai_response[:100]}...")
        
        # Check if the response contains audio
        if not data.get("audio"):
            print("⚠️ Warning: No audio in response")
        else:
            # Save the audio to a file
            audio_data = base64.b64decode(data["audio"])
            output_file = "test_conversation_flow_audio.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"✅ Audio response saved to {output_file}")
            print(f"   File size: {len(audio_data) / 1024:.2f} KB")
        
        print("\n✅ Full voice interview flow test completed successfully!")
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
    print("🚀 Starting Conversation API Tests with Voice Mode")
    print("==================================================")
    
    # Get authentication token for pro user
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Cannot proceed with tests.")
        sys.exit(1)
    
    print("✅ Successfully authenticated as pro_user@example.com")
    
    # Run the text-to-speech test
    tts_success = test_text_to_speech(token)
    
    # Run the speech-to-text test
    stt_success = False
    if tts_success:
        stt_success = test_speech_to_text(token)
    else:
        print("⚠️ Skipping speech-to-text test because text-to-speech test failed")
    
    # Run the conversation API test
    conversation_success = test_conversation_api(token)
    
    # Run the full voice interview flow test
    flow_success = False
    if tts_success and conversation_success:
        flow_success = test_full_voice_interview_flow(token)
    else:
        print("⚠️ Skipping full voice interview flow test because prerequisite tests failed")
    
    # Print summary
    print("\n==================================================")
    print("📊 Test Summary:")
    print(f"   Text-to-Speech API: {'✅ Passed' if tts_success else '❌ Failed'}")
    print(f"   Speech-to-Text API: {'✅ Passed' if stt_success else '❌ Failed'}")
    print(f"   Conversation API: {'✅ Passed' if conversation_success else '❌ Failed'}")
    print(f"   Full Voice Interview Flow: {'✅ Passed' if flow_success else '❌ Failed'}")
    
    # Determine overall success
    if tts_success and stt_success and conversation_success and flow_success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests()) 