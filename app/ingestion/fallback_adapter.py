"""
Fallback job search adapter using free APIs (no API key required).
Used when Adzuna quota is exhausted.

Sources:
- Arbeitnow (free, no key) — remote-friendly tech jobs
- Jobicy (free, no key) — remote tech/IT jobs
"""

import logging
import re
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)


class FallbackJobAdapter:
    """
    Fallback adapter using free job APIs that require no API key.
    Tries multiple free sources to maximize results.
    """

    async def search_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for jobs using free APIs.

        Args:
            search_params: Dictionary with 'keywords', 'location', 'page'

        Returns:
            List of standardized job dictionaries
        """
        jobs = []

        # Try Jobicy first (better for IT/tech remote roles)
        jobicy_jobs = await self._search_jobicy(search_params)
        jobs.extend(jobicy_jobs)

        # Then Arbeitnow
        arbeitnow_jobs = await self._search_arbeitnow(search_params)
        jobs.extend(arbeitnow_jobs)

        if not jobs:
            logger.warning("Fallback adapter: no results from any free source")

        return jobs[:20]  # Cap at 20 results

    async def _search_jobicy(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search Jobicy free remote jobs API."""
        keywords = search_params.get("keywords", "")

        # Jobicy supports tag-based search
        url = "https://jobicy.com/api/v2/remote-jobs"
        params = {"count": 20}

        # Map keywords to Jobicy industry tags
        kw_lower = keywords.lower()
        if any(x in kw_lower for x in ["project manager", "program manager", "delivery", "scrum"]):
            params["tag"] = "project-management"
        elif any(x in kw_lower for x in ["engineer", "developer", "software", "devops"]):
            params["tag"] = "software-dev"
        elif any(x in kw_lower for x in ["director", "cto", "vp", "head of", "manager"]):
            params["tag"] = "management"
        elif any(x in kw_lower for x in ["data", "analytics", "machine learning"]):
            params["tag"] = "data"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    logger.error(f"Jobicy API error: HTTP {response.status_code}")
                    return []

                data = response.json()
                all_jobs = data.get("jobs", [])

                # Filter by keywords locally for better matching
                if keywords:
                    keyword_list = [k.strip().lower().strip('"') for k in keywords.replace(" OR ", "|").split("|")]
                    filtered = []
                    for job in all_jobs:
                        title = job.get("jobTitle", "").lower()
                        industry = job.get("jobIndustry", [])
                        industry_str = " ".join(industry).lower() if isinstance(industry, list) else str(industry).lower()
                        combined = f"{title} {industry_str}"
                        if any(kw in combined for kw in keyword_list):
                            filtered.append(job)
                    if filtered:
                        all_jobs = filtered

                jobs = []
                for raw in all_jobs[:10]:
                    job = self._normalize_jobicy(raw)
                    if job:
                        jobs.append(job)

                logger.info(f"Jobicy (fallback) returned {len(jobs)} jobs matching '{keywords}'")
                return jobs

        except Exception as e:
            logger.error(f"Jobicy API error: {e}")
            return []

    async def _search_arbeitnow(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search Arbeitnow free job API."""
        keywords = search_params.get("keywords", "")
        page = search_params.get("page", 1)

        url = "https://www.arbeitnow.com/api/job-board-api"
        params = {}
        if page > 1:
            params["page"] = page

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    logger.error(f"Arbeitnow API error: HTTP {response.status_code}")
                    return []

                data = response.json()
                all_jobs = data.get("data", [])

                # Filter by keywords locally
                if keywords:
                    keyword_list = [k.strip().lower().strip('"') for k in keywords.replace(" OR ", "|").split("|")]
                    filtered = []
                    for job in all_jobs:
                        title = job.get("title", "").lower()
                        description = job.get("description", "").lower()
                        tags = " ".join(job.get("tags", [])).lower()
                        combined = f"{title} {description} {tags}"
                        if any(kw in combined for kw in keyword_list):
                            filtered.append(job)
                    all_jobs = filtered

                jobs = []
                for raw in all_jobs[:10]:
                    job = self._normalize_arbeitnow(raw)
                    if job:
                        jobs.append(job)

                logger.info(f"Arbeitnow (fallback) returned {len(jobs)} jobs matching '{keywords}'")
                return jobs

        except Exception as e:
            logger.error(f"Arbeitnow API error: {e}")
            return []

    def _normalize_jobicy(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Jobicy job to standard format."""
        geo = raw.get("jobGeo", "Remote")
        location = geo if geo else "Remote"

        # Clean description
        description = raw.get("jobExcerpt", "") or ""
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        salary_range = ""
        if raw.get("annualSalaryMin") and raw.get("annualSalaryMax"):
            salary_range = f"{raw['annualSalaryMin']} - {raw['annualSalaryMax']} {raw.get('salaryCurrency', '')}"

        return {
            "title": raw.get("jobTitle", ""),
            "company": raw.get("companyName", ""),
            "location": location,
            "description": description,
            "url": raw.get("url", ""),
            "source": "jobicy_free",
            "external_id": f"jobicy_{raw.get('id', '')}",
            "salary_range": salary_range,
            "category": ", ".join(raw.get("jobIndustry", [])) if isinstance(raw.get("jobIndustry"), list) else "",
            "created": raw.get("pubDate", ""),
            "contract_type": raw.get("jobType", ""),
            "contract_time": "",
        }

    def _normalize_arbeitnow(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Arbeitnow job to standard format."""
        description = raw.get("description", "")
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()
        if len(description) > 500:
            description = description[:500] + "..."

        location = raw.get("location", "Remote")
        if raw.get("remote", False):
            location = f"{location} (Remote)" if location and location != "Remote" else "Remote"

        return {
            "title": raw.get("title", ""),
            "company": raw.get("company_name", ""),
            "location": location,
            "description": description,
            "url": raw.get("url", ""),
            "source": "arbeitnow_free",
            "external_id": f"arbeitnow_{raw.get('slug', '')}",
            "salary_range": "",
            "category": ", ".join(raw.get("tags", [])),
            "created": raw.get("created_at", ""),
            "contract_type": "",
            "contract_time": "",
        }
