#!/usr/bin/env python3
"""
Fix Free User Script
-----------------
This script fixes the subscription for the free_user.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.database.db import get_db_connection

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        return True
    
    logger.error(f"Failed to create subscription for user {user_id} to plan {plan_id}")
    return False

def fix_free_user_subscription():
    conn = None
    try:
        # Get a database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the free user ID
        cursor.execute('SELECT id FROM users WHERE email = %s', ('free_user@example.com',))
        user_result = cursor.fetchone()
        if not user_result:
            logger.error("Free user not found")
            return False
        
        user_id = user_result['id']
        logger.info(f"Found free user with ID {user_id}")
        
        # Get the Free plan ID
        cursor.execute('SELECT id FROM subscription_plans WHERE name = %s', ('Free',))
        plan_result = cursor.fetchone()
        if not plan_result:
            logger.error("Free plan not found")
            return False
        
        plan_id = plan_result['id']
        logger.info(f"Found Free plan with ID {plan_id}")
        
        # Check if subscription already exists
        cursor.execute(
            'SELECT id FROM user_subscriptions WHERE user_id = %s AND subscription_plan_id = %s',
            (user_id, plan_id)
        )
        existing_sub = cursor.fetchone()
        
        if existing_sub:
            logger.info(f"Free user already has a Free subscription (ID: {existing_sub['id']})")
            return True
        
        # Create subscription
        now = datetime.now()
        end_date = now + timedelta(days=365)  # Free plan for a year
        
        cursor.execute(
            '''
            INSERT INTO user_subscriptions 
            (user_id, subscription_plan_id, stripe_customer_id, stripe_subscription_id, 
             status, current_period_start, current_period_end, cancel_at_period_end) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id
            ''',
            (
                user_id, 
                plan_id, 
                f'cus_free_{user_id}', 
                f'sub_free_{user_id}', 
                'active', 
                now, 
                end_date, 
                False
            )
        )
        
        result = cursor.fetchone()
        if result:
            subscription_id = result['id']
            logger.info(f"Successfully created Free subscription (ID: {subscription_id}) for free user")
            
            # Commit the transaction
            conn.commit()
            logger.info("Transaction committed")
            
            # Verify the subscription was created
            cursor.execute('SELECT * FROM user_subscriptions WHERE id = %s', (subscription_id,))
            verify = cursor.fetchone()
            if verify:
                logger.info(f"Verification successful: subscription exists with ID {subscription_id}")
            else:
                logger.error(f"Verification failed: subscription with ID {subscription_id} not found")
            
            return True
        else:
            logger.error("Failed to create subscription - no ID returned")
            return False
            
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        if conn:
            conn.rollback()
            logger.info("Transaction rolled back due to error")
        return False
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    fix_free_user_subscription() 