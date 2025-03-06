import os
import stripe
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from datetime import datetime
from dotenv import load_dotenv
import json

from database.db import execute_query, execute_transaction
from models.subscription import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    PaymentHistoryCreate
)

# Load environment variables
load_dotenv()

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
        features, is_active, created_at, updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    RETURNING *
    """
    
    results = execute_query(
        query, 
        (
            plan.name, plan.description, plan.price_monthly, plan.price_yearly,
            plan.stripe_price_id_monthly, plan.stripe_price_id_yearly,
            plan.features, plan.is_active
        )
    )
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create subscription plan"
    )

def update_subscription_plan(plan_id: int, plan_update: SubscriptionPlanUpdate):
    """Update a subscription plan"""
    # Get the current plan
    current_plan = get_subscription_plan_by_id(plan_id)
    
    if not current_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Build the update query dynamically based on provided fields
    update_fields = []
    params = []
    
    if plan_update.name is not None:
        update_fields.append("name = %s")
        params.append(plan_update.name)
        
    if plan_update.description is not None:
        update_fields.append("description = %s")
        params.append(plan_update.description)
        
    if plan_update.price_monthly is not None:
        update_fields.append("price_monthly = %s")
        params.append(plan_update.price_monthly)
        
    if plan_update.price_yearly is not None:
        update_fields.append("price_yearly = %s")
        params.append(plan_update.price_yearly)
        
    if plan_update.stripe_price_id_monthly is not None:
        update_fields.append("stripe_price_id_monthly = %s")
        params.append(plan_update.stripe_price_id_monthly)
        
    if plan_update.stripe_price_id_yearly is not None:
        update_fields.append("stripe_price_id_yearly = %s")
        params.append(plan_update.stripe_price_id_yearly)
        
    if plan_update.features is not None:
        update_fields.append("features = %s")
        params.append(plan_update.features)
        
    if plan_update.is_active is not None:
        update_fields.append("is_active = %s")
        params.append(plan_update.is_active)
    
    # Add updated_at timestamp
    update_fields.append("updated_at = NOW()")
    
    # If no fields to update, return the current plan
    if not update_fields:
        return current_plan
    
    # Build and execute the query
    query = f"UPDATE subscription_plans SET {', '.join(update_fields)} WHERE id = %s RETURNING *"
    params.append(plan_id)
    
    results = execute_query(query, tuple(params))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to update subscription plan"
    )

def update_subscription_plan_features():
    """Update subscription plan features to include voice_interviews for Professional and Enterprise plans"""
    try:
        # Get Professional plan
        query = """
        SELECT * FROM subscription_plans
        WHERE name = 'Professional' AND is_active = TRUE
        """
        results = execute_query(query)
        
        if results and len(results) > 0:
            pro_plan = dict(results[0])
            features = json.loads(pro_plan["features"]) if isinstance(pro_plan["features"], str) else pro_plan["features"]
            
            # Add voice_interviews feature if it doesn't exist
            if "voice_interviews" not in features:
                features["voice_interviews"] = True
                
                # Update the plan
                update_query = """
                UPDATE subscription_plans
                SET features = %s
                WHERE id = %s
                """
                execute_query(update_query, (json.dumps(features), pro_plan["id"]), fetch=False)
                print(f"Added voice_interviews feature to Professional plan")
        
        # Get Enterprise plan
        query = """
        SELECT * FROM subscription_plans
        WHERE name = 'Enterprise' AND is_active = TRUE
        """
        results = execute_query(query)
        
        if results and len(results) > 0:
            enterprise_plan = dict(results[0])
            features = json.loads(enterprise_plan["features"]) if isinstance(enterprise_plan["features"], str) else enterprise_plan["features"]
            
            # Add voice_interviews feature if it doesn't exist
            if "voice_interviews" not in features:
                features["voice_interviews"] = True
                
                # Update the plan
                update_query = """
                UPDATE subscription_plans
                SET features = %s
                WHERE id = %s
                """
                execute_query(update_query, (json.dumps(features), enterprise_plan["id"]), fetch=False)
                print(f"Added voice_interviews feature to Enterprise plan")
                
        return True
    except Exception as e:
        print(f"Error updating subscription plan features: {str(e)}")
        return False

# User subscription functions
def get_user_subscription(user_id: int):
    """Get a user's active subscription"""
    query = """
    SELECT us.*, sp.*
    FROM user_subscriptions us
    JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
    WHERE us.user_id = %s AND us.status = 'active'
    ORDER BY us.created_at DESC
    LIMIT 1
    """
    
    results = execute_query(query, (user_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def get_user_subscription_by_id(subscription_id: int):
    """Get a user subscription by ID"""
    query = """
    SELECT us.*, sp.*
    FROM user_subscriptions us
    JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
    WHERE us.id = %s
    """
    
    results = execute_query(query, (subscription_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def create_user_subscription(subscription: UserSubscriptionCreate):
    """Create a new user subscription"""
    # Check if user already has an active subscription
    existing_subscription = get_user_subscription(subscription.user_id)
    
    if existing_subscription:
        # Update the existing subscription status to 'canceled'
        cancel_query = """
        UPDATE user_subscriptions
        SET status = 'canceled', updated_at = NOW()
        WHERE id = %s
        """
        
        execute_query(cancel_query, (existing_subscription["id"],), fetch=False)
    
    # Create the new subscription
    query = """
    INSERT INTO user_subscriptions (
        user_id, subscription_plan_id, stripe_customer_id, stripe_subscription_id,
        status, current_period_start, current_period_end, cancel_at_period_end,
        created_at, updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    RETURNING *
    """
    
    results = execute_query(
        query, 
        (
            subscription.user_id, subscription.subscription_plan_id,
            subscription.stripe_customer_id, subscription.stripe_subscription_id,
            subscription.status, subscription.current_period_start,
            subscription.current_period_end, subscription.cancel_at_period_end
        )
    )
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create user subscription"
    )

def update_user_subscription(subscription_id: int, subscription_update: UserSubscriptionUpdate):
    """Update a user subscription"""
    # Get the current subscription
    current_subscription = get_user_subscription_by_id(subscription_id)
    
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Build the update query dynamically based on provided fields
    update_fields = []
    params = []
    
    if subscription_update.subscription_plan_id is not None:
        update_fields.append("subscription_plan_id = %s")
        params.append(subscription_update.subscription_plan_id)
        
    if subscription_update.status is not None:
        update_fields.append("status = %s")
        params.append(subscription_update.status)
        
    if subscription_update.current_period_start is not None:
        update_fields.append("current_period_start = %s")
        params.append(subscription_update.current_period_start)
        
    if subscription_update.current_period_end is not None:
        update_fields.append("current_period_end = %s")
        params.append(subscription_update.current_period_end)
        
    if subscription_update.cancel_at_period_end is not None:
        update_fields.append("cancel_at_period_end = %s")
        params.append(subscription_update.cancel_at_period_end)
        
    if subscription_update.stripe_subscription_id is not None:
        update_fields.append("stripe_subscription_id = %s")
        params.append(subscription_update.stripe_subscription_id)
    
    # Add updated_at timestamp
    update_fields.append("updated_at = NOW()")
    
    # If no fields to update, return the current subscription
    if not update_fields:
        return current_subscription
    
    # Build and execute the query
    query = f"UPDATE user_subscriptions SET {', '.join(update_fields)} WHERE id = %s RETURNING *"
    params.append(subscription_id)
    
    results = execute_query(query, tuple(params))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to update user subscription"
    )

def cancel_user_subscription(user_id: int, cancel_immediately: bool = False):
    """Cancel a user's subscription"""
    # Get the current subscription
    current_subscription = get_user_subscription(user_id)
    
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        if cancel_immediately:
            # Cancel the subscription in Stripe immediately
            stripe.Subscription.delete(current_subscription["stripe_subscription_id"])
            
            # Update the subscription in the database
            query = """
            UPDATE user_subscriptions
            SET status = 'canceled', updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """
        else:
            # Cancel the subscription in Stripe at the end of the period
            stripe.Subscription.modify(
                current_subscription["stripe_subscription_id"],
                cancel_at_period_end=True
            )
            
            # Update the subscription in the database
            query = """
            UPDATE user_subscriptions
            SET cancel_at_period_end = TRUE, updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """
        
        results = execute_query(query, (current_subscription["id"],))
        
        if results and len(results) > 0:
            return dict(results[0])
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

# Payment history functions
def create_payment_record(payment: PaymentHistoryCreate):
    """Create a payment history record"""
    query = """
    INSERT INTO payment_history (
        user_id, subscription_id, stripe_payment_intent_id,
        amount, currency, status, payment_method_type, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    RETURNING *
    """
    
    results = execute_query(
        query, 
        (
            payment.user_id, payment.subscription_id, payment.stripe_payment_intent_id,
            payment.amount, payment.currency, payment.status, payment.payment_method_type
        )
    )
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create payment record"
    )

def get_user_payment_history(user_id: int, limit: int = 10, offset: int = 0):
    """Get a user's payment history"""
    query = """
    SELECT * FROM payment_history
    WHERE user_id = %s
    ORDER BY created_at DESC
    LIMIT %s OFFSET %s
    """
    
    results = execute_query(query, (user_id, limit, offset))
    return results

# Stripe checkout session
def create_checkout_session(user_id: int, plan_id: int, is_yearly: bool = False):
    """Create a Stripe checkout session for subscription"""
    # Get the subscription plan
    plan = get_subscription_plan_by_id(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Get the user
    query = "SELECT * FROM users WHERE id = %s"
    user_results = execute_query(query, (user_id,))
    
    if not user_results or len(user_results) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = dict(user_results[0])
    
    try:
        # Get or create Stripe customer
        stripe_customer = None
        
        # Check if user already has a subscription with a Stripe customer ID
        existing_subscription = get_user_subscription(user_id)
        
        if existing_subscription:
            stripe_customer_id = existing_subscription["stripe_customer_id"]
        else:
            # Create a new Stripe customer
            stripe_customer = stripe.Customer.create(
                email=user["email"],
                name=user["full_name"],
                metadata={"user_id": user_id}
            )
            stripe_customer_id = stripe_customer.id
        
        # Determine which price ID to use
        price_id = plan["stripe_price_id_yearly"] if is_yearly else plan["stripe_price_id_monthly"]
        
        # Create the checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/subscription/success?session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/subscription/cancel"),
            metadata={
                "user_id": user_id,
                "plan_id": plan_id,
                "is_yearly": "true" if is_yearly else "false"
            }
        )
        
        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

# Stripe webhook handler
def handle_stripe_webhook(payload: Dict[str, Any], signature: str):
    """Handle Stripe webhook events"""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Handle the event
    if event["type"] == "checkout.session.completed":
        handle_checkout_session_completed(event["data"]["object"])
    elif event["type"] == "invoice.paid":
        handle_invoice_paid(event["data"]["object"])
    elif event["type"] == "invoice.payment_failed":
        handle_invoice_payment_failed(event["data"]["object"])
    elif event["type"] == "customer.subscription.updated":
        handle_subscription_updated(event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        handle_subscription_deleted(event["data"]["object"])
    
    return {"status": "success"}

def handle_checkout_session_completed(session):
    """Handle checkout.session.completed event"""
    # Extract metadata
    user_id = int(session["metadata"]["user_id"])
    plan_id = int(session["metadata"]["plan_id"])
    is_yearly = session["metadata"]["is_yearly"] == "true"
    
    # Get subscription ID from the session
    subscription_id = session["subscription"]
    
    # Get subscription details from Stripe
    subscription = stripe.Subscription.retrieve(subscription_id)
    
    # Create user subscription record
    user_subscription = UserSubscriptionCreate(
        user_id=user_id,
        subscription_plan_id=plan_id,
        stripe_customer_id=session["customer"],
        stripe_subscription_id=subscription_id,
        status=subscription["status"],
        current_period_start=datetime.fromtimestamp(subscription["current_period_start"]),
        current_period_end=datetime.fromtimestamp(subscription["current_period_end"]),
        cancel_at_period_end=subscription["cancel_at_period_end"]
    )
    
    create_user_subscription(user_subscription)

def handle_invoice_paid(invoice):
    """Handle invoice.paid event"""
    # Get subscription ID from the invoice
    subscription_id = invoice["subscription"]
    
    # Get customer ID from the invoice
    customer_id = invoice["customer"]
    
    # Find the user subscription
    query = """
    SELECT * FROM user_subscriptions
    WHERE stripe_subscription_id = %s AND stripe_customer_id = %s
    """
    
    results = execute_query(query, (subscription_id, customer_id))
    
    if results and len(results) > 0:
        user_subscription = dict(results[0])
        
        # Create payment record
        payment = PaymentHistoryCreate(
            user_id=user_subscription["user_id"],
            subscription_id=user_subscription["id"],
            stripe_payment_intent_id=invoice["payment_intent"],
            amount=invoice["amount_paid"] / 100,  # Convert from cents
            currency=invoice["currency"],
            status="succeeded",
            payment_method_type=invoice["payment_method_types"][0] if "payment_method_types" in invoice else None
        )
        
        create_payment_record(payment)
        
        # Update subscription dates if needed
        if "period_end" in invoice:
            subscription_update = UserSubscriptionUpdate(
                current_period_end=datetime.fromtimestamp(invoice["period_end"])
            )
            
            update_user_subscription(user_subscription["id"], subscription_update)

def handle_invoice_payment_failed(invoice):
    """Handle invoice.payment_failed event"""
    # Get subscription ID from the invoice
    subscription_id = invoice["subscription"]
    
    # Get customer ID from the invoice
    customer_id = invoice["customer"]
    
    # Find the user subscription
    query = """
    SELECT * FROM user_subscriptions
    WHERE stripe_subscription_id = %s AND stripe_customer_id = %s
    """
    
    results = execute_query(query, (subscription_id, customer_id))
    
    if results and len(results) > 0:
        user_subscription = dict(results[0])
        
        # Create payment record
        payment = PaymentHistoryCreate(
            user_id=user_subscription["user_id"],
            subscription_id=user_subscription["id"],
            stripe_payment_intent_id=invoice["payment_intent"],
            amount=invoice["amount_due"] / 100,  # Convert from cents
            currency=invoice["currency"],
            status="failed",
            payment_method_type=invoice["payment_method_types"][0] if "payment_method_types" in invoice else None
        )
        
        create_payment_record(payment)
        
        # Update subscription status if needed
        if invoice["attempt_count"] >= 3:  # After multiple failed attempts
            subscription_update = UserSubscriptionUpdate(
                status="past_due"
            )
            
            update_user_subscription(user_subscription["id"], subscription_update)

def handle_subscription_updated(subscription):
    """Handle customer.subscription.updated event"""
    # Find the user subscription
    query = """
    SELECT * FROM user_subscriptions
    WHERE stripe_subscription_id = %s
    """
    
    results = execute_query(query, (subscription["id"],))
    
    if results and len(results) > 0:
        user_subscription = dict(results[0])
        
        # Update subscription
        subscription_update = UserSubscriptionUpdate(
            status=subscription["status"],
            current_period_start=datetime.fromtimestamp(subscription["current_period_start"]),
            current_period_end=datetime.fromtimestamp(subscription["current_period_end"]),
            cancel_at_period_end=subscription["cancel_at_period_end"]
        )
        
        update_user_subscription(user_subscription["id"], subscription_update)

def handle_subscription_deleted(subscription):
    """Handle customer.subscription.deleted event"""
    # Find the user subscription
    query = """
    SELECT * FROM user_subscriptions
    WHERE stripe_subscription_id = %s
    """
    
    results = execute_query(query, (subscription["id"],))
    
    if results and len(results) > 0:
        user_subscription = dict(results[0])
        
        # Update subscription status
        subscription_update = UserSubscriptionUpdate(
            status="canceled"
        )
        
        update_user_subscription(user_subscription["id"], subscription_update)

# Check user subscription access
def check_user_subscription_access(user_id: int, feature: str):
    """Check if a user has access to a specific feature based on their subscription"""
    # Get the user's active subscription
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        # No active subscription, check if there's a free plan
        query = """
        SELECT * FROM subscription_plans
        WHERE name = 'Free' AND is_active = TRUE
        """
        
        results = execute_query(query)
        
        if results and len(results) > 0:
            free_plan = dict(results[0])
            features = free_plan["features"]
            
            # Check if the feature is available in the free plan
            if feature in features:
                return {"has_access": True, "plan": free_plan}
            else:
                return {"has_access": False, "reason": "Feature not available in free plan"}
        else:
            return {"has_access": False, "reason": "No active subscription"}
    
    # Check if the feature is available in the user's plan
    features = subscription["features"]
    
    if feature in features:
        # Check usage limits if applicable
        if feature == "interviews_per_month":
            # Get the number of interviews this month
            query = """
            SELECT COUNT(*) as count FROM interview_sessions
            WHERE user_id = %s AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
            """
            
            results = execute_query(query, (user_id,))
            
            if results and len(results) > 0:
                count = results[0]["count"]
                limit = features[feature]
                
                # -1 means unlimited
                if limit == -1 or count < limit:
                    return {"has_access": True, "plan": subscription, "usage": count, "limit": limit}
                else:
                    return {"has_access": False, "reason": "Monthly interview limit reached", "usage": count, "limit": limit}
        
        # For other features, just check if they're enabled
        if isinstance(features[feature], bool):
            return {"has_access": features[feature], "plan": subscription}
        else:
            return {"has_access": True, "plan": subscription}
    else:
        return {"has_access": False, "reason": "Feature not available in current plan"} 