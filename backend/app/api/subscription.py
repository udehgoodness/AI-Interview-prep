"""
Subscription API
-------------
This module contains the subscription API endpoints.
"""

import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from typing import Dict, Any, List

from app.models.subscription import (
    SubscriptionPlanResponse,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    UserSubscriptionResponse,
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    PaymentHistoryResponse,
    StripeWebhookEvent
)
from app.services.auth import get_current_active_user
from app.services.subscription import (
    get_all_subscription_plans,
    get_subscription_plan_by_id,
    create_subscription_plan,
    update_subscription_plan,
    delete_subscription_plan,
    get_user_subscription,
    create_user_subscription,
    update_user_subscription,
    cancel_user_subscription,
    get_user_payment_history,
    create_payment_history,
    STRIPE_WEBHOOK_SECRET
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/subscription", tags=["Subscription"])

# Subscription plan endpoints
@router.get("/plans", response_model=List[Dict[str, Any]])
async def get_subscription_plans(active_only: bool = True):
    """
    Get all subscription plans
    """
    plans = get_all_subscription_plans(active_only)
    return plans

@router.get("/plans/{plan_id}", response_model=Dict[str, Any])
async def get_subscription_plan(plan_id: int):
    """
    Get a subscription plan by ID
    """
    plan = get_subscription_plan_by_id(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    return plan

@router.post("/plans", response_model=Dict[str, Any])
async def create_new_subscription_plan(
    plan: SubscriptionPlanCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create a new subscription plan
    """
    # Check if user is admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create subscription plans"
        )
    
    result = create_subscription_plan(plan)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription plan"
        )
    
    return result

@router.put("/plans/{plan_id}", response_model=Dict[str, Any])
async def update_existing_subscription_plan(
    plan_id: int,
    plan: SubscriptionPlanUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update a subscription plan
    """
    # Check if user is admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update subscription plans"
        )
    
    result = update_subscription_plan(plan_id, plan)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    return result

@router.delete("/plans/{plan_id}", response_model=Dict[str, Any])
async def delete_existing_subscription_plan(
    plan_id: int,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Delete a subscription plan
    """
    # Check if user is admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete subscription plans"
        )
    
    result = delete_subscription_plan(plan_id)
    
    return result

# User subscription endpoints
@router.get("/user", response_model=Dict[str, Any])
async def get_user_current_subscription(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get the current user's subscription
    """
    subscription = get_user_subscription(current_user["id"])
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for this user"
        )
    
    # Get the subscription plan
    plan = get_subscription_plan_by_id(subscription["subscription_plan_id"])
    
    if plan:
        subscription["plan"] = plan
    
    return subscription

@router.post("/user", response_model=Dict[str, Any])
async def create_user_new_subscription(
    subscription_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create a new subscription for the current user
    """
    # Get the plan
    plan_id = subscription_data.get("plan_id")
    
    if not plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan ID is required"
        )
    
    plan = get_subscription_plan_by_id(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Check if user already has a subscription
    existing_subscription = get_user_subscription(current_user["id"])
    
    if existing_subscription and existing_subscription["status"] == "active":
        # Cancel the existing subscription
        cancel_user_subscription(existing_subscription["id"])
    
    # Create a Stripe customer if not exists
    stripe_customer_id = subscription_data.get("stripe_customer_id")
    
    if not stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=current_user["email"],
                name=current_user["full_name"]
            )
            stripe_customer_id = customer.id
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating Stripe customer"
            )
    
    # Create a Stripe subscription
    try:
        # Get the price ID based on the billing interval
        billing_interval = subscription_data.get("billing_interval", "monthly")
        price_id = plan["stripe_price_id_monthly"]
        
        if billing_interval == "yearly":
            price_id = plan["stripe_price_id_yearly"]
        
        # Create the subscription
        stripe_subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[
                {"price": price_id},
            ],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        
        # Create the subscription in the database
        from datetime import datetime
        
        subscription = UserSubscriptionCreate(
            user_id=current_user["id"],
            subscription_plan_id=plan_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription.id,
            status=stripe_subscription.status,
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
            cancel_at_period_end=stripe_subscription.cancel_at_period_end
        )
        
        result = create_user_subscription(subscription)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create subscription"
            )
        
        # Return the client secret for the payment intent
        return {
            "subscription_id": result["id"],
            "stripe_subscription_id": stripe_subscription.id,
            "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret,
            "status": stripe_subscription.status
        }
        
    except Exception as e:
        logger.error(f"Error creating Stripe subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating subscription: {str(e)}"
        )

@router.put("/user/{subscription_id}", response_model=Dict[str, Any])
async def update_user_existing_subscription(
    subscription_id: int,
    subscription: UserSubscriptionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update a user subscription
    """
    # Check if the subscription belongs to the user
    existing_subscription = get_user_subscription(current_user["id"])
    
    if not existing_subscription or existing_subscription["id"] != subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    result = update_user_subscription(subscription_id, subscription)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )
    
    return result

@router.delete("/user/{subscription_id}", response_model=Dict[str, Any])
async def cancel_user_existing_subscription(
    subscription_id: int,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Cancel a user subscription
    """
    # Check if the subscription belongs to the user
    existing_subscription = get_user_subscription(current_user["id"])
    
    if not existing_subscription or existing_subscription["id"] != subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    result = cancel_user_subscription(subscription_id)
    
    return result

@router.get("/payment-history", response_model=List[Dict[str, Any]])
async def get_user_payments(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get the current user's payment history
    """
    payments = get_user_payment_history(current_user["id"])
    return payments

@router.post("/webhook", response_model=Dict[str, Any])
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    """
    # Get the webhook signature
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    # Get the request body
    payload = await request.body()
    
    try:
        # Verify the webhook signature
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature"
        )
    
    # Handle the event
    if event["type"] == "invoice.payment_succeeded":
        # Payment succeeded, update the subscription status
        invoice = event["data"]["object"]
        subscription_id = invoice["subscription"]
        
        # Find the user subscription
        from app.database.db import execute_query
        
        query = "SELECT * FROM user_subscriptions WHERE stripe_subscription_id = %s"
        results = execute_query(query, (subscription_id,))
        
        if results and len(results) > 0:
            user_subscription = dict(results[0])
            
            # Update the subscription status
            update_user_subscription(
                user_subscription["id"],
                UserSubscriptionUpdate(status="active")
            )
            
            # Create a payment history entry
            payment_intent = invoice["payment_intent"]
            
            if payment_intent:
                from app.models.subscription import PaymentHistoryCreate
                from decimal import Decimal
                
                payment = PaymentHistoryCreate(
                    user_id=user_subscription["user_id"],
                    subscription_id=user_subscription["id"],
                    stripe_payment_intent_id=payment_intent,
                    amount=Decimal(invoice["amount_paid"]) / 100,  # Convert from cents
                    currency=invoice["currency"],
                    status="succeeded",
                    payment_method_type=invoice.get("payment_method_details", {}).get("type")
                )
                
                create_payment_history(payment)
    
    elif event["type"] == "invoice.payment_failed":
        # Payment failed, update the subscription status
        invoice = event["data"]["object"]
        subscription_id = invoice["subscription"]
        
        # Find the user subscription
        from app.database.db import execute_query
        
        query = "SELECT * FROM user_subscriptions WHERE stripe_subscription_id = %s"
        results = execute_query(query, (subscription_id,))
        
        if results and len(results) > 0:
            user_subscription = dict(results[0])
            
            # Update the subscription status
            update_user_subscription(
                user_subscription["id"],
                UserSubscriptionUpdate(status="past_due")
            )
    
    elif event["type"] == "customer.subscription.deleted":
        # Subscription deleted, update the subscription status
        subscription = event["data"]["object"]
        subscription_id = subscription["id"]
        
        # Find the user subscription
        from app.database.db import execute_query
        
        query = "SELECT * FROM user_subscriptions WHERE stripe_subscription_id = %s"
        results = execute_query(query, (subscription_id,))
        
        if results and len(results) > 0:
            user_subscription = dict(results[0])
            
            # Update the subscription status
            update_user_subscription(
                user_subscription["id"],
                UserSubscriptionUpdate(status="canceled")
            )
    
    return {"status": "success"} 