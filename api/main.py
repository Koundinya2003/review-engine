"""
FastAPI application with comprehensive service integration.

Main entry point for the Review Discovery Engine API.
Includes middleware, exception handlers, and all service integrations.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api.middleware import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    db_exception_handler,
    exception_handler,
    general_exception_handler,
)
from api.security import get_current_user
from config import settings
from core import AppException, get_logger
from database.connection import get_session, init_db
from database.schemas import (
    ReviewCreate,
    ReviewPaginatedResponse,
    ReviewResponse,
    SemanticSearchRequest,
    SearchResponse,
    SearchResult,
    ThemePaginatedResponse,
    ThemeResponse,
    AnalyticsResponse,
    HealthResponse,
)
from services import (
    AnalyticsService,
    ClusteringService,
    ReviewService,
    VectorService,
)
from sqlalchemy.exc import SQLAlchemyError
from api.auth import router as auth_router
from core.metrics import get_metrics

logger = get_logger(__name__)


# ============================================================================
# LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Application starting...")
    init_db()
    logger.info("Database initialized")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    logger.info("Application shutting down...")
    try:
        from database.connection import get_engine
        engine = get_engine()
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# ============================================================================
# APPLICATION
# ============================================================================

app = FastAPI(
    title="Review Discovery API",
    version="2.0.0",
    description="AI-powered review discovery and analysis engine",
    lifespan=lifespan,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# Add middleware (order matters - first added, last executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

app.add_exception_handler(AppException, exception_handler)
app.add_exception_handler(SQLAlchemyError, db_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# ============================================================================
# ROUTER REGISTRATION
# ============================================================================

app.include_router(auth_router)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_session)) -> HealthResponse:
    """Check API and database health, verifying all critical services."""
    try:
        # Check database connectivity
        db_status = "ok"
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        # Check embedding service
        embedding_status = "ok"
        try:
            from services.embedding_service import EmbeddingService
            service = EmbeddingService.get_instance()
            if service is None or not hasattr(service, "model"):
                embedding_status = "error: not initialized"
            else:
                # Verify model is loaded
                _ = service.model.get_sentence_embedding_dimension()
        except Exception as e:
            embedding_status = f"error: {str(e)}"
            logger.warning(f"Embedding service health check failed: {e}")
        
        # Determine overall status
        services = {
            "embeddings": embedding_status,
            "clustering": "ok",
            "analytics": "ok",
        }
        
        overall_status = "healthy" if all(s == "ok" for s in services.values() and db_status == "ok") else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            database=db_status,
            services=services,
            version="2.0.0",
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database="error",
            services={},
            version="2.0.0",
        )


# ============================================================================
# REVIEW ENDPOINTS
# ============================================================================

@app.post("/api/v1/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> ReviewResponse:
    """Create a new review."""
    logger.info(f"Creating review for {review.source}")
    return ReviewService.create_review(db, review)


@app.get("/api/v1/reviews", response_model=ReviewPaginatedResponse)
async def list_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    source: str | None = None,
    theme: str | None = None,
    sentiment: str | None = None,
    min_rating: int | None = None,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> ReviewPaginatedResponse:
    """List reviews with filtering and pagination."""
    items, total = ReviewService.list_reviews(
        db,
        skip=skip,
        limit=limit,
        source=source,
        theme=theme,
        sentiment=sentiment,
        min_rating=min_rating,
    )
    return ReviewPaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@app.get("/api/v1/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> ReviewResponse:
    """Get single review by ID."""
    review = ReviewService.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/api/v1/reviews/bulk", response_model=dict)
async def bulk_create_reviews(
    reviews: list[ReviewCreate],
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Bulk create reviews."""
    return ReviewService.bulk_create_reviews(db, reviews)


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@app.post("/api/v1/search/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """Semantic similarity search."""
    # Validate parameters
    limit = min(max(1, request.limit or 20), settings.api.max_search_limit)
    threshold = max(0.0, min(1.0, request.threshold or 0.3))
    
    # Validate query
    if not request.query or len(request.query.strip()) < 2:
        raise HTTPException(
            status_code=422,
            detail="Query must be at least 2 characters long"
        )
    
    results = VectorService.search_semantic(
        db,
        request.query,
        top_k=limit,
        threshold=threshold,
    )
    
    search_results = [
        SearchResult(
            review=ReviewResponse.model_validate(review),
            score=score,
            rank=idx + 1,
        )
        for idx, (review, score) in enumerate(results)
    ]
    
    return SearchResponse(
        query=request.query,
        total_results=len(search_results),
        limit=request.limit,
        results=search_results,
    )


@app.post("/api/v1/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """Hybrid keyword + semantic search."""
    # Validate parameters
    limit = min(max(1, request.limit or 20), settings.api.max_search_limit)
    
    # Validate query
    if not request.query or len(request.query.strip()) < 2:
        raise HTTPException(
            status_code=422,
            detail="Query must be at least 2 characters long"
        )
    
    results = VectorService.search_hybrid(
        db,
        request.query,
        top_k=limit,
    )
    
    search_results = [
        SearchResult(
            review=ReviewResponse.model_validate(review),
            score=score,
            rank=idx + 1,
        )
        for idx, (review, score) in enumerate(results)
    ]
    
    return SearchResponse(
        query=request.query,
        total_results=len(search_results),
        limit=request.limit,
        results=search_results,
    )


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@app.post("/api/v1/analysis/discover-themes")
async def discover_themes(
    n_themes: int | None = None,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Discover themes from reviews."""
    logger.info("Starting theme discovery")
    return ClusteringService.discover_themes(db, n_themes)


@app.post("/api/v1/analysis/index-embeddings")
async def index_embeddings(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate and index embeddings for all reviews."""
    logger.info("Starting embedding indexing")
    count = VectorService.index_embeddings(db)
    return {"indexed_count": count}


# ============================================================================
# THEME ENDPOINTS
# ============================================================================

@app.get("/api/v1/themes", response_model=ThemePaginatedResponse)
async def list_themes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> ThemePaginatedResponse:
    """List themes."""
    from database.repository import ThemeRepository
    
    themes, total = ThemeRepository.list_themes(db, skip=skip, limit=limit)
    return ThemePaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[ThemeResponse.model_validate(t) for t in themes],
    )


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/v1/analytics/overview", response_model=AnalyticsResponse)
async def get_analytics(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> AnalyticsResponse:
    """Get comprehensive analytics overview."""
    return AnalyticsService.get_overview(db)


@app.get("/api/v1/analytics/themes/{theme_id}")
async def get_theme_analytics(
    theme_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get analytics for specific theme."""
    return AnalyticsService.get_theme_analytics(db, theme_id)


@app.get("/api/v1/analytics/sources/{source}")
async def get_source_analytics(
    source: str,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get analytics for specific source."""
    return AnalyticsService.get_source_analytics(db, source)


@app.get("/api/v1/analytics/trends")
async def get_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get trend data."""
    return AnalyticsService.get_trend_data(db, days)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Review Discovery Engine",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response
    return Response(content=get_metrics(), media_type="text/plain")
