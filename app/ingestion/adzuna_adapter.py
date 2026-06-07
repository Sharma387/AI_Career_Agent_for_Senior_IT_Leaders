"""
Adzuna Job API adapter for AI Career Agent.
Uses the free Adzuna API to search for job listings across multiple countries.

Sign up for free API keys at: https://developer.adzuna.com/signup
"""

import logging
from typing import Any, Dict, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaAdapter:
    """Adapter for fetching jobs from the Adzuna API."""

    def __init__(self):
        self.app_id = settings.ADZUNA_APP_ID
        self.app_key = settings.ADZUNA_APP_KEY
        self.country = settings.ADZUNA_COUNTRY
        self.results_per_page = settings.ADZUNA_RESULTS_PER_PAGE

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    async def search_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for jobs using the Adzuna API.

        Args:
            search_params: Dictionary with keys:
                - keywords (str): Search keywords e.g. "CTO", "Engineering Manager"
                - location (str): Location filter e.g. "Auckland", "Sydney"
                - page (int): Page number (1-based)
                - country (str): Override country code (nz, au, gb, us)
                - salary_min (int): Minimum salary filter
                - full_time (bool): Filter for full-time only
                - permanent (bool): Filter for permanent only
                - category (str): Adzuna category tag e.g. "it-jobs"
                - max_days_old (int): Max age of listing in days

        Returns:
            List of standardized job dictionaries
        """
        if not self.is_configured:
            logger.error("Adzuna API not configured. Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env")
            return []

        country = search_params.get("country", self.country)
        page = search_params.get("page", 1)

        url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": self.results_per_page,
            "content-type": "application/json",
        }

        # Add search keywords
        if search_params.get("keywords"):
            params["what"] = search_params["keywords"]

        # Add location
        if search_params.get("location"):
            params["where"] = search_params["location"]

        # Optional filters
        if search_params.get("salary_min"):
            params["salary_min"] = search_params["salary_min"]

        if search_params.get("full_time"):
            params["full_time"] = 1

        if search_params.get("permanent"):
            params["permanent"] = 1

        if search_params.get("category"):
            params["category"] = search_params["category"]

        if search_params.get("max_days_old"):
            params["max_days_old"] = search_params["max_days_old"]

        if search_params.get("sort_by"):
            params["sort_by"] = search_params["sort_by"]

        logger.info(f"Searching Adzuna: country={country}, keywords={params.get('what', '')}, location={params.get('where', '')}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    logger.error(f"Adzuna API error: HTTP {response.status_code} - {response.text[:200]}")
                    return []

                data = response.json()
                results = data.get("results", [])

                logger.info(f"Adzuna returned {len(results)} jobs (total available: {data.get('count', 0)})")

                # Convert to standardized format
                jobs = []
                for result in results:
                    job = self._normalize_job(result, country)
                    if job:
                        jobs.append(job)

                return jobs

        except httpx.TimeoutException:
            logger.error("Adzuna API request timed out")
            return []
        except Exception as e:
            logger.error(f"Adzuna API error: {e}")
            return []

    def _normalize_job(self, raw: Dict[str, Any], country: str) -> Dict[str, Any]:
        """Convert Adzuna response to our standard job format."""
        location = raw.get("location", {})
        location_display = location.get("display_name", "") if isinstance(location, dict) else ""

        company = raw.get("company", {})
        company_name = company.get("display_name", "") if isinstance(company, dict) else ""

        category = raw.get("category", {})
        category_label = category.get("label", "") if isinstance(category, dict) else ""

        # Build a description from available fields
        description_parts = []
        if raw.get("description"):
            description_parts.append(raw["description"])
        if raw.get("contract_type"):
            description_parts.append(f"Contract: {raw['contract_type']}")
        if raw.get("contract_time"):
            description_parts.append(f"Type: {raw['contract_time']}")
        if raw.get("salary_min") or raw.get("salary_max"):
            salary_min = raw.get("salary_min", "")
            salary_max = raw.get("salary_max", "")
            if salary_min and salary_max:
                description_parts.append(f"Salary: {salary_min:,.0f} - {salary_max:,.0f}")
            elif salary_min:
                description_parts.append(f"Salary: from {salary_min:,.0f}")

        description = "\n".join(description_parts)

        # Build salary range string
        salary_range = ""
        if raw.get("salary_min") and raw.get("salary_max"):
            salary_range = f"{raw['salary_min']:,.0f} - {raw['salary_max']:,.0f}"
        elif raw.get("salary_min"):
            salary_range = f"From {raw['salary_min']:,.0f}"

        return {
            "title": raw.get("title", ""),
            "company": company_name,
            "location": location_display,
            "description": description,
            "url": raw.get("redirect_url", ""),
            "source": f"adzuna_{country}",
            "external_id": f"adzuna_{raw.get('id', '')}",
            "salary_range": salary_range,
            "category": category_label,
            "created": raw.get("created", ""),
            "contract_type": raw.get("contract_type", ""),
            "contract_time": raw.get("contract_time", ""),
        }
