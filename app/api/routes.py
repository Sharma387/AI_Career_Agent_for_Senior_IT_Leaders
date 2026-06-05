import os
import tempfile
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, ApplicationStatus, CareerProfile, JobPosting, Project, Skill, Certification, get_db
from app.db.models import User
from app.api.auth import get_current_user
from app.services.profile_service import ProfileService
from app.services.job_service import JobService
from app.services.tracking_service import TrackingService
from app.services.document_service import (
    render_resume_html,
    render_cover_letter_html,
    generate_resume_docx,
    generate_cover_letter_docx,
)

router = APIRouter()

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
        result = await profile_service.upload_resume(tmp_path, db_session)
        return result
    finally:
        os.unlink(tmp_path)


@router.get("/api/profile/{profile_id}")
async def get_profile(profile_id: int, db_session: AsyncSession = Depends(get_db)):
    result = await profile_service.get_profile(profile_id, db_session)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/api/profile/{profile_id}/resume/html")
async def download_base_resume_html(
    profile_id: int,
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

    return StreamingResponse(
        BytesIO(html.encode()),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=resume_{profile_id}.html"},
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


@router.get("/api/jobs")
async def list_jobs(db_session: AsyncSession = Depends(get_db)):
    return await job_service.get_all_jobs(db_session)


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
    return StreamingResponse(
        BytesIO(html.encode()),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=resume_{application_id}.html"},
    )


@router.get("/api/applications/{application_id}/cover-letter/html")
async def download_cover_letter_html(
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
    html = render_cover_letter_html(profile_data, job_data, cover_letter_text)
    return StreamingResponse(
        BytesIO(html.encode()),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=cover_letter_{application_id}.html"},
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
