import requests
import json
import pytest

# Base URL for the API (will be overridden by the fixture)
BASE_URL = "http://localhost:8000"

def test_health(api_base_url):
    """Test the health check endpoint"""
    response = requests.get(f"{api_base_url}/api/health")
    print(f"Health check: {response.status_code}")
    print(response.json())
    print()
    assert response.status_code == 200

def test_generate_questions(api_base_url):
    """Test the generate questions endpoint"""
    data = {
        "job_title": "Software Engineer",
        "job_description": "We are looking for a skilled software engineer with experience in Python and React.",
        "interview_type": "technical",
        "duration": 30
    }
    
    response = requests.post(f"{api_base_url}/api/interview/questions", json=data)
    print(f"Generate questions: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Interview ID: {result.get('interview_id')}")
        print(f"Number of questions: {len(result.get('questions', []))}")
        print("First question:", json.dumps(result.get('questions', [])[0], indent=2) if result.get('questions') else "No questions")
    else:
        print(response.text)
    print()
    assert response.status_code == 200
    assert 'interview_id' in response.json()
    assert 'questions' in response.json()

def test_evaluate_interview(api_base_url):
    """Test the evaluate interview endpoint"""
    data = {
        "interview_id": "test-id",
        "answers": [
            {
                "question_id": "1",
                "question": "Tell me about your experience with Python.",
                "answer": "I have 5 years of experience with Python, working on web applications using Django and FastAPI."
            },
            {
                "question_id": "2",
                "question": "How would you handle a difficult team member?",
                "answer": "I would try to understand their perspective and work together to find a solution."
            }
        ]
    }
    
    response = requests.post(f"{api_base_url}/api/evaluate-interview", json=data)
    print(f"Evaluate interview: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(response.text)
    print()
    assert response.status_code == 200
    assert 'score' in response.json()
    assert 'feedback' in response.json()
    assert 'strengths' in response.json()
    assert 'improvement_areas' in response.json()

if __name__ == "__main__":
    print("Testing API endpoints...\n")
    
    try:
        test_health(BASE_URL)
        test_generate_questions(BASE_URL)
        test_evaluate_interview(BASE_URL)
        print("All tests completed.")
    except Exception as e:
        print(f"Error during testing: {str(e)}") 