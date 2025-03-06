#!/usr/bin/env python3
"""
Test script for OpenAI's Whisper API.
This script tests if the audio file can be transcribed directly using the OpenAI API.
"""

import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

def test_whisper_api():
    """Test OpenAI's Whisper API with a sample audio file"""
    print("\n🧪 Testing: OpenAI Whisper API")
    print("--------------------------------------------------")
    
    # Check if we have a test audio file
    test_audio_file = "test_tts_output.mp3"
    if not os.path.exists(test_audio_file):
        print(f"❌ Error: No test audio file found at {test_audio_file}")
        return False
    
    try:
        # Get file size
        file_size = os.path.getsize(test_audio_file)
        print(f"Audio file size: {file_size / 1024:.2f} KB")
        
        # Open the audio file
        with open(test_audio_file, "rb") as audio_file:
            # Read the first 20 bytes for debugging
            audio_file.seek(0)
            first_bytes = audio_file.read(20)
            print(f"Audio file first 20 bytes: {first_bytes}")
            
            # Reset file pointer
            audio_file.seek(0)
            
            print("Sending request to OpenAI Whisper API...")
            
            # Transcribe the audio using OpenAI's Whisper API
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        
        print(f"✅ Success! Speech transcribed to text:")
        print(f"   Text: {transcript.text}")
        return True
            
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI Whisper API directly")
    result = test_whisper_api()
    if result:
        print("\n✅ OpenAI Whisper API test passed!")
        sys.exit(0)
    else:
        print("\n❌ OpenAI Whisper API test failed!")
        sys.exit(1) 