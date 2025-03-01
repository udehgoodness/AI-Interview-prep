import requests
import base64
import json
import os
import time

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Health check: {response.status_code}")
    if response.status_code == 200:
        print("Health check passed!")
        return True
    else:
        print(f"Health check failed with status code: {response.status_code}")
        return False

def test_text_to_speech():
    """Test the text-to-speech endpoint"""
    print("\nTesting text-to-speech...")
    
    payload = {
        "text": "Hello, this is a test of the text to speech API.",
        "voice": "alloy"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/text-to-speech",
        json=payload
    )
    
    if response.status_code == 200:
        # Save the audio to a file for testing
        with open("test_tts_output.mp3", "wb") as f:
            f.write(response.content)
        print("Text-to-speech test passed! Audio saved to test_tts_output.mp3")
        return True
    else:
        print(f"Text-to-speech test failed with status code: {response.status_code}")
        if response.text:
            print(f"Error: {response.text}")
        return False

def test_speech_to_text():
    """Test the speech-to-text endpoint with a sample audio file"""
    print("\nTesting speech-to-text...")
    
    # Check if we have a test audio file from the TTS test
    if not os.path.exists("test_tts_output.mp3"):
        print("No test audio file found. Skipping speech-to-text test.")
        return False
    
    # Read the audio file and convert to base64
    with open("test_tts_output.mp3", "rb") as f:
        audio_data = f.read()
    
    base64_audio = base64.b64encode(audio_data).decode("utf-8")
    
    payload = {
        "audio": base64_audio,
        "language": "en"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/speech-to-text",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Speech-to-text result: {result['text']}")
        print("Speech-to-text test passed!")
        return True
    else:
        print(f"Speech-to-text test failed with status code: {response.status_code}")
        if response.text:
            print(f"Error: {response.text}")
        return False

def test_conversation():
    """Test the conversation endpoint"""
    print("\nTesting conversation endpoint...")
    
    conversation_history = [
        {"role": "assistant", "content": "Hello! I'm your AI interviewer. Can you tell me about your experience with Python?"},
        {"role": "user", "content": "I've been using Python for about 5 years, mainly for web development with Django and data analysis with pandas."}
    ]
    
    payload = {
        "job_title": "Python Developer",
        "job_description": "We are looking for a Python developer with experience in web development and data analysis.",
        "conversation_history": conversation_history,
        "current_question_index": 0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/interview/conversation",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Conversation response text: {result['text']}")
        print(f"Audio response included: {'Yes' if 'audio' in result and result['audio'] else 'No'}")
        
        # Save the audio to a file if it exists
        if 'audio' in result and result['audio']:
            audio_data = base64.b64decode(result['audio'])
            with open("test_conversation_audio.mp3", "wb") as f:
                f.write(audio_data)
            print("Conversation audio saved to test_conversation_audio.mp3")
        
        print("Conversation test passed!")
        return True
    else:
        print(f"Conversation test failed with status code: {response.status_code}")
        if response.text:
            print(f"Error: {response.text}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("Starting API tests for audio conversation functionality...")
    
    # First check if the server is running
    if not test_health():
        print("Server health check failed. Make sure the server is running.")
        return
    
    # Run the tests
    tests = [
        ("Text-to-Speech", test_text_to_speech),
        ("Speech-to-Text", test_speech_to_text),
        ("Conversation", test_conversation)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {name} test...")
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"Error during {name} test: {str(e)}")
            results.append((name, False))
    
    # Print summary
    print(f"\n{'='*50}")
    print("Test Summary:")
    all_passed = True
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"{name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed. Please check the logs above for details.")

if __name__ == "__main__":
    run_all_tests() 