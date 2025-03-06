#!/usr/bin/env python3
"""
Test script for the interview API to verify question generation.
"""

import requests
import json
import os
import sys
from datetime import datetime

# API configuration
API_BASE_URL = os.environ.get('API_URL', 'http://localhost:8000')

# Test data for different interview types
TEST_CASES = [
    {
        "name": "General Interview",
        "data": {
            "job_title": "Software Engineer",
            "job_description": "We are looking for a software engineer with 3+ years of experience in JavaScript, React, and Node.js.",
            "interview_type": "general",
            "duration": 30,
            "cv_text": "Experienced software engineer with 5 years of experience in web development using JavaScript, React, and Node.js."
        }
    },
    {
        "name": "Technical Interview",
        "data": {
            "job_title": "Senior Frontend Developer",
            "job_description": "Looking for a senior frontend developer with expertise in React, TypeScript, and modern web technologies.",
            "interview_type": "technical",
            "duration": 45,
            "cv_text": "Senior developer with 7 years of experience in frontend development, specializing in React, TypeScript, and Redux."
        }
    },
    {
        "name": "Behavioral Interview",
        "data": {
            "job_title": "Product Manager",
            "job_description": "Seeking a product manager to lead our product development team and drive product strategy.",
            "interview_type": "behavioral",
            "duration": 30,
            "cv_text": "Product manager with experience in agile methodologies, user research, and product roadmap development."
        }
    },
    {
        "name": "Case Study Interview",
        "data": {
            "job_title": "Business Analyst",
            "job_description": "We need a business analyst to help identify business needs and recommend solutions.",
            "interview_type": "case_study",
            "duration": 45,
            "cv_text": "Business analyst with experience in requirements gathering, process improvement, and data analysis."
        }
    }
]

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

def test_interview_generation(test_case, token):
    """Test the interview generation API with the given test case"""
    print(f"\n🧪 Testing: {test_case['name']}")
    print("--------------------------------------------------")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        print("Sending request...")
        response = requests.post(
            f"{API_BASE_URL}/api/interview/questions",
            headers=headers,
            json=test_case["data"]
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Check if the response contains the expected fields
        if "interview_id" in result and "questions" in result:
            print(f"✅ Success! Generated {len(result['questions'])} questions")
            print(f"   Interview ID: {result['interview_id']}")
            
            # Print a sample of questions
            if result["questions"]:
                print("\n📝 Sample questions:")
                for i, q in enumerate(result["questions"][:3], 1):
                    print(f"   {i}. {q['question']}")
                if len(result["questions"]) > 3:
                    print(f"   ... and {len(result['questions']) - 3} more")
            
            return True
        else:
            print("❌ Error: Response missing expected fields")
            print(f"   Response: {json.dumps(result, indent=2)}")
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
    """Run all test cases"""
    print(f"Running tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 Starting Interview Generation Tests")
    print("==================================================")
    
    # Get authentication token for pro user
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token. Cannot proceed with tests.")
        sys.exit(1)
    
    print("✅ Successfully authenticated as pro_user@example.com")
    
    # Run each test case
    passed = 0
    for test_case in TEST_CASES:
        if test_interview_generation(test_case, token):
            passed += 1
    
    # Print summary
    print("\n==================================================")
    print(f"📊 Test Results: {passed}/{len(TEST_CASES)} tests passed")
    
    if passed == len(TEST_CASES):
        print("✅ All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests()) 