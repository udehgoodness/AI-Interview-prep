#!/usr/bin/env python3
"""
Consolidated test file for interview functionality.
"""

import os
import sys
import json
import pytest
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_interview_questions(api_base_url, auth_headers, model="openai"):
    """Test the interview questions generation API with a specific model"""
    
    # Prepare the request payload
    payload = {
        "job_title": "Software Engineer",
        "job_description": "We are looking for a skilled software engineer with experience in Python and web development.",
        "interview_type": "technical",
        "duration": 30,
        "model": model
    }
    
    try:
        # Make the API request
        response = requests.post(
            f"{api_base_url}/api/interview/questions",
            json=payload,
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        
        result = response.json()
        assert "interview_id" in result, "Response does not contain 'interview_id' field"
        assert "questions" in result, "Response does not contain 'questions' field"
        
        questions = result["questions"]
        assert len(questions) > 0, "No questions were generated"
        
        logger.info(f"Generated {len(questions)} questions using {model} model")
        
        # Return the interview data for use in other tests
        return result
    except Exception as e:
        logger.error(f"Error in interview questions test with {model}: {str(e)}")
        return None

def test_interview_feedback(api_base_url, auth_headers, interview_data=None, model="openai"):
    """Test the interview feedback API with the specified model"""
    print(f"\n🧪 Testing: Interview Feedback API with {model.upper()} model")
    print("--------------------------------------------------")
    
    if not interview_data:
        logger.error("No interview data provided for feedback test")
        return None
    
    # Extract questions from the interview data
    questions = interview_data.get("questions", [])
    
    if not questions:
        logger.error("No questions found in interview data")
        return None
    
    # Create mock answers for each question
    answers = []
    for question in questions:
        answers.append({
            "question_id": question["id"],
            "answer": f"This is a test answer for the question about {question['question'][:30]}..."
        })
    
    # Prepare the request payload
    payload = {
        "interview_id": interview_data["interview_id"],
        "job_title": "Software Engineer",
        "questions": questions,
        "answers": answers,
        "model": model
    }
    
    try:
        # Make the API request
        response = requests.post(
            f"{api_base_url}/api/interview/feedback",
            json=payload,
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        
        result = response.json()
        assert "score" in result, "Response does not contain 'score' field"
        assert "feedback" in result, "Response does not contain 'feedback' field"
        assert "strengths" in result, "Response does not contain 'strengths' field"
        assert "weaknesses" in result, "Response does not contain 'weaknesses' field"
        
        logger.info(f"Received feedback with score {result['score']} using {model} model")
        
        return result
    except Exception as e:
        logger.error(f"Error in interview feedback test with {model}: {str(e)}")
        return None

def test_conversation_api(api_base_url, auth_headers, interview_data=None, model="openai"):
    """Test the conversation API with the specified model"""
    print(f"\n🧪 Testing: Conversation API with {model.upper()} model")
    print("--------------------------------------------------")
    
    if not interview_data:
        logger.error("No interview data provided for conversation test")
        return None
    
    # Extract questions from the interview data
    questions = interview_data.get("questions", [])
    
    if not questions:
        logger.error("No questions found in interview data")
        return None
    
    # Create a conversation history
    conversation_history = [
        {"role": "system", "content": "You are an AI interviewer."},
        {"role": "assistant", "content": questions[0]["question"]},
        {"role": "user", "content": "This is my answer to the first question."}
    ]
    
    # Prepare the request payload
    payload = {
        "job_title": "Software Engineer",
        "job_description": "We are looking for a skilled software engineer with experience in Python and web development.",
        "conversation_history": conversation_history,
        "current_question_index": 0,
        "model": model
    }
    
    try:
        # Make the API request
        response = requests.post(
            f"{api_base_url}/api/interview/conversation",
            json=payload,
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        
        result = response.json()
        assert "response" in result, "Response does not contain 'response' field"
        
        logger.info(f"Received conversation response using {model} model")
        
        return result
    except Exception as e:
        logger.error(f"Error in conversation test with {model}: {str(e)}")
        return None

@pytest.mark.parametrize("interview_type", ["technical", "behavioral", "case_study"])
def test_interview_types(api_base_url, auth_headers, interview_type):
    """Test different interview types"""
    
    # Prepare the request payload
    payload = {
        "job_title": "Product Manager",
        "job_description": "We are looking for a product manager with experience in agile methodologies.",
        "interview_type": interview_type,
        "duration": 30
    }
    
    try:
        # Make the API request
        response = requests.post(
            f"{api_base_url}/api/interview/questions",
            json=payload,
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        
        result = response.json()
        assert "interview_id" in result, "Response does not contain 'interview_id' field"
        assert "questions" in result, "Response does not contain 'questions' field"
        
        questions = result["questions"]
        assert len(questions) > 0, "No questions were generated"
        
        logger.info(f"Generated {len(questions)} questions for {interview_type} interview")
        
        return True
    except Exception as e:
        logger.error(f"Error in {interview_type} interview test: {str(e)}")
        return False

if __name__ == "__main__":
    # This allows running the test directly
    from conftest import api_base_url, auth_headers
    
    # Run the tests
    api_base = api_base_url()
    auth_hdrs = auth_headers()
    
    # Test with OpenAI model
    interview_data_openai = test_interview_questions(api_base, auth_hdrs, "openai")
    if interview_data_openai:
        feedback_result_openai = test_interview_feedback(api_base, auth_hdrs, interview_data_openai, "openai")
        conversation_result_openai = test_conversation_api(api_base, auth_hdrs, interview_data_openai, "openai")
    
    # Test with DeepSeek model
    interview_data_deepseek = test_interview_questions(api_base, auth_hdrs, "deepseek")
    if interview_data_deepseek:
        feedback_result_deepseek = test_interview_feedback(api_base, auth_hdrs, interview_data_deepseek, "deepseek")
        conversation_result_deepseek = test_conversation_api(api_base, auth_hdrs, interview_data_deepseek, "deepseek")
    
    # Test different interview types
    for interview_type in ["technical", "behavioral", "case_study"]:
        test_interview_types(api_base, auth_hdrs, interview_type) 