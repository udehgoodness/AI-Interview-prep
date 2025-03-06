#!/usr/bin/env python3
"""
Comprehensive test script for all APIs with both OpenAI and DeepSeek models.
"""

import os
import sys
import json
import base64
import requests
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        logger.error(f"❌ Error getting auth token: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response: {e.response.text}")
        return None

def test_interview_questions(token, model="openai"):
    """Test the interview questions API with the specified model"""
    print(f"\n🧪 Testing: Interview Questions API with {model.upper()} model")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Test data
    data = {
        "job_title": "Senior DevSecOps Engineer",
        "job_description": "We are looking for a Senior DevSecOps Engineer to join our team. The ideal candidate will have experience with CI/CD pipelines, infrastructure as code, and security best practices.",
        "interview_type": "technical",
        "duration": 5,
        "model": model  # Specify the model to use
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/interview/questions",
            headers=headers,
            json=data
        )
        
        print(f"Response status code: {response.status_code}")
        
        try:
            print(f"Response body: {response.text[:200]}...")
        except:
            print("Could not print response body")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        print(f"\n✅ Success! Generated {len(result.get('questions', []))} questions")
        print(f"   Interview ID: {result.get('interview_id', 'N/A')}")
        
        # Print a few sample questions
        questions = result.get('questions', [])
        if questions:
            print("\n📝 Sample questions:")
            for i, q in enumerate(questions[:3]):
                print(f"   {i+1}. {q.get('id', 'N/A')}: {q.get('question', 'N/A')}")
            if len(questions) > 3:
                print(f"   ... and {len(questions) - 3} more")
        
        # Return the interview ID and questions for use in other tests
        return {
            "interview_id": result.get('interview_id'),
            "questions": result.get('questions', [])
        }
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return None

