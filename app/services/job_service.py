from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Application, ApplicationStatus, JobPosting, MatchResult, CareerProfile, Project, Skill
from app.rag.job_rag import JobRAG
from app.rag.career_rag import CareerRAG
from app.ingestion.job_parser import JobParser
from app.agents.job_matcher_agent import JobMatcherAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.insight_agent import InsightAgent


class JobService:
    def __init__(self):
        self._job_rag = None
        self._career_rag = None
        self._parser = None
        self._matcher = None
        self._resume_agent = None
        self._insight_agent = None

    @property
    def job_rag(self):
        if self._job_rag is None:
            self._job_rag = JobRAG()
        return self._job_rag

    @property
    def career_rag(self):
        if self._career_rag is None:
            self._career_rag = CareerRAG()
        return self._career_rag

    @property
    def parser(self):
        if self._parser is None:
            self._parser = JobParser()
        return self._parser

    @property
    def matcher(self):
        if self._matcher is None:
            self._matcher = JobMatcherAgent()
        return self._matcher

    @property
    def resume_agent(self):
        if self._resume_agent is None:
            self._resume_agent = ResumeAgent()
        return self._resume_agent

    @property
    def insight_agent(self):
        if self._insight_agent is None:
            self._insight_agent = InsightAgent()
        return self._insight_agent

    async def add_job(self, job_text: str, source: str = "manual", db_session: AsyncSession = None) -> dict:
        parsed = self.parser.parse_job_description(job_text)

        job = JobPosting(
            title=parsed.get("title", ""),
            company=parsed.get("company", ""),
            description=job_text,
            source=source,
            location=parsed.get("location", ""),
            seniority_level=parsed.get("seniority_level", ""),
            salary_range=parsed.get("salary_range", ""),
            requirements_text="\n".join(parsed.get("requirements", [])),
            extracted_skills=parsed.get("skills_detected", []),
        )
        db_session.add(job)
        await db_session.flush()

        job_rag_data = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "seniority_level": job.seniority_level,
            "description": job.description,
            "requirements": job.requirements_text or "",
            "skills": job.extracted_skills or [],
        }
        self.job_rag.ingest_job(job_rag_data)

        return {
            "job_id": job.id,
            "parsed_data": parsed,
        }

    async def match_job(self, job_id: int, profile_id: int, db_session: AsyncSession) -> dict:
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

        career_chunks = self.career_rag.get_all_chunks()

        job_rag_data = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "seniority_level": job.seniority_level,
            "description": job.description,
            "requirements": job.requirements_text or "",
            "skills": job.extracted_skills or [],
        }
        self.job_rag.ingest_job(job_rag_data)
        job_chunks_result = self.job_rag.query(
            f"{job.title} {job.company} {job.requirements_text or ''}"
        )
        job_chunks = [{"content": doc.page_content, "metadata": meta} for doc, meta in job_chunks_result]

        job_data = {
            "title": job.title,
            "company": job.company,
            "seniority_level": job.seniority_level,
        }

        match_result = self.matcher.match_job(career_chunks, job_chunks, job_data)

        record = MatchResult(
            job_id=job_id,
            profile_id=profile_id,
            match_score=match_result.get("match_score", 0),
            strengths=match_result.get("strengths", []),
            gaps=match_result.get("gaps", []),
            evidence=match_result.get("evidence", []),
            explanation_text=match_result.get("explanation", ""),
        )
        db_session.add(record)
        await db_session.flush()

        return {
            "match_id": record.id,
            "match_score": record.match_score,
            "strengths": record.strengths,
            "gaps": record.gaps,
            "evidence": record.evidence,
            "explanation": record.explanation_text,
            "recommendation": match_result.get("recommendation", "weak_match"),
        }

    async def generate_application_materials(self, job_id: int, profile_id: int, db_session: AsyncSession) -> dict:
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

        career_chunks = self.career_rag.get_all_chunks()

        job_rag_data = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "seniority_level": job.seniority_level,
            "description": job.description,
            "requirements": job.requirements_text or "",
            "skills": job.extracted_skills or [],
        }
        self.job_rag.ingest_job(job_rag_data)
        job_chunks_result = self.job_rag.query(
            f"{job.title} {job.company} {job.requirements_text or ''}"
        )
        job_chunks = [{"content": doc.page_content, "metadata": meta} for doc, meta in job_chunks_result]

        job_data = {
            "title": job.title,
            "company": job.company,
            "seniority_level": job.seniority_level,
        }

        resume_text = self.resume_agent.generate_resume(career_chunks, job_chunks, job_data)
        cover_letter_text = self.resume_agent.generate_cover_letter(career_chunks, job_chunks, job_data)

        app_result = await db_session.execute(
            select(Application).where(
                Application.job_id == job_id,
                Application.profile_id == profile_id,
            )
        )
        application = app_result.scalar_one_or_none()
        if not application:
            application = Application(
                job_id=job_id,
                profile_id=profile_id,
                status=ApplicationStatus.applied,
            )
            db_session.add(application)
            await db_session.flush()

        application.resume_version_text = resume_text
        application.cover_letter_text = cover_letter_text
        await db_session.flush()

        return {
            "application_id": application.id,
            "resume": resume_text,
            "cover_letter": cover_letter_text,
        }

    async def get_all_jobs(self, db_session: AsyncSession) -> list:
        result = await db_session.execute(
            select(JobPosting).where(JobPosting.is_active == True).order_by(JobPosting.created_at.desc())
        )
        jobs = result.scalars().all()

        return [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "seniority_level": j.seniority_level,
                "source": j.source,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
