"""
Production initialization script.

Sets up admin user, verifies database connection, and initializes the application.
Run this before starting the application for the first time.
"""

from __future__ import annotations

import argparse
import sys
from getpass import getpass

from database.connection import engine, get_session, init_db
from database.auth_models import UserRepository
from api.security import hash_password
from core import get_logger

logger = get_logger(__name__)


def setup_database():
    """Initialize database schema."""
    logger.info("Initializing database schema...")
    init_db()
    logger.info("✅ Database schema initialized")


def verify_database_connection():
    """Verify database connectivity."""
    logger.info("Verifying database connection...")
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("✅ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def create_admin_user(username: str, email: str, password: str):
    """Create admin user."""
    logger.info(f"Creating admin user: {username}")
    
    session = get_session()
    
    try:
        # Check if user exists
        existing = UserRepository.get_user_by_username(session, username)
        if existing:
            logger.warning(f"⚠️ User already exists: {username}")
            session.close()
            return False
        
        # Create user
        hashed_password = hash_password(password)
        user = UserRepository.create_user(
            session,
            username=username,
            email=email,
            hashed_password=hashed_password,
            role="admin",
        )
        
        logger.info(f"✅ Admin user created: {username}")
        session.close()
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to create user: {e}")
        session.close()
        return False


def main():
    """Run production initialization."""
    parser = argparse.ArgumentParser(description="Production initialization script")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--email", help="Admin email")
    parser.add_argument("--password", help="Admin password (will prompt if not provided)")
    parser.add_argument("--skip-admin", action="store_true", help="Skip admin user creation")
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting production initialization...")
    
    # Step 1: Verify database connection
    if not verify_database_connection():
        logger.error("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Step 2: Initialize database
    setup_database()
    
    # Step 3: Create admin user
    if not args.skip_admin:
        username = args.username
        email = args.email
        password = args.password
        
        # Prompt if not provided
        if not username:
            username = input("Admin username: ").strip()
        if not email:
            email = input("Admin email: ").strip()
        if not password:
            password = getpass("Admin password: ")
            password_confirm = getpass("Confirm password: ")
            if password != password_confirm:
                logger.error("❌ Passwords do not match")
                sys.exit(1)
        
        # Validate inputs
        if not all([username, email, password]):
            logger.error("❌ All fields required")
            sys.exit(1)
        
        if len(password) < 8:
            logger.error("❌ Password must be at least 8 characters")
            sys.exit(1)
        
        if "@" not in email:
            logger.error("❌ Invalid email format")
            sys.exit(1)
        
        if not create_admin_user(username, email, password):
            logger.warning("⚠️ Admin user creation failed or already exists")
    
    logger.info("✅ Production initialization complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Set environment variables in .env.production")
    logger.info("2. Run migrations: alembic upgrade head")
    logger.info("3. Start API: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000")
    logger.info("4. Start dashboard: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
