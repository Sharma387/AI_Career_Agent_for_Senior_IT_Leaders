"""Unit tests for the deduplication engine."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobPosting
from app.ingestion.deduplication import is_duplicate


@pytest_asyncio.fixture
async def active_job(db_session: AsyncSession) -> JobPosting:
    """Create an active job posting for testing."""
    job = JobPosting(
        title="Engineering Manager",
        company="TechCorp",
        description="Lead the engineering team",
        source="seek_nz",
        url="https://www.seek.co.nz/job/12345",
        location="Auckland",
        is_active=True,
    )
    db_session.add(job)
    await db_session.flush()
    return job


@pytest_asyncio.fixture
async def inactive_job(db_session: AsyncSession) -> JobPosting:
    """Create an inactive job posting for testing."""
    job = JobPosting(
        title="Project Manager",
        company="OldCorp",
        description="Manage projects",
        source="adzuna",
        url="https://www.seek.co.nz/job/99999",
        location="Wellington",
        is_active=False,
    )
    db_session.add(job)
    await db_session.flush()
    return job


class TestIsDuplicate:
    """Tests for is_duplicate function."""

    async def test_returns_true_for_exact_url_match(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """Primary check: exact URL match on active job returns True."""
        result = await is_duplicate(
            url="https://www.seek.co.nz/job/12345",
            title="",
            company="",
            db_session=db_session,
        )
        assert result is True

    async def test_returns_true_for_title_company_match(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """Secondary check: title + company match on active job returns True."""
        result = await is_duplicate(
            url="",
            title="Engineering Manager",
            company="TechCorp",
            db_session=db_session,
        )
        assert result is True

    async def test_returns_false_for_no_match(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """No URL or title+company match returns False."""
        result = await is_duplicate(
            url="https://www.seek.co.nz/job/99998",
            title="Software Engineer",
            company="OtherCorp",
            db_session=db_session,
        )
        assert result is False

    async def test_ignores_inactive_jobs_url(
        self, db_session: AsyncSession, inactive_job: JobPosting
    ):
        """URL match on inactive job returns False."""
        result = await is_duplicate(
            url="https://www.seek.co.nz/job/99999",
            title="",
            company="",
            db_session=db_session,
        )
        assert result is False

    async def test_ignores_inactive_jobs_title_company(
        self, db_session: AsyncSession, inactive_job: JobPosting
    ):
        """Title+company match on inactive job returns False."""
        result = await is_duplicate(
            url="",
            title="Project Manager",
            company="OldCorp",
            db_session=db_session,
        )
        assert result is False

    async def test_returns_false_with_empty_inputs(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """Empty URL and empty title/company returns False."""
        result = await is_duplicate(
            url="",
            title="",
            company="",
            db_session=db_session,
        )
        assert result is False

    async def test_url_match_takes_priority(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """URL match is checked first (returns True even without title/company)."""
        result = await is_duplicate(
            url="https://www.seek.co.nz/job/12345",
            title="Different Title",
            company="Different Company",
            db_session=db_session,
        )
        assert result is True

    async def test_partial_title_match_not_duplicate(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """Only title matching (without company) does not count as duplicate."""
        result = await is_duplicate(
            url="",
            title="Engineering Manager",
            company="DifferentCorp",
            db_session=db_session,
        )
        assert result is False

    async def test_partial_company_match_not_duplicate(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """Only company matching (without title) does not count as duplicate."""
        result = await is_duplicate(
            url="",
            title="Different Role",
            company="TechCorp",
            db_session=db_session,
        )
        assert result is False

    async def test_no_side_effects_on_database(
        self, db_session: AsyncSession, active_job: JobPosting
    ):
        """Deduplication check does not modify database state."""
        # Run the dedup check
        await is_duplicate(
            url="https://www.seek.co.nz/job/12345",
            title="Engineering Manager",
            company="TechCorp",
            db_session=db_session,
        )

        # Verify the job is still unchanged
        await db_session.refresh(active_job)
        assert active_job.title == "Engineering Manager"
        assert active_job.company == "TechCorp"
        assert active_job.url == "https://www.seek.co.nz/job/12345"
        assert active_job.is_active is True
