#!/usr/bin/env python3
"""
Test script for the interview feedback API.
"""

import os
import sys
import json
import requests
import logging
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

def test_interview_feedback(token):
    """Test the interview feedback API"""
    print("\n🧪 Testing: Interview Feedback API")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Test data
    data = {
        "interview_id": "test-feedback-id",
        "job_title": "Senior DevSecOps Engineer",
        "questions": [
            {
                "id": "q1",
                "question": "Can you explain the principle of 'Shift Left' in DevSecOps and how you would implement it in a CI/CD pipeline?",
                "type": "technical",
                "difficulty": "intermediate",
                "expected_answer_points": [
                    "Early integration of security practices",
                    "Automated security scanning",
                    "Pre-commit hooks",
                    "CI/CD pipeline integration"
                ]
            }
        ],
        "answers": [
            {
                "question_id": "q1",
                "answer": "Shift Left in DevSecOps means integrating security practices early in the development lifecycle rather than treating it as an afterthought. I would implement this by adding automated security scanning in the CI pipeline, including SAST tools like SonarQube for code analysis, dependency scanning with tools like Snyk, and container image scanning. I would also implement pre-commit hooks for basic security checks and automate security testing as part of the pipeline."
            }
        ]
    }
    
    try:
        print("Sending request...")
        print(f"Request data: {json.dumps(data, indent=2)}")
        response = requests.post(
            f"{API_BASE_URL}/api/interview/feedback",
            headers=headers,
            json=data
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        try:
            print(f"Response body: {response.text}")
        except:
            print("Could not print response body")
        
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
        
        return True
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error:\n   {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error:\n   {e}")
        return False

def main():
    """Run the test"""
    print(f"Running test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Cannot proceed with tests.")
        return False
    
    print("✅ Successfully authenticated")
    
    # Test interview feedback
    result = test_interview_feedback(token)
    
    if result:
        print("\n✅ Interview feedback test passed!")
    else:
        print("\n❌ Interview feedback test failed!")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 