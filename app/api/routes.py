import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApplicationStatus, get_db
from app.services.profile_service import ProfileService
from app.services.job_service import JobService
from app.services.tracking_service import TrackingService

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


@router.get("/api/health")
async def health_check():
    return {"status": "ok"}
