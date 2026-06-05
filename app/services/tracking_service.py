from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Application, ApplicationStatus, JobPosting, CareerProfile, Project, Skill
from app.rag.application_rag import ApplicationRAG
from app.rag.career_rag import CareerRAG
from app.agents.insight_agent import InsightAgent


class TrackingService:
    def __init__(self):
        self._application_rag = None
        self._career_rag = None
        self._insight_agent = None

    @property
    def application_rag(self):
        if self._application_rag is None:
            self._application_rag = ApplicationRAG()
        return self._application_rag

    @property
    def career_rag(self):
        if self._career_rag is None:
            self._career_rag = CareerRAG()
        return self._career_rag

    @property
    def insight_agent(self):
        if self._insight_agent is None:
            self._insight_agent = InsightAgent()
        return self._insight_agent

    async def track_application(self, job_id: int, profile_id: int, status: str, db_session: AsyncSession) -> dict:
        job_result = await db_session.execute(
            select(JobPosting).where(JobPosting.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if not job:
            return {}

        profile_result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return {}

        application = Application(
            job_id=job_id,
            profile_id=profile_id,
            status=status,
        )
        db_session.add(application)
        await db_session.flush()

        app_data = {
            "job_title": job.title,
            "company": job.company,
            "status": status,
            "date_applied": application.date_applied.isoformat() if application.date_applied else "",
            "rejection_stage": "",
            "feedback": "",
        }
        self.application_rag.ingest_application(app_data)

        return {
            "application_id": application.id,
            "job_id": job_id,
            "profile_id": profile_id,
            "status": status,
            "date_applied": application.date_applied.isoformat() if application.date_applied else None,
        }

    async def update_application_status(
        self, application_id: int, new_status: str, feedback: str = None, db_session: AsyncSession = None
    ) -> dict:
        result = await db_session.execute(
            select(Application).where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            return {}

        application.status = new_status
        application.last_updated = datetime.utcnow()
        if feedback:
            application.feedback_notes = feedback
        if new_status == ApplicationStatus.rejected:
            application.rejection_stage = new_status
        await db_session.flush()

        job_result = await db_session.execute(
            select(JobPosting).where(JobPosting.id == application.job_id)
        )
        job = job_result.scalar_one_or_none()

        app_data = {
            "job_title": job.title if job else "",
            "company": job.company if job else "",
            "status": new_status,
            "date_applied": application.date_applied.isoformat() if application.date_applied else "",
            "rejection_stage": application.rejection_stage or "",
            "feedback": feedback or "",
        }
        self.application_rag.ingest_application(app_data)

        return {
            "application_id": application.id,
            "status": new_status,
            "last_updated": application.last_updated.isoformat(),
        }

    async def get_application_stats(self, profile_id: int, db_session: AsyncSession) -> dict:
        result = await db_session.execute(
            select(Application).where(Application.profile_id == profile_id)
        )
        applications = result.scalars().all()

        total_applied = len(applications)
        interview_count = sum(
            1 for a in applications
            if a.status in {
                ApplicationStatus.phone_screen,
                ApplicationStatus.technical_interview,
                ApplicationStatus.final_interview,
            }
        )
        rejection_count = sum(1 for a in applications if a.status == ApplicationStatus.rejected)
        offer_count = sum(
            1 for a in applications
            if a.status in {ApplicationStatus.offered, ApplicationStatus.accepted}
        )

        success_rate = (offer_count / total_applied * 100) if total_applied > 0 else 0.0
        interview_rate = (interview_count / total_applied * 100) if total_applied > 0 else 0.0

        return {
            "total_applied": total_applied,
            "interview_count": interview_count,
            "rejection_count": rejection_count,
            "offer_count": offer_count,
            "success_rate": round(success_rate, 2),
            "interview_rate": round(interview_rate, 2),
        }

    async def get_all_applications(self, profile_id: int, db_session: AsyncSession) -> list:
        result = await db_session.execute(
            select(Application).where(Application.profile_id == profile_id).order_by(Application.date_applied.desc())
        )
        applications = result.scalars().all()

        output = []
        for app in applications:
            job_result = await db_session.execute(
                select(JobPosting).where(JobPosting.id == app.job_id)
            )
            job = job_result.scalar_one_or_none()

            output.append({
                "application_id": app.id,
                "status": app.status,
                "date_applied": app.date_applied.isoformat() if app.date_applied else None,
                "last_updated": app.last_updated.isoformat() if app.last_updated else None,
                "feedback_notes": app.feedback_notes,
                "has_materials": bool(app.resume_version_text or app.cover_letter_text),
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                } if job else None,
            })

        return output

    async def get_insights(self, profile_id: int, db_session: AsyncSession) -> dict:
        application_chunks = self.application_rag.get_analytics_chunks()

        profile_result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        career_chunks = self.career_rag.get_all_chunks() if profile else []

        insights = self.insight_agent.analyze_patterns(application_chunks, career_chunks)

        return insights
