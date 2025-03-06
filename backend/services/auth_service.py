import os
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import requests
from jose import jwk, jwt as jose_jwt
from jose.utils import base64url_decode
import json

from database.db import execute_query
from models.user import UserCreate, UserResponse, Auth0Profile
from services.subscription_service import get_user_subscription, get_subscription_plan_by_id

# Load environment variables
load_dotenv()

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
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password"""
    return pwd_context.hash(password)

# User authentication functions
def authenticate_user(email: str, password: str):
    """Authenticate a user with email and password"""
    user = get_user_by_email(email)
    
    if not user:
        return False
    
    if not verify_password(password, user.get("password_hash")):
        return False
    
    return user

def get_user_by_email(email: str):
    """Get a user by email"""
    query = "SELECT * FROM users WHERE email = %s"
    results = execute_query(query, (email,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def get_user_by_id(user_id: int):
    """Get a user by ID"""
    query = "SELECT * FROM users WHERE id = %s"
    results = execute_query(query, (user_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def get_user_by_auth0_id(auth0_id: str):
    """Get a user by Auth0 ID"""
    query = "SELECT * FROM users WHERE auth0_id = %s"
    results = execute_query(query, (auth0_id,))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    return None

def create_user(user: UserCreate):
    """Create a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password
    hashed_password = get_password_hash(user.password)
    
    # Insert the user into the database
    query = """
    INSERT INTO users (email, password_hash, full_name, created_at, updated_at)
    VALUES (%s, %s, %s, NOW(), NOW())
    RETURNING id, email, full_name, created_at, is_active, is_admin
    """
    
    results = execute_query(query, (user.email, hashed_password, user.full_name))
    
    if results and len(results) > 0:
        return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create user"
    )

def create_or_update_auth0_user(profile: Auth0Profile):
    """Create or update a user from Auth0 profile"""
    # Check if user already exists by Auth0 ID
    existing_user = get_user_by_auth0_id(profile.sub)
    
    if existing_user:
        # Update existing user
        query = """
        UPDATE users 
        SET email = %s, full_name = %s, updated_at = NOW(), last_login = NOW()
        WHERE auth0_id = %s
        RETURNING id, email, full_name, created_at, is_active, is_admin
        """
        
        full_name = profile.name or profile.nickname or profile.email.split('@')[0]
        results = execute_query(query, (profile.email, full_name, profile.sub))
        
        if results and len(results) > 0:
            return dict(results[0])
    else:
        # Check if user exists by email
        existing_user_by_email = get_user_by_email(profile.email)
        
        if existing_user_by_email:
            # Link existing user to Auth0
            query = """
            UPDATE users 
            SET auth0_id = %s, updated_at = NOW(), last_login = NOW()
            WHERE email = %s
            RETURNING id, email, full_name, created_at, is_active, is_admin
            """
            
            results = execute_query(query, (profile.sub, profile.email))
            
            if results and len(results) > 0:
                return dict(results[0])
        else:
            # Create new user
            full_name = profile.name or profile.nickname or profile.email.split('@')[0]
            
            query = """
            INSERT INTO users (email, full_name, auth0_id, created_at, updated_at, last_login)
            VALUES (%s, %s, %s, NOW(), NOW(), NOW())
            RETURNING id, email, full_name, created_at, is_active, is_admin
            """
            
            results = execute_query(query, (profile.email, full_name, profile.sub))
            
            if results and len(results) > 0:
                return dict(results[0])
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create or update user from Auth0"
    )

# Auth0 JWT validation
async def get_auth0_jwks():
    """Get Auth0 JSON Web Key Set"""
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    return response.json()

async def verify_auth0_token(token: str = Depends(oauth2_scheme)):
    """Verify Auth0 JWT token"""
    try:
        jwks = await get_auth0_jwks()
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
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        payload = jose_jwt.decode(
            token,
            rsa_key,
            algorithms=AUTH0_ALGORITHMS,
            audience=AUTH0_API_AUDIENCE,
            issuer=AUTH0_ISSUER,
        )
        
        # Create Auth0Profile from payload
        auth0_profile = Auth0Profile(
            sub=payload["sub"],
            email=payload["email"],
            name=payload.get("name"),
            nickname=payload.get("nickname"),
            picture=payload.get("picture"),
            email_verified=payload.get("email_verified", False)
        )
        
        # Get or create user from Auth0 profile
        user = create_or_update_auth0_user(auth0_profile)
        
        return user
    except jose_jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Get current user dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current authenticated user"""
    try:
        # First try to decode as Auth0 token
        try:
            user = await verify_auth0_token(token)
            
            # Add subscription data
            subscription = get_user_subscription(user["id"])
            if subscription:
                user["subscription"] = {
                    "id": subscription["id"],
                    "status": subscription["status"],
                    "current_period_end": subscription["current_period_end"],
                    "cancel_at_period_end": subscription["cancel_at_period_end"],
                    "plan": {
                        "id": subscription["subscription_plan_id"],
                        "name": subscription["name"],
                        "features": subscription["features"]
                    }
                }
            else:
                # If no active subscription, assign the free plan
                free_plan = get_subscription_plan_by_id(1)  # Assuming Free plan has ID 1
                if free_plan:
                    user["subscription"] = {
                        "status": "active",
                        "plan": {
                            "id": free_plan["id"],
                            "name": free_plan["name"],
                            "features": free_plan["features"]
                        }
                    }
            
            return user
        except:
            # If Auth0 validation fails, try local JWT
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            user = get_user_by_id(int(user_id))
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Add subscription data
            subscription = get_user_subscription(user["id"])
            if subscription:
                user["subscription"] = {
                    "id": subscription["id"],
                    "status": subscription["status"],
                    "current_period_end": subscription["current_period_end"],
                    "cancel_at_period_end": subscription["cancel_at_period_end"],
                    "plan": {
                        "id": subscription["subscription_plan_id"],
                        "name": subscription["name"],
                        "features": subscription["features"]
                    }
                }
            else:
                # If no active subscription, assign the free plan
                free_plan = get_subscription_plan_by_id(1)  # Assuming Free plan has ID 1
                if free_plan:
                    user["subscription"] = {
                        "status": "active",
                        "plan": {
                            "id": free_plan["id"],
                            "name": free_plan["name"],
                            "features": free_plan["features"]
                        }
                    }
                
            return user
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Get current active user dependency
async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get the current active user"""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

# Get current admin user dependency
async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """Get the current admin user"""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user 