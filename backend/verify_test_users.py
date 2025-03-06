#!/usr/bin/env python3
"""
Verify Test Users Script
-----------------------
This script verifies that the test users were created with their respective subscription plans.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database functions
from app.database.db import execute_query

def get_user_by_email(email):
    """Get a user by email"""
    query = "SELECT * FROM users WHERE email = %s"
    results = execute_query(query, (email,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def get_user_subscription(user_id):
    """Get a user's subscription"""
    query = """
    SELECT us.*, sp.name as plan_name, sp.features 
    FROM user_subscriptions us
    JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
    WHERE us.user_id = %s
    ORDER BY us.created_at DESC
    LIMIT 1
    """
    
    results = execute_query(query, (user_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def main():
    """Verify test users with their respective subscription plans"""
    # Users to verify
    users = [
        {
            "email": "free_user@example.com",
            "expected_plan": "Free"
        },
        {
            "email": "basic_user@example.com",
            "expected_plan": "Basic"
        },
        {
            "email": "pro_user@example.com",
            "expected_plan": "Professional"
        },
        {
            "email": "enterprise_user@example.com",
            "expected_plan": "Enterprise"
        }
    ]
    
    for user_data in users:
        email = user_data["email"]
        expected_plan = user_data["expected_plan"]
        
        # Get user
        user = get_user_by_email(email)
        
        if user:
            logger.info(f"User {email} exists with ID {user['id']}")
            
            # Get subscription
            subscription = get_user_subscription(user["id"])
            
            if subscription:
                plan_name = subscription["plan_name"]
                logger.info(f"User {email} has subscription to {plan_name} plan")
                
                if plan_name == expected_plan:
                    logger.info(f"✅ User {email} has the expected {expected_plan} plan")
                else:
                    logger.error(f"❌ User {email} has {plan_name} plan, but expected {expected_plan}")
            else:
                logger.error(f"❌ User {email} has no subscription")
        else:
            logger.error(f"❌ User {email} does not exist")

if __name__ == "__main__":
    main() 