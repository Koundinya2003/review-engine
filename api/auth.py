"""
Authentication API endpoints.

Provides login, registration, and token management endpoints.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from api.security import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user,
)
from config import settings
from core import get_logger, ValidationError
from database.connection import get_session
from database.auth_models import UserRepository, UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""
    
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response."""
    
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login: str | None
    
    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_session),
) -> TokenResponse:
    """Register new user."""
    
    if not settings.auth.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication not enabled",
        )
    
    # Check if user exists
    existing_username = UserRepository.get_user_by_username(db, request.username)
    if existing_username:
        logger.warning(f"Registration failed: username already exists: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    
    existing_email = UserRepository.get_user_by_email(db, request.email)
    if existing_email:
        logger.warning(f"Registration failed: email already exists: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    
    # Create user
    hashed_password = hash_password(request.password)
    user = UserRepository.create_user(
        db,
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        role="viewer",  # Default role
    )
    
    # Create token
    access_token_expires = timedelta(
        minutes=settings.auth.access_token_expire_minutes
    )
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )
    
    logger.info(f"User registered: {request.username}")
    
    return TokenResponse(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_session),
) -> TokenResponse:
    """Login user."""
    
    if not settings.auth.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication not enabled",
        )
    
    # Get user
    user = UserRepository.get_user_by_username(db, request.username)
    if not user or not user.is_active:
        logger.warning(f"Login failed: user not found: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        logger.warning(f"Login failed: invalid password: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Update last login
    UserRepository.update_last_login(db, user.id)
    
    # Create token
    access_token_expires = timedelta(
        minutes=settings.auth.access_token_expire_minutes
    )
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )
    
    logger.info(f"User logged in: {request.username}")
    
    return TokenResponse(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> UserResponse:
    """Get current user information."""
    
    user_id = int(current_user.get("user_id"))
    user = UserRepository.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    """Change password."""
    
    if not settings.auth.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication not enabled",
        )
    
    user_id = int(current_user.get("user_id"))
    user = UserRepository.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Verify old password
    if not verify_password(old_password, user.hashed_password):
        logger.warning(f"Password change failed: invalid old password for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid old password",
        )
    
    # Update password
    hashed_new_password = hash_password(new_password)
    UserRepository.update_user(db, user_id, hashed_password=hashed_new_password)
    
    logger.info(f"Password changed for user: {user.username}")
    
    return {"message": "Password changed successfully"}
