import requests
import base64
import json
import os
import time
import pytest

# Base URL for the API (will be overridden by the fixture)
BASE_URL = "http://localhost:8000"

# Directory for test output files
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

def test_health(api_base_url):
    """Test the health endpoint"""
    response = requests.get(f"{api_base_url}/api/health")
    print(f"Health check: {response.status_code}")
    assert response.status_code == 200
    print("Health check passed!")

def test_text_to_speech(api_base_url):
    """Test the text-to-speech endpoint"""
    print("\nTesting text-to-speech...")
    
    payload = {
        "text": "Hello, this is a test of the text to speech API.",
        "voice": "alloy"
    }
    
    response = requests.post(
        f"{api_base_url}/api/text-to-speech",
        json=payload
    )
    
    assert response.status_code == 200
    assert response.content, "Response content should not be empty"
    
    # Save the audio to a file for testing
    output_file = os.path.join(TEST_DIR, "test_tts_output.mp3")
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Text-to-speech test passed! Audio saved to {output_file}")
    
    # Check that the file was created and has content
    assert os.path.exists(output_file), f"Output file {output_file} should exist"
    assert os.path.getsize(output_file) > 0, f"Output file {output_file} should not be empty"

def test_speech_to_text(api_base_url):
    """Test the speech-to-text endpoint with a sample audio file"""
    print("\nTesting speech-to-text...")
    
    # Check if we have a test audio file from the TTS test
    test_audio_file = os.path.join(TEST_DIR, "test_tts_output.mp3")
    if not os.path.exists(test_audio_file):
        pytest.skip("No test audio file found. Skipping speech-to-text test.")
    
    # Read the audio file and convert to base64
    with open(test_audio_file, "rb") as f:
        audio_data = f.read()
    
    base64_audio = base64.b64encode(audio_data).decode("utf-8")
    
    payload = {
        "audio": base64_audio,
        "language": "en"
    }
    
    response = requests.post(
        f"{api_base_url}/api/speech-to-text",
        json=payload
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "text" in result, "Response should contain 'text' field"
    print(f"Speech-to-text result: {result['text']}")
    print("Speech-to-text test passed!")

def test_conversation(api_base_url):
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
        f"{api_base_url}/api/interview/conversation",
        json=payload
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "text" in result, "Response should contain 'text' field"
    print(f"Conversation response text: {result['text']}")
    print(f"Audio response included: {'Yes' if 'audio' in result and result['audio'] else 'No'}")
    
    # Save the audio to a file if it exists
    if 'audio' in result and result['audio']:
        audio_data = base64.b64decode(result['audio'])
        output_file = os.path.join(TEST_DIR, "test_conversation_audio.mp3")
        with open(output_file, "wb") as f:
            f.write(audio_data)
        print(f"Conversation audio saved to {output_file}")
        
        # Check that the file was created and has content
        assert os.path.exists(output_file), f"Output file {output_file} should exist"
        assert os.path.getsize(output_file) > 0, f"Output file {output_file} should not be empty"
    
    print("Conversation test passed!")

@pytest.mark.skip(reason="This is a manual test function, not a pytest test")
def run_all_tests():
    """Run all tests and report results"""
    print("Starting API tests for audio conversation functionality...")
    
    # First check if the server is running
    try:
        test_health(BASE_URL)
    except Exception as e:
        print(f"Server health check failed. Make sure the server is running. Error: {str(e)}")
        return
    
    # Run the tests
    tests = [
        ("Text-to-Speech", lambda: test_text_to_speech(BASE_URL)),
        ("Speech-to-Text", lambda: test_speech_to_text(BASE_URL)),
        ("Conversation", lambda: test_conversation(BASE_URL))
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {name} test...")
        try:
            test_func()
            results.append((name, True))
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