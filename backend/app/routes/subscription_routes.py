from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Header
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from models.subscription import (
    SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate,
    UserSubscriptionCreate, UserSubscriptionResponse, UserSubscriptionUpdate,
    PaymentHistoryCreate, PaymentHistoryResponse, StripeWebhookEvent
)
from app.services.auth import get_current_active_user, get_current_admin_user
from app.services.subscription import (
    get_all_subscription_plans, get_subscription_plan_by_id, create_subscription_plan, update_subscription_plan,
    delete_subscription_plan, get_user_subscription, get_user_subscription_by_id, create_user_subscription,
    update_user_subscription, cancel_user_subscription, create_stripe_checkout_session,
    handle_stripe_webhook_event, get_user_payment_history, create_checkout_session
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

# Subscription plans endpoints
@router.get("/plans", response_model=List[Dict[str, Any]])
async def get_subscription_plans(active_only: bool = True):
    """
    Get all subscription plans
    """
    plans = get_all_subscription_plans(active_only)
    return plans

@router.get("/plans/{plan_id}", response_model=Dict[str, Any])
async def get_plan(plan_id: int):
    """
    Get a specific subscription plan by ID
    """
    plan = get_subscription_plan_by_id(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    return plan

@router.post("/plans", response_model=Dict[str, Any])
async def create_plan(
    plan: SubscriptionPlanCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Create a new subscription plan (admin only)
    """
    new_plan = create_subscription_plan(plan)
    return new_plan

@router.put("/plans/{plan_id}", response_model=Dict[str, Any])
async def update_plan(
    plan_id: int,
    plan_update: SubscriptionPlanUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Update a subscription plan (admin only)
    """
    updated_plan = update_subscription_plan(plan_id, plan_update)
    return updated_plan

# User subscription endpoints
@router.get("/my-subscription", response_model=Dict[str, Any])
async def get_my_subscription(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get the current user's active subscription
    """
    subscription = get_user_subscription(current_user["id"])
    
    if not subscription:
        # Return free plan if no active subscription
        free_plans = get_all_subscription_plans(active_only=True)
        free_plan = next((plan for plan in free_plans if plan["name"] == "Free"), None)
        
        if free_plan:
            return {
                "subscription": None,
                "plan": free_plan,
                "is_subscribed": False
            }
        else:
            return {
                "subscription": None,
                "plan": None,
                "is_subscribed": False
            }
    
    return {
        "subscription": subscription,
        "plan": {
            "id": subscription["id"],
            "name": subscription["name"],
            "description": subscription["description"],
            "price_monthly": subscription["price_monthly"],
            "price_yearly": subscription["price_yearly"],
            "features": subscription["features"]
        },
        "is_subscribed": True
    }

@router.post("/checkout", response_model=Dict[str, Any])
async def create_subscription_checkout(
    plan_id: int = Body(...),
    is_yearly: bool = Body(False),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Create a Stripe checkout session for subscription
    """
    checkout = create_checkout_session(current_user["id"], plan_id, is_yearly)
    return checkout

@router.post("/cancel", response_model=Dict[str, Any])
async def cancel_subscription(
    cancel_immediately: bool = Body(False),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Cancel the current user's subscription
    """
    result = cancel_user_subscription(current_user["id"], cancel_immediately)
    return {"status": "success", "subscription": result}

@router.get("/payment-history", response_model=List[Dict[str, Any]])
async def get_payment_history(
    limit: int = 10,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get the current user's payment history
    """
    payments = get_user_payment_history(current_user["id"], limit, offset)
    return payments

@router.post("/webhook", response_model=Dict[str, Any])
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None)
):
    """
    Handle Stripe webhook events
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    # Get the request body
    payload = await request.body()
    
    # Handle the webhook
    result = handle_stripe_webhook_event(payload, stripe_signature)
    return result

@router.get("/access/{feature}", response_model=Dict[str, Any])
async def check_feature_access(
    feature: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Check if the current user has access to a specific feature
    """
    access = check_user_subscription_access(current_user["id"], feature)
    return access

# Admin endpoints
@router.get("/users/{user_id}/subscription", response_model=Dict[str, Any])
async def get_user_subscription_admin(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Get a user's subscription (admin only)
    """
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found for this user"
        )
    
    return subscription

@router.put("/users/{user_id}/subscription/{subscription_id}", response_model=Dict[str, Any])
async def update_user_subscription_admin(
    user_id: int,
    subscription_id: int,
    subscription_update: UserSubscriptionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Update a user's subscription (admin only)
    """
    # Verify the subscription belongs to the user
    subscription = get_user_subscription_by_id(subscription_id)
    
    if not subscription or subscription["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found for this user"
        )
    
    updated_subscription = update_user_subscription(subscription_id, subscription_update)
    return updated_subscription 