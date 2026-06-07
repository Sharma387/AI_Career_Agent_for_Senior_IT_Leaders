import os
import tempfile
import logging
import time
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, ApplicationStatus, CareerProfile, JobPosting, Project, Skill, Certification, MatchResult, SkillArticulation, get_db
from app.db.models import User
from app.api.auth import get_current_user, require_user
from app.services.profile_service import ProfileService
from app.services.job_service import JobService
from app.services.tracking_service import TrackingService
from app.services.document_service import (
    render_resume_html,
    render_cover_letter_html,
    generate_resume_docx,
    generate_cover_letter_docx,
)
from app.core.config import settings
from app.ingestion.seek_models import SeekSearchParams
from app.ingestion.linkedin_models import LinkedInJobIngestRequest, LinkedInJobIngestResponse
from app.ingestion.deduplication import is_duplicate

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiting for LinkedIn ingest endpoint: max 10 requests per minute per user
_linkedin_ingest_rate: dict[int, list[float]] = defaultdict(list)

profile_service = ProfileService()
job_service = JobService()
tracking_service = TrackingService()


class AddJobRequest(BaseModel):
    text: str
    source: str = "manual"


class AddProjectRequest(BaseModel):
    title: str
    description: str = ""
    role: str = ""
    technologies: list[str] | str = ""
    impact: str = ""
    star_situation: str = ""
    star_task: str = ""
    star_action: str = ""
    star_result: str = ""


class TrackApplicationRequest(BaseModel):
    job_id: int
    profile_id: int
    status: str = "applied"


class UpdateStatusRequest(BaseModel):
    new_status: str
    feedback: str | None = None


class UpdateResumeRequest(BaseModel):
    resume_text: str
    cover_letter_text: str | None = None


