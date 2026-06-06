"""
Job scraping service for AI Career Agent.
Handles scraping jobs from various sources and storing them in the database.
"""

import abc
import asyncio
import logging
import re
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, urlencode

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.scraper_utils import (
    retry_with_exponential_backoff,
    add_rate_limiting_delay,
    extract_text_safely,
    extract_attribute_safely,
    build_url_with_params
)
from app.services.job_service import JobService
from app.ingestion.job_parser import JobParser
from app.db.models import JobPosting
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


logger = logging.getLogger(__name__)


class JobSourceAdapter(abc.ABC):
    """Abstract base class for job source adapters."""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    @abc.abstractmethod
    async def scrape_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape jobs from the source.

        Args:
            search_params: Dictionary containing search parameters like keywords, location, etc.

        Returns:
            List of raw job dictionaries
        """
        pass

    @abc.abstractmethod
    def extract_job_data(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized job data from raw job data.

        Args:
            raw_job: Raw job data from the source

        Returns:
            Standardized job dictionary
        """
        pass

    @abc.abstractmethod
    def get_external_id(self, raw_job: Dict[str, Any]) -> str:
        """
        Extract the external ID from raw job data for duplicate detection.

        Args:
            raw_job: Raw job data from the source

        Returns:
            External ID string
        """
        pass


class SeekAdapter(JobSourceAdapter):
    """Adapter for scraping jobs from Seek.com.au"""

    def __init__(self):
        super().__init__("seek")
        self.base_url = "https://www.seek.com.au"

    async def scrape_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Seek.

        Args:
            search_params: Dictionary with keys like 'keywords', 'location', 'page'

        Returns:
            List of raw job dictionaries
        """
        if not self.session:
            raise RuntimeError("Adapter not initialized. Use async context manager.")

        jobs = []
        try:
            # Build search URL
            params = []
            if search_params.get('keywords'):
                params.append(f"keywords={search_params['keywords']}")
            if search_params.get('location'):
                params.append(f"location={search_params['location']}")
            if search_params.get('page'):
                params.append(f"page={search_params['page']}")

            query_string = "&".join(params)
            url = f"{self.base_url}/jobs?{query_string}" if query_string else f"{self.base_url}/jobs"

            logger.info(f"Scraping Seek jobs from: {url}")

            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch Seek jobs: HTTP {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find job cards (Seek's structure may vary)
                job_cards = soup.find_all('div', {'data-automation': 'normalJob'})

                for card in job_cards[:20]:  # Limit to 20 jobs per request
                    try:
                        # Extract job data
                        title_elem = card.find('a', {'data-automation': 'jobTitle'})
                        company_elem = card.find('a', {'data-automation': 'jobCompany'})
                        location_elem = card.find('a', {'data-automation': 'jobLocation'})

                        if not title_elem:
                            continue

                        job_url = urljoin(self.base_url, title_elem.get('href', ''))

                        raw_job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True) if company_elem else '',
                            'location': location_elem.get_text(strip=True) if location_elem else '',
                            'url': job_url,
                            'source': self.source_name,
                            'raw_html': str(card),
                        }

                        jobs.append(raw_job)

                    except Exception as e:
                        logger.warning(f"Error parsing Seek job card: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error scraping Seek jobs: {e}")

        return jobs

    def extract_job_data(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized job data from raw Seek job data.

        Args:
            raw_job: Raw job data from Seek

        Returns:
            Standardized job dictionary
        """
        return {
            'title': raw_job.get('title', ''),
            'company': raw_job.get('company', ''),
            'location': raw_job.get('location', ''),
            'description': f"Job from Seek: {raw_job.get('title', '')} at {raw_job.get('company', '')}",
            'source': self.source_name,
            'url': raw_job.get('url', ''),
            'external_id': self.get_external_id(raw_job),
        }

    def get_external_id(self, raw_job: Dict[str, Any]) -> str:
        """
        Extract the external ID from raw Seek job data.

        Args:
            raw_job: Raw job data from Seek

        Returns:
            External ID string (Seek job ID from URL)
        """
        url = raw_job.get('url', '')
        # Extract job ID from Seek URL pattern: /job/12345678
        match = re.search(r'/job/(\d+)', url)
        if match:
            return f"seek_{match.group(1)}"

        # Fallback to URL hash
        import hashlib
        return f"seek_{hashlib.md5(url.encode()).hexdigest()[:12]}"


