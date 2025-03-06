"""
Tests for the interview generation functionality.
"""
import requests
import json
import pytest
import time

def test_general_interview(api_base_url, auth_headers):
    """Test generating questions for a general interview"""
    data = {
        "job_title": "Software Engineer",
        "job_description": "We are looking for a software engineer with 3+ years of experience in JavaScript, React, and Node.js.",
        "interview_type": "general",
        "duration": 30,
        "cv_text": "Experienced software engineer with 5 years of experience in web development using JavaScript, React, and Node.js."
    }
    
    response = requests.post(
        f"{api_base_url}/api/interview/questions", 
        json=data,
        headers=auth_headers
    )
    print(f"\nGeneral Interview: {response.status_code}")
    
    # For testing purposes, we'll skip the assertion if we get a 401 or 403
    # This allows the tests to run even without valid authentication
    if response.status_code in [401, 403]:
        pytest.skip("Authentication required for this endpoint")
    
    assert response.status_code == 200
    result = response.json()
    assert "interview_id" in result
    assert "questions" in result
    assert len(result["questions"]) > 0
    
    print(f"Interview ID: {result.get('interview_id')}")
    print(f"Number of questions: {len(result.get('questions', []))}")
    print("Sample questions:")
    for i, q in enumerate(result.get("questions", [])[:3]):
        question_text = q.get("text") or q.get("question")
        print(f"{i+1}. {question_text}")
    
    # Add a delay to avoid rate limiting
    time.sleep(2)

@pytest.mark.parametrize("interview_type", ["technical", "behavioral", "case_study"])
def test_interview_types(api_base_url, auth_headers, interview_type):
    """Test generating questions for different interview types"""
    data = {
        "job_title": "Product Manager",
        "job_description": "Looking for a product manager to lead our product development team.",
        "interview_type": interview_type,
        "duration": 30,
        "cv_text": "Product manager with 5 years of experience in agile methodologies."
    }
    
    response = requests.post(
        f"{api_base_url}/api/interview/questions", 
        json=data,
        headers=auth_headers
    )
    print(f"\n{interview_type.capitalize()} Interview: {response.status_code}")
    
    # For testing purposes, we'll skip the assertion if we get a 401 or 403
    # This allows the tests to run even without valid authentication
    if response.status_code in [401, 403]:
        pytest.skip("Authentication required for this endpoint")
    
    assert response.status_code == 200
    result = response.json()
    assert "interview_id" in result
    assert "questions" in result
    assert len(result["questions"]) > 0
    
    print(f"Interview ID: {result.get('interview_id')}")
    print(f"Number of questions: {len(result.get('questions', []))}")
    print("Sample questions:")
    for i, q in enumerate(result.get("questions", [])[:2]):
        question_text = q.get("text") or q.get("question")
        print(f"{i+1}. {question_text}")
    
    # Add a delay to avoid rate limiting
    time.sleep(2)

def test_interview_with_modes(api_base_url, auth_headers):
    """Test generating questions for an interview with different modes"""
    data = {
        "job_title": "Customer Service Representative",
        "job_description": "Looking for a customer service representative to handle customer inquiries.",
        "interview_type": "general",
        "duration": 30,
        "cv_text": "Customer service representative with experience in handling customer inquiries.",
        "useVoiceMode": True,
        "useVideoMode": True
    }
    
    response = requests.post(
        f"{api_base_url}/api/interview/questions", 
        json=data,
        headers=auth_headers
    )
    print(f"\nInterview with Voice & Video Mode: {response.status_code}")
    
    # For testing purposes, we'll skip the assertion if we get a 401 or 403
    # This allows the tests to run even without valid authentication
    if response.status_code in [401, 403]:
        pytest.skip("Authentication required for this endpoint")
    
    assert response.status_code == 200
    result = response.json()
    assert "interview_id" in result
    assert "questions" in result
    assert len(result["questions"]) > 0
    
    print(f"Interview ID: {result.get('interview_id')}")
    print(f"Number of questions: {len(result.get('questions', []))}")
    print("Sample questions:")
    for i, q in enumerate(result.get("questions", [])[:2]):
        question_text = q.get("text") or q.get("question")
        print(f"{i+1}. {question_text}")
    
    # Add a delay to avoid rate limiting
    time.sleep(2) 