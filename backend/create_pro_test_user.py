#!/usr/bin/env python3
"""
Script to create a pro user for testing.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = os.environ.get('API_URL', 'http://localhost:8000')

def create_pro_user():
    """Create a pro user for testing"""
    # Try to login with pro test user
    login_data = {
        "username": "pro_user@example.com",
        "password": "Test1234!"
    }
    
    print("Trying to login with pro test user...")
    response = requests.post(
        f"{API_BASE_URL}/api/auth/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        print("✅ Pro test user already exists and login successful")
        token = response.json().get("access_token")
        
        # Check if user has pro plan
        print("Checking if user has pro plan...")
        user_response = requests.get(
            f"{API_BASE_URL}/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if user_response.status_code == 200:
            user_data = user_response.json()
            if user_data.get("subscription_plan") == "pro":
                print("✅ User already has pro plan")
                return token
            else:
                print("User does not have pro plan, upgrading...")
                upgrade_response = requests.post(
                    f"{API_BASE_URL}/api/subscriptions/upgrade/pro",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if upgrade_response.status_code == 200:
                    print("✅ User upgraded to pro plan")
                    return token
                else:
                    print(f"❌ Failed to upgrade user to pro plan: {upgrade_response.text}")
        else:
            print(f"❌ Failed to get user data: {user_response.text}")
    else:
        print(f"❌ Login failed: {response.text}")
        
        # Try to create a test user with the provided credentials
        print("Creating a new test user with the provided credentials...")
        register_data = {
            "email": "pro_user@example.com",
            "password": "Test1234!",
            "full_name": "Pro Test User"
        }
        
        register_response = requests.post(
            f"{API_BASE_URL}/api/auth/register",
            json=register_data
        )
        
        if register_response.status_code == 200:
            print("✅ Pro test user created successfully")
            # Try to login with the new user
            login_data = {
                "username": "pro_user@example.com",
                "password": "Test1234!"
            }
            
            response = requests.post(
                f"{API_BASE_URL}/api/auth/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                print("✅ Login successful")
                token = response.json().get("access_token")
                
                # Upgrade user to pro plan
                print("Upgrading user to pro plan...")
                upgrade_response = requests.post(
                    f"{API_BASE_URL}/api/subscriptions/upgrade/pro",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if upgrade_response.status_code == 200:
                    print("✅ User upgraded to pro plan")
                    return token
                else:
                    print(f"❌ Failed to upgrade user to pro plan: {upgrade_response.text}")
            else:
                print(f"❌ Failed to login after registration: {response.text}")
        else:
            print(f"❌ Failed to create pro test user: {register_response.text}")
    
    return None

if __name__ == "__main__":
    token = create_pro_user()
    
    if token:
        print(f"✅ Pro test user created/verified successfully")
        print(f"Access token: {token}")
        sys.exit(0)
    else:
        print("❌ Failed to create/verify pro test user")
        sys.exit(1) 