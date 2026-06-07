"""
Internal job scraping scheduler for AI Career Agent.
Handles automated scraping from LinkedIn and Seek using APScheduler.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.base import get_async_session_context
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


class JobScrapingScheduler:
    """Internal scheduler for automated job scraping."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_service = JobService()
        self._is_running = False

    async def _scrape_linkedin_incremental(self):
        """Incremental LinkedIn scraping for recent jobs (last N hours)."""
        logger.info("Starting incremental LinkedIn job scraping...")
        try:
            async with get_async_session_context() as session:
                result = await self.job_service.scrape_and_store_jobs(
                    source="linkedin",
                    search_params={
                        "keywords": settings.LINKEDIN_DEFAULT_KEYWORDS or "",
                        "location": settings.LINKEDIN_DEFAULT_LOCATION or "",
                        "hours": settings.INCREMENTAL_SCRAPE_HOURS
                    },
                    db_session=session
                )
                logger.info(
                    f"Incremental LinkedIn scraping completed: "
                    f"{result.get('new_jobs', 0)} new jobs, "
                    f"{result.get('duplicates', 0)} duplicates"
                )
        except Exception as e:
            logger.error(f"Error in incremental LinkedIn scraping: {e}")

    async def _scrape_linkedin_full(self):
        """Full LinkedIn scraping for comprehensive job collection."""
        logger.info("Starting full LinkedIn job scraping...")
        try:
            async with get_async_session_context() as session:
                result = await self.job_service.scrape_and_store_jobs(
                    source="linkedin",
                    search_params={
                        "keywords": settings.LINKEDIN_DEFAULT_KEYWORDS or "",
                        "location": settings.LINKEDIN_DEFAULT_LOCATION or ""
                    },
                    db_session=session
                )
                logger.info(
                    f"Full LinkedIn scraping completed: "
                    f"{result.get('new_jobs', 0)} new jobs, "
                    f"{result.get('duplicates', 0)} duplicates"
                )
        except Exception as e:
            logger.error(f"Error in full LinkedIn scraping: {e}")

    async def _scrape_seek_incremental(self):
        """Incremental Seek scraping for recent jobs (last N hours)."""
        logger.info("Starting incremental Seek job scraping...")
        try:
            async with get_async_session_context() as session:
                result = await self.job_service.scrape_and_store_jobs(
                    source="seek",
                    search_params={
                        "keywords": settings.SEEK_DEFAULT_KEYWORDS or "",
                        "location": settings.SEEK_DEFAULT_LOCATION or "",
                        "hours": settings.INCREMENTAL_SCRAPE_HOURS
                    },
                    db_session=session
                )
                logger.info(
                    f"Incremental Seek scraping completed: "
                    f"{result.get('new_jobs', 0)} new jobs, "
                    f"{result.get('duplicates', 0)} duplicates"
                )
        except Exception as e:
            logger.error(f"Error in incremental Seek scraping: {e}")

    async def _scrape_seek_full(self):
        """Full Seek scraping for comprehensive job collection."""
        logger.info("Starting full Seek job scraping...")
        try:
            async with get_async_session_context() as session:
                result = await self.job_service.scrape_and_store_jobs(
                    source="seek",
                    search_params={
                        "keywords": settings.SEEK_DEFAULT_KEYWORDS or "",
                        "location": settings.SEEK_DEFAULT_LOCATION or ""
                    },
                    db_session=session
                )
                logger.info(
                    f"Full Seek scraping completed: "
                    f"{result.get('new_jobs', 0)} new jobs, "
                    f"{result.get('duplicates', 0)} duplicates"
                )
        except Exception as e:
            logger.error(f"Error in full Seek scraping: {e}")

    async def _scrape_all_incremental(self):
        """Run incremental scraping for all enabled sources."""
        logger.info("Starting incremental scraping for all sources...")
        tasks = []

        if settings.LINKEDIN_SCRAPING_ENABLED:
            tasks.append(self._scrape_linkedin_incremental())

        if settings.SEEK_SCRAPING_ENABLED:
            tasks.append(self._scrape_seek_incremental())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _scrape_all_full(self):
        """Run full scraping for all enabled sources."""
        logger.info("Starting full scraping for all sources...")
        tasks = []

        if settings.LINKEDIN_SCRAPING_ENABLED:
            tasks.append(self._scrape_linkedin_full())

        if settings.SEEK_SCRAPING_ENABLED:
            tasks.append(self._scrape_seek_full())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _scrape_seek_daily_presets(self):
        """Daily Seek scraping with role presets."""
        logger.info("Starting daily Seek scrape with role presets...")
        try:
            from app.ingestion.seek_scheduled import SeekScheduledScraper

            scraper = SeekScheduledScraper()
            result = await scraper.run_daily_scrape()

            if result.get("status") == "disabled":
                logger.info("Daily Seek scrape skipped (disabled)")
            else:
                logger.info(
                    f"Daily Seek scrape complete: "
                    f"{result.get('total_new_jobs', 0)} new jobs "
                    f"across {result.get('presets_run', 0)} presets"
                )
        except Exception as e:
            logger.error(f"Error in daily Seek preset scraping: {e}")

    def start(self):
        """Start the scheduler with configured jobs."""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting job scraping scheduler...")
        print("JOB SCHEDULER START CALLED")  # Debug print
        self.scheduler = AsyncIOScheduler()

        # Incremental scraping every 2 hours during business hours (using NZ time settings)
        if settings.SCHEDULER_INCREMENTAL_ENABLED:
            # Calculate hours for every 2 hours during business hours
            start_hour = settings.BUSINESS_HOURS_START
            end_hour = settings.BUSINESS_HOURS_END
            incremental_hours = []

            for hour in range(start_hour, end_hour + 1, 2):  # Every 2 hours
                incremental_hours.append(str(hour))

            hour_str = ",".join(incremental_hours)

            self.scheduler.add_job(
                self._scrape_all_incremental,
                trigger=CronTrigger(
                    hour=hour_str,  # Every 2 hours during business hours
                    minute="0",  # At the top of the hour
                    timezone=settings.SCHEDULER_TIMEZONE
                ),
                id="incremental_job_scraping",
                name="Incremental Job Scraping (LinkedIn + Seek)",
                replace_existing=True
            )
            logger.info(
                f"Added incremental job scraping job "
                f"(every 2 hours from {start_hour}:00 to {end_hour}:00, "
                f"timezone: {settings.SCHEDULER_TIMEZONE})"
            )

        # Full scraping once daily at configured time
        if settings.SCHEDULER_FULL_ENABLED:
            self.scheduler.add_job(
                self._scrape_all_full,
                trigger=CronTrigger(
                    hour=settings.FULL_SCRAPE_TIME_HOUR,
                    minute=settings.FULL_SCRAPE_TIME_MINUTE,
                    timezone=settings.SCHEDULER_TIMEZONE
                ),
                id="full_job_scraping",
                name="Full Job Scraping (LinkedIn + Seek)",
                replace_existing=True
            )
            logger.info(
                f"Added full job scraping job "
                f"(daily at {settings.FULL_SCRAPE_TIME_HOUR:02d}:{settings.FULL_SCRAPE_TIME_MINUTE:02d}, "
                f"timezone: {settings.SCHEDULER_TIMEZONE})"
            )

        # Daily Seek scrape with role presets
        if settings.SEEK_SCRAPING_ENABLED:
            self.scheduler.add_job(
                self._scrape_seek_daily_presets,
                trigger=CronTrigger(
                    hour=settings.SEEK_DAILY_SCRAPE_HOUR,
                    minute=settings.SEEK_DAILY_SCRAPE_MINUTE,
                    timezone=settings.SCHEDULER_TIMEZONE
                ),
                id="seek_daily_preset_scraping",
                name="Daily Seek Scraping (Role Presets)",
                replace_existing=True
            )
            logger.info(
                f"Added daily Seek preset scraping job "
                f"(daily at {settings.SEEK_DAILY_SCRAPE_HOUR:02d}:{settings.SEEK_DAILY_SCRAPE_MINUTE:02d}, "
                f"timezone: {settings.SCHEDULER_TIMEZONE})"
            )

        self.scheduler.start()
        self._is_running = True
        logger.info("Job scraping scheduler started successfully")
        print("JOB SCHEDULER STARTED SUCCESSFULLY")  # Debug print

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if not self._is_running or not self.scheduler:
            logger.warning("Scheduler is not running")
            return

        logger.info("Shutting down job scraping scheduler...")
        self.scheduler.shutdown(wait=False)
        self._is_running = False
        logger.info("Job scraping scheduler shutdown complete")

    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        return self._is_running and self.scheduler is not None and self.scheduler.running

    def get_jobs(self):
        """Get list of scheduled jobs for inspection."""
        if not self.scheduler:
            return []
        return self.scheduler.get_jobs()


# Global scheduler instance
job_scheduler = JobScrapingScheduler()