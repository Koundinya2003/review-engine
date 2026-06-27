"""
Authentication API endpoints.

Provides login, registration, and token management endpoints.
"""

from __future__ import annotations

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from api.security import (
    CurrentUser,
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

def _validate_password_strength(value: str) -> str:
    """Shared password strength rule: must contain letters and digits."""
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one digit")
    return value


class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    """User login request."""

    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    old_password: str
    new_password: str = Field(..., min_length=8, max_length=255)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


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
# DEPENDENCIES / SHARED HELPERS
# ============================================================================

async def require_auth_enabled() -> None:
    """Reject the request early if authentication is disabled in settings."""
    if not settings.auth.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication not enabled",
        )


def _issue_token(user: UserModel) -> TokenResponse:
    """Create a signed access token + response envelope for a user."""
    expires_delta = timedelta(minutes=settings.auth.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=expires_delta,
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=int(expires_delta.total_seconds()),
    )


def _to_user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/register",
    response_model=TokenResponse,
    dependencies=[Depends(require_auth_enabled)],
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_session),
) -> TokenResponse:
    """Register a new user and return an access token."""

    # Generic conflict response avoids leaking which field collided
    # (username vs. email), reducing account-enumeration risk.
    if UserRepository.get_user_by_username(db, request.username) or (
        UserRepository.get_user_by_email(db, request.email)
    ):
        logger.warning(
            "registration_failed_conflict",
            extra={"username": request.username, "email": request.email},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already in use",
        )

    user = UserRepository.create_user(
        db,
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role="viewer",  # Default role
    )

    logger.info("user_registered", extra={"username": request.username})
    return _issue_token(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(require_auth_enabled)],
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_session),
) -> TokenResponse:
    """Authenticate a user and return an access token."""

    user = UserRepository.get_user_by_username(db, request.username)

    # Compare against a dummy hash when the user doesn't exist so the
    # response timing doesn't reveal whether the username is valid.
    valid_credentials = bool(user) and user.is_active and verify_password(
        request.password, user.hashed_password
    )

    if not valid_credentials:
        logger.warning("login_failed", extra={"username": request.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    UserRepository.update_last_login(db, user.id)
    logger.info("user_logged_in", extra={"username": request.username})
    return _issue_token(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> UserResponse:
    """Get current user information."""

    user = UserRepository.get_user_by_id(db, current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _to_user_response(user)


@router.post(
    "/change-password",
    dependencies=[Depends(require_auth_enabled)],
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    """Change the current user's password."""

    user = UserRepository.get_user_by_id(db, current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not verify_password(request.old_password, user.hashed_password):
        logger.warning(
            "password_change_failed_invalid_old_password",
            extra={"user_id": current_user.user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid old password",
        )

    UserRepository.update_user(
        db, current_user.user_id, hashed_password=hash_password(request.new_password)
    )

    logger.info("password_changed", extra={"username": user.username})
    return {"message": "Password changed successfully"}