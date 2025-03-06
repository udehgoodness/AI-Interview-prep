#!/usr/bin/env python3
"""
Script to create test users for each subscription plan
"""

import json
import bcrypt
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from database.db import execute_query

# Database connection parameters
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ai_interview_prep")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Test user credentials
test_users = [
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

def get_password_hash(password):
    """Generate a password hash using bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

def main():
    print("Creating test users for each subscription plan...")
    
    # Get all subscription plans
    plans = execute_query("SELECT * FROM subscription_plans")
    
    if not plans:
        print("No subscription plans found in the database. Please seed the database first.")
        return
    
    # Get a database connection
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database.")
        return
    
    try:
        cursor = conn.cursor()
        
        # First, check if the users table exists
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("The users table does not exist. Please initialize the database first.")
            conn.close()
            return
        
        # Delete existing test users to start fresh
        print("Deleting existing test users...")
        for user_data in test_users:
            email = user_data["email"]
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                user_id = existing_user[0]
                # Delete user subscriptions
                cursor.execute("DELETE FROM user_subscriptions WHERE user_id = %s", (user_id,))
                # Delete user
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                print(f"Deleted existing user: {email}")
        
        conn.commit()
        
        for user_data in test_users:
            email = user_data["email"]
            password = user_data["password"]
            full_name = user_data["full_name"]
            plan_name = user_data["plan_name"]
            
            # Create user
            password_hash = get_password_hash(password)
            now = datetime.now()
            
            cursor.execute(
                """
                INSERT INTO users (
                    email, password_hash, full_name, created_at, updated_at, is_active, is_admin
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
                """,
                (
                    email, 
                    password_hash, 
                    full_name, 
                    now, 
                    now, 
                    True, 
                    False
                )
            )
            
            user_id = cursor.fetchone()[0]
            print(f"Created user: {email} with ID: {user_id}")
            
            # Find the corresponding plan
            plan = next((p for p in plans if p["name"] == plan_name), None)
            
            if not plan:
                print(f"Plan {plan_name} not found, skipping subscription")
                conn.commit()
                continue
            
            # For Free plan, we don't need to create a subscription
            if plan_name == "Free":
                print(f"User {email} is on Free plan, no subscription needed")
                conn.commit()
                continue
            
            # Create subscription for paid plans
            now = datetime.now()
            period_end = now + timedelta(days=30)
            
            cursor.execute(
                """
                INSERT INTO user_subscriptions (
                    user_id, subscription_plan_id, stripe_customer_id, 
                    stripe_subscription_id, status, current_period_start, 
                    current_period_end, cancel_at_period_end, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    user_id, 
                    plan["id"], 
                    f"cus_test_{user_id}", 
                    f"sub_test_{user_id}", 
                    "active", 
                    now, 
                    period_end, 
                    False, 
                    now, 
                    now
                )
            )
            
            # Commit the transaction
            conn.commit()
            print(f"Created {plan_name} subscription for {email}")
        
        print("\nTest users created successfully!")
        print("\nUser credentials:")
        for user in test_users:
            print(f"- {user['plan_name']} Plan: {user['email']} / {user['password']}")
    
    except Exception as e:
        conn.rollback()
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 