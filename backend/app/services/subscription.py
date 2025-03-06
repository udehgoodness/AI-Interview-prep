"""
Subscription Service
-----------------
This module contains the subscription service for the application.
"""

import os
import logging
import stripe
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from datetime import datetime
import json

from app.database.db import execute_query, execute_transaction
from app.models.subscription import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    PaymentHistoryCreate
)

# Configure logging
logger = logging.getLogger(__name__)

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Subscription plan functions
def get_all_subscription_plans(active_only: bool = True):
    """Get all subscription plans"""
    query = "SELECT * FROM subscription_plans"
    
    if active_only:
        query += " WHERE is_active = TRUE"
        
    query += " ORDER BY price_monthly ASC"
    
    results = execute_query(query)
    return results

def get_subscription_plan_by_id(plan_id: int):
    """Get a subscription plan by ID"""
    query = "SELECT * FROM subscription_plans WHERE id = %s"
    results = execute_query(query, (plan_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def create_subscription_plan(plan: SubscriptionPlanCreate):
    """Create a new subscription plan"""
    # Create the plan in the database
    query = """
    INSERT INTO subscription_plans (
        name, description, price_monthly, price_yearly, 
        stripe_price_id_monthly, stripe_price_id_yearly, 
        features, is_active
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    params = (
        plan.name,
        plan.description,
        plan.price_monthly,
        plan.price_yearly,
        plan.stripe_price_id_monthly,
        plan.stripe_price_id_yearly,
        json.dumps(plan.features),
        plan.is_active
    )
    
    results = execute_query(query, params)
    
    if results and len(results) > 0:
        plan_id = results[0]["id"]
        return get_subscription_plan_by_id(plan_id)
    
    return None

def update_subscription_plan(plan_id: int, plan: SubscriptionPlanUpdate):
    """Update a subscription plan"""
    # Get the current plan
    current_plan = get_subscription_plan_by_id(plan_id)
    
    if not current_plan:
        return None
    
    # Build the update query
    query_parts = []
    params = []
    
    if plan.name is not None:
        query_parts.append("name = %s")
        params.append(plan.name)
        
    if plan.description is not None:
        query_parts.append("description = %s")
        params.append(plan.description)
        
    if plan.price_monthly is not None:
        query_parts.append("price_monthly = %s")
        params.append(plan.price_monthly)
        
    if plan.price_yearly is not None:
        query_parts.append("price_yearly = %s")
        params.append(plan.price_yearly)
        
    if plan.stripe_price_id_monthly is not None:
        query_parts.append("stripe_price_id_monthly = %s")
        params.append(plan.stripe_price_id_monthly)
        
    if plan.stripe_price_id_yearly is not None:
        query_parts.append("stripe_price_id_yearly = %s")
        params.append(plan.stripe_price_id_yearly)
        
    if plan.features is not None:
        query_parts.append("features = %s")
        params.append(json.dumps(plan.features))
        
    if plan.is_active is not None:
        query_parts.append("is_active = %s")
        params.append(plan.is_active)
    
    # Add updated_at
    query_parts.append("updated_at = NOW()")
    
    # If nothing to update, return the current plan
    if not query_parts:
        return current_plan
    
    # Build the final query
    query = f"UPDATE subscription_plans SET {', '.join(query_parts)} WHERE id = %s"
    params.append(plan_id)
    
    execute_query(query, tuple(params), fetch=False)
    
    return get_subscription_plan_by_id(plan_id)

def delete_subscription_plan(plan_id: int):
    """Delete a subscription plan (soft delete by setting is_active to False)"""
    query = "UPDATE subscription_plans SET is_active = FALSE, updated_at = NOW() WHERE id = %s"
    execute_query(query, (plan_id,), fetch=False)
    
    return {"message": "Subscription plan deleted successfully"}

# User subscription functions
def get_user_subscription(user_id: int):
    """Get a user's subscription"""
    query = """
    SELECT * FROM user_subscriptions 
    WHERE user_id = %s 
    ORDER BY created_at DESC 
    LIMIT 1
    """
    
    results = execute_query(query, (user_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def create_user_subscription(subscription: UserSubscriptionCreate):
    """Create a new user subscription"""
    query = """
    INSERT INTO user_subscriptions (
        user_id, subscription_plan_id, stripe_customer_id, 
        stripe_subscription_id, status, current_period_start, 
        current_period_end, cancel_at_period_end
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    params = (
        subscription.user_id,
        subscription.subscription_plan_id,
        subscription.stripe_customer_id,
        subscription.stripe_subscription_id,
        subscription.status,
        subscription.current_period_start,
        subscription.current_period_end,
        subscription.cancel_at_period_end
    )
    
    results = execute_query(query, params)
    
    if results and len(results) > 0:
        subscription_id = results[0]["id"]
        
        # Get the subscription with plan details
        query = """
        SELECT us.*, sp.* FROM user_subscriptions us
        JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
        WHERE us.id = %s
        """
        
        results = execute_query(query, (subscription_id,))
        
        if results and len(results) > 0:
            return dict(results[0])
    
    return None

def update_user_subscription(subscription_id: int, subscription: UserSubscriptionUpdate):
    """Update a user subscription"""
    # Get the current subscription
    query = "SELECT * FROM user_subscriptions WHERE id = %s"
    results = execute_query(query, (subscription_id,))
    
    if not results or len(results) == 0:
        return None
    
    current_subscription = dict(results[0])
    
    # Build the update query
    query_parts = []
    params = []
    
    if subscription.subscription_plan_id is not None:
        query_parts.append("subscription_plan_id = %s")
        params.append(subscription.subscription_plan_id)
        
    if subscription.status is not None:
        query_parts.append("status = %s")
        params.append(subscription.status)
        
    if subscription.current_period_start is not None:
        query_parts.append("current_period_start = %s")
        params.append(subscription.current_period_start)
        
    if subscription.current_period_end is not None:
        query_parts.append("current_period_end = %s")
        params.append(subscription.current_period_end)
        
    if subscription.cancel_at_period_end is not None:
        query_parts.append("cancel_at_period_end = %s")
        params.append(subscription.cancel_at_period_end)
        
    if subscription.stripe_subscription_id is not None:
        query_parts.append("stripe_subscription_id = %s")
        params.append(subscription.stripe_subscription_id)
    
    # Add updated_at
    query_parts.append("updated_at = NOW()")
    
    # If nothing to update, return the current subscription
    if not query_parts:
        return current_subscription
    
    # Build the final query
    query = f"UPDATE user_subscriptions SET {', '.join(query_parts)} WHERE id = %s"
    params.append(subscription_id)
    
    execute_query(query, tuple(params), fetch=False)
    
    # Get the updated subscription with plan details
    query = """
    SELECT us.*, sp.* FROM user_subscriptions us
    JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
    WHERE us.id = %s
    """
    
    results = execute_query(query, (subscription_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def cancel_user_subscription(subscription_id: int):
    """Cancel a user subscription"""
    # Get the current subscription
    query = "SELECT * FROM user_subscriptions WHERE id = %s"
    results = execute_query(query, (subscription_id,))
    
    if not results or len(results) == 0:
        return None
    
    current_subscription = dict(results[0])
    
    # Update the subscription in Stripe
    try:
        stripe.Subscription.modify(
            current_subscription["stripe_subscription_id"],
            cancel_at_period_end=True
        )
    except Exception as e:
        logger.error(f"Error canceling Stripe subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error canceling subscription in Stripe"
        )
    
    # Update the subscription in the database
    query = """
    UPDATE user_subscriptions 
    SET cancel_at_period_end = TRUE, updated_at = NOW() 
    WHERE id = %s
    """
    
    execute_query(query, (subscription_id,), fetch=False)
    
    return {"message": "Subscription canceled successfully"}

# Payment history functions
def create_payment_history(payment: PaymentHistoryCreate):
    """Create a new payment history entry"""
    query = """
    INSERT INTO payment_history (
        user_id, subscription_id, stripe_payment_intent_id, 
        amount, currency, status, payment_method_type
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    params = (
        payment.user_id,
        payment.subscription_id,
        payment.stripe_payment_intent_id,
        payment.amount,
        payment.currency,
        payment.status,
        payment.payment_method_type
    )
    
    results = execute_query(query, params)
    
    if results and len(results) > 0:
        payment_id = results[0]["id"]
        
        # Get the payment history
        query = "SELECT * FROM payment_history WHERE id = %s"
        results = execute_query(query, (payment_id,))
        
        if results and len(results) > 0:
            return dict(results[0])
    
    return None

def get_user_payment_history(user_id: int):
    """Get a user's payment history"""
    query = """
    SELECT * FROM payment_history 
    WHERE user_id = %s 
    ORDER BY created_at DESC
    """
    
    results = execute_query(query, (user_id,))
    return results

# Subscription access functions
def check_user_subscription_access(user_id: int, feature_name: str):
    """
    Check if a user has access to a specific feature based on their subscription
    Returns True if the user has access, False otherwise
    """
    # Get the user's subscription
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        return False
    
    # Check if the subscription is active
    if subscription["status"] != "active":
        return False
    
    # Get the subscription plan
    plan = get_subscription_plan_by_id(subscription["subscription_plan_id"])
    
    if not plan:
        return False
    
    # Check if the plan has the feature
    features = plan["features"]
    
    if isinstance(features, str):
        features = json.loads(features)
    
    if feature_name not in features:
        return False
    
    # Check if the user has exceeded the feature limit
    feature_value = features[feature_name]
    
    # If the feature value is -1, it means unlimited access
    if feature_value == -1:
        return True
    
    # If the feature value is 0, it means no access
    if feature_value == 0:
        return False
    
    # Otherwise, check the usage
    # This would require a more complex implementation to track usage
    # For now, we'll just return True
    return True

def update_subscription_plan_features():
    """
    Update subscription plan features
    This function is called on application startup to ensure all plans have the required features
    """
    # Define the default features for each plan
    default_features = {
        "free": {
            "interviews_per_month": 3,
            "voice_interviews": False,
            "code_challenges": False,
            "resume_analysis": False,
            "interview_feedback": True,
            "interview_recording": False,
            "custom_questions": False,
            "ai_model": "basic"
        },
        "basic": {
            "interviews_per_month": 10,
            "voice_interviews": True,
            "code_challenges": True,
            "resume_analysis": True,
            "interview_feedback": True,
            "interview_recording": True,
            "custom_questions": False,
            "ai_model": "standard"
        },
        "premium": {
            "interviews_per_month": -1,  # Unlimited
            "voice_interviews": True,
            "code_challenges": True,
            "resume_analysis": True,
            "interview_feedback": True,
            "interview_recording": True,
            "custom_questions": True,
            "ai_model": "advanced"
        }
    }
    
    # Get all plans
    plans = get_all_subscription_plans(active_only=False)
    
    for plan in plans:
        plan_name = plan["name"].lower()
        
        # Skip plans that don't match our default plans
        if plan_name not in default_features:
            continue
        
        # Get the default features for this plan
        features = default_features[plan_name]
        
        # Update the plan features
        update_subscription_plan(
            plan["id"],
            SubscriptionPlanUpdate(features=features)
        ) 