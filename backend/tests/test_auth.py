import requests
import json
import sys
import os
from dotenv import load_dotenv

def get_access_token(api_base_url):
    """Get an access token for testing"""
    # Try to login with pro test user
    login_data = {
        "username": "pro_user@example.com",
        "password": "Test1234!"
    }
    
    response = requests.post(
        f"{api_base_url}/api/auth/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        # If login fails, try to create a pro test user
        register_data = {
            "email": "pro_user@example.com",
            "password": "Test1234!",
            "full_name": "Pro Test User"
        }
        
        register_response = requests.post(
            f"{api_base_url}/api/auth/register",
            json=register_data
        )
        
        if register_response.status_code == 200:
            # Try to login again
            response = requests.post(
                f"{api_base_url}/api/auth/token",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                # Upgrade user to pro plan
                token = response.json().get("access_token")
                
                # Make a request to upgrade the user to pro plan
                upgrade_response = requests.post(
                    f"{api_base_url}/api/subscriptions/upgrade/pro",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if upgrade_response.status_code == 200:
                    return token
    
    return None

def check_jwt_secret():
    """Check if the JWT secret key is properly set"""
    # Load environment variables
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    
    # Check JWT secret key
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if jwt_secret == "your_jwt_secret_key_here":
        print("WARNING: JWT_SECRET_KEY is set to the default value. Authentication will not work properly.")
        print("Please update the JWT_SECRET_KEY in the .env file with a proper secret key.")
        return False
    return True

if __name__ == "__main__":
    api_base_url = "http://localhost:8000"
    
    # Check JWT secret key
    if not check_jwt_secret():
        sys.exit(1)
    
    token = get_access_token(api_base_url)
    
    if token:
        print(f"Access token: {token}")
        sys.exit(0)
    else:
        print("Failed to get access token")
        sys.exit(1) 