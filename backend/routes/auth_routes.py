from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
from datetime import timedelta
import json

from models.user import UserCreate, UserResponse, UserLogin, UserUpdate, Auth0Profile
from services.auth_service import (
    authenticate_user, create_user, create_access_token, 
    get_current_active_user, get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, create_or_update_auth0_user
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=Dict[str, Any])
async def register_user(user: UserCreate):
    """
    Register a new user
    """
    db_user = create_user(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_user["id"])},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": db_user
    }

@router.post("/token", response_model=Dict[str, Any])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/login", response_model=Dict[str, Any])
async def login(user_data: UserLogin):
    """
    Login with email and password
    """
    user = authenticate_user(user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=access_token_expires
    )
    
    # Update last login timestamp
    # This would be handled in a real implementation
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/auth0-callback", response_model=Dict[str, Any])
async def auth0_callback(profile: Auth0Profile):
    """
    Handle Auth0 authentication callback
    """
    # Create or update user from Auth0 profile
    user = create_or_update_auth0_user(profile)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=Dict[str, Any])
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get current user profile
    """
    return current_user

@router.put("/me", response_model=Dict[str, Any])
async def update_user_me(
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update current user profile
    """
    # Build the update query dynamically based on provided fields
    update_fields = []
    params = []
    
    if user_update.full_name is not None:
        update_fields.append("full_name = %s")
        params.append(user_update.full_name)
        
    if user_update.email is not None:
        update_fields.append("email = %s")
        params.append(user_update.email)
        
    if user_update.password is not None:
        from services.auth_service import get_password_hash
        hashed_password = get_password_hash(user_update.password)
        update_fields.append("password_hash = %s")
        params.append(hashed_password)
    
    # Add updated_at timestamp
    update_fields.append("updated_at = NOW()")
    
    # If no fields to update, return the current user
    if not update_fields:
        return current_user
    
    # Build and execute the query
    from database.db import execute_query
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s RETURNING *"
    params.append(current_user["id"])
    
    results = execute_query(query, tuple(params))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to update user"
    )

@router.get("/users", response_model=list)
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Get all users (admin only)
    """
    from database.db import execute_query
    query = "SELECT * FROM users ORDER BY id LIMIT %s OFFSET %s"
    results = execute_query(query, (limit, skip))
    
    return results

@router.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Get a specific user by ID (admin only)
    """
    from database.db import execute_query
    query = "SELECT * FROM users WHERE id = %s"
    results = execute_query(query, (user_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

@router.put("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """
    Update a specific user (admin only)
    """
    # Build the update query dynamically based on provided fields
    update_fields = []
    params = []
    
    if user_update.full_name is not None:
        update_fields.append("full_name = %s")
        params.append(user_update.full_name)
        
    if user_update.email is not None:
        update_fields.append("email = %s")
        params.append(user_update.email)
        
    if user_update.password is not None:
        from services.auth_service import get_password_hash
        hashed_password = get_password_hash(user_update.password)
        update_fields.append("password_hash = %s")
        params.append(hashed_password)
        
    if user_update.is_active is not None:
        update_fields.append("is_active = %s")
        params.append(user_update.is_active)
    
    # Add updated_at timestamp
    update_fields.append("updated_at = NOW()")
    
    # If no fields to update, return error
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Build and execute the query
    from database.db import execute_query
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s RETURNING *"
    params.append(user_id)
    
    results = execute_query(query, tuple(params))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    ) 