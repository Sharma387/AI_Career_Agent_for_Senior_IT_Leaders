"""
Tests for the job scraping service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.job_scraper import (
    JobSourceAdapter,
    SeekAdapter,
    LinkedInAdapter,
    JobScrapingService
)


class TestJobSourceAdapter:
    """Test the abstract base class."""

    def test_adapter_cannot_be_instantiated(self):
        """Test that abstract adapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            JobSourceAdapter("test_source")


class TestSeekAdapter:
    """Test the Seek adapter."""

    @pytest.fixture
    def seek_adapter(self):
        return SeekAdapter()

    def test_seek_adapter_initialization(self, seek_adapter):
        """Test Seek adapter initialization."""
        assert seek_adapter.source_name == "seek"
        assert seek_adapter.base_url == "https://www.seek.com.au"

    def test_get_external_id_from_url(self, seek_adapter):
        """Test extracting external ID from Seek URL."""
        raw_job = {
            'url': 'https://www.seek.com.au/job/12345678'
        }
        external_id = seek_adapter.get_external_id(raw_job)
        assert external_id == "seek_12345678"

    def test_get_external_id_fallback(self, seek_adapter):
        """Test fallback external ID generation."""
        raw_job = {
            'url': 'https://www.seek.com.au/some/job/path'
        }
        external_id = seek_adapter.get_external_id(raw_job)
        assert external_id.startswith("seek_")
        assert len(external_id) > 5  # seek_ + hash

    def test_extract_job_data(self, seek_adapter):
        """Test job data extraction."""
        raw_job = {
            'title': 'Software Engineer',
            'company': 'Tech Corp',
            'location': 'Sydney',
            'url': 'https://www.seek.com.au/job/12345678'
        }
        job_data = seek_adapter.extract_job_data(raw_job)

        assert job_data['title'] == 'Software Engineer'
        assert job_data['company'] == 'Tech Corp'
        assert job_data['location'] == 'Sydney'
        assert job_data['source'] == 'seek'
        assert job_data['external_id'] == 'seek_12345678'

    @pytest.mark.asyncio
    async def test_scrape_jobs_not_implemented(self, seek_adapter):
        """Test that scrape_jobs returns empty list (simplified implementation)."""
        # Mock the session
        seek_adapter.session = AsyncMock()

        # Test with empty search params
        jobs = await seek_adapter.scrape_jobs({})
        assert isinstance(jobs, list)
        # In current implementation, it returns empty list due to simplified scraping


class TestLinkedInAdapter:
    """Test the LinkedIn adapter."""

    @pytest.fixture
    def linkedin_adapter(self):
        return LinkedInAdapter()

    def test_linkedin_adapter_initialization(self, linkedin_adapter):
        """Test LinkedIn adapter initialization."""
        assert linkedin_adapter.source_name == "linkedin"
        assert linkedin_adapter.base_url == "https://www.linkedin.com"

    def test_get_external_id_from_url(self, linkedin_adapter):
        """Test extracting external ID from LinkedIn URL."""
        raw_job = {
            'url': 'https://www.linkedin.com/jobs/view/9876543210/'
        }
        external_id = linkedin_adapter.get_external_id(raw_job)
        assert external_id == "linkedin_9876543210"

    def test_get_external_id_fallback(self, linkedin_adapter):
        """Test fallback external ID generation."""
        raw_job = {
            'url': 'https://www.linkedin.com/some/job/path'
        }
        external_id = linkedin_adapter.get_external_id(raw_job)
        assert external_id.startswith("linkedin_")
        assert len(external_id) > 5  # linkedin_ + hash

    def test_extract_job_data(self, linkedin_adapter):
        """Test job data extraction."""
        raw_job = {
            'title': 'Senior Developer',
            'company': 'Big Tech',
            'location': 'Melbourne',
            'url': 'https://www.linkedin.com/jobs/view/9876543210/'
        }
        job_data = linkedin_adapter.extract_job_data(raw_job)

        assert job_data['title'] == 'Senior Developer'
        assert job_data['company'] == 'Big Tech'
        assert job_data['location'] == 'Melbourne'
        assert job_data['source'] == 'linkedin'
        assert job_data['external_id'] == 'linkedin_9876543210'


class TestJobScrapingService:
    """Test the job scraping service."""

    @pytest.fixture
    def scraping_service(self):
        return JobScrapingService()

    def test_service_initialization(self, scraping_service):
        """Test service initialization."""
        assert scraping_service.job_service is not None
        assert scraping_service.job_parser is not None
        assert 'seek' in scraping_service.adapters
        assert 'linkedin' in scraping_service.adapters

    @pytest.mark.asyncio
    async def test_scrape_and_store_jobs_invalid_source(self, scraping_service):
        """Test scraping with invalid source."""
        with pytest.raises(ValueError, match="Unsupported source"):
            await scraping_service.scrape_and_store_jobs(
                source="invalid_source",
                search_params={},
                db_session=AsyncMock()
            )

    @pytest.mark.asyncio
    async def test_scrape_multiple_sources(self, scraping_service):
        """Test scraping from multiple sources."""
        # Mock the database session
        mock_db_session = AsyncMock()

        # Test with valid sources
        result = await scraping_service.scrape_multiple_sources(
            sources=['seek', 'linkedin'],
            search_params={'keywords': 'engineer'},
            db_session=mock_db_session
        )

        assert result['sources'] == ['seek', 'linkedin']
        assert 'source_results' in result
        assert 'seek' in result['source_results']
        assert 'linkedin' in result['source_results']


if __name__ == "__main__":
    pytest.main([__file__])