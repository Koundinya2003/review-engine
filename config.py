"""
Centralized configuration management system.

All configuration must come from environment variables or this file.
No hardcoded values should exist elsewhere in the codebase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    url: str = Field(
        default="sqlite:///./reviews.db",
        description="Database URL. SQLite for dev, PostgreSQL for production",
    )
    echo_sql: bool = Field(
        default=False,
        description="Log all SQL statements",
    )
    pool_size: int = Field(
        default=20,
        description="Number of database connections to maintain",
    )
    max_overflow: int = Field(
        default=40,
        description="Maximum overflow connections during peaks",
    )
    pool_recycle: int = Field(
        default=3600,
        description="Recycle connections every N seconds",
    )
    
    class Config:
        env_prefix = "DB_"


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""
    
    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="SentenceTransformer model name",
    )
    batch_size: int = Field(
        default=32,
        description="Batch size for encoding texts",
    )
    cache_dir: str = Field(
        default="./.models",
        description="Directory to cache downloaded models",
    )
    device: str = Field(
        default="cpu",
        description="Device for embeddings: cpu, cuda, mps",
    )
    
    class Config:
        env_prefix = "EMBEDDING_"
        protected_namespaces = ("settings_",)


class ClusteringSettings(BaseSettings):
    """Clustering/theme discovery configuration."""
    
    n_themes: int = Field(
        default=8,
        description="Target number of themes",
    )
    min_topic_size: int = Field(
        default=5,
        description="Minimum documents per theme",
    )
    language: str = Field(
        default="english",
        description="Language for NLP processing",
    )
    
    # UMAP parameters
    umap_n_neighbors: int = Field(
        default=15,
        description="UMAP neighborhood size",
    )
    umap_n_components: int = Field(
        default=5,
        description="UMAP reduced dimensions",
    )
    
    # HDBSCAN parameters
    hdbscan_min_cluster_size: int = Field(
        default=10,
        description="HDBSCAN minimum cluster size",
    )
    
    class Config:
        env_prefix = "CLUSTERING_"


class APISettings(BaseSettings):
    """FastAPI configuration."""
    
    title: str = Field(default="Review Discovery API")
    version: str = Field(default="1.0.0")
    description: str = Field(default="AI-powered review analysis engine")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        description="CORS allowed origins (restrict in production)",
    )
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    cors_headers: list[str] = Field(
        default=["*"],
    )
    
    # Pagination defaults
    default_limit: int = Field(default=50, ge=1)
    max_limit: int = Field(default=500, ge=1)
    default_search_limit: int = Field(default=20, ge=1)
    max_search_limit: int = Field(default=100, ge=1)
    
    # Rate limiting (requests per minute)
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)  # seconds
    
    class Config:
        env_prefix = "API_"


class AuthSettings(BaseSettings):
    """Authentication configuration."""
    
    enabled: bool = Field(default=False, description="Enable authentication")
    secret_key: str = Field(
        default=None,
        description="JWT secret key (required for production - use environment variable)"
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    @validator('secret_key', pre=True, always=True)
    def validate_secret_key(cls, v):
        """Ensure secret key is set, generate random if not provided."""
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and not v:
            raise ValueError(
                "AUTH_SECRET_KEY environment variable must be set in production"
            )
        # Generate random key if not provided in dev
        if not v:
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    class Config:
        env_prefix = "AUTH_"


class DashboardSettings(BaseSettings):
    """Streamlit dashboard configuration."""
    
    api_url: str = Field(default="http://localhost:8000")
    cache_ttl: int = Field(default=300, description="Cache results for N seconds")
    theme: str = Field(default="light")
    
    class Config:
        env_prefix = "DASHBOARD_"


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file: str | None = Field(default=None, description="Log file path")
    use_json: bool = Field(default=False, description="JSON structured logging")
    
    class Config:
        env_prefix = "LOG_"


class SchedulerSettings(BaseSettings):
    """Job scheduler configuration."""
    
    enabled: bool = Field(default=False)
    # Collection schedule (cron format)
    collection_schedule: str = Field(default="0 * * * *")  # Every hour
    # Analysis schedule
    analysis_schedule: str = Field(default="0 2 * * *")  # 2 AM daily
    
    class Config:
        env_prefix = "SCHEDULER_"


class Settings(BaseSettings):
    """Root settings combining all subsystems."""
    
    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    
    # Subsystems
    database: DatabaseSettings = DatabaseSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    clustering: ClusteringSettings = ClusteringSettings()
    api: APISettings = APISettings()
    auth: AuthSettings = AuthSettings()
    dashboard: DashboardSettings = DashboardSettings()
    logging: LoggingSettings = LoggingSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get global settings instance (cached)."""
    return Settings()


# Export for convenience
settings = get_settings()


def validate_production_settings():
    """Validate that production settings are properly configured."""
    s = settings
    
    if s.environment != "production":
        return  # No validation needed for non-production
    
    errors = []
    
    # Check secret key
    if not s.auth.secret_key or s.auth.secret_key == "dev-secret-key":
        errors.append("AUTH_SECRET_KEY must be set in production (not empty or 'dev-secret-key')")
    
    # Check CORS
    if "*" in s.api.cors_origins:
        errors.append("CORS origins cannot be '*' in production - must specify exact domains")
    
    # Check authentication
    if not s.auth.enabled:
        errors.append("Authentication must be enabled in production (AUTH_ENABLED=true)")
    
    # Check database
    if s.database.url.startswith("sqlite"):
        errors.append("SQLite cannot be used in production - must use PostgreSQL")
    
    # Log and raise if errors found
    if errors:
        from core import get_logger
        logger = get_logger(__name__)
        error_msg = "\n".join(f"  • {e}" for e in errors)
        logger.error(f"Production settings validation FAILED:\n{error_msg}")
        raise ValueError(f"Production configuration errors:\n{error_msg}")
