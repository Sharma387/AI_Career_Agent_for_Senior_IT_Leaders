"""Pydantic data models for Seek.co.nz job scraping.

Defines request/response models for the Seek automation pipeline including
search parameters, job cards, job details, scrape results, and role presets.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class BrowserProfileLocked(Exception):
    """Raised when the Chrome profile is already in use by another process."""

    pass


class SeekSearchParams(BaseModel):
    """Parameters for a Seek.co.nz job search.

    Used to construct search URLs and control pagination/filtering behaviour
    for the Playwright-based Seek scraper.
    """

    keywords: str = Field(
        ..., min_length=1, description="Search keywords e.g. 'project manager'"
    )
    location: str = Field(default="New Zealand", description="Location filter")
    classification: Optional[str] = Field(
        default=None, description="Seek classification ID"
    )
    salary_min: Optional[int] = Field(
        default=None, description="Minimum salary filter"
    )
    salary_max: Optional[int] = Field(
        default=None, description="Maximum salary filter"
    )
    work_type: Optional[str] = Field(
        default=None, description="full-time, part-time, contract"
    )
    date_range: Optional[int] = Field(
        default=None, description="Days since posted (1, 3, 7, 14, 30)"
    )
    max_pages: int = Field(
        default=3, ge=1, le=10, description="Maximum search result pages to scrape"
    )
    page: int = Field(default=1, ge=1, description="Starting page number")

    @model_validator(mode="after")
    def validate_salary_range(self) -> "SeekSearchParams":
        """Ensure salary_min is less than salary_max when both are provided."""
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min >= self.salary_max:
                raise ValueError("salary_min must be less than salary_max")
        return self

    @model_validator(mode="after")
    def validate_date_range(self) -> "SeekSearchParams":
        """Ensure date_range is one of the allowed Seek filter values."""
        allowed_values = {1, 3, 7, 14, 30}
        if self.date_range is not None and self.date_range not in allowed_values:
            raise ValueError(
                f"date_range must be one of {sorted(allowed_values)}, got {self.date_range}"
            )
        return self


class SeekJobCard(BaseModel):
    """Job card data extracted from Seek search results.

    Represents the summary information visible on a search results page
    before navigating to the full job detail.
    """

    title: str
    company: str
    location: str
    salary_range: Optional[str] = None
    url: str
    posted_date: Optional[str] = None
    classification: Optional[str] = None
    work_type: Optional[str] = None
    is_featured: bool = False


class SeekJobDetail(BaseModel):
    """Full job details from a Seek job detail page.

    Contains the complete job description and metadata extracted
    after navigating to an individual job posting page.
    """

    title: str
    company: str
    location: str
    description: str
    salary_range: Optional[str] = None
    url: str
    posted_date: Optional[str] = None
    classification: Optional[str] = None
    sub_classification: Optional[str] = None
    work_type: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    external_id: str = Field(
        ..., description="Seek external ID in format seek_{job_id}"
    )


class SeekScrapeResult(BaseModel):
    """Result of a Seek scraping operation.

    Maintains the counting invariant: scraped == new_jobs + duplicates + errors.
    """

    source: str = "seek_nz"
    scraped: int = 0
    new_jobs: int = 0
    duplicates: int = 0
    errors: int = 0
    job_ids: list[int] = Field(default_factory=list)
    pages_scraped: int = 0
    search_params: SeekSearchParams


class RolePreset(BaseModel):
    """Configuration for a scheduled role search preset.

    Each preset defines a search template for a specific senior role type
    used by the daily scheduled Seek scraper.
    """

    id: str = Field(..., min_length=1, description="Unique preset identifier e.g. 'project-manager'")
    label: str = Field(..., min_length=1, description="Display label e.g. 'Project Manager'")
    keywords: str = Field(..., min_length=1, description="Search keywords e.g. 'project manager'")
    location: str = Field(default="New Zealand", description="Location filter")
    classification: Optional[str] = Field(
        default=None, description="Seek classification ID"
    )
    enabled: bool = Field(default=True, description="Whether this preset is active")
    salary_min: Optional[int] = Field(
        default=None, description="Minimum salary filter"
    )
