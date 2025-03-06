"""
Authentication API
---------------
This module contains the authentication API endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any

from app.models.user import UserCreate, UserLogin, UserResponse, Auth0Profile
from app.services.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_active_user,
    verify_auth0_token
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Get an access token for authentication
    """
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user["email"]})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    """
    Register a new user
    """
    from app.services.auth import get_user_by_email
    
    # Check if user already exists
    existing_user = get_user_by_email(user.email)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create the user
    from app.database.db import execute_query
    from app.services.auth import get_password_hash
    
    hashed_password = get_password_hash(user.password)
    
    query = """
    INSERT INTO users (email, full_name, password, is_active, is_admin)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, email, full_name, is_active, is_admin, created_at
    """
    
    params = (user.email, user.full_name, hashed_password, True, False)
    
    results = execute_query(query, params)
    
    if not results or len(results) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    new_user = dict(results[0])
    
    # Create a free subscription for the user
    from app.services.subscription import create_user_subscription, get_all_subscription_plans
    from app.models.subscription import UserSubscriptionCreate
    from datetime import datetime, timedelta
    import stripe
    
    # Get the free plan
    plans = get_all_subscription_plans()
    free_plan = None
    
    for plan in plans:
        if plan["name"].lower() == "free":
            free_plan = plan
            break
    
    if not free_plan:
        logger.warning("No free plan found, skipping subscription creation")
        return UserResponse(
            id=new_user["id"],
            email=new_user["email"],
            full_name=new_user["full_name"],
            is_active=new_user["is_active"],
            is_admin=new_user["is_admin"],
            created_at=new_user["created_at"]
        )
    
    # Create a Stripe customer
    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name
        )
        
        # Create a subscription
        now = datetime.utcnow()
        end_date = now + timedelta(days=30)
        
        subscription = UserSubscriptionCreate(
            user_id=new_user["id"],
            subscription_plan_id=free_plan["id"],
            stripe_customer_id=customer.id,
            stripe_subscription_id="free_tier",
            status="active",
            current_period_start=now,
            current_period_end=end_date,
            cancel_at_period_end=False
        )
        
        subscription_result = create_user_subscription(subscription)
        
        if subscription_result:
            logger.info(f"Created free subscription for user {new_user['id']}")
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
    
    return UserResponse(
        id=new_user["id"],
        email=new_user["email"],
        full_name=new_user["full_name"],
        is_active=new_user["is_active"],
        is_admin=new_user["is_admin"],
        created_at=new_user["created_at"]
    )

@router.post("/auth0", response_model=Dict[str, Any])
async def auth0_login(auth0_token: str = Body(..., embed=True)):
    """
    Login with Auth0
    """
    try:
        # Verify the Auth0 token
        payload = await verify_auth0_token(auth0_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Auth0 token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get the user profile from Auth0
        auth0_profile = Auth0Profile(
            sub=payload["sub"],
            email=payload["email"],
            name=payload.get("name"),
            nickname=payload.get("nickname"),
            picture=payload.get("picture"),
            email_verified=payload.get("email_verified", False)
        )
        
        # Check if user exists
        from app.services.auth import get_user_by_email
        
        user = get_user_by_email(auth0_profile.email)
        
        if not user:
            # Create the user
            from app.database.db import execute_query
            
            query = """
            INSERT INTO users (email, full_name, password, is_active, is_admin, auth0_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, email, full_name, is_active, is_admin, created_at
            """
            
            params = (
                auth0_profile.email, 
                auth0_profile.name or auth0_profile.nickname or auth0_profile.email,
                "auth0_user",  # Placeholder password
                True, 
                False,
                auth0_profile.sub
            )
            
            results = execute_query(query, params)
            
            if not results or len(results) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )
            
            user = dict(results[0])
            
            # Create a free subscription for the user
            from app.services.subscription import create_user_subscription, get_all_subscription_plans
            from app.models.subscription import UserSubscriptionCreate
            from datetime import datetime, timedelta
            import stripe
            
            # Get the free plan
            plans = get_all_subscription_plans()
            free_plan = None
            
            for plan in plans:
                if plan["name"].lower() == "free":
                    free_plan = plan
                    break
            
            if free_plan:
                # Create a Stripe customer
                try:
                    customer = stripe.Customer.create(
                        email=auth0_profile.email,
                        name=auth0_profile.name or auth0_profile.nickname or auth0_profile.email
                    )
                    
                    # Create a subscription
                    now = datetime.utcnow()
                    end_date = now + timedelta(days=30)
                    
                    subscription = UserSubscriptionCreate(
                        user_id=user["id"],
                        subscription_plan_id=free_plan["id"],
                        stripe_customer_id=customer.id,
                        stripe_subscription_id="free_tier",
                        status="active",
                        current_period_start=now,
                        current_period_end=end_date,
                        cancel_at_period_end=False
                    )
                    
                    subscription_result = create_user_subscription(subscription)
                    
                    if subscription_result:
                        logger.info(f"Created free subscription for user {user['id']}")
                except Exception as e:
                    logger.error(f"Error creating subscription: {str(e)}")
        
        # Create an access token
        access_token = create_access_token(data={"sub": user["email"]})
        
        return {"access_token": access_token, "token_type": "bearer", "user": user}
        
    except Exception as e:
        logger.error(f"Error in auth0_login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during Auth0 login"
        )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get the current user's information
    """
    return current_user 