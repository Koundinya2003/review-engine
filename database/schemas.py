"""
Pydantic schemas for database models.

Provides request/response validation and serialization for all database entities.
Separates API contracts from database models following best practices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# REVIEW SCHEMAS
# ============================================================================

class ReviewBase(BaseModel):
    """Base review data (shared fields)."""
    
    source: str = Field(..., description="Review source (app-store, play-store, reddit)")
    app_name: str = Field(..., description="Application name")
    reviewer: str = Field(default="Unknown", description="Reviewer name")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    title: str = Field(..., min_length=1, description="Review title")
    text: str = Field(..., min_length=1, description="Review content")
    url: Optional[str] = Field(None, description="URL to review")
    source_metadata: Optional[dict[str, Any]] = Field(None, description="Source-specific data")
    
    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source is one of supported values."""
        allowed = {"app-store", "play-store", "reddit"}
        if v.lower() not in allowed:
            raise ValueError(f"source must be one of {allowed}")
        return v.lower()


class ReviewCreate(ReviewBase):
    """Review creation request."""
    
    external_id: Optional[str] = Field(None, description="External ID from source")
    date: Optional[datetime] = Field(None, description="Review date")


class ReviewUpdate(BaseModel):
    """Review update request (partial)."""
    
    theme: Optional[str] = None
    theme_confidence: Optional[float] = Field(None, ge=0, le=1)
    sentiment: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ReviewResponse(ReviewBase):
    """Review response (full data)."""
    
    id: int = Field(..., description="Database ID")
    external_id: str = Field(..., description="External ID")
    date: datetime = Field(..., description="Review date")
    theme: Optional[str] = None
    theme_confidence: Optional[float] = None
    sentiment: Optional[str] = None
    embedding: Optional[list[float]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ReviewPaginatedResponse(BaseModel):
    """Paginated review response."""
    
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Skip offset")
    limit: int = Field(..., description="Result limit")
    items: list[ReviewResponse]


# ============================================================================
# THEME SCHEMAS
# ============================================================================

class ThemeBase(BaseModel):
    """Base theme data."""
    
    theme_name: str = Field(..., min_length=1, description="Theme name")
    description: str = Field(default="", description="Theme description")
    keywords: Optional[list[str]] = Field(None, description="Keywords for theme")


class ThemeCreate(ThemeBase):
    """Theme creation."""
    
    topic_id: int = Field(..., description="BERTopic topic ID")
    count: int = Field(default=0, ge=0)


class ThemeUpdate(BaseModel):
    """Theme update (partial)."""
    
    description: Optional[str] = None
    keywords: Optional[list[str]] = None


class ThemeResponse(ThemeBase):
    """Theme response."""
    
    id: int
    topic_id: int
    count: int
    keywords: Optional[list[str]]
    top_reviews: Optional[list[dict[str, Any]]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ThemePaginatedResponse(BaseModel):
    """Paginated theme response."""
    
    total: int
    skip: int
    limit: int
    items: list[ThemeResponse]


# ============================================================================
# SEARCH SCHEMAS
# ============================================================================

class SemanticSearchRequest(BaseModel):
    """Semantic search request."""
    
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=20, ge=1, le=100)
    threshold: Optional[float] = Field(None, ge=0, le=1, description="Similarity threshold")
    filters: Optional[dict[str, Any]] = None


class SearchResult(BaseModel):
    """Single search result with similarity score."""
    
    review: ReviewResponse
    score: float = Field(..., ge=0, le=1, description="Similarity score")
    rank: int = Field(..., ge=1)


class SearchResponse(BaseModel):
    """Search results response."""
    
    query: str
    total_results: int
    limit: int
    results: list[SearchResult]


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class SentimentBreakdown(BaseModel):
    """Sentiment distribution."""
    
    positive: int
    negative: int
    neutral: int
    unknown: int
    
    @property
    def total(self) -> int:
        """Total reviews."""
        return self.positive + self.negative + self.neutral + self.unknown
    
    @property
    def positive_percentage(self) -> float:
        """Positive sentiment percentage."""
        return (self.positive / self.total * 100) if self.total > 0 else 0


class RatingBreakdown(BaseModel):
    """Rating distribution."""
    
    one_star: int
    two_star: int
    three_star: int
    four_star: int
    five_star: int
    
    @property
    def average(self) -> float:
        """Average rating."""
        total = self.one_star + self.two_star + self.three_star + self.four_star + self.five_star
        if total == 0:
            return 0
        weighted = (
            self.one_star * 1 +
            self.two_star * 2 +
            self.three_star * 3 +
            self.four_star * 4 +
            self.five_star * 5
        )
        return weighted / total


class AnalyticsResponse(BaseModel):
    """Analytics aggregation."""
    
    total_reviews: int = Field(..., description="Total review count")
    average_rating: float = Field(..., description="Average rating")
    sentiment_breakdown: SentimentBreakdown
    rating_breakdown: RatingBreakdown
    unique_themes: int = Field(..., description="Number of unique themes")
    unique_sources: int = Field(..., description="Number of unique sources")
    reviews_by_source: dict[str, int]
    top_themes: list[dict[str, Any]]


# ============================================================================
# PROCESSING JOB SCHEMAS
# ============================================================================

class JobStatus(BaseModel):
    """Job status."""
    
    job_id: str
    status: str = Field(..., description="Status: pending, running, completed, failed")
    job_type: str = Field(..., description="Type: collection, analysis, refresh")
    progress: int = Field(default=0, ge=0, le=100)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# HEALTH CHECK SCHEMAS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Status: healthy, degraded, unhealthy")
    timestamp: datetime
    database: str = Field(..., description="Database status")
    services: dict[str, str] = Field(default_factory=dict)
    version: str = Field(default="1.0.0")
