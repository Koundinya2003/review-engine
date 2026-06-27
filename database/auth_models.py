"""
Authentication models and endpoints.

Provides user management, JWT token handling, and role-based access control.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Integer, func
from sqlalchemy.orm import Session

from database.models import Base
from core import get_logger

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================================
# USER MODEL
# ============================================================================

class UserModel(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="viewer")  # admin, analyst, viewer
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ============================================================================
# USER REPOSITORY
# ============================================================================

class UserRepository:
    """Repository for user operations."""
    
    @staticmethod
    def create_user(
        db: Session,
        username: str,
        email: str,
        hashed_password: str,
        role: str = "viewer",
    ) -> UserModel:
        """Create new user."""
        try:
            user = UserModel(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=role,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created user: {username}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create user {username}: {e}")
            raise
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> UserModel | None:
        """Get user by username."""
        return db.query(UserModel).filter(UserModel.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> UserModel | None:
        """Get user by email."""
        return db.query(UserModel).filter(UserModel.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> UserModel | None:
        """Get user by ID."""
        return db.query(UserModel).filter(UserModel.id == user_id).first()
    
    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 50) -> tuple[list[UserModel], int]:
        """List users."""
        query = db.query(UserModel).filter(UserModel.is_active == 1)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total
    
    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs) -> UserModel | None:
        """Update user."""
        try:
            user = UserRepository.get_user_by_id(db, user_id)
            if not user:
                return None
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            logger.info(f"Updated user: {user.username}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update user {user_id}: {e}")
            raise
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Soft delete user."""
        user = UserRepository.get_user_by_id(db, user_id)
        if not user:
            return False
        
        user.is_active = 0
        db.commit()
        logger.info(f"Deactivated user: {user.username}")
        return True
    
    @staticmethod
    def update_last_login(db: Session, user_id: int) -> None:
        """Update last login timestamp."""
        db.query(UserModel).filter(UserModel.id == user_id).update(
            {UserModel.last_login: datetime.now(timezone.utc)}
        )
        db.commit()
