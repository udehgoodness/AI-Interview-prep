#!/usr/bin/env python3
"""
Script to check user subscriptions in the database
"""

from app.database.db import execute_query
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_user_subscription(email):
    # Check if user exists
    user_result = execute_query('SELECT id FROM users WHERE email = %s', (email,))
    if not user_result:
        logger.error(f"User with email {email} does not exist")
        return False
    
    user_id = user_result[0]['id']
    logger.info(f"User with email {email} exists with ID {user_id}")
    
    # Check subscription
    subscription_result = execute_query('''
        SELECT us.id, sp.name as plan_name 
        FROM user_subscriptions us
        JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
        WHERE us.user_id = %s AND us.status = 'active'
    ''', (user_id,))
    
    if not subscription_result:
        logger.info(f"User {email} has no active subscription")
        return False
    
    subscription_id = subscription_result[0]['id']
    plan_name = subscription_result[0]['plan_name']
    logger.info(f"User {email} has an active {plan_name} subscription (ID: {subscription_id})")
    return True

def main():
    test_users = [
        'free_user@example.com',
        'basic_user@example.com',
        'pro_user@example.com',
        'enterprise_user@example.com'
    ]
    
    for email in test_users:
        check_user_subscription(email)

if __name__ == "__main__":
    main() 