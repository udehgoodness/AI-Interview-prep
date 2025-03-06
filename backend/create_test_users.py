#!/usr/bin/env python3
"""
Create Test Users Script
-----------------------
This script creates test users with different subscription plans.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from passlib.context import CryptContext
import json

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """Hash a password"""
    return pwd_context.hash(password)

# Import database functions
from app.database.db import execute_query, execute_transaction

def create_user(email, password, full_name, is_active=True, is_admin=False):
    """Create a new user"""
    # Check if user already exists
    query = "SELECT * FROM users WHERE email = %s"
    results = execute_query(query, (email,))
    
    if results and len(results) > 0:
        logger.info(f"User {email} already exists")
        return dict(results[0])
    
    # Hash the password
    hashed_password = get_password_hash(password)
    
    # Insert the user into the database
    query = """
    INSERT INTO users (email, password_hash, full_name, created_at, updated_at, is_active, is_admin)
    VALUES (%s, %s, %s, NOW(), NOW(), %s, %s)
    RETURNING id, email, full_name, created_at, is_active, is_admin
    """
    
    results = execute_query(query, (email, hashed_password, full_name, is_active, is_admin))
    
    if results and len(results) > 0:
        logger.info(f"User {email} created successfully")
        return dict(results[0])
    
    logger.error(f"Failed to create user {email}")
    return None

def get_subscription_plan_by_name(name):
    """Get a subscription plan by name"""
    query = "SELECT * FROM subscription_plans WHERE name = %s"
    results = execute_query(query, (name,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def create_user_subscription(user_id, plan_id, status="active"):
    """Create a user subscription"""
    # Check if subscription already exists
    query = "SELECT * FROM user_subscriptions WHERE user_id = %s AND subscription_plan_id = %s"
    results = execute_query(query, (user_id, plan_id))
    
    if results and len(results) > 0:
        logger.info(f"Subscription for user {user_id} to plan {plan_id} already exists")
        return dict(results[0])
    
    # Create a new subscription
    current_period_start = datetime.now()
    current_period_end = current_period_start + timedelta(days=30)
    
    query = """
    INSERT INTO user_subscriptions (
        user_id, subscription_plan_id, stripe_customer_id, 
        stripe_subscription_id, status, current_period_start, 
        current_period_end, cancel_at_period_end
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    # Generate fake Stripe IDs
    stripe_customer_id = f"cus_test_{user_id}"
    stripe_subscription_id = f"sub_test_{user_id}_{plan_id}"
    
    params = (
        user_id,
        plan_id,
        stripe_customer_id,
        stripe_subscription_id,
        status,
        current_period_start,
        current_period_end,
        False  # cancel_at_period_end
    )
    
    results = execute_query(query, params)
    
    if results and len(results) > 0:
        subscription_id = results[0]["id"]
        logger.info(f"Subscription {subscription_id} created successfully")
        
        # Get the subscription with plan details
        query = """
        SELECT us.*, sp.* FROM user_subscriptions us
        JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
        WHERE us.id = %s
        """
        
        results = execute_query(query, (subscription_id,))
        
        if results and len(results) > 0:
            return dict(results[0])
    
    logger.error(f"Failed to create subscription for user {user_id} to plan {plan_id}")
    return None

def main():
    """Create test users with different subscription plans"""
    # Create users
    users = [
        {
            "email": "free_user@example.com",
            "password": "Test1234!",
            "full_name": "Free User",
            "plan_name": "Free"
        },
        {
            "email": "basic_user@example.com",
            "password": "Test1234!",
            "full_name": "Basic User",
            "plan_name": "Basic"
        },
        {
            "email": "pro_user@example.com",
            "password": "Test1234!",
            "full_name": "Professional User",
            "plan_name": "Professional"
        },
        {
            "email": "enterprise_user@example.com",
            "password": "Test1234!",
            "full_name": "Enterprise User",
            "plan_name": "Enterprise"
        }
    ]
    
    for user_data in users:
        # Create user
        user = create_user(
            user_data["email"],
            user_data["password"],
            user_data["full_name"]
        )
        
        if user:
            # Get subscription plan
            plan = get_subscription_plan_by_name(user_data["plan_name"])
            
            if plan:
                # Create subscription
                subscription = create_user_subscription(user["id"], plan["id"])
                
                if subscription:
                    logger.info(f"User {user_data['email']} with {user_data['plan_name']} plan created successfully")
                else:
                    logger.error(f"Failed to create subscription for user {user_data['email']}")
            else:
                logger.error(f"Subscription plan {user_data['plan_name']} not found")
        else:
            logger.error(f"Failed to create user {user_data['email']}")

if __name__ == "__main__":
    main() 