def test_interview_feedback(token, interview_data, model="openai"):
    """Test the interview feedback API with the specified model"""
    print(f"\n🧪 Testing: Interview Feedback API with {model.upper()} model")
    print("--------------------------------------------------")
    
    if not interview_data or not interview_data.get('questions'):
        print("❌ No interview data available for feedback test")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Test data
    data = {
        "interview_id": interview_data.get('interview_id', 'test-id'),
        "job_title": "Senior DevSecOps Engineer",
        "questions": interview_data.get('questions', []),
        "answers": [
            {
                "question_id": q.get('id'),
                "answer": f"This is a detailed answer to the question about {q.get('question', '').split(' ')[-3:]}. I have extensive experience in this area and have implemented similar solutions in my previous roles."
            }
            for q in interview_data.get('questions', [])[:3]  # Use first 3 questions
        ]
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/interview/feedback",
            headers=headers,
            json=data
        )
        
        print(f"Response status code: {response.status_code}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        print("\n✅ Success! Interview feedback received:")
        print(f"Score: {result.get('score', 'N/A')}/100")
        print("\nFeedback:")
        print(result.get('feedback', 'No feedback provided'))
        
        print("\nStrengths:")
        for strength in result.get('strengths', []):
            print(f"- {strength}")
        
        print("\nWeaknesses:")
        for weakness in result.get('weaknesses', []):
            print(f"- {weakness}")
        
        print("\nImprovement Areas:")
        for area in result.get('improvement_areas', []):
            print(f"- {area}")
        
        return result
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return None

def test_text_to_speech(token, model="openai"):
    """Test the text-to-speech API with the specified model"""
    print(f"\n🧪 Testing: Text-to-Speech API with {model.upper()} model")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Test data
    data = {
        "text": f"Hello, this is a test of the text to speech API using the {model} model.",
        "voice": "alloy",
        "model": model  # Specify the model to use
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/text-to-speech",
            headers=headers,
            json=data
        )
        
        print(f"Response status code: {response.status_code}")
        
        try:
            print(f"Response headers: {response.headers}")
            if response.status_code != 200:
                print(f"Response body: {response.text}")
        except:
            print("Could not print response details")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Check if the audio data is present
        if "audio" in result and result["audio"].startswith("data:audio/mp3;base64,"):
            print("\n✅ Success! Received audio data")
            audio_size = len(result["audio"]) / 1024
            print(f"   Audio data size: {audio_size:.2f} KB")
            
            # Save the audio to a file for testing
            audio_data = result["audio"].split(",")[1]
            audio_bytes = base64.b64decode(audio_data)
            
            filename = f"test_tts_output_{model}.mp3"
            with open(filename, "wb") as f:
                f.write(audio_bytes)
            
            print(f"   Saved audio to {filename}")
            return True
        else:
            print("❌ No audio data received in the response")
            return False
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def test_speech_to_text(token, model="openai"):
    """Test the speech-to-text API with the specified model"""
    print(f"\n🧪 Testing: Speech-to-Text API with {model.upper()} model")
    print("--------------------------------------------------")
    
    # Check if we have a test audio file
    test_audio_file = "test_audio.wav"
    if not os.path.exists(test_audio_file):
        print(f"❌ Test audio file {test_audio_file} not found")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Read the audio file and encode it as base64
    with open(test_audio_file, "rb") as f:
        audio_bytes = f.read()
    
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    # Test data
    data = {
        "audio": audio_base64,
        "language": "en",
        "model": model  # Specify the model to use
    }
    
    try:
        print("Sending request...")
        print(f"Audio data size: {len(audio_bytes) / 1024:.2f} KB")
        
        response = requests.post(
            f"{API_BASE_URL}/api/speech-to-text",
            headers=headers,
            json=data
        )
        
        print(f"Response status code: {response.status_code}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Check if the text data is present
        if "text" in result:
            print("\n✅ Success! Received transcribed text:")
            print(f"   {result['text']}")
            return True
        else:
            print("❌ No text data received in the response")
            return False
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def test_conversation_api(token, interview_data, model="openai"):
    """Test the conversation API with the specified model"""
    print(f"\n🧪 Testing: Conversation API with {model.upper()} model")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Test data
    data = {
        "job_title": "Senior DevSecOps Engineer",
        "job_description": "We are looking for a Senior DevSecOps Engineer to join our team. The ideal candidate will have experience with CI/CD pipelines, infrastructure as code, and security best practices.",
        "conversation_history": [
            {
                "role": "assistant",
                "content": "Hello! I'm your AI interviewer today. Could you tell me about your experience with DevSecOps practices?"
            },
            {
                "role": "user",
                "content": "I have 5 years of experience implementing DevSecOps practices in cloud environments. I've worked with AWS, Azure, and GCP, and have implemented CI/CD pipelines using Jenkins, GitHub Actions, and GitLab CI."
            }
        ],
        "current_question_index": 0,
        "time_up": False,
        "time_running_low": False,
        "no_response_detected": False,
        "is_code_submission": False,
        "question_type": "technical",
        "include_follow_up": True,
        "model": model  # Specify the model to use
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/interview/conversation",
            headers=headers,
            json=data
        )
        
        print(f"Response status code: {response.status_code}")
        
        try:
            print(f"Response headers: {response.headers}")
            if response.status_code != 200:
                print(f"Response body: {response.text}")
        except:
            print("Could not print response details")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Check if the response data is present
        if "response" in result:
            print("\n✅ Success! Received conversation response:")
            print(f"   {result['response'][:150]}...")
            
            # Check if audio data is present
            if "audio" in result and result["audio"].startswith("data:audio/mp3;base64,"):
                print("   Audio data received")
                audio_size = len(result["audio"]) / 1024
                print(f"   Audio data size: {audio_size:.2f} KB")
                
                # Save the audio to a file for testing
                audio_data = result["audio"].split(",")[1]
                audio_bytes = base64.b64decode(audio_data)
                
                filename = f"test_conversation_audio_{model}.mp3"
                with open(filename, "wb") as f:
                    f.write(audio_bytes)
                
                print(f"   Saved audio to {filename}")
            
            return True
        else:
            print("❌ No response data received")
            return False
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def run_all_tests():
    """Run all API tests with both OpenAI and DeepSeek models"""
    print(f"Running tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("==================================================")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Cannot proceed with tests.")
        return False
    
    print("✅ Successfully authenticated")
    
    # Test results tracking
    results = {
        "openai": {
            "interview_questions": False,
            "interview_feedback": False,
            "text_to_speech": False,
            "speech_to_text": False,
            "conversation": False
        },
        "deepseek": {
            "interview_questions": False,
            "interview_feedback": False,
            "text_to_speech": False,
            "speech_to_text": False,
            "conversation": False
        }
    }
    
    # Test with OpenAI model
    print("\n🔍 Testing APIs with OpenAI model")
    print("==================================================")
    
    # Test interview questions API
    interview_data_openai = test_interview_questions(token, "openai")
    results["openai"]["interview_questions"] = bool(interview_data_openai)
    
    # Test interview feedback API
    if interview_data_openai:
        feedback_result_openai = test_interview_feedback(token, interview_data_openai, "openai")
        results["openai"]["interview_feedback"] = bool(feedback_result_openai)
    
    # Test text-to-speech API
    results["openai"]["text_to_speech"] = test_text_to_speech(token, "openai")
    
    # Test speech-to-text API
    results["openai"]["speech_to_text"] = test_speech_to_text(token, "openai")
    
    # Test conversation API
    results["openai"]["conversation"] = test_conversation_api(token, interview_data_openai, "openai")
    
    # Test with DeepSeek model
    print("\n🔍 Testing APIs with DeepSeek model")
    print("==================================================")
    
    # Test interview questions API
    interview_data_deepseek = test_interview_questions(token, "deepseek")
    results["deepseek"]["interview_questions"] = bool(interview_data_deepseek)
    
    # Test interview feedback API
    if interview_data_deepseek:
        feedback_result_deepseek = test_interview_feedback(token, interview_data_deepseek, "deepseek")
        results["deepseek"]["interview_feedback"] = bool(feedback_result_deepseek)
    
    # Test text-to-speech API
    results["deepseek"]["text_to_speech"] = test_text_to_speech(token, "deepseek")
    
    # Test speech-to-text API
    results["deepseek"]["speech_to_text"] = test_speech_to_text(token, "deepseek")
    
    # Test conversation API
    results["deepseek"]["conversation"] = test_conversation_api(token, interview_data_deepseek, "deepseek")
    
    # Print summary
    print("\n📊 Test Results Summary")
    print("==================================================")
    print("OpenAI Model:")
    for api, result in results["openai"].items():
        print(f"   {api.replace('_', ' ').title()}: {'✅ Passed' if result else '❌ Failed'}")
    
    print("\nDeepSeek Model:")
    for api, result in results["deepseek"].items():
        print(f"   {api.replace('_', ' ').title()}: {'✅ Passed' if result else '❌ Failed'}")
    
    # Overall result
    all_passed = all(all(api_results.values()) for api_results in results.values())
    if all_passed:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 