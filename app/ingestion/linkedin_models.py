"""
LinkedIn job ingestion Pydantic models for the browser extension API.

These models validate job data received from the LinkedIn browser extension
and structure the API response sent back to the extension.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LinkedInJobIngestRequest(BaseModel):
    """Request body for LinkedIn job ingestion from browser extension.

    Validates incoming job data captured by the LinkedIn browser extension,
    ensuring URL matches the LinkedIn jobs pattern, description meets minimum
    length, and required fields are present.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Job title extracted from the LinkedIn posting",
    )
    company: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Company name from the LinkedIn posting",
    )
    location: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Job location (city, region, or remote)",
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Full job description text (minimum 10 characters)",
    )
    url: str = Field(
        ...,
        pattern=r"^https://(www\.)?linkedin\.com/jobs/",
        description="LinkedIn job URL (must match LinkedIn jobs URL pattern)",
    )
    salary_range: Optional[str] = Field(
        default=None,
        description="Salary range if listed on the posting",
    )
    seniority_level: Optional[str] = Field(
        default=None,
        description="Seniority level (e.g., Director, Executive)",
    )
    employment_type: Optional[str] = Field(
        default=None,
        description="Employment type (e.g., Full-time, Contract)",
    )
    posted_date: Optional[str] = Field(
        default=None,
        description="Date the job was posted on LinkedIn",
    )

    @field_validator("title", "company")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        """Ensure title and company are not just whitespace."""
        if not v.strip():
            raise ValueError("must not be blank or whitespace-only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_min_content(cls, v: str) -> str:
        """Ensure description has meaningful content (>= 10 chars after strip)."""
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("description must be at least 10 characters")
        return stripped


class LinkedInJobIngestResponse(BaseModel):
    """Response from LinkedIn job ingestion endpoint.

    Communicates the outcome of the ingestion attempt back to the
    browser extension: created (new job stored), duplicate (already exists),
    or error (processing failure).
    """

    status: str = Field(
        ...,
        description='Ingestion result status: "created", "duplicate", or "error"',
    )
    job_id: Optional[int] = Field(
        default=None,
        description="ID of the newly created job (only set when status is 'created')",
    )
    message: str = Field(
        ...,
        description="Human-readable message describing the result",
    )
