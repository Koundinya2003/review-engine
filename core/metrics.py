"""
Prometheus metrics configuration for Review Discovery Engine.

This module exports application metrics to Prometheus.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

# ============================================================================
# METRICS REGISTRY
# ============================================================================
#
# NOTE: this is a single in-process registry. If this service ever runs
# under multiple worker processes (e.g. gunicorn with >1 worker), each
# process gets its own registry and /metrics will only reflect whichever
# process happened to handle the scrape - counters will appear to reset
# or undercount. For multi-process deployments, switch to
# `prometheus_client.multiprocess` with PROMETHEUS_MULTIPROC_DIR set.

registry = CollectorRegistry()


# ============================================================================
# REQUEST METRICS
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    registry=registry,
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    registry=registry,
)


# ============================================================================
# DATABASE METRICS
# ============================================================================

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    registry=registry,
)

database_connections_active = Gauge(
    "database_connections_active",
    "Active database connections",
    registry=registry,
)

database_operations_total = Counter(
    "database_operations_total",
    "Total database operations",
    ["operation", "table", "status"],
    registry=registry,
)


# ============================================================================
# REVIEW METRICS
# ============================================================================

reviews_total = Gauge(
    "reviews_total",
    "Total reviews in database",
    registry=registry,
)

reviews_by_source = Gauge(
    "reviews_by_source",
    "Reviews by source",
    ["source"],
    registry=registry,
)

reviews_by_sentiment = Gauge(
    "reviews_by_sentiment",
    "Reviews by sentiment",
    ["sentiment"],
    registry=registry,
)

reviews_average_rating = Gauge(
    "reviews_average_rating",
    "Average review rating",
    registry=registry,
)

reviews_created_total = Counter(
    "reviews_created_total",
    "Total reviews created",
    ["source"],
    registry=registry,
)


# ============================================================================
# THEME METRICS
# ============================================================================

themes_total = Gauge(
    "themes_total",
    "Total themes",
    registry=registry,
)

theme_discovery_duration_seconds = Histogram(
    "theme_discovery_duration_seconds",
    "Theme discovery duration in seconds",
    registry=registry,
)

theme_discovery_total = Counter(
    "theme_discovery_total",
    "Total theme discoveries",
    ["status"],
    registry=registry,
)


# ============================================================================
# EMBEDDING METRICS
# ============================================================================

embedding_generation_duration_seconds = Histogram(
    "embedding_generation_duration_seconds",
    "Embedding generation duration in seconds",
    ["model"],
    registry=registry,
)

embeddings_total = Gauge(
    "embeddings_total",
    "Total embeddings generated",
    registry=registry,
)

# Default Histogram buckets are tuned for sub-second latencies, not batch
# counts - explicit buckets give this metric meaningful resolution.
embedding_batch_size = Histogram(
    "embedding_batch_size",
    "Embedding batch sizes",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
    registry=registry,
)


# ============================================================================
# SEARCH METRICS
# ============================================================================

search_queries_total = Counter(
    "search_queries_total",
    "Total search queries",
    ["search_type"],
    registry=registry,
)

search_duration_seconds = Histogram(
    "search_duration_seconds",
    "Search duration in seconds",
    ["search_type"],
    registry=registry,
)

search_results = Histogram(
    "search_results",
    "Number of search results",
    ["search_type"],
    buckets=(0, 1, 5, 10, 20, 50, 100, 250, 500),
    registry=registry,
)


# ============================================================================
# AUTHENTICATION METRICS
# ============================================================================

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["method", "status"],
    registry=registry,
)

active_users = Gauge(
    "active_users",
    "Active authenticated users",
    registry=registry,
)

token_generation_total = Counter(
    "token_generation_total",
    "Total tokens generated",
    ["role"],
    registry=registry,
)


# ============================================================================
# ERROR METRICS
# ============================================================================

errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "endpoint"],
    registry=registry,
)

validation_errors_total = Counter(
    "validation_errors_total",
    "Total validation errors",
    ["field"],
    registry=registry,
)


# ============================================================================
# SYSTEM METRICS
# ============================================================================

cache_hits_total = Counter(
    "cache_hits_total",
    "Cache hits",
    registry=registry,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Cache misses",
    registry=registry,
)

queue_size = Gauge(
    "queue_size",
    "Background job queue size",
    registry=registry,
)


def get_metrics() -> bytes:
    """Get all metrics in Prometheus text-exposition format."""
    return generate_latest(registry)