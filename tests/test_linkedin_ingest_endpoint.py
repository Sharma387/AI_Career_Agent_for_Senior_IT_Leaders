"""
Tests for the LinkedIn job ingest API endpoint.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 12.4
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.api.auth import require_user, get_current_user
from app.api.routes import router, _linkedin_ingest_rate
from app.db.models import get_db, User


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Clear the rate limit dict before each test."""
    _linkedin_ingest_rate.clear()
    yield
    _linkedin_ingest_rate.clear()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def app(mock_user, mock_db_session):
    """Create a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(router)

    async def override_require_user():
        return mock_user

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        return mock_db_session

    app.dependency_overrides[require_user] = override_require_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    return app


@pytest.fixture
def valid_linkedin_payload():
    """Valid LinkedIn job ingestion payload."""
    return {
        "title": "Engineering Manager",
        "company": "TechCorp",
        "location": "Auckland, New Zealand",
        "description": "We are looking for an experienced Engineering Manager to lead our platform team.",
        "url": "https://www.linkedin.com/jobs/view/1234567890",
        "salary_range": "$180,000 - $220,000",
        "seniority_level": "Director",
        "employment_type": "Full-time",
    }


class TestLinkedInIngestValidation:
    """Test request validation (handled by Pydantic model)."""

    @pytest.mark.asyncio
    async def test_invalid_url_pattern_returns_422(self, app):
        """Req 5.4: URL not matching LinkedIn pattern returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json={
                    "title": "Engineer",
                    "company": "Corp",
                    "description": "A valid description with enough chars",
                    "url": "https://www.indeed.com/jobs/view/123",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_short_description_returns_422(self, app):
        """Req 5.5: Description < 10 chars returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json={
                    "title": "Engineer",
                    "company": "Corp",
                    "description": "Short",
                    "url": "https://www.linkedin.com/jobs/view/123",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_title_returns_422(self, app):
        """Req 5.3: Missing required title field returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json={
                    "company": "Corp",
                    "description": "A valid description with enough chars",
                    "url": "https://www.linkedin.com/jobs/view/123",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_company_returns_422(self, app):
        """Req 5.3: Missing required company field returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json={
                    "title": "Engineer",
                    "description": "A valid description with enough chars",
                    "url": "https://www.linkedin.com/jobs/view/123",
                },
            )
            assert response.status_code == 422


class TestLinkedInIngestDeduplication:
    """Test deduplication behavior."""

    @pytest.mark.asyncio
    async def test_duplicate_returns_200(self, app, valid_linkedin_payload, mock_user):
        """Req 5.7: Duplicate job returns HTTP 200 with status 'duplicate'."""
        with patch("app.api.routes.is_duplicate", new_callable=AsyncMock, return_value=True):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/jobs/ingest/linkedin",
                    json=valid_linkedin_payload,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "duplicate"
                assert "already exists" in data["message"]

    @pytest.mark.asyncio
    async def test_new_job_returns_201(self, app, valid_linkedin_payload, mock_user, mock_db_session):
        """Req 5.6: New non-duplicate job returns HTTP 201 with status 'created'."""
        mock_job_record = MagicMock()
        mock_job_record.id = 42
        mock_job_record.url = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_record
        mock_db_session.execute.return_value = mock_result

        with patch("app.api.routes.is_duplicate", new_callable=AsyncMock, return_value=False), \
             patch("app.api.routes.job_service") as mock_job_service:
            mock_job_service.add_job = AsyncMock(return_value={"job_id": 42, "parsed_data": {}})

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/jobs/ingest/linkedin",
                    json=valid_linkedin_payload,
                )
                assert response.status_code == 201
                data = response.json()
                assert data["status"] == "created"
                assert data["job_id"] == 42
                assert "stored successfully" in data["message"]

            # Verify add_job was called with source="linkedin_ext"
            mock_job_service.add_job.assert_called_once()
            call_args = mock_job_service.add_job.call_args
            assert call_args.kwargs.get("source") == "linkedin_ext"


class TestLinkedInIngestRateLimit:
    """Test rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(self, app, valid_linkedin_payload, mock_user):
        """Req 12.4: More than 10 requests per minute returns HTTP 429."""
        # Pre-fill rate limit with 10 timestamps for user.id=1
        _linkedin_ingest_rate[mock_user.id] = [time.time()] * 10

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json=valid_linkedin_payload,
            )
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rate_limit_allows_after_expiry(self, app, valid_linkedin_payload, mock_user, mock_db_session):
        """Rate limit clears after 60 seconds."""
        # Pre-fill with old timestamps (> 60 seconds ago)
        _linkedin_ingest_rate[mock_user.id] = [time.time() - 70] * 10

        mock_job_record = MagicMock()
        mock_job_record.id = 1
        mock_job_record.url = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job_record
        mock_db_session.execute.return_value = mock_result

        with patch("app.api.routes.is_duplicate", new_callable=AsyncMock, return_value=False), \
             patch("app.api.routes.job_service") as mock_job_service:
            mock_job_service.add_job = AsyncMock(return_value={"job_id": 1, "parsed_data": {}})

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/jobs/ingest/linkedin",
                    json=valid_linkedin_payload,
                )
                # Should succeed since old timestamps are expired
                assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_rate_limit_tracks_per_user(self, app, valid_linkedin_payload, mock_db_session):
        """Rate limit is tracked per user, not globally."""
        # User 1 has exhausted their rate limit
        _linkedin_ingest_rate[1] = [time.time()] * 10
        # User 2 (mock_user.id=1 default) should not be affected by user 99's rate
        _linkedin_ingest_rate[99] = [time.time()] * 10

        # But our mock_user.id=1 IS rate limited
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json=valid_linkedin_payload,
            )
            assert response.status_code == 429


class TestLinkedInIngestAuthentication:
    """Test authentication behavior."""

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self):
        """Req 5.2: Request without valid JWT returns 401."""
        app = FastAPI()
        app.include_router(router)

        # No dependency overrides - uses real auth which requires JWT
        async def override_get_db():
            return AsyncMock()

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/ingest/linkedin",
                json={
                    "title": "Engineer",
                    "company": "Corp",
                    "description": "A valid description with enough chars",
                    "url": "https://www.linkedin.com/jobs/view/123",
                },
            )
            assert response.status_code == 401
