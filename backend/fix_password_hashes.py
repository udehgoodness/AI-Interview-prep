"""
Script to fix password hashes for all users
"""

import os
import sys
import logging
from dotenv import load_dotenv
import json
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_password_hashes():
    """
    Fix password hashes for all users
    
    This function:
    1. Gets all users from the database
    2. Checks each user's password hash format
    3. If the hash is malformed, generates a new hash
    4. Updates the user's password hash in the database
    5. Logs the results
    """
    try:
        from app.services.auth import get_password_hash
        from app.database.db import get_db_connection, execute_query
        
        # Get all users
        users = execute_query("SELECT id, email, password_hash FROM users")
        
        if not users:
            logger.error("No users found in the database")
            return
        
        logger.info(f"Found {len(users)} users in the database")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Default test password
        default_password = "password123"
        
        # Track results
        fixed_users = []
        already_valid_users = []
        failed_users = []
        
        # Fix each user's password hash
        for user in users:
            user_id = user["id"]
            email = user["email"]
            current_hash = user["password_hash"]
            
            # Check if the hash is malformed
            if not current_hash or not isinstance(current_hash, str) or not current_hash.startswith('$2b$'):
                logger.info(f"Fixing password hash for user {email} (ID: {user_id})")
                
                try:
                    # Generate a new hash
                    new_hash = get_password_hash(default_password)
                    
                    # Update the user's password hash
                    cur.execute(
                        "UPDATE users SET password_hash = %s WHERE id = %s",
                        (new_hash, user_id)
                    )
                    
                    fixed_users.append(email)
                    logger.info(f"Updated password hash for user {email}")
                except Exception as e:
                    logger.error(f"Failed to update password hash for user {email}: {str(e)}")
                    failed_users.append(email)
            else:
                logger.info(f"Password hash for user {email} is already valid")
                already_valid_users.append(email)
        
        # Commit the changes
        conn.commit()
        logger.info("All password hashes have been processed")
        
        # Close the connection
        conn.close()
        
        # Log summary
        logger.info(f"Summary:")
        logger.info(f"  - Fixed users: {len(fixed_users)}")
        logger.info(f"  - Already valid users: {len(already_valid_users)}")
        logger.info(f"  - Failed users: {len(failed_users)}")
        
        if fixed_users:
            logger.info(f"  - Fixed users list: {', '.join(fixed_users)}")
        if failed_users:
            logger.error(f"  - Failed users list: {', '.join(failed_users)}")
        
    except Exception as e:
        logger.error(f"Error fixing password hashes: {str(e)}")

def test_all_users():
    """
    Test login for all users
    
    This function:
    1. Gets all users from the database
    2. Attempts to authenticate each user
    3. Logs the results
    """
    try:
        from app.services.auth import authenticate_user
        from app.database.db import execute_query
        
        # Get all users
        users = execute_query("SELECT email FROM users")
        
        if not users:
            logger.error("No users found in the database")
            return
        
        logger.info(f"Testing authentication for {len(users)} users")
        
        # Default test password
        default_password = "password123"
        
        # Track results
        successful_users = []
        failed_users = []
        
        # Test login for each user
        for user in users:
            email = user["email"]
            
            # Try to authenticate the user
            auth_result = authenticate_user(email, default_password)
            
            if auth_result:
                logger.info(f"Authentication successful for user {email}")
                successful_users.append(email)
            else:
                logger.error(f"Authentication failed for user {email}")
                failed_users.append(email)
        
        # Log summary
        logger.info(f"Authentication Summary:")
        logger.info(f"  - Successful: {len(successful_users)}")
        logger.info(f"  - Failed: {len(failed_users)}")
        
        if successful_users:
            logger.info(f"  - Successful users: {', '.join(successful_users)}")
        if failed_users:
            logger.error(f"  - Failed users: {', '.join(failed_users)}")
        
    except Exception as e:
        logger.error(f"Error testing users: {str(e)}")

def test_login_api():
    """
    Test the login API endpoint
    
    This function:
    1. Makes HTTP requests to the login endpoint
    2. Tests each user's credentials
    3. Logs the results
    """
    try:
        import requests
        from app.database.db import execute_query
        
        # Get all users
        users = execute_query("SELECT email FROM users")
        
        if not users:
            logger.error("No users found in the database")
            return
        
        logger.info(f"Testing login API for {len(users)} users")
        
        # Default test password
        default_password = "password123"
        
        # Track results
        successful_users = []
        failed_users = []
        
        # Test login API for each user
        for user in users:
            email = user["email"]
            
            try:
                # Make a request to the login endpoint
                response = requests.post(
                    "http://localhost:8000/api/auth/login",
                    json={"email": email, "password": default_password},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info(f"Login API successful for user {email}")
                    successful_users.append(email)
                else:
                    logger.error(f"Login API failed for user {email}: {response.status_code} - {response.text}")
                    failed_users.append(email)
                    
                # Add a small delay to avoid overwhelming the server
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error testing login API for user {email}: {str(e)}")
                failed_users.append(email)
        
        # Log summary
        logger.info(f"Login API Summary:")
        logger.info(f"  - Successful: {len(successful_users)}")
        logger.info(f"  - Failed: {len(failed_users)}")
        
        if successful_users:
            logger.info(f"  - Successful users: {', '.join(successful_users)}")
        if failed_users:
            logger.error(f"  - Failed users: {', '.join(failed_users)}")
        
    except Exception as e:
        logger.error(f"Error testing login API: {str(e)}")

if __name__ == "__main__":
    # Fix password hashes
    fix_password_hashes()
    
    # Test all users
    test_all_users()
    
    # Test login API
    test_login_api() 