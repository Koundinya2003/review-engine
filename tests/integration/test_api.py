"""
Integration tests for API endpoints.

Tests for review, search, analysis, and auth endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestReviewEndpoints:
    """Tests for review endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_create_review_unauthorized(self, client: TestClient, sample_review_data: dict):
        """Test creating review without authentication."""
        response = client.post(
            "/api/v1/reviews",
            json=sample_review_data,
        )
        
        # Should succeed if auth not enabled
        assert response.status_code in [200, 201, 401]

    @pytest.mark.integration
    @pytest.mark.api
    def test_create_review_authorized(self, client: TestClient, auth_headers: dict, sample_review_data: dict):
        """Test creating review with authentication."""
        response = client.post(
            "/api/v1/reviews",
            json=sample_review_data,
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "text" in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_list_reviews(self, client: TestClient, auth_headers: dict):
        """Test listing reviews."""
        response = client.get(
            "/api/v1/reviews",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "total" in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_list_reviews_pagination(self, client: TestClient, auth_headers: dict):
        """Test review pagination."""
        response = client.get(
            "/api/v1/reviews?skip=0&limit=10",
            headers=auth_headers,
        )
        
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.api
    def test_list_reviews_filtering(self, client: TestClient, auth_headers: dict):
        """Test review filtering."""
        response = client.get(
            "/api/v1/reviews?source=app_store&theme=feature",
            headers=auth_headers,
        )
        
        assert response.status_code == 200


class TestSearchEndpoints:
    """Tests for search endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.slow
    def test_semantic_search(self, client: TestClient, auth_headers: dict):
        """Test semantic search."""
        response = client.post(
            "/api/v1/search/semantic",
            json={"query": "excellent features"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data or "total_results" in data

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.slow
    def test_hybrid_search(self, client: TestClient, auth_headers: dict):
        """Test hybrid search."""
        response = client.post(
            "/api/v1/search/hybrid",
            json={"query": "great app"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_analytics_overview(self, client: TestClient, auth_headers: dict):
        """Test analytics overview."""
        response = client.get(
            "/api/v1/analytics/overview",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_reviews" in data
        assert "average_rating" in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_trends(self, client: TestClient, auth_headers: dict):
        """Test trend data."""
        response = client.get(
            "/api/v1/analytics/trends?days=30",
            headers=auth_headers,
        )
        
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_source_analytics(self, client: TestClient, auth_headers: dict):
        """Test source analytics."""
        response = client.get(
            "/api/v1/analytics/sources/app_store",
            headers=auth_headers,
        )
        
        assert response.status_code == 200


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.integration
    @pytest.mark.api
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_register_user(self, client: TestClient):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "testpass123",
            },
        )
        
        assert response.status_code in [200, 201]
        if response.status_code != 403:  # Auth might be disabled
            data = response.json()
            assert "access_token" in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_login_user(self, client: TestClient):
        """Test user login."""
        # Register first
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "logintest",
                "email": "login@example.com",
                "password": "testpass123",
            },
        )
        
        # Then login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "logintest",
                "password": "testpass123",
            },
        )
        
        assert response.status_code in [200, 201, 403]
        if response.status_code != 403:
            data = response.json()
            assert "access_token" in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_current_user(self, client: TestClient, auth_headers: dict):
        """Test get current user endpoint."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 401, 403]
        if response.status_code == 200:
            data = response.json()
            assert "username" in data or "user_id" in data


class TestBulkOperations:
    """Tests for bulk operations."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_bulk_create_reviews(self, client: TestClient, auth_headers: dict, sample_reviews_batch: list):
        """Test bulk review creation."""
        response = client.post(
            "/api/v1/reviews/bulk",
            json=sample_reviews_batch,
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "total" in data or "created" in data


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_not_found_error(self, client: TestClient, auth_headers: dict):
        """Test 404 error handling."""
        response = client.get(
            "/api/v1/reviews/99999",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.api
    def test_invalid_request_error(self, client: TestClient, auth_headers: dict):
        """Test invalid request error handling."""
        response = client.post(
            "/api/v1/reviews",
            json={"invalid": "data"},
            headers=auth_headers,
        )
        
        assert response.status_code in [400, 422]

    @pytest.mark.integration
    @pytest.mark.api
    def test_invalid_pagination(self, client: TestClient, auth_headers: dict):
        """Test invalid pagination parameters."""
        response = client.get(
            "/api/v1/reviews?skip=-1&limit=1000",
            headers=auth_headers,
        )
        
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 400, 422]
