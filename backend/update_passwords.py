"""
Script to update all test users' passwords
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def update_all_passwords():
    """
    Update all test users' passwords to Test1234!
    """
    try:
        from app.services.auth import get_password_hash
        from app.database.db import get_db_connection, execute_query
        
        # Get all users
        users = execute_query("SELECT id, email FROM users")
        
        if not users:
            logger.error("No users found in the database")
            return
        
        logger.info(f"Found {len(users)} users in the database")
        
        # New password for all users
        new_password = "Test1234!"
        
        # Generate the password hash
        password_hash = get_password_hash(new_password)
        logger.info(f"Generated new password hash: {password_hash}")
        
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update each user's password
        for user in users:
            user_id = user["id"]
            email = user["email"]
            
            try:
                # Update the user's password hash
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hash, user_id)
                )
                
                logger.info(f"Updated password for user {email} (ID: {user_id})")
            except Exception as e:
                logger.error(f"Failed to update password for user {email}: {str(e)}")
        
        # Commit the changes
        conn.commit()
        logger.info("All passwords have been updated")
        
        # Close the connection
        conn.close()
        
    except Exception as e:
        logger.error(f"Error updating passwords: {str(e)}")

def test_all_users():
    """
    Test login for all users with the new password
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
        
        # New password for all users
        new_password = "Test1234!"
        
        # Track results
        successful_users = []
        failed_users = []
        
        # Test login for each user
        for user in users:
            email = user["email"]
            
            # Try to authenticate the user
            auth_result = authenticate_user(email, new_password)
            
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

if __name__ == "__main__":
    # Update all passwords
    update_all_passwords()
    
    # Test all users
    test_all_users() 