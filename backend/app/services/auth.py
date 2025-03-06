"""
Authentication Service
-------------------
This module contains the authentication service for the application.
"""

import os
import logging
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any
from jose import jwk, jwt as jose_jwt
from jose.utils import base64url_decode
import json
import requests

from app.database.db import execute_query, get_db_connection
from app.models.user import UserCreate, UserResponse, Auth0Profile
from app.services.subscription import get_user_subscription, get_subscription_plan_by_id

# Configure logging
logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Auth0 settings
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE", "")
AUTH0_ALGORITHMS = ["RS256"]
AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

# JWT token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a new JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    """
    Verify a password against a hash
    
    This function handles various edge cases:
    - Malformed hashes (not starting with $2b$)
    - Empty or None passwords
    - Exceptions during verification
    """
    if not plain_password or not hashed_password:
        logger.error("Empty password or hash provided")
        return False
        
    try:
        # Check if the hash is properly formatted
        if not isinstance(hashed_password, str) or not hashed_password.startswith('$2b$'):
            logger.warning(f"Malformed password hash detected: {hashed_password[:10]}...")
            return False
            
        # Verify the password
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def get_password_hash(password):
    """
    Get password hash
    
    This function handles various edge cases:
    - Empty or None passwords
    - Exceptions during hashing
    """
    if not password:
        logger.error("Empty password provided for hashing")
        raise ValueError("Password cannot be empty")
        
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

# User authentication functions
def get_user_by_email(email: str):
    """Get a user by email"""
    query = "SELECT * FROM users WHERE email = %s"
    results = execute_query(query, (email,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def authenticate_user(email: str, password: str):
    """
    Authenticate a user with email and password
    
    This function handles various edge cases:
    - Empty or None email/password
    - User not found
    - Invalid password
    - Exceptions during authentication
    """
    if not email or not password:
        logger.error("Empty email or password provided for authentication")
        return False
        
    try:
        # Get the user by email
        user = get_user_by_email(email)
        
        if not user:
            logger.warning(f"Authentication failed: User with email {email} not found")
            return False
        
        # Verify the password
        if not verify_password(password, user["password_hash"]):
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            return False
        
        # Update last login timestamp
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET last_login = %s WHERE id = %s",
                (datetime.utcnow(), user["id"])
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating last login timestamp: {str(e)}")
            # Continue with authentication even if updating timestamp fails
        
        return user
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        return False

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current user from the JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = get_user_by_email(email)
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get the current active user"""
    if not current_user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    # Add subscription information
    subscription = get_user_subscription(current_user["id"])
    
    if subscription:
        plan = get_subscription_plan_by_id(subscription["subscription_plan_id"])
        current_user["subscription"] = {
            "id": subscription["id"],
            "status": subscription["status"],
            "current_period_end": subscription["current_period_end"],
            "plan": plan
        }
    
    return current_user

# Auth0 authentication
async def get_auth0_public_key():
    """Get Auth0 public key for JWT verification"""
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    jwks = requests.get(jwks_url).json()
    return jwks

async def verify_auth0_token(token: str):
    """Verify an Auth0 JWT token"""
    try:
        jwks = await get_auth0_public_key()
        unverified_header = jose_jwt.get_unverified_header(token)
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        payload = jose_jwt.decode(
            token,
            rsa_key,
            algorithms=AUTH0_ALGORITHMS,
            audience=AUTH0_API_AUDIENCE,
            issuer=AUTH0_ISSUER
        )
        
        return payload
        
    except jose_jwt.JWTError as e:
        logger.error(f"JWT error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) 