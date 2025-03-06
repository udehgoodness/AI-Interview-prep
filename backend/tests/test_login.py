"""
Test script to debug the login process
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_login():
    """
    Test the login process
    """
    try:
        from app.services.auth import authenticate_user, get_password_hash, verify_password
        from app.database.db import execute_query
        
        # Test user credentials
        email = "pro_user@example.com"
        password = "password123"
        
        # Get the user from the database
        logger.info(f"Getting user with email: {email}")
        user = execute_query("SELECT * FROM users WHERE email = %s", (email,))
        
        if not user or len(user) == 0:
            logger.error(f"User with email {email} not found")
            return
        
        user = dict(user[0])
        logger.info(f"User found: {user['id']} - {user['email']}")
        
        # Test password verification
        hashed_password = user["password_hash"]
        logger.info(f"Hashed password: {hashed_password}")
        
        # Create a new hash for comparison
        new_hash = get_password_hash(password)
        logger.info(f"New hash: {new_hash}")
        
        # Verify the password
        try:
            is_valid = verify_password(password, hashed_password)
            logger.info(f"Password verification result: {is_valid}")
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
        
        # Test the authenticate_user function
        try:
            auth_result = authenticate_user(email, password)
            logger.info(f"Authentication result: {auth_result}")
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in test_login: {str(e)}")

if __name__ == "__main__":
    test_login() 