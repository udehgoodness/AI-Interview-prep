#!/usr/bin/env python3
"""
Script to reseed the subscription plans in the database.
This will delete all existing plans and create new ones based on the frontend definitions.
"""

import os
import sys
import json
from decimal import Decimal
from dotenv import load_dotenv

# Update import to use app structure
from app.database.db import execute_query

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def main():
    # Delete existing plans
    print("Deleting existing subscription plans...")
    execute_query("DELETE FROM subscription_plans;", fetch=False)
    
    # Define plans based on frontend definitions
    plans = [
        {
            "name": "Free",
            "description": "Get started with basic interview preparation",
            "price_monthly": Decimal("0.00"),
            "price_yearly": Decimal("0.00"),
            "stripe_price_id_monthly": "price_free_monthly",
            "stripe_price_id_yearly": "price_free_yearly",
            "features": {
                "interviews_per_month": 3,
                "feedback_detail": "basic",
                "video_interviews": False,
                "code_challenges": False,
                "interview_duration_max": 15,
                "question_library_access": "limited",
                "support": "community",
                "text_interviews": True,
                "voice_interviews": False
            },
            "is_active": True
        },
        {
            "name": "Basic",
            "description": "Perfect for individuals preparing for job interviews",
            "price_monthly": Decimal("9.99"),
            "price_yearly": Decimal("99.99"),
            "stripe_price_id_monthly": "price_basic_monthly",
            "stripe_price_id_yearly": "price_basic_yearly",
            "features": {
                "interviews_per_month": 10,
                "feedback_detail": "detailed",
                "video_interviews": False,
                "code_challenges": True,
                "interview_duration_max": 30,
                "question_library_access": "full",
                "support": "email",
                "voice_interviews": True,
                "text_interviews": True
            },
            "is_active": True
        },
        {
            "name": "Professional",
            "description": "For serious job seekers who want comprehensive preparation",
            "price_monthly": Decimal("19.99"),
            "price_yearly": Decimal("199.99"),
            "stripe_price_id_monthly": "price_pro_monthly",
            "stripe_price_id_yearly": "price_pro_yearly",
            "features": {
                "interviews_per_month": -1,  # Unlimited
                "feedback_detail": "comprehensive",
                "video_interviews": True,
                "code_challenges": True,
                "interview_duration_max": 60,
                "question_library_access": "full",
                "support": "priority_email",
                "voice_interviews": True,
                "text_interviews": True,
                "cv_review": True,
                "performance_analytics": True,
                "personalized_suggestions": True
            },
            "is_active": True
        },
        {
            "name": "Enterprise",
            "description": "For teams and organizations preparing multiple candidates",
            "price_monthly": Decimal("49.99"),
            "price_yearly": Decimal("499.99"),
            "stripe_price_id_monthly": "price_enterprise_monthly",
            "stripe_price_id_yearly": "price_enterprise_yearly",
            "features": {
                "interviews_per_month": -1,  # Unlimited
                "feedback_detail": "comprehensive",
                "video_interviews": True,
                "code_challenges": True,
                "interview_duration_max": 120,
                "question_library_access": "full",
                "support": "24/7",
                "voice_interviews": True,
                "text_interviews": True,
                "cv_review": True,
                "performance_analytics": True,
                "personalized_suggestions": True,
                "team_management": True,
                "bulk_user_management": True,
                "custom_templates": True,
                "dedicated_account_manager": True
            },
            "is_active": True
        }
    ]
    
    # Insert plans
    print("Inserting new subscription plans...")
    for plan in plans:
        query = """
        INSERT INTO subscription_plans (
            name, description, price_monthly, price_yearly, 
            stripe_price_id_monthly, stripe_price_id_yearly, 
            features, is_active, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        execute_query(
            query, 
            (
                plan["name"], 
                plan["description"], 
                plan["price_monthly"], 
                plan["price_yearly"],
                plan["stripe_price_id_monthly"], 
                plan["stripe_price_id_yearly"],
                json.dumps(plan["features"]), 
                plan["is_active"]
            ),
            fetch=False
        )
    
    print("Done!")

if __name__ == "__main__":
    main() 