class LinkedInAdapter(JobSourceAdapter):
    """Adapter for scraping jobs from LinkedIn with provider abstraction."""

    def __init__(self):
        super().__init__("linkedin")
        self.base_url = "https://www.linkedin.com"
        self.login_url = "https://www.linkedin.com/login"
        self.jobs_search_url = "https://www.linkedin.com/jobs/search/"
        self.session_cookies = {}
        self.is_authenticated = False
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Minimum 2 seconds between requests

    async def __aenter__(self):
        """Async context manager entry with authentication."""
        self.session = aiohttp.ClientSession()

        # Attempt to authenticate if credentials are provided
        if settings.LINKEDIN_EMAIL and settings.LINKEDIN_PASSWORD:
            try:
                await self._authenticate()
            except Exception as e:
                logger.warning(f"LinkedIn authentication failed: {e}")
                logger.info("Continuing without authentication - may have limited access")

        return self

    async def _authenticate(self):
        """Authenticate with LinkedIn using email and password."""
        logger.info("Attempting LinkedIn authentication...")

        # Get login page to obtain CSRF token
        async with self.session.get(self.login_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to load LinkedIn login page: {response.status}")

            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')

            # Extract CSRF token (simplified - LinkedIn's actual mechanism is more complex)
            csrf_token = soup.find('input', {'name': 'loginCsrfParam'})
            csrf_value = csrf_token.get('value') if csrf_token else ''

        # Prepare login data
        login_data = {
            'session_key': settings.LINKEDIN_EMAIL,
            'session_password': settings.LINKEDIN_PASSWORD,
            'loginCsrfParam': csrf_value,
        }

        # Attempt login
        async with self.session.post(self.login_url, data=login_data) as response:
            if response.status == 200:
                # Check if login was successful by looking for indicators in response
                html = await response.text()
                if 'feed' in html or 'invitations' in html or 'mynetwork' in html:
                    self.is_authenticated = True
                    logger.info("LinkedIn authentication successful")
                else:
                    # Check for error messages
                    if 'incorrect' in html.lower() or 'invalid' in html.lower():
                        raise Exception("Invalid LinkedIn credentials")
                    else:
                        logger.warning("LinkedIn login response unclear - proceeding anyway")
                        self.is_authenticated = True  # Assume success for now
            else:
                raise Exception(f"LinkedIn login failed with status: {response.status}")

    async def scrape_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape jobs from LinkedIn with support for incremental and full scraping.

        Args:
            search_params: Dictionary with keys like 'keywords', 'location', 'page',
                          'time_filter' (for incremental scraping: past hour, day, week, month)

        Returns:
            List of raw job dictionaries
        """
        if not self.session:
            raise RuntimeError("Adapter not initialized. Use async context manager.")

        # Check if LinkedIn scraping is enabled
        if not settings.LINKEDIN_SCRAPING_ENABLED:
            logger.info("LinkedIn scraping is disabled via configuration")
            return []

        jobs = []
        try:
            # Build search URL with parameters
            params = {}

            # Basic search parameters
            if search_params.get('keywords'):
                params['keywords'] = search_params['keywords']
            if search_params.get('location'):
                params['location'] = search_params['location']

            # Time filter for incremental scraping (LinkedIn uses f_TPR parameter)
            time_filter = search_params.get('time_filter')
            if time_filter:
                # Map common time filters to LinkedIn's format
                time_map = {
                    'past_hour': 'r3600',      # past hour
                    'past_24h': 'r86400',      # past 24 hours
                    'past_week': 'r604800',    # past week
                    'past_month': 'r2592000',  # past month
                }
                if time_filter in time_map:
                    params['f_TPR'] = time_map[time_filter]

            # Pagination
            if search_params.get('page') is not None:
                params['start'] = search_params['page'] * 25  # LinkedIn uses start parameter

            # Build URL
            query_string = urlencode(params)
            url = f"{self.jobs_search_url}/?{query_string}" if query_string else self.jobs_search_url

            logger.info(f"Scraping LinkedIn jobs from: {url}")

            # Apply rate limiting
            await self._apply_rate_limiting()

            # Make request with authentication headers if available
            headers = {}
            if self.is_authenticated and self.session.cookie_jar:
                # Cookies are handled automatically by aiohttp session
                pass

            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch LinkedIn jobs: HTTP {response.status}")
                    # Handle authentication errors
                    if response.status == 401 or response.status == 403:
                        logger.warning("LinkedIn authentication may have expired")
                        self.is_authenticated = False
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find job cards (LinkedIn's structure)
                job_cards = soup.find_all('div', {'class': 'base-card'}) or \
                           soup.find_all('div', {'class': 'job-search-card'}) or \
                           soup.find_all('li', {'class': 'result-card'}) or \
                           soup.find_all('div', {'data-entity-urn': True})  # Fallback

                # Limit results to prevent overwhelming
                max_results = search_params.get('limit', 50)
                job_cards = job_cards[:max_results]

                logger.info(f"Found {len(job_cards)} LinkedIn job cards")

                for card in job_cards:
                    try:
                        # Extract job data from card
                        raw_job = self._extract_job_from_card(card)
                        if raw_job:
                            jobs.append(raw_job)
                    except Exception as e:
                        logger.warning(f"Error parsing LinkedIn job card: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error scraping LinkedIn jobs: {e}")
            # Try to recover from transient errors
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                logger.info("Retrying after brief delay due to connection issue")
                await asyncio.sleep(5)
                # Could implement retry logic here

        return jobs

    def _extract_job_from_card(self, card) -> Optional[Dict[str, Any]]:
        """
        Extract job data from a LinkedIn job card element.

        Args:
            card: BeautifulSoup element representing a job card

        Returns:
            Dictionary with raw job data or None if extraction failed
        """
        try:
            # Extract title
            title_elem = card.find('h3', {'class': 'base-search-card__title'}) or \
                        card.find('h3', {'class': 'job-search-card__title'}) or \
                        card.find('a', {'class': 'result-card__title'}) or \
                        card.find('span', {'aria-label': True})  # Fallback

            title = extract_text_safely(title_elem) if title_elem else ""

            # Extract company
            company_elem = card.find('h4', {'class': 'base-search-card__subtitle'}) or \
                          card.find('h4', {'class': 'job-search-card__subtitle'}) or \
                          card.find('a', {'class': 'result-card__subtitle'}) or \
                          card.find('span', {'class': 'job-search-card__subtitle'}) or \
                          card.find('a', {'data-test-id': 'subtitle'})  # Fallback

            company = extract_text_safely(company_elem) if company_elem else ""

            # Extract location
            location_elem = card.find('span', {'class': 'job-search-card__location'}) or \
                           card.find('span', {'class': 'base-search-card__metadata'}) or \
                           card.find('span', {'class': 'result-card__metadata'}) or \
                           card.find('div', {'class': 'job-search-card__location'})  # Fallback

            location = extract_text_safely(location_elem) if location_elem else ""

            # Extract job URL
            url_elem = card.find('a', {'class': 'base-card__full-link'}) or \
                      card.find('a', {'class': 'job-search-card__link'}) or \
                      card.find('a', {'class': 'result-card__full-link'}) or \
                      card.find('a', href=True)  # Fallback

            job_url = extract_attribute_safely(url_elem, 'href') if url_elem else ""
            if job_url and not job_url.startswith('http'):
                job_url = urljoin(self.base_url, job_url)

            # Extract posted time (for incremental scraping relevance)
            time_elem = card.find('time', {'class': 'job-search-card__listdate'}) or \
                       card.find('time', {'class': 'job-search-card__listdate--new'}) or \
                       card.find('time')  # Fallback

            posted_time = extract_attribute_safely(time_elem, 'datetime') if time_elem else ""

            # Only return job if we have essential information
            if title and company:
                return {
                    'title': title,
                    'company': company,
                    'location': location,
                    'url': job_url,
                    'source': self.source_name,
                    'posted_time': posted_time,
                    'raw_html': str(card),
                }
            else:
                logger.debug(f"Skipping job card with insufficient data: title='{title}', company='{company}'")
                return None

        except Exception as e:
            logger.warning(f"Error extracting job data from LinkedIn card: {e}")
            return None

    def extract_job_data(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized job data from raw LinkedIn job data.

        Args:
            raw_job: Raw job data from LinkedIn

        Returns:
            Standardized job dictionary
        """
        # Create a descriptive text for the job
        description_parts = [
            f"Job from LinkedIn: {raw_job.get('title', '')}",
            f"at {raw_job.get('company', '')}",
        ]
        if raw_job.get('location'):
            description_parts.append(f"Location: {raw_job['location']}")
        if raw_job.get('posted_time'):
            description_parts.append(f"Posted: {raw_job['posted_time']}")

        description = " ".join(description_parts)

        return {
            'title': raw_job.get('title', ''),
            'company': raw_job.get('company', ''),
            'location': raw_job.get('location', ''),
            'description': description,
            'source': self.source_name,
            'url': raw_job.get('url', ''),
            'external_id': self.get_external_id(raw_job),
            'posted_time': raw_job.get('posted_time', ''),
        }

    def get_external_id(self, raw_job: Dict[str, Any]) -> str:
        """
        Extract the external ID from raw LinkedIn job data.

        Args:
            raw_job: Raw job data from LinkedIn

        Returns:
            External ID string (LinkedIn job ID from URL)
        """
        url = raw_job.get('url', '')
        # Extract job ID from LinkedIn URL pattern: /jobs/view/1234567890/
        match = re.search(r'/jobs/view/(\d+)', url)
        if match:
            return f"linkedin_{match.group(1)}"

        # Alternative pattern: /jobs/collections/recommended/?currentJobId=123456789
        match = re.search(r'[?&]currentJobId=(\d+)', url)
        if match:
            return f"linkedin_{match.group(1)}"

        # Fallback to URL hash
        import hashlib
        return f"linkedin_{hashlib.md5(url.encode()).hexdigest()[:12]}"

    async def _apply_rate_limiting(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()


class JobScrapingService:
    """Service for coordinating job scraping and storage."""

    def __init__(self):
        self.job_service = JobService()
        self.job_parser = JobParser()
        self.adapters: Dict[str, JobSourceAdapter] = {
            'seek': SeekAdapter(),
            'linkedin': LinkedInAdapter(),
        }

    async def scrape_and_store_jobs(
        self,
        source: str,
        search_params: Dict[str, Any],
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Scrape jobs from a source and store them in the database.

        Args:
            source: Source name ('seek', 'linkedin', etc.)
            search_params: Search parameters for the source
            db_session: Database session

        Returns:
            Dictionary with results statistics
        """
        if source not in self.adapters:
            raise ValueError(f"Unsupported source: {source}")

        adapter = self.adapters[source]
        stats = {
            'source': source,
            'scraped': 0,
            'new_jobs': 0,
            'duplicates': 0,
            'errors': 0,
            'job_ids': []
        }

        try:
            async with adapter:
                # Scrape raw jobs
                raw_jobs = await adapter.scrape_jobs(search_params)
                stats['scraped'] = len(raw_jobs)

                logger.info(f"Scraped {len(raw_jobs)} raw jobs from {source}")

                # Process each job
                for raw_job in raw_jobs:
                    try:
                        # Extract standardized job data
                        job_data = adapter.extract_job_data(raw_job)

                        # Check for duplicates
                        external_id = job_data['external_id']
                        source_name = job_data['source']

                        # Query for existing job with same external_id and source
                        result = await db_session.execute(
                            select(JobPosting).where(
                                JobPosting.source == source_name,
                                JobPosting.description.like(f"%{external_id}%")  # Simple approach
                            )
                        )
                        existing_job = result.scalar_one_or_none()

                        if existing_job:
                            stats['duplicates'] += 1
                            logger.debug(f"Duplicate job found: {external_id}")
                            continue

                        # Store the job using JobService
                        job_text = f"""
                        Title: {job_data['title']}
                        Company: {job_data['company']}
                        Location: {job_data['location']}
                        Source: {job_data['source']}
                        URL: {job_data.get('url', '')}

                        Description:
                        {job_data['description']}
                        """

                        result = await self.job_service.add_job(
                            job_text=job_text,
                            source=source_name,
                            db_session=db_session
                        )

                        if result and 'job_id' in result:
                            stats['new_jobs'] += 1
                            stats['job_ids'].append(result['job_id'])
                            logger.info(f"Stored new job: {job_data['title']} at {job_data['company']}")

                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"Error processing job from {source}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error in scrape_and_store_jobs for {source}: {e}")
            stats['errors'] += 1

        logger.info(f"Finished scraping {source}: {stats}")
        return stats

    async def scrape_multiple_sources(
        self,
        sources: List[str],
        search_params: Dict[str, Any],
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Scrape jobs from multiple sources.

        Args:
            sources: List of source names to scrape
            search_params: Search parameters to use for all sources
            db_session: Database session

        Returns:
- Dictionary with combined results statistics
        """
        combined_stats = {
            'sources': sources,
            'total_scraped': 0,
            'total_new_jobs': 0,
            'total_duplicates': 0,
            'total_errors': 0,
            'source_results': {},
            'all_job_ids': []
        }

        # Scrape each source
        for source in sources:
            if source in self.adapters:
                try:
                    source_stats = await self.scrape_and_store_jobs(
                        source, search_params, db_session
                    )

                    combined_stats['source_results'][source] = source_stats
                    combined_stats['total_scraped'] += source_stats['scraped']
                    combined_stats['total_new_jobs'] += source_stats['new_jobs']
                    combined_stats['total_duplicates'] += source_stats['duplicates']
                    combined_stats['total_errors'] += source_stats['errors']
                    combined_stats['all_job_ids'].extend(source_stats['job_ids'])

                except Exception as e:
                    logger.error(f"Error scraping source {source}: {e}")
                    combined_stats['source_results'][source] = {
                        'error': str(e),
                        'scraped': 0,
                        'new_jobs': 0,
                        'duplicates': 0,
                        'errors': 1
                    }
                    combined_stats['total_errors'] += 1
            else:
                logger.warning(f"Unknown source: {source}")
                combined_stats['source_results'][source] = {
                    'error': f'Unsupported source: {source}',
                    'scraped': 0,
                    'new_jobs': 0,
                    'duplicates': 0,
                    'errors': 1
                }
                combined_stats['total_errors'] += 1

        return combined_stats