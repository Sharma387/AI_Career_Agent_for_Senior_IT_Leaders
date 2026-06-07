import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.auth import get_current_user


@pytest.fixture
def mock_job_service():
    with patch("app.api.routes.job_service") as mock:
        mock.add_job = AsyncMock()
        mock.get_all_jobs = AsyncMock()
        mock.match_job = AsyncMock()
        mock.generate_application_materials = AsyncMock()
        yield mock


@pytest.fixture
def mock_profile_service():
    with patch("app.api.routes.profile_service") as mock:
        mock.upload_resume = AsyncMock()
        mock.get_profile = AsyncMock()
        mock.add_project = AsyncMock()
        yield mock


@pytest.fixture
def mock_tracking_service():
    with patch("app.api.routes.tracking_service") as mock:
        mock.track_application = AsyncMock()
        mock.update_application_status = AsyncMock()
        mock.get_application_stats = AsyncMock()
        mock.get_all_applications = AsyncMock()
        mock.get_insights = AsyncMock()
        yield mock


@pytest.fixture
async def client():
    async def override_auth():
        return None
    app.dependency_overrides[get_current_user] = override_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_add_job(client: AsyncClient, mock_job_service, sample_job_text):
    mock_job_service.add_job.return_value = {"job_id": 1, "parsed_data": {}}
    resp = await client.post("/api/jobs/add", json={"text": sample_job_text})
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    mock_job_service.add_job.assert_called_once()


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, mock_job_service):
    mock_job_service.get_all_jobs.return_value = [
        {"id": 1, "title": "CTO", "company": "TestCo"}
    ]
    resp = await client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    mock_job_service.get_all_jobs.assert_called_once()


@pytest.mark.asyncio
async def test_add_job_invalid_body(client: AsyncClient):
    resp = await client.post("/api/jobs/add", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_match_job_no_profile(client: AsyncClient, mock_job_service):
    mock_job_service.match_job.return_value = {}
    resp = await client.post("/api/jobs/1/match", params={"profile_id": 999})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_track_application_no_job(client: AsyncClient, mock_tracking_service):
    mock_tracking_service.track_application.return_value = {}
    resp = await client.post(
        "/api/applications/track",
        json={"job_id": 999, "profile_id": 1, "status": "applied"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_resume_invalid_filetype(client: AsyncClient):
    resp = await client.post(
        "/api/profile/upload-resume",
        files={"file": ("malware.exe", b"\x00\x01\x02", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "PDF, DOCX, or TXT" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_profile_not_found(client: AsyncClient, mock_profile_service):
    mock_profile_service.get_profile.return_value = {}
    resp = await client.get("/api/profile/999")
    assert resp.status_code == 404
