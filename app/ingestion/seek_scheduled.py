"""Scheduled Seek scraping with role preset rotation.

Implements daily automated Seek scraping across configured role presets,
with rate limiting, error isolation, and result aggregation.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from app.core.config import settings
from app.db.base import get_async_session_context
from app.ingestion.role_presets import get_active_presets
from app.ingestion.seek_models import SeekSearchParams
from app.ingestion.seek_scraper_service import SeekScrapingService

logger = logging.getLogger(__name__)


class SeekScheduledScraper:
    """Scheduled Seek scraping with role preset rotation.

    Iterates through active role presets, executing Seek scrapes for each
    with configurable delays between searches. Aggregates results and
    isolates failures so one preset error doesn't block the rest.
    """

    def __init__(self) -> None:
        """Initialize the scheduled scraper."""
        pass

    async def run_daily_scrape(self) -> dict[str, Any]:
        """Execute scheduled scrape for all active role presets.

        Iterates through enabled presets, calling SeekScrapingService.scrape_and_store()
        for each with date_range=1 (last 24 hours). Introduces a 30-60 second random
        delay between preset searches to avoid detection.

        Returns:
            Dictionary with aggregated results including:
            - status: "completed" or "disabled"
            - presets_run: number of presets executed
            - total_new_jobs: sum of new jobs across all presets
            - total_duplicates: sum of duplicates across all presets
            - total_errors: number of presets that failed
            - per_preset: dict mapping preset ID to individual results
        """
        # Skip execution if scraping is disabled
        if not settings.SEEK_SCRAPING_ENABLED:
            logger.info("Seek scraping is disabled. Skipping daily scrape.")
            return {"status": "disabled"}

        presets = get_active_presets()
        if not presets:
            logger.info("No active role presets configured. Skipping daily scrape.")
            return {
                "status": "completed",
                "presets_run": 0,
                "total_new_jobs": 0,
                "total_duplicates": 0,
                "total_errors": 0,
                "per_preset": {},
            }

        logger.info(
            f"Starting daily Seek scrape for {len(presets)} presets: "
            f"{[p.id for p in presets]}"
        )

        total_results: dict[str, Any] = {
            "status": "completed",
            "presets_run": 0,
            "total_new_jobs": 0,
            "total_duplicates": 0,
            "total_errors": 0,
            "per_preset": {},
        }

        seek_service = SeekScrapingService(
            chrome_profile_path=settings.SEEK_CHROME_PROFILE_PATH,
            headless=settings.SEEK_HEADLESS,
        )

        for i, preset in enumerate(presets):
            try:
                params = SeekSearchParams(
                    keywords=preset.keywords,
                    location=preset.location,
                    classification=preset.classification,
                    salary_min=preset.salary_min,
                    max_pages=settings.SEEK_MAX_PAGES_PER_SEARCH,
                    date_range=1,  # Only jobs from last 24 hours for daily scrape
                )

                logger.info(f"Scraping preset '{preset.id}': keywords='{preset.keywords}'")

                async with get_async_session_context() as db_session:
                    result = await seek_service.scrape_and_store(params, db_session)

                total_results["presets_run"] += 1
                total_results["total_new_jobs"] += result.new_jobs
                total_results["total_duplicates"] += result.duplicates
                total_results["per_preset"][preset.id] = {
                    "new_jobs": result.new_jobs,
                    "duplicates": result.duplicates,
                    "errors": result.errors,
                    "scraped": result.scraped,
                    "pages_scraped": result.pages_scraped,
                }

                logger.info(
                    f"Preset '{preset.id}' complete: "
                    f"{result.new_jobs} new, {result.duplicates} duplicates, "
                    f"{result.errors} errors"
                )

            except Exception as e:
                # Preset isolation: log error and continue to next preset
                total_results["total_errors"] += 1
                total_results["per_preset"][preset.id] = {"error": str(e)}
                logger.error(f"Error scraping preset '{preset.id}': {e}")

            # Rate limiting between presets (30-60 seconds), skip delay after last preset
            if i < len(presets) - 1:
                delay = random.uniform(30, 60)
                logger.debug(f"Waiting {delay:.1f}s before next preset...")
                await asyncio.sleep(delay)

        logger.info(
            f"Daily Seek scrape complete: "
            f"{total_results['total_new_jobs']} new jobs, "
            f"{total_results['total_duplicates']} duplicates, "
            f"{total_results['total_errors']} errors "
            f"across {total_results['presets_run']} presets"
        )

        return total_results
