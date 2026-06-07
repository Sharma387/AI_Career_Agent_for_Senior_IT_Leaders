"""
Deduplication Engine for job ingestion.

Checks whether a job already exists in the database before storage,
using URL and title+company matching against active job postings.
This module performs read-only operations with no side effects.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobPosting

logger = logging.getLogger(__name__)


async def is_duplicate(
    url: str,
    title: str,
    company: str,
    db_session: AsyncSession,
) -> bool:
    """
    Check if a job already exists in the database.

    Uses a two-stage deduplication strategy:
    1. Primary: exact URL match on active JobPostings
    2. Secondary: title + company combination on active JobPostings

    This function is read-only and produces no side effects on the database.

    Args:
        url: The job posting URL to check (may be empty string).
        title: The job title to check (may be empty string).
        company: The company name to check (may be empty string).
        db_session: An active SQLAlchemy async session.

    Returns:
        True if a matching active job posting exists, False otherwise.
    """
    # Primary check: exact URL match on active job postings
    if url:
        stmt = select(JobPosting).where(
            JobPosting.url == url,
            JobPosting.is_active == True,  # noqa: E712
        )
        result = await db_session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            logger.debug(f"Duplicate detected by URL: {url}")
            return True

    # Secondary check: title + company combination on active job postings
    if title and company:
        stmt = select(JobPosting).where(
            JobPosting.title == title,
            JobPosting.company == company,
            JobPosting.is_active == True,  # noqa: E712
        )
        result = await db_session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            logger.debug(
                f"Duplicate detected by title+company: '{title}' at '{company}'"
            )
            return True

    return False
