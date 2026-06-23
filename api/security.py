"""
API security module for authentication and authorization.

Provides JWT token handling, password hashing, and permission checking.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from core import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT security
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.auth.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )
    
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Get current authenticated user from token."""
    if not settings.auth.enabled:
        # No authentication required
        return {"user_id": "system", "role": "admin"}
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    return {
        "user_id": user_id,
        "role": payload.get("role", "viewer"),
        "scopes": payload.get("scopes", []),
    }


def require_role(required_role: str):
    """Decorator to require specific role."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        role_hierarchy = {
            "admin": 3,
            "analyst": 2,
            "viewer": 1,
        }
        
        user_role_level = role_hierarchy.get(current_user.get("role"), 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_role_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return current_user
    
    return role_checker


def require_scope(required_scope: str):
    """Decorator to require specific scope."""
    async def scope_checker(current_user: dict = Depends(get_current_user)):
        scopes = current_user.get("scopes", [])
        
        if required_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return current_user
    
    return scope_checker
