"""
Database connection and session management.

Handles database initialization, connection pooling, and session lifecycle
with support for both SQLite and PostgreSQL.
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from core import get_logger

logger = get_logger(__name__)


def create_db_engine():
    """Create database engine with appropriate configuration."""
    
    logger.info(f"Initializing database: {settings.database.url}")
    
    engine_kwargs = {
        "echo": settings.database.echo_sql,
        "pool_pre_ping": True,  # Verify connections before using
    }
    
    if settings.database.url.startswith("sqlite"):
        # SQLite configuration
        from sqlalchemy.pool import NullPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = NullPool
        logger.debug("Using SQLite with NullPool")
    else:
        # PostgreSQL configuration
        engine_kwargs["pool_size"] = settings.database.pool_size
        engine_kwargs["max_overflow"] = settings.database.max_overflow
        engine_kwargs["pool_recycle"] = settings.database.pool_recycle
        logger.debug(
            f"Using PostgreSQL with pool_size={settings.database.pool_size}, "
            f"max_overflow={settings.database.max_overflow}"
        )
    
    engine = create_engine(settings.database.url, **engine_kwargs)
    
    # Add event listeners for connection debugging
    if settings.debug:
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            logger.debug("Database connection returned to pool")
    
    return engine


# Module-level engine and session factory
_engine = None
_session_factory = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_session() -> Session:
    """Get a database session."""
    factory = get_session_factory()
    return factory()


@contextmanager
def session_scope():
    """
    Provide a transactional scope for database operations.
    
    Usage:
        with session_scope() as session:
            session.add(obj)
            # Transaction commits automatically or rolls back on error
    """
    session = get_session()
    try:
        yield session
        session.commit()
        logger.debug("Transaction committed")
    except Exception as e:
        session.rollback()
        logger.error(f"Transaction rolled back: {e}")
        raise
    finally:
        session.close()


def init_db():
    """Initialize database schema."""
    from database.models import Base
    
    logger.info("Initializing database schema")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized")


def close_db():
    """Close database connections."""
    global _engine, _session_factory
    
    if _engine is not None:
        logger.info("Closing database engine")
        _engine.dispose()
        _engine = None
        _session_factory = None