@router.post("/api/profile/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    allowed = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="File must be PDF, DOCX, or TXT")

    suffix = ""
    if file.content_type == "application/pdf":
        suffix = ".pdf"
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        suffix = ".docx"
    else:
        suffix = ".txt"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await profile_service.upload_resume(tmp_path, db_session, user_id=user.id if user else None)
        return result
    finally:
        os.unlink(tmp_path)


@router.get("/api/profile/me")
async def get_my_profile(
    user: User = Depends(require_user),
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {"profile": None, "projects": [], "skills": []}
    return await profile_service.get_profile(profile.id, db_session)


@router.get("/api/profile/{profile_id}")
async def get_profile(profile_id: int, db_session: AsyncSession = Depends(get_db)):
    result = await profile_service.get_profile(profile_id, db_session)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/api/profile/{profile_id}/resume/html")
async def download_base_resume_html(
    profile_id: int,
    download: bool = Query(default=False, description="Force download instead of inline display"),
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    html = profile.formatted_resume_html or ""
    if not html:
        from app.services.document_service import render_resume_html
        profile_data = await _get_profile_structured(profile_id, db_session)
        html = render_resume_html(profile_data)

    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename=resume_{profile_id}.html"
    return StreamingResponse(
        BytesIO(html.encode()),
        media_type="text/html",
        headers=headers,
    )


@router.get("/api/profile/{profile_id}/resume/docx")
async def download_base_resume_docx(
    profile_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = await _get_profile_structured(profile_id, db_session)
    docx_bytes = generate_resume_docx(profile_data)
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=resume_{profile_id}.docx"},
    )


@router.post("/api/profile/{profile_id}/project")
async def add_project(
    profile_id: int,
    request: AddProjectRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await profile_service.add_project(profile_id, request.model_dump(), db_session)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.post("/api/jobs/add")
async def add_job(
    request: AddJobRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await job_service.add_job(request.text, source=request.source, db_session=db_session)
    return result


@router.post("/api/jobs/ingest/linkedin")
async def ingest_linkedin_job(
    request: LinkedInJobIngestRequest,
    db_session: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """
    Receive and store a LinkedIn job captured by the browser extension.

    Validates the incoming job data, checks for duplicates, and stores
    new jobs through the existing JobService pipeline with source="linkedin_ext".

    Rate limited to 10 requests per minute per user.
    """
    # Rate limiting: max 10 requests per minute per user
    now = time.time()
    user_timestamps = _linkedin_ingest_rate[user.id]
    # Remove timestamps older than 60 seconds
    _linkedin_ingest_rate[user.id] = [
        ts for ts in user_timestamps if now - ts < 60
    ]
    if len(_linkedin_ingest_rate[user.id]) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: maximum 10 requests per minute",
        )
    _linkedin_ingest_rate[user.id].append(now)

    # Deduplication check (URL match, then title+company)
    duplicate = await is_duplicate(
        url=request.url,
        title=request.title,
        company=request.company,
        db_session=db_session,
    )
    if duplicate:
        return JSONResponse(
            status_code=200,
            content=LinkedInJobIngestResponse(
                status="duplicate",
                message=f"Job '{request.title}' at '{request.company}' already exists",
            ).model_dump(),
        )

    # Build job text from LinkedIn data for the pipeline
    parts = [
        f"Title: {request.title}",
        f"Company: {request.company}",
    ]
    if request.location:
        parts.append(f"Location: {request.location}")
    if request.salary_range:
        parts.append(f"Salary: {request.salary_range}")
    if request.seniority_level:
        parts.append(f"Seniority Level: {request.seniority_level}")
    if request.employment_type:
        parts.append(f"Employment Type: {request.employment_type}")
    parts.append(f"\nDescription:\n{request.description}")

    job_text = "\n".join(parts)

    # Store via existing pipeline
    result = await job_service.add_job(
        job_text, source="linkedin_ext", db_session=db_session
    )

    if result and "job_id" in result:
        # Update the job record with URL and salary (similar to Adzuna adapter)
        job_result = await db_session.execute(
            select(JobPosting).where(JobPosting.id == result["job_id"])
        )
        job_record = job_result.scalar_one_or_none()
        if job_record:
            job_record.url = request.url
            if request.salary_range:
                job_record.salary_range = request.salary_range

        return JSONResponse(
            status_code=201,
            content=LinkedInJobIngestResponse(
                status="created",
                job_id=result["job_id"],
                message=f"Job '{request.title}' at '{request.company}' stored successfully",
            ).model_dump(),
        )

    # Fallback error case
    raise HTTPException(
        status_code=500,
        detail="Failed to store job through pipeline",
    )


@router.get("/api/jobs")
async def list_jobs(db_session: AsyncSession = Depends(get_db)):
    return await job_service.get_all_jobs(db_session)


@router.post("/api/jobs/scrape")
async def scrape_jobs(
    source: str,
    keywords: str = "",
    location: str = "",
    page: int = 1,
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Scrape jobs from a specific source.
    Requires authentication.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    search_params = {
        "keywords": keywords,
        "location": location,
        "page": page
    }

    try:
        result = await job_service.scrape_and_store_jobs(
            source=source,
            search_params=search_params,
            db_session=db_session
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error scraping jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/jobs/scrape-multiple")
async def scrape_multiple_jobs(
    sources: List[str],
    keywords: str = "",
    location: str = "",
    page: int = 1,
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Scrape jobs from multiple sources.
    Requires authentication.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    search_params = {
        "keywords": keywords,
        "location": location,
        "page": page
    }

    try:
        result = await job_service.scrape_multiple_sources(
            sources=sources,
            search_params=search_params,
            db_session=db_session
        )
        return result
    except Exception as e:
        logger.error(f"Error scraping multiple job sources: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/jobs/{job_id}/match")
async def match_job(
    job_id: int,
    profile_id: int = Query(...),
    db_session: AsyncSession = Depends(get_db),
):
    result = await job_service.match_job(job_id, profile_id, db_session)
    if not result:
        raise HTTPException(status_code=404, detail="Job or profile not found")
    return result


@router.post("/api/jobs/{job_id}/match-enhanced")
async def match_job_enhanced(
    job_id: int,
    profile_id: int = Query(...),
    db_session: AsyncSession = Depends(get_db),
):
    result = await job_service.match_job_enhanced(job_id, profile_id, db_session)
    if not result:
        raise HTTPException(status_code=404, detail="Job or profile not found")
    return result


@router.post("/api/jobs/{job_id}/generate-materials")
async def generate_materials(
    job_id: int,
    profile_id: int = Query(...),
    db_session: AsyncSession = Depends(get_db),
):
    result = await job_service.generate_application_materials(job_id, profile_id, db_session)
    if not result:
        raise HTTPException(status_code=404, detail="Job or profile not found")
    return result


@router.post("/api/applications/track")
async def track_application(
    request: TrackApplicationRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await tracking_service.track_application(
        request.job_id, request.profile_id, request.status, db_session
    )
    if not result:
        raise HTTPException(status_code=404, detail="Job or profile not found")
    return result


@router.put("/api/applications/{application_id}/status")
async def update_application_status(
    application_id: int,
    request: UpdateStatusRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await tracking_service.update_application_status(
        application_id, request.new_status, feedback=request.feedback, db_session=db_session
    )
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.get("/api/applications/stats/{profile_id}")
async def get_application_stats(
    profile_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    return await tracking_service.get_application_stats(profile_id, db_session)


@router.get("/api/applications/{profile_id}")
async def list_applications(
    profile_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    return await tracking_service.get_all_applications(profile_id, db_session)


@router.get("/api/applications/{profile_id}/insights")
async def get_insights(
    profile_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    return await tracking_service.get_insights(profile_id, db_session)


@router.get("/api/applications/{application_id}/materials")
async def get_application_materials(
    application_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db_session.execute(
        select(Application.job.property.mapper.class_).where(
            Application.job.property.mapper.class_.id == application.job_id
        )
    )
    from app.db.models import JobPosting
    job_result = await db_session.execute(
        select(JobPosting).where(JobPosting.id == application.job_id)
    )
    job = job_result.scalar_one_or_none()

    return {
        "application_id": application.id,
        "resume_version_text": application.resume_version_text or "",
        "cover_letter_text": application.cover_letter_text or "",
        "job_title": job.title if job else "",
        "company": job.company if job else "",
    }


@router.put("/api/applications/{application_id}/materials")
async def update_application_materials(
    application_id: int,
    request: UpdateResumeRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.resume_version_text = request.resume_text
    if request.cover_letter_text is not None:
        application.cover_letter_text = request.cover_letter_text
    await db_session.flush()

    return {
        "application_id": application.id,
        "resume_version_text": application.resume_version_text,
        "cover_letter_text": application.cover_letter_text or "",
    }


async def _get_profile_structured(profile_id: int, db_session: AsyncSession) -> dict:
    profile_result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        return {}

    projects_result = await db_session.execute(
        select(Project).where(Project.profile_id == profile_id)
    )
    projects = projects_result.scalars().all()

    skills_result = await db_session.execute(
        select(Skill).where(Skill.profile_id == profile_id)
    )
    skills = skills_result.scalars().all()

    certs_result = await db_session.execute(
        select(Certification).where(Certification.profile_id == profile_id)
    )
    certs = certs_result.scalars().all()

    skills_dict = {}
    for s in skills:
        cat = s.category or "General"
        if cat not in skills_dict:
            skills_dict[cat] = []
        skills_dict[cat].append(s.name)

    return {
        "full_name": profile.full_name,
        "email": profile.email or "",
        "summary": profile.summary or "",
        "resume_text": profile.raw_resume_text or "",
        "projects": [
            {
                "title": p.title,
                "description": p.description or "",
                "role": p.role or "",
                "technologies": p.technologies or "",
                "impact": p.impact or "",
            }
            for p in projects
        ],
        "skills": skills_dict,
        "certifications": [{"name": c.name, "issuer": c.issuer or ""} for c in certs],
    }


@router.get("/api/applications/{application_id}/resume/html")
async def download_resume_html(
    application_id: int,
    download: bool = Query(default=False, description="Force download instead of inline display"),
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db_session.execute(
        select(JobPosting).where(JobPosting.id == application.job_id)
    )
    job = job_result.scalar_one_or_none()

    profile_data = await _get_profile_structured(application.profile_id, db_session)
    job_data = {"title": job.title, "company": job.company} if job else {}

    resume_text = application.resume_version_text or profile_data.get("resume_text", "")
    profile_data["resume_text"] = resume_text

    html = render_resume_html(profile_data, job_data)
    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename=resume_{application_id}.html"
    return StreamingResponse(
        BytesIO(html.encode()),
        media_type="text/html",
        headers=headers,
    )


@router.get("/api/applications/{application_id}/cover-letter/html")
async def download_cover_letter_html(
    application_id: int,
    download: bool = Query(default=False, description="Force download instead of inline display"),
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db_session.execute(
        select(JobPosting).where(JobPosting.id == application.job_id)
    )
    job = job_result.scalar_one_or_none()

    profile_data = await _get_profile_structured(application.profile_id, db_session)
    job_data = {"title": job.title, "company": job.company} if job else {}

    cover_letter_text = application.cover_letter_text or ""
    html = render_cover_letter_html(profile_data, job_data, cover_letter_text)
    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename=cover_letter_{application_id}.html"
    return StreamingResponse(
        BytesIO(html.encode()),
        media_type="text/html",
        headers=headers,
    )


@router.get("/api/applications/{application_id}/resume/docx")
async def download_resume_docx(
    application_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db_session.execute(
        select(JobPosting).where(JobPosting.id == application.job_id)
    )
    job = job_result.scalar_one_or_none()

    profile_data = await _get_profile_structured(application.profile_id, db_session)
    job_data = {"title": job.title, "company": job.company} if job else {}

    resume_text = application.resume_version_text or profile_data.get("resume_text", "")
    profile_data["resume_text"] = resume_text

    docx_bytes = generate_resume_docx(profile_data, job_data)
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=resume_{application_id}.docx"},
    )


@router.get("/api/applications/{application_id}/cover-letter/docx")
async def download_cover_letter_docx(
    application_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job_result = await db_session.execute(
        select(JobPosting).where(JobPosting.id == application.job_id)
    )
    job = job_result.scalar_one_or_none()

    profile_data = await _get_profile_structured(application.profile_id, db_session)
    job_data = {"title": job.title, "company": job.company} if job else {}

    cover_letter_text = application.cover_letter_text or ""
    docx_bytes = generate_cover_letter_docx(profile_data, job_data, cover_letter_text)
    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=cover_letter_{application_id}.docx"},
    )


class ArticulationRequest(BaseModel):
    gap_text: str
    has_skill: bool
    evidence: str = ""


@router.get("/api/llm/info")
async def get_llm_info():
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.NVIDIA_MODEL if settings.LLM_PROVIDER == "nvidia" else settings.OLLAMA_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


@router.get("/api/jobs/search/usage")
async def get_search_usage():
    """Get API usage statistics for job searching."""
    from app.core.api_usage import get_usage_stats
    return get_usage_stats()


# Scheduler Status Endpoints
@router.get("/api/scheduler/status")
async def get_scheduler_status(
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Get the current status of the job scraping scheduler.
    Requires authentication.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Return scheduler status from the global instance
    from app.core.scheduler.job_scheduler import job_scheduler

    if not job_scheduler.is_running():
        return {
            "isRunning": False,
            "nextIncrementalRun": None,
            "nextFullRun": None,
            "jobs": []
        }

    jobs = job_scheduler.get_jobs()
    next_incremental = None
    next_full = None

    # Find next runs for our specific jobs
    for job in jobs:
        if job.id == "incremental_job_scraping":
            next_incremental = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else None
        elif job.id == "full_job_scraping":
            next_full = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else None

    return {
        "isRunning": job_scheduler.is_running(),
        "nextIncrementalRun": next_incremental,
        "nextFullRun": next_full,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "nextRun": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else None
            }
            for job in jobs
        ]
    }


@router.post("/api/scheduler/trigger-incremental")
async def trigger_scheduler_incremental(
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Manually trigger an incremental scrape via the scheduler.
    Requires authentication.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Trigger the incremental scrape function directly
    from app.core.scheduler.job_scheduler import job_scheduler
    await job_scheduler._scrape_all_incremental()

    return {"message": "Incremental scrape triggered successfully"}


@router.post("/api/scheduler/trigger-full")
async def trigger_scheduler_full(
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Manually trigger a full scrape via the scheduler.
    Requires authentication.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Trigger the full scrape function directly
    from app.core.scheduler.job_scheduler import job_scheduler
    await job_scheduler._scrape_all_full()

    return {"message": "Full scrape triggered successfully"}


# External Scheduler API Endpoints for Job Scraping
# These endpoints are designed to be triggered by external schedulers (cron, cloud schedulers, etc.)

class ScrapeTriggerRequest(BaseModel):
    source: Optional[str] = None  # Specific source to scrape (linkedin, seek, etc.) or None for all
    keywords: str = ""
    location: str = ""
    hours: Optional[int] = None  # For incremental scrape: how many hours back to look
    force: bool = False  # Bypass deduplication checks


@router.post("/api/jobs/scrape/trigger")
async def trigger_job_scrape(
    request: ScrapeTriggerRequest,
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Trigger job scraping manually or via external scheduler.
    Requires authentication for security.

    This endpoint can be called by external schedulers (cron, GitHub Actions,
    AWS EventBridge, Azure Logic Apps, Cloud Scheduler, etc.) to initiate
    job scraping on demand.

    Args:
        request: Scrape configuration including source, keywords, location, etc.
        db_session: Database session
        user: Current authenticated user (required for security)

    Returns:
        Dictionary with scraping results and statistics
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Prepare search parameters
    search_params = {
        "keywords": request.keywords,
        "location": request.location,
        "page": 1
    }

    # Add time filter for incremental scraping if hours specified
    if request.hours is not None and request.hours > 0:
        # Convert hours to seconds for LinkedIn's f_TPR parameter
        seconds = request.hours * 3600
        search_params["time_filter"] = f"r{seconds}"  # Custom time filter in seconds

    try:
        # Determine which sources to scrape
        sources_to_scrape = [request.source] if request.source else None

        if sources_to_scrape:
            # Scrape specific source
            if request.source not in ['seek', 'linkedin', 'adzuna']:
                raise HTTPException(status_code=400, detail=f"Unsupported source: {request.source}")

            result = await job_service.scrape_and_store_jobs(
                source=request.source,
                search_params=search_params,
                db_session=db_session
            )

            # Format response for single source
            response = {
                "trigger_type": "manual" if request.force else "scheduled",
                "source": request.source,
                "search_params": search_params,
                "results": result,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        else:
            # Scrape all sources
            result = await job_service.scrape_multiple_sources(
                sources=None,  # None means all sources
                search_params=search_params,
                db_session=db_session
            )

            # Format response for multiple sources
            response = {
                "trigger_type": "manual" if request.force else "scheduled",
                "sources": ['adzuna'],  # Primary supported source
                "search_params": search_params,
                "results": result,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering job scrape: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/jobs/scrape/incremental")
async def trigger_incremental_scrape(
    hours: int = Query(2, description="Hours back to look for new jobs"),
    source: Optional[str] = Query(None, description="Specific source to scrape (linkedin, seek, etc.)"),
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Trigger incremental job scraping for recently posted jobs.
    Designed to be called every 2 hours during business hours.

    Args:
        hours: How many hours back to look for new jobs (default: 2)
        source: Specific source to scrape or None for all sources
        db_session: Database session
        user: Current authenticated user (required for security)

    Returns:
        Dictionary with scraping results and statistics
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if hours <= 0:
        raise HTTPException(status_code=400, detail="Hours must be positive")

    # Use the trigger endpoint with incremental parameters
    request = ScrapeTriggerRequest(
        source=source,
        hours=hours,
        force=False  # Incremental scrape respects deduplication
    )

    return await trigger_job_scrape(request, db_session, user)


@router.post("/api/jobs/scrape/full")
async def trigger_full_scrape(
    source: Optional[str] = Query(None, description="Specific source to scrape (linkedin, seek, etc.)"),
    db_session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """
    Trigger full job scraping for all jobs.
    Designed to be called once daily for complete refresh.

    Args:
        source: Specific source to scrape or None for all sources
        db_session: Database session
        user: Current authenticated user (required for security)

    Returns:
        Dictionary with scraping results and statistics
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Use the trigger endpoint with no time filter for full scrape
    request = ScrapeTriggerRequest(
        source=source,
        force=True  # Full scrape can bypass deduplication for completeness
    )

    return await trigger_job_scrape(request, db_session, user)


@router.post("/api/jobs/scrape/seek")
async def scrape_seek_jobs(
    params: SeekSearchParams,
    db_session: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """
    Trigger a Seek.co.nz job scrape using Playwright automation.

    Accepts search parameters (keywords, location, optional filters) and
    invokes the SeekScrapingService to browse Seek using the configured
    Chrome profile.

    Requires JWT authentication.

    Returns:
        SeekScrapeResult with counts of new jobs, duplicates, and errors.
    """
    from app.ingestion.seek_models import BrowserProfileLocked

    try:
        from app.ingestion.seek_scraper_service import SeekScrapingService
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Playwright is not installed. Install it with: "
                "pip install playwright && python -m playwright install chromium"
            ),
        )

    try:
        service = SeekScrapingService(
            chrome_profile_path=settings.SEEK_CHROME_PROFILE_PATH,
            headless=settings.SEEK_HEADLESS,
        )
        result = await service.scrape_and_store(params, db_session)
        return result
    except BrowserProfileLocked as e:
        raise HTTPException(
            status_code=409,
            detail=f"Chrome profile is locked by another process. Close other Chrome instances and retry. {e}",
        )
    except Exception as e:
        if "playwright" in str(e).lower() and ("install" in str(e).lower() or "not found" in str(e).lower()):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Playwright browser not available. Install with: "
                    "python -m playwright install chromium"
                ),
            )
        logger.error(f"Error during Seek scrape: {e}")
        raise HTTPException(status_code=500, detail=f"Seek scraping failed: {e}")


@router.get("/api/match/{job_id}/{profile_id}")
async def get_match_result(
    job_id: int,
    profile_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(MatchResult).where(
            MatchResult.job_id == job_id,
            MatchResult.profile_id == profile_id,
        ).order_by(MatchResult.created_at.desc())
    )
    match = result.first()
    if not match:
        return None

    match_record = match[0]

    arts_result = await db_session.execute(
        select(SkillArticulation).where(
            SkillArticulation.match_result_id == match_record.id
        )
    )
    articulations = arts_result.scalars().all()

    return {
        "match_id": match_record.id,
        "match_score": match_record.match_score,
        "strengths": match_record.strengths or [],
        "gaps": match_record.gaps or [],
        "evidence": match_record.evidence or [],
        "explanation": match_record.explanation_text or "",
        "recommendation": match_record.recommendation or "",
        "created_at": match_record.created_at.isoformat() if match_record.created_at else None,
        "articulations": [
            {
                "id": a.id,
                "gap_text": a.gap_text,
                "has_skill": a.has_skill,
                "evidence": a.evidence or "",
            }
            for a in articulations
        ],
    }


@router.post("/api/match/{match_id}/articulations")
async def save_articulations(
    match_id: int,
    articulations: list[ArticulationRequest],
    db_session: AsyncSession = Depends(get_db),
):
    match_result = await db_session.execute(
        select(MatchResult).where(MatchResult.id == match_id)
    )
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")

    existing_result = await db_session.execute(
        select(SkillArticulation).where(SkillArticulation.match_result_id == match_id)
    )
    for existing in existing_result.scalars().all():
        await db_session.delete(existing)

    for art in articulations:
        record = SkillArticulation(
            match_result_id=match_id,
            profile_id=match.profile_id,
            gap_text=art.gap_text,
            has_skill=art.has_skill,
            evidence=art.evidence,
        )
        db_session.add(record)

    await db_session.flush()
    return {"saved": len(articulations)}


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    summary: str | None = None
    interests: list[str] | None = None
    education: list[dict] | None = None


class UpdateSkillsRequest(BaseModel):
    skills: list[dict]


class UpdateProjectRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    role: str | None = None
    technologies: list[str] | str | None = None
    impact: str | None = None
    star_situation: str | None = None
    star_task: str | None = None
    star_action: str | None = None
    star_result: str | None = None


@router.put("/api/profile/{profile_id}")
async def update_profile(
    profile_id: int,
    request: UpdateProfileRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db_session.flush()
    await db_session.refresh(profile)

    projects_result = await db_session.execute(
        select(Project).where(Project.profile_id == profile_id)
    )
    projects = projects_result.scalars().all()
    skills_result = await db_session.execute(
        select(Skill).where(Skill.profile_id == profile_id)
    )
    skills = skills_result.scalars().all()
    certs_result = await db_session.execute(
        select(Certification).where(Certification.profile_id == profile_id)
    )
    certs = certs_result.scalars().all()

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "linkedin_url": profile.linkedin_url,
        "summary": profile.summary,
        "raw_resume_text": profile.raw_resume_text,
        "formatted_resume_html": profile.formatted_resume_html,
        "interests": profile.interests or [],
        "education": profile.education or [],
        "projects": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description or "",
                "role": p.role or "",
                "technologies": p.technologies or "",
                "impact": p.impact or "",
                "star_situation": p.star_situation or "",
                "star_task": p.star_task or "",
                "star_action": p.star_action or "",
                "star_result": p.star_result or "",
            }
            for p in projects
        ],
        "skills": [
            {"id": s.id, "name": s.name, "category": s.category or "", "proficiency": s.proficiency or ""}
            for s in skills
        ],
        "certifications": [
            {"name": c.name, "issuer": c.issuer or "", "date_obtained": str(c.date_obtained) if c.date_obtained else None, "expiry_date": str(c.expiry_date) if c.expiry_date else None}
            for c in certs
        ],
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }


@router.put("/api/profile/{profile_id}/skills")
async def update_skills(
    profile_id: int,
    request: UpdateSkillsRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    existing_skills = await db_session.execute(
        select(Skill).where(Skill.profile_id == profile_id)
    )
    for skill in existing_skills.scalars().all():
        await db_session.delete(skill)

    for skill_data in request.skills:
        skill = Skill(
            profile_id=profile_id,
            name=skill_data.get("name", ""),
            category=skill_data.get("category", ""),
            proficiency=skill_data.get("proficiency"),
        )
        db_session.add(skill)

    await db_session.flush()

    updated_skills = await db_session.execute(
        select(Skill).where(Skill.profile_id == profile_id)
    )
    return [
        {"id": s.id, "name": s.name, "category": s.category or "", "proficiency": s.proficiency or ""}
        for s in updated_skills.scalars().all()
    ]


@router.put("/api/profile/{profile_id}/projects/{project_id}")
async def update_project(
    profile_id: int,
    project_id: int,
    request: UpdateProjectRequest,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db_session.execute(
        select(Project).where(Project.id == project_id, Project.profile_id == profile_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db_session.flush()
    await db_session.refresh(project)

    return {
        "id": project.id,
        "title": project.title,
        "description": project.description or "",
        "role": project.role or "",
        "technologies": project.technologies or "",
        "impact": project.impact or "",
        "star_situation": project.star_situation or "",
        "star_task": project.star_task or "",
        "star_action": project.star_action or "",
        "star_result": project.star_result or "",
    }


@router.delete("/api/profile/{profile_id}/projects/{project_id}")
async def delete_project(
    profile_id: int,
    project_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db_session.execute(
        select(Project).where(Project.id == project_id, Project.profile_id == profile_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db_session.delete(project)
    await db_session.flush()
    return {"deleted": True}


@router.get("/api/jobs/{job_id}/interview-strategy/{profile_id}")
async def get_interview_strategy(
    job_id: int,
    profile_id: int,
    db_session: AsyncSession = Depends(get_db),
):
    from app.services.job_service import JobService
    job_svc = JobService()

    match_result = await job_svc.match_job(job_id, profile_id, db_session)

    result = await db_session.execute(
        select(CareerProfile).where(CareerProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    skills_result = await db_session.execute(
        select(Skill).where(Skill.profile_id == profile_id)
    )
    skills = skills_result.scalars().all()
    skill_names = [s.name for s in skills]

    projects_result = await db_session.execute(
        select(Project).where(Project.profile_id == profile_id)
    )
    projects = projects_result.scalars().all()

    job_result = await db_session.execute(
        select(JobPosting).where(JobPosting.id == job_id)
    )
    job = job_result.scalar_one_or_none()

    strengths = match_result.get("strengths", [])
    gaps = match_result.get("gaps", [])

    key_themes = []
    if profile.summary:
        key_themes.append("Lead with executive summary highlighting leadership journey")
    if skill_names:
        key_themes.append(f"Emphasize expertise in {', '.join(skill_names[:3])}")
    if profile.raw_resume_text:
        key_themes.append("Reference specific quantified achievements from resume")

    potential_questions = [
        "Tell me about your most significant career achievement and its impact.",
        "How do you approach leading technical transformation in large organizations?",
        "Describe a time you managed a cross-functional team through a major initiative.",
        "How do you evaluate and adopt emerging technologies?",
        "What is your leadership philosophy when building high-performance teams?",
        "How do you balance innovation with operational stability?",
    ]

    talking_points = []
    for p in projects[:3]:
        if p.impact:
            talking_points.append(f"{p.title}: {p.impact}")
        elif p.description:
            talking_points.append(f"{p.title}: {p.description[:100]}")
    if profile.summary:
        talking_points.append(profile.summary[:150])

    areas_to_prepare = []
    for g in gaps[:3]:
        areas_to_prepare.append(f"Prepare examples addressing: {g}")
    for s in skill_names[:3]:
        areas_to_prepare.append(f"Deep dive into {s} experience and results")

    return {
        "job_id": job_id,
        "profile_id": profile_id,
        "match_score": match_result.get("match_score", 0),
        "strengths": strengths,
        "gaps": gaps,
        "explanation": match_result.get("explanation", ""),
        "recommendation": match_result.get("recommendation", ""),
        "key_themes": key_themes,
        "potential_questions": potential_questions,
        "talking_points": talking_points,
        "areas_to_prepare": areas_to_prepare,
        "improvement_recommendations": [
            {"area": "Gap", "gap": g, "recommendation": f"Develop concrete examples and evidence for: {g}", "priority": "high", "estimated_impact": "Improves interview responses"}
            for g in gaps
        ],
    }
