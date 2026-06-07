"""Seek.co.nz Playwright-based scraping service.

Manages browser automation for scraping job listings from seek.co.nz using
the user's existing Chrome profile. Implements rate limiting, CAPTCHA detection,
deduplication, and graceful error handling.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ingestion.seek_models import SeekJobCard, SeekJobDetail, SeekSearchParams, SeekScrapeResult
from app.ingestion.seek_parser import SeekPageParser

logger = logging.getLogger(__name__)

# Lazy import for Playwright — it may not be installed
_playwright_available: Optional[bool] = None


def _check_playwright() -> bool:
    """Check if Playwright is available and importable."""
    global _playwright_available
    if _playwright_available is None:
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            _playwright_available = True
        except ImportError:
            _playwright_available = False
    return _playwright_available


class PlaywrightNotInstalledError(Exception):
    """Raised when Playwright is not installed or browsers are not set up."""

    def __init__(self) -> None:
        super().__init__(
            "Playwright is not installed. Install with: "
            "pip install playwright && playwright install chromium"
        )


class ChromeProfileLockedError(Exception):
    """Raised when the Chrome profile is already in use by another process."""

    def __init__(self, profile_path: str) -> None:
        super().__init__(
            f"Chrome profile is locked (already in use): {profile_path}. "
            "Close other Chrome instances using this profile and try again."
        )
        self.profile_path = profile_path


class CaptchaDetectedError(Exception):
    """Raised when a CAPTCHA or bot detection page is encountered."""

    def __init__(self) -> None:
        super().__init__(
            "CAPTCHA or bot detection page encountered. "
            "Aborting scrape and returning partial results."
        )


# CAPTCHA detection keywords in page content
CAPTCHA_INDICATORS = [
    "captcha",
    "are you a robot",
    "verify you are human",
    "unusual traffic",
    "automated access",
    "please verify",
    "security check",
]


class SeekScrapingService:
    """Playwright-based Seek.co.nz job scraper using the user's Chrome profile.

    Manages browser lifecycle, pagination, rate limiting, and error handling
    for automated Seek job search and detail extraction.
    """

    def __init__(
        self,
        chrome_profile_path: Optional[str] = None,
        headless: bool = True,
    ) -> None:
        """Configure Playwright settings for Seek scraping.

        Args:
            chrome_profile_path: Path to Chrome user data directory. Falls back
                to settings.SEEK_CHROME_PROFILE_PATH if not provided.
            headless: Whether to run the browser in headless mode.
        """
        self._chrome_profile_path = chrome_profile_path or settings.SEEK_CHROME_PROFILE_PATH
        self._headless = headless
        self._parser = SeekPageParser()
        self._delay_min = settings.SEEK_REQUEST_DELAY_MIN
        self._delay_max = settings.SEEK_REQUEST_DELAY_MAX

    async def _random_delay(self) -> None:
        """Introduce a random delay between requests for rate limiting."""
        delay = random.uniform(self._delay_min, self._delay_max)
        await asyncio.sleep(delay)

    def _detect_captcha(self, page_content: str) -> bool:
        """Check if the page content indicates a CAPTCHA or bot detection.

        Args:
            page_content: The HTML content of the current page.

        Returns:
            True if CAPTCHA indicators are found, False otherwise.
        """
        content_lower = page_content.lower()
        return any(indicator in content_lower for indicator in CAPTCHA_INDICATORS)

    async def scrape_jobs(self, search_params: SeekSearchParams) -> SeekScrapeResult:
        """Scrape job listings from seek.co.nz search results.

        Launches a Playwright browser with the configured Chrome profile,
        navigates through search result pages, and extracts job cards.
        Does NOT perform deduplication or storage — use scrape_and_store()
        for the full pipeline.

        Args:
            search_params: Search parameters including keywords, location,
                and pagination settings.

        Returns:
            SeekScrapeResult containing extracted job cards info and page counts.
            The result only populates scraped/pages_scraped (no new_jobs/duplicates
            since this method doesn't do dedup/storage).

        Raises:
            PlaywrightNotInstalledError: If Playwright is not installed.
            ChromeProfileLockedError: If the Chrome profile is locked.
        """
        if not _check_playwright():
            raise PlaywrightNotInstalledError()

        from playwright.async_api import async_playwright, Error as PlaywrightError

        result = SeekScrapeResult(search_params=search_params)
        context = None

        try:
            pw = await async_playwright().start()

            try:
                context = await pw.chromium.launch_persistent_context(
                    user_data_dir=self._chrome_profile_path,
                    headless=self._headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except PlaywrightError as e:
                error_msg = str(e).lower()
                if "lock" in error_msg or "already in use" in error_msg or "single instance" in error_msg:
                    raise ChromeProfileLockedError(self._chrome_profile_path) from e
                raise

            page = await context.new_page()

            # Paginate through search results
            for page_num in range(search_params.page, search_params.page + search_params.max_pages):
                search_url = self._parser.build_search_url(search_params, page=page_num)
                logger.info(f"Navigating to Seek search page {page_num}: {search_url}")

                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await self._random_delay()

                page_html = await page.content()

                # Check for CAPTCHA
                if self._detect_captcha(page_html):
                    logger.warning(
                        "CAPTCHA detected on Seek. Aborting scrape and returning partial results."
                    )
                    break

                # Parse job cards from the page
                job_cards = self._parser.parse_search_results(page_html)

                if not job_cards:
                    logger.info(f"No job cards found on page {page_num}. Stopping pagination.")
                    break

                result.scraped += len(job_cards)
                result.pages_scraped += 1

                logger.info(f"Found {len(job_cards)} job cards on page {page_num}")

        finally:
            if context:
                await context.close()
            # Stop playwright
            try:
                await pw.stop()
            except Exception:
                pass

        return result

    async def scrape_job_detail(
        self, page, job_url: str
    ) -> Optional[SeekJobDetail]:
        """Navigate to a single job page and extract full details.

        Args:
            page: An active Playwright page instance.
            job_url: The URL of the job detail page.

        Returns:
            SeekJobDetail if extraction succeeds, None if the page
            cannot be parsed or a CAPTCHA is detected.
        """
        try:
            await page.goto(job_url, wait_until="networkidle", timeout=30000)
            await self._random_delay()

            page_html = await page.content()

            # Check for CAPTCHA on detail page
            if self._detect_captcha(page_html):
                logger.warning(f"CAPTCHA detected on job detail page: {job_url}")
                return None

            detail = self._parser.parse_job_detail(page_html, job_url)
            return detail

        except Exception as e:
            logger.error(f"Error extracting job detail from {job_url}: {e}")
            return None

    async def scrape_and_store(
        self,
        params: SeekSearchParams,
        db_session: AsyncSession,
    ) -> SeekScrapeResult:
        """Scrape Seek jobs and store new ones in the database.

        Full pipeline: launches browser, paginates through results,
        checks deduplication for each card, navigates to detail pages
        for new jobs, stores via JobService, and updates metadata.

        Maintains the counting invariant:
            result.scraped == result.new_jobs + result.duplicates + result.errors

        Args:
            params: Search parameters for the Seek search.
            db_session: Active SQLAlchemy async session for DB operations.

        Returns:
            SeekScrapeResult with accurate counts of new jobs, duplicates,
            errors, and stored job IDs.

        Raises:
            PlaywrightNotInstalledError: If Playwright is not installed.
            ChromeProfileLockedError: If the Chrome profile is locked.
        """
        if not _check_playwright():
            raise PlaywrightNotInstalledError()

        from playwright.async_api import async_playwright, Error as PlaywrightError
        from app.ingestion.deduplication import is_duplicate
        from app.services.job_service import JobService

        result = SeekScrapeResult(search_params=params)
        job_service = JobService()
        context = None

        try:
            pw = await async_playwright().start()

            try:
                context = await pw.chromium.launch_persistent_context(
                    user_data_dir=self._chrome_profile_path,
                    headless=self._headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except PlaywrightError as e:
                error_msg = str(e).lower()
                if "lock" in error_msg or "already in use" in error_msg or "single instance" in error_msg:
                    raise ChromeProfileLockedError(self._chrome_profile_path) from e
                raise

            page = await context.new_page()

            # Paginate through search results
            for page_num in range(params.page, params.page + params.max_pages):
                search_url = self._parser.build_search_url(params, page=page_num)
                logger.info(f"Navigating to Seek search page {page_num}: {search_url}")

                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await self._random_delay()

                page_html = await page.content()

                # Check for CAPTCHA
                if self._detect_captcha(page_html):
                    logger.warning(
                        "CAPTCHA detected on Seek. Aborting scrape and returning partial results."
                    )
                    break

                # Parse job cards from the page
                job_cards = self._parser.parse_search_results(page_html)

                if not job_cards:
                    logger.info(f"No job cards found on page {page_num}. Stopping pagination.")
                    break

                result.pages_scraped += 1
                logger.info(f"Found {len(job_cards)} job cards on page {page_num}")

                # Process each job card
                for card in job_cards:
                    result.scraped += 1

                    try:
                        # Check deduplication before fetching detail
                        duplicate = await is_duplicate(
                            url=card.url,
                            title=card.title,
                            company=card.company,
                            db_session=db_session,
                        )

                        if duplicate:
                            result.duplicates += 1
                            logger.debug(f"Duplicate job skipped: {card.title} at {card.company}")
                            continue

                        # Navigate to detail page for full description
                        detail = await self.scrape_job_detail(page, card.url)

                        if detail is None:
                            # CAPTCHA on detail page or parse failure
                            result.errors += 1
                            logger.warning(f"Failed to extract detail for: {card.url}")
                            # If CAPTCHA was detected, abort entirely
                            detail_html = await page.content()
                            if self._detect_captcha(detail_html):
                                logger.warning("CAPTCHA on detail page. Aborting scrape.")
                                return result
                            continue

                        # Format job text for storage
                        job_text = self._format_job_text(detail)

                        # Store via JobService pipeline
                        stored = await job_service.add_job(
                            job_text=job_text,
                            source="seek_nz",
                            db_session=db_session,
                        )

                        if stored and "job_id" in stored:
                            job_id = stored["job_id"]
                            # Update job metadata (URL and salary_range)
                            await self._update_job_metadata(
                                job_id=job_id,
                                url=detail.url,
                                salary_range=detail.salary_range,
                                db_session=db_session,
                            )
                            result.new_jobs += 1
                            result.job_ids.append(job_id)
                            logger.info(
                                f"Stored new Seek job #{job_id}: {detail.title} at {detail.company}"
                            )
                        else:
                            result.errors += 1
                            logger.error(f"Failed to store job: {detail.title}")

                    except Exception as e:
                        result.errors += 1
                        logger.error(f"Error processing job card {card.url}: {e}")

        except (PlaywrightNotInstalledError, ChromeProfileLockedError):
            # Re-raise these specific errors for the API layer to handle
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Seek scrape: {e}")
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            try:
                await pw.stop()
            except Exception:
                pass

        return result

    def _format_job_text(self, detail: SeekJobDetail) -> str:
        """Format a SeekJobDetail into a text block for JobService.add_job().

        Constructs a structured text representation that the job parser
        can extract title, company, location, and description from.

        Args:
            detail: The full job detail extracted from a Seek page.

        Returns:
            Formatted job text string.
        """
        parts = [
            f"Title: {detail.title}",
            f"Company: {detail.company}",
            f"Location: {detail.location}",
        ]

        if detail.salary_range:
            parts.append(f"Salary: {detail.salary_range}")

        if detail.work_type:
            parts.append(f"Work Type: {detail.work_type}")

        if detail.classification:
            parts.append(f"Classification: {detail.classification}")

        if detail.sub_classification:
            parts.append(f"Sub-classification: {detail.sub_classification}")

        parts.append(f"\nDescription:\n{detail.description}")

        if detail.requirements:
            parts.append(f"\nRequirements:\n{detail.requirements}")

        if detail.benefits:
            parts.append(f"\nBenefits:\n{detail.benefits}")

        return "\n".join(parts)

    async def _update_job_metadata(
        self,
        job_id: int,
        url: str,
        salary_range: Optional[str],
        db_session: AsyncSession,
    ) -> None:
        """Update URL and salary_range on a stored JobPosting record.

        Args:
            job_id: The ID of the stored JobPosting.
            url: The original Seek URL for the job.
            salary_range: The salary range text, if available.
            db_session: Active async session.
        """
        from sqlalchemy import update
        from app.db.models import JobPosting

        try:
            values: dict = {"url": url}
            if salary_range:
                values["salary_range"] = salary_range

            stmt = update(JobPosting).where(JobPosting.id == job_id).values(**values)
            await db_session.execute(stmt)
            await db_session.flush()
        except Exception as e:
            logger.error(f"Failed to update metadata for job #{job_id}: {e}")
