"""
Subscription Models
-----------------
This module contains the Pydantic models for subscription-related data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class SubscriptionPlanBase(BaseModel):
    """Base model for subscription plan data"""
    name: str
    description: Optional[str] = None
    price_monthly: Decimal
    price_yearly: Decimal
    features: Dict[str, Any]

class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Model for creating a new subscription plan"""
    stripe_price_id_monthly: str
    stripe_price_id_yearly: str
    is_active: bool = True

class SubscriptionPlanResponse(SubscriptionPlanBase):
    """Model for subscription plan response data"""
    id: int
    stripe_price_id_monthly: str
    stripe_price_id_yearly: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class SubscriptionPlanUpdate(BaseModel):
    """Model for updating subscription plan data"""
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = None
    price_yearly: Optional[Decimal] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class UserSubscriptionBase(BaseModel):
    """Base model for user subscription data"""
    user_id: int
    subscription_plan_id: int
    stripe_customer_id: str
    stripe_subscription_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False

class UserSubscriptionCreate(UserSubscriptionBase):
    """Model for creating a new user subscription"""
    pass

class UserSubscriptionResponse(UserSubscriptionBase):
    """Model for user subscription response data"""
    id: int
    created_at: datetime
    updated_at: datetime
    plan: Optional[SubscriptionPlanResponse] = None

class UserSubscriptionUpdate(BaseModel):
    """Model for updating user subscription data"""
    subscription_plan_id: Optional[int] = None
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    stripe_subscription_id: Optional[str] = None

class PaymentHistoryBase(BaseModel):
    """Base model for payment history data"""
    user_id: int
    subscription_id: Optional[int] = None
    stripe_payment_intent_id: str
    amount: Decimal
    currency: str = "USD"
    status: str
    payment_method_type: Optional[str] = None

class PaymentHistoryCreate(PaymentHistoryBase):
    """Model for creating a new payment history entry"""
    pass

class PaymentHistoryResponse(PaymentHistoryBase):
    """Model for payment history response data"""
    id: int
    created_at: datetime

class StripeWebhookEvent(BaseModel):
    """Model for Stripe webhook event data"""
    id: str
    type: str
    data: Dict[str, Any] 