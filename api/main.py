"""
FastAPI application with comprehensive service integration.

Main entry point for the Review Discovery Engine API.
Includes middleware, exception handlers, and all service integrations.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as PlainResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
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
from api.security import CurrentUser, get_current_user, require_role
from api.auth import router as auth_router
from config import settings
from core import AppException, get_logger
from core.metrics import get_metrics
from database.connection import get_session, init_db, get_engine
from database.repository import ThemeRepository
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
from services.embedding_service import EmbeddingService

logger = get_logger(__name__)


# ============================================================================
# STARTUP VALIDATION
# ============================================================================

def _validate_cors_settings() -> None:
    """Fail fast if CORS is configured in a way browsers will reject.

    A wildcard origin ("*") combined with allow_credentials=True is
    rejected by browsers (and is a real security footgun if it weren't) -
    catch it at startup instead of discovering it as a confusing CORS
    error in production.
    """
    if "*" in settings.api.cors_origins:
        raise RuntimeError(
            "CORS misconfiguration: cors_origins contains '*' while "
            "allow_credentials=True. List explicit origins instead."
        )


_validate_cors_settings()


# ============================================================================
# LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_starting")
    init_db()
    logger.info("database_initialized")

    yield  # Application runs here

    logger.info("application_shutting_down")
    try:
        get_engine().dispose()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error("database_shutdown_error", extra={"error": str(e)})


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

# Starlette executes middleware outermost-to-innermost in the order they
# are added LAST-to-FIRST (the last one added wraps everything else, so it
# runs first on the way in). We want, on the way in:
#   1. CORS          - handle preflight before anything else runs
#   2. RateLimit      - reject abusive traffic as cheaply/early as possible
#   3. CorrelationID  - tag the request before it gets logged
#   4. RequestLogging - log using the correlation ID set above
#   5. SecurityHeaders - closest to the route, stamps the outgoing response
# which means we add them in the REVERSE of that order:
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
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
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error("db_health_check_failed", extra={"error": str(e)})

    embedding_status = "ok"
    try:
        service = EmbeddingService.get_instance()
        if service is None or not hasattr(service, "model"):
            embedding_status = "error: not initialized"
        else:
            _ = service.model.get_sentence_embedding_dimension()
    except Exception as e:
        embedding_status = f"error: {str(e)}"
        logger.warning("embedding_health_check_failed", extra={"error": str(e)})

    services = {
        "embeddings": embedding_status,
        "clustering": "ok",
        "analytics": "ok",
    }

    overall_status = (
        "healthy"
        if db_status == "ok" and all(s == "ok" for s in services.values())
        else "degraded"
    )

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        services=services,
        version="2.0.0",
    )


# ============================================================================
# REVIEW ENDPOINTS
# ============================================================================
#
# Read endpoints accept any authenticated user. Write/mutating endpoints
# require at least the "analyst" role - previously every endpoint here only
# checked that *some* valid token was present, so any "viewer" could create,
# bulk-load, or mutate review data. Tighten that with require_role().

@app.post("/api/v1/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(require_role("analyst")),
) -> ReviewResponse:
    """Create a new review."""
    logger.info("creating_review", extra={"source": review.source})
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
    current_user: CurrentUser = Depends(get_current_user),
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
    return ReviewPaginatedResponse(total=total, skip=skip, limit=limit, items=items)


@app.get("/api/v1/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
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
    current_user: CurrentUser = Depends(require_role("analyst")),
) -> dict:
    """Bulk create reviews."""
    return ReviewService.bulk_create_reviews(db, reviews)


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

def _validate_search_request(request: SemanticSearchRequest) -> tuple[int, float]:
    """Shared validation for the two search endpoints below."""
    if not request.query or len(request.query.strip()) < 2:
        raise HTTPException(
            status_code=422,
            detail="Query must be at least 2 characters long",
        )

    limit = min(max(1, request.limit or 20), settings.api.max_search_limit)
    threshold = max(0.0, min(1.0, request.threshold or 0.3))
    return limit, threshold


def _to_search_response(
    request: SemanticSearchRequest, results: list[tuple]
) -> SearchResponse:
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


@app.post("/api/v1/search/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> SearchResponse:
    """Semantic similarity search."""
    limit, threshold = _validate_search_request(request)
    results = VectorService.search_semantic(db, request.query, top_k=limit, threshold=threshold)
    return _to_search_response(request, results)


@app.post("/api/v1/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> SearchResponse:
    """Hybrid keyword + semantic search."""
    limit, _ = _validate_search_request(request)
    results = VectorService.search_hybrid(db, request.query, top_k=limit)
    return _to_search_response(request, results)


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================
#
# These are CPU/GPU-bound, potentially long-running ML operations. Declared
# as plain `def` (not `async def`) so FastAPI runs them in its threadpool
# instead of blocking the single asyncio event loop that's also serving
# every other concurrent request.

@app.post("/api/v1/analysis/discover-themes")
def discover_themes(
    n_themes: int | None = None,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(require_role("analyst")),
) -> dict:
    """Discover themes from reviews."""
    logger.info("theme_discovery_started")
    return ClusteringService.discover_themes(db, n_themes)


@app.post("/api/v1/analysis/index-embeddings")
def index_embeddings(
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(require_role("analyst")),
) -> dict:
    """Generate and index embeddings for all reviews."""
    logger.info("embedding_indexing_started")
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
    current_user: CurrentUser = Depends(get_current_user),
) -> ThemePaginatedResponse:
    """List themes."""
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
    current_user: CurrentUser = Depends(get_current_user),
) -> AnalyticsResponse:
    """Get comprehensive analytics overview."""
    return AnalyticsService.get_overview(db)


@app.get("/api/v1/analytics/themes/{theme_id}")
async def get_theme_analytics(
    theme_id: int,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get analytics for specific theme."""
    return AnalyticsService.get_theme_analytics(db, theme_id)


@app.get("/api/v1/analytics/sources/{source}")
async def get_source_analytics(
    source: str,
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get analytics for specific source."""
    return AnalyticsService.get_source_analytics(db, source)


@app.get("/api/v1/analytics/trends")
async def get_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get trend data."""
    return AnalyticsService.get_trend_data(db, days)


# ============================================================================
# ROOT / OPS ENDPOINTS
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
async def metrics_endpoint(
    current_user: CurrentUser = Depends(require_role("admin")),
) -> PlainResponse:
    """Prometheus metrics endpoint.

    Restricted to admins - metrics can reveal internal request rates,
    error counts, and route names that are useful reconnaissance for an
    attacker and otherwise have no reason to be public.
    """
    return PlainResponse(content=get_metrics(), media_type="text/plain")