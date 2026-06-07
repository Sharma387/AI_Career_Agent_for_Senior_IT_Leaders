"""Seek.co.nz HTML page parser for extracting structured job data.

Parses search result pages and individual job detail pages from seek.co.nz
into structured Pydantic models. Uses BeautifulSoup with multiple fallback
selectors for resilience against Seek DOM changes.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from app.ingestion.seek_models import SeekJobCard, SeekJobDetail, SeekSearchParams

# Base URL for Seek.co.nz job search
SEEK_BASE_URL = "https://www.seek.co.nz/jobs"

# Regex to extract numeric job ID from Seek URLs
SEEK_JOB_ID_PATTERN = re.compile(r"/job/(\d+)")


def _strip_html_and_normalize(text: str) -> str:
    """Strip HTML tags and normalize whitespace in a string.

    Removes all HTML tags, collapses multiple whitespace characters into
    single spaces, and strips leading/trailing whitespace.

    Args:
        text: Raw text potentially containing HTML tags.

    Returns:
        Cleaned text with no HTML and normalized whitespace.
    """
    # Parse as HTML and extract text content
    soup = BeautifulSoup(text, "html.parser")
    plain_text = soup.get_text(separator=" ")
    # Collapse multiple whitespace (spaces, newlines, tabs) into single space
    normalized = re.sub(r"\s+", " ", plain_text).strip()
    return normalized


def _extract_external_id(url: str) -> str:
    """Extract Seek external ID from a job URL.

    Matches the pattern /job/{numeric_id} and formats as seek_{numeric_id}.

    Args:
        url: Seek job URL (e.g. https://www.seek.co.nz/job/12345678).

    Returns:
        External ID string in format "seek_{numeric_id}", or "seek_unknown"
        if the ID cannot be extracted.
    """
    match = SEEK_JOB_ID_PATTERN.search(url)
    if match:
        return f"seek_{match.group(1)}"
    return "seek_unknown"


def _safe_text(element: Optional[Tag]) -> str:
    """Safely extract text from a BeautifulSoup element.

    Args:
        element: A BeautifulSoup Tag or None.

    Returns:
        Stripped text content, or empty string if element is None.
    """
    if element is None:
        return ""
    return element.get_text(strip=True)


class SeekPageParser:
    """Parses seek.co.nz HTML pages into structured job data.

    Provides methods to build search URLs, parse search result pages for
    job cards, and parse individual job detail pages for full descriptions.
    Uses multiple fallback CSS selectors to handle Seek DOM variations.
    """

    def build_search_url(self, params: SeekSearchParams, page: int = 1) -> str:
        """Construct a seek.co.nz search URL from parameters.

        Uses the query parameter format:
        https://www.seek.co.nz/jobs?keywords={keywords}&where={location}&page={page}

        Additional optional parameters are appended when provided.

        Args:
            params: Search parameters including keywords, location, and filters.
            page: The page number to request (1-indexed).

        Returns:
            Fully-formed Seek search URL string.
        """
        query_params: dict[str, str] = {
            "keywords": params.keywords,
            "where": params.location,
            "page": str(page),
        }

        if params.classification:
            query_params["classification"] = params.classification

        if params.salary_min is not None and params.salary_max is not None:
            query_params["salaryrange"] = f"{params.salary_min}-{params.salary_max}"
            query_params["salarytype"] = "annual"
        elif params.salary_min is not None:
            query_params["salaryrange"] = f"{params.salary_min}-"
            query_params["salarytype"] = "annual"
        elif params.salary_max is not None:
            query_params["salaryrange"] = f"0-{params.salary_max}"
            query_params["salarytype"] = "annual"

        if params.work_type:
            query_params["worktype"] = params.work_type

        if params.date_range is not None:
            query_params["daterange"] = str(params.date_range)

        return f"{SEEK_BASE_URL}?{urlencode(query_params)}"

    def parse_search_results(self, page_html: str) -> list[SeekJobCard]:
        """Extract job cards from a Seek search results page.

        Tries multiple CSS selectors to find job card elements, then extracts
        title, company, location, salary, URL, and posted date from each.

        Args:
            page_html: Raw HTML string of a Seek search results page.

        Returns:
            List of SeekJobCard objects extracted from the page. Returns empty
            list if no job cards can be found.
        """
        soup = BeautifulSoup(page_html, "html.parser")
        cards: list[SeekJobCard] = []

        # Try multiple selectors for job card containers (Seek may change DOM)
        job_elements = soup.select('[data-testid="job-card"]')
        if not job_elements:
            job_elements = soup.select("article[data-card-type='JobCard']")
        if not job_elements:
            job_elements = soup.select("article")
        if not job_elements:
            job_elements = soup.select('[data-automation="normalJob"]')

        for element in job_elements:
            card = self._parse_single_card(element)
            if card is not None:
                cards.append(card)

        return cards

    def _parse_single_card(self, element: Tag) -> Optional[SeekJobCard]:
        """Parse a single job card element into a SeekJobCard.

        Uses multiple fallback selectors for each field to handle DOM variations.

        Args:
            element: BeautifulSoup Tag representing a single job card.

        Returns:
            SeekJobCard if at least title and URL could be extracted, else None.
        """
        # Extract title - try multiple selectors
        title_el = element.select_one('[data-automation="jobTitle"]')
        if not title_el:
            title_el = element.select_one('a[data-automation="jobTitle"]')
        if not title_el:
            title_el = element.select_one("h3 a")
        if not title_el:
            title_el = element.select_one("a[href*='/job/']")

        title = _safe_text(title_el)

        # Extract URL from the title link
        url = ""
        if title_el and title_el.name == "a":
            url = title_el.get("href", "")
        elif title_el:
            # Title element might be inside an anchor
            link_el = title_el.find_parent("a") or title_el.find("a")
            if link_el:
                url = link_el.get("href", "")

        # Ensure URL is absolute
        if url and not url.startswith("http"):
            url = f"https://www.seek.co.nz{url}"

        # Must have at least title and URL to be a valid card
        if not title or not url:
            return None

        # Extract company
        company_el = element.select_one('[data-automation="jobCompany"]')
        if not company_el:
            company_el = element.select_one('[aria-label="company"]')
        if not company_el:
            company_el = element.select_one("span.company")
        company = _safe_text(company_el)

        # Extract location
        location_el = element.select_one('[data-automation="jobLocation"]')
        if not location_el:
            location_el = element.select_one('[aria-label="location"]')
        if not location_el:
            location_el = element.select_one("span.location")
        location = _safe_text(location_el)

        # Extract salary (optional)
        salary_el = element.select_one('[data-automation="jobSalary"]')
        if not salary_el:
            salary_el = element.select_one('[aria-label="salary"]')
        if not salary_el:
            salary_el = element.select_one("span.salary")
        salary_range = _safe_text(salary_el) or None

        # Extract posted date (optional)
        date_el = element.select_one('[data-automation="jobListingDate"]')
        if not date_el:
            date_el = element.select_one("time")
        if not date_el:
            date_el = element.select_one("span.listing-date")
        posted_date = _safe_text(date_el) or None

        # Extract work type (optional)
        work_type_el = element.select_one('[data-automation="jobWorkType"]')
        if not work_type_el:
            work_type_el = element.select_one('[aria-label="work type"]')
        work_type = _safe_text(work_type_el) or None

        # Extract classification (optional)
        classification_el = element.select_one('[data-automation="jobClassification"]')
        if not classification_el:
            classification_el = element.select_one('[aria-label="classification"]')
        classification = _safe_text(classification_el) or None

        # Check if featured
        is_featured = bool(
            element.select_one('[data-automation="premiumJob"]')
            or element.select_one(".featured")
            or element.get("data-featured") == "true"
        )

        return SeekJobCard(
            title=title,
            company=company,
            location=location,
            salary_range=salary_range,
            url=url,
            posted_date=posted_date,
            classification=classification,
            work_type=work_type,
            is_featured=is_featured,
        )

    def parse_job_detail(self, page_html: str, job_url: str) -> SeekJobDetail:
        """Extract full job details from a Seek job detail page.

        Parses the full job description, metadata, and derives the external ID
        from the URL. HTML tags are stripped and whitespace normalized in the
        description.

        Args:
            page_html: Raw HTML string of a Seek job detail page.
            job_url: The URL of the job detail page (used for external_id extraction).

        Returns:
            SeekJobDetail with all extractable fields populated. Fields that
            cannot be extracted default to empty strings.
        """
        soup = BeautifulSoup(page_html, "html.parser")

        # Extract title
        title = self._extract_detail_title(soup)

        # Extract company
        company = self._extract_detail_company(soup)

        # Extract location
        location = self._extract_detail_location(soup)

        # Extract description (main content)
        description = self._extract_detail_description(soup)

        # Extract salary
        salary_range = self._extract_detail_salary(soup)

        # Extract posted date
        posted_date = self._extract_detail_posted_date(soup)

        # Extract classification
        classification = self._extract_detail_field(
            soup,
            [
                '[data-automation="job-detail-classification"]',
                '[data-automation="jobClassification"]',
                "span.classification",
            ],
        )

        # Extract sub-classification
        sub_classification = self._extract_detail_field(
            soup,
            [
                '[data-automation="job-detail-subclassification"]',
                '[data-automation="jobSubClassification"]',
            ],
        )

        # Extract work type
        work_type = self._extract_detail_field(
            soup,
            [
                '[data-automation="job-detail-work-type"]',
                '[data-automation="jobWorkType"]',
                "span.work-type",
            ],
        )

        # Extract external ID from URL
        external_id = _extract_external_id(job_url)

        return SeekJobDetail(
            title=title,
            company=company,
            location=location,
            description=description,
            salary_range=salary_range or None,
            url=job_url,
            posted_date=posted_date or None,
            classification=classification or None,
            sub_classification=sub_classification or None,
            work_type=work_type or None,
            requirements=None,
            benefits=None,
            external_id=external_id,
        )

    def _extract_detail_title(self, soup: BeautifulSoup) -> str:
        """Extract job title from detail page with fallbacks."""
        selectors = [
            '[data-automation="job-detail-title"]',
            '[data-automation="jobTitle"]',
            "h1[data-automation]",
            "h1",
        ]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = _safe_text(el)
                if text:
                    return text
        return ""

    def _extract_detail_company(self, soup: BeautifulSoup) -> str:
        """Extract company name from detail page with fallbacks."""
        selectors = [
            '[data-automation="advertiser-name"]',
            '[data-automation="jobCompany"]',
            '[data-automation="job-detail-company"]',
            "span.company-name",
            '[aria-label="company"]',
        ]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = _safe_text(el)
                if text:
                    return text
        return ""

    def _extract_detail_location(self, soup: BeautifulSoup) -> str:
        """Extract location from detail page with fallbacks."""
        selectors = [
            '[data-automation="job-detail-location"]',
            '[data-automation="jobLocation"]',
            "span.location",
            '[aria-label="location"]',
        ]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = _safe_text(el)
                if text:
                    return text
        return ""

    def _extract_detail_description(self, soup: BeautifulSoup) -> str:
        """Extract and clean job description from detail page.

        Strips HTML tags and normalizes whitespace.
        """
        selectors = [
            '[data-automation="jobDescription"]',
            '[data-automation="job-detail-description"]',
            '[data-automation="jobAdDetails"]',
            "div.job-description",
            "#job-details",
            "div[class*='description']",
        ]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                raw_html = str(el)
                cleaned = _strip_html_and_normalize(raw_html)
                if cleaned:
                    return cleaned
        return ""

    def _extract_detail_salary(self, soup: BeautifulSoup) -> str:
        """Extract salary from detail page with fallbacks."""
        selectors = [
            '[data-automation="job-detail-salary"]',
            '[data-automation="jobSalary"]',
            "span.salary",
            '[aria-label="salary"]',
        ]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = _safe_text(el)
                if text:
                    return text
        return ""

    def _extract_detail_posted_date(self, soup: BeautifulSoup) -> str:
        """Extract posted date from detail page with fallbacks."""
        selectors = [
            '[data-automation="job-detail-date"]',
            '[data-automation="jobListingDate"]',
            "time",
            "span.listing-date",
        ]
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = _safe_text(el)
                if text:
                    return text
        return ""

    def _extract_detail_field(
        self, soup: BeautifulSoup, selectors: list[str]
    ) -> str:
        """Generic field extraction with a list of fallback selectors.

        Args:
            soup: Parsed HTML document.
            selectors: List of CSS selectors to try in order.

        Returns:
            Text content from the first matching selector, or empty string.
        """
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = _safe_text(el)
                if text:
                    return text
        return ""
