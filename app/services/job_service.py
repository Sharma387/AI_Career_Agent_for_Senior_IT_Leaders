from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Application, ApplicationStatus, JobPosting, MatchResult, CareerProfile, Project, Skill, Skill as SkillModel
from app.rag.job_rag import JobRAG
from app.rag.career_rag import CareerRAG
from app.ingestion.job_parser import JobParser
from app.agents.job_matcher_agent import JobMatcherAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.insight_agent import InsightAgent
from app.services.document_service import (
    render_resume_html,
    render_cover_letter_html,
    generate_resume_docx,
    generate_cover_letter_docx,
)


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
            recommendation=match_result.get("recommendation", "weak_match"),
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

    async def match_job_enhanced(self, job_id: int, profile_id: int, db_session: AsyncSession) -> dict:
        base_result = await self.match_job(job_id, profile_id, db_session)

        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {**base_result, "score_breakdown": {}, "improvement_recommendations": [], "interview_strategy": {}}

        job_result = await db_session.execute(
            select(JobPosting).where(JobPosting.id == job_id)
        )
        job = job_result.scalar_one_or_none()

        skills_result = await db_session.execute(
            select(SkillModel).where(SkillModel.profile_id == profile_id)
        )
        skills = skills_result.scalars().all()
        skill_names = [s.name for s in skills]
        skill_categories = list(set(s.category for s in skills if s.category))

        from app.db.models import Certification
        certs_result = await db_session.execute(
            select(Certification).where(Certification.profile_id == profile_id)
        )
        certs = certs_result.scalars().all()

        projects_result = await db_session.execute(
            select(Project).where(Project.profile_id == profile_id)
        )
        projects = projects_result.scalars().all()

        job_skills = job.extracted_skills if job else []
        job_requirements = job.requirements_text if job else ""

        matched_skills = set(skill_names) & set(job_skills) if job_skills else set()
        skills_score = min(100, round(len(matched_skills) / max(len(job_skills), 1) * 100)) if job_skills else 50
        skills_weighted = round(skills_score * 0.30, 2)

        seniority_map = {
            "junior": 2, "mid": 5, "senior": 8, "lead": 10,
            "director": 12, "vp": 15, "cto": 18, "c-level": 20, "executive": 20,
        }
        required_exp = 5
        if job and job.seniority_level:
            for level, yrs in seniority_map.items():
                if level in job.seniority_level.lower():
                    required_exp = yrs
                    break
        actual_exp = len(projects) * 2 + len(skills) * 0.5
        experience_score = min(100, round(actual_exp / max(required_exp, 1) * 100))
        experience_weighted = round(experience_score * 0.25, 2)

        industry_score = min(100, 60 + len(certs) * 10 + (10 if profile.summary else 0))
        industry_weighted = round(industry_score * 0.20, 2)

        leadership_keywords = ["lead", "director", "vp", "cto", "architect", "principal", "head", "chief", "managed", "directed", "oversaw"]
        leadership_count = sum(1 for kw in leadership_keywords if kw in (profile.summary or "").lower())
        for p in projects:
            leadership_count += sum(1 for kw in leadership_keywords if kw in (p.description or "").lower())
            leadership_count += sum(1 for kw in leadership_keywords if kw in (p.role or "").lower())
        leadership_score = min(100, 30 + leadership_count * 12)
        leadership_weighted = round(leadership_score * 0.25, 2)

        match_score = round(skills_weighted + experience_weighted + industry_weighted + leadership_weighted)

        strengths = list(base_result.get("strengths", []))
        gaps = list(base_result.get("gaps", []))
        improvement_recommendations = []

        if skills_score < 70:
            missing = [s for s in (job_skills or []) if s not in skill_names]
            if missing:
                gaps.append(f"Missing skills: {', '.join(missing[:5])}")
                improvement_recommendations.append({
                    "area": "Skills",
                    "gap": f"Proficiency in {', '.join(missing[:3])}",
                    "recommendation": f"Consider obtaining certifications or hands-on experience in: {', '.join(missing[:3])}. Lead a project utilizing these technologies.",
                    "priority": "high",
                    "estimated_impact": f"+{100 - skills_score}% skills match",
                })
        else:
            strengths.append(f"Strong skills alignment ({len(matched_skills)}/{len(job_skills)} required skills)")

        if experience_score < 70:
            gaps.append(f"Experience level below target ({required_exp}+ years expected)")
            improvement_recommendations.append({
                "area": "Experience",
                "gap": f"Need {required_exp}+ years of relevant experience",
                "recommendation": "Seek interim leadership roles, lead cross-functional initiatives, or take on advisory positions to build executive-level experience.",
                "priority": "medium",
                "estimated_impact": f"+{100 - experience_score}% experience score",
            })
        else:
            strengths.append(f"Adequate experience ({len(projects)} projects, {len(skills)} skills demonstrated)")

        if leadership_score < 60:
            gaps.append("Limited leadership signals in profile")
            improvement_recommendations.append({
                "area": "Leadership",
                "gap": "Executive leadership visibility",
                "recommendation": "Publish thought leadership articles, speak at conferences, or take on VP/Director level advisory roles.",
                "priority": "high",
                "estimated_impact": f"+{100 - leadership_score}% leadership score",
            })
        else:
            strengths.append("Strong leadership signals")

        if industry_score < 60:
            gaps.append("Could strengthen industry-specific positioning")
            improvement_recommendations.append({
                "area": "Industry Relevance",
                "gap": "Industry-specific certifications",
                "recommendation": "Obtain industry-recognized certifications and highlight domain-specific project experience.",
                "priority": "medium",
                "estimated_impact": f"+{100 - industry_score}% industry score",
            })

        if match_score >= 80:
            recommendation = "strong_match"
            explanation = "Profile strongly aligns with the target role. Proceed with application."
        elif match_score >= 60:
            recommendation = "moderate_match"
            explanation = "Profile has good alignment with some gaps. Address key gaps before applying."
        elif match_score >= 40:
            recommendation = "partial_match"
            explanation = "Profile has some relevant experience but significant gaps. Consider upskilling first."
        else:
            recommendation = "weak_match"
            explanation = "Profile has limited alignment with the target role. Significant development needed."

        key_themes = []
        if profile.summary:
            key_themes.append("Lead with executive summary highlighting leadership journey")
        if matched_skills:
            key_themes.append(f"Emphasize expertise in {', '.join(list(matched_skills)[:3])}")
        if projects:
            key_themes.append("Reference specific quantified achievements from projects")

        potential_questions = [
            "Tell me about your most significant career achievement and its impact.",
            "How do you approach leading technical transformation in large organizations?",
            "Describe a time you managed a cross-functional team through a major initiative.",
            "How do you evaluate and adopt emerging technologies?",
            "What is your leadership philosophy when building high-performance teams?",
        ]

        talking_points = []
        for p in projects[:3]:
            if p.impact:
                talking_points.append(f"{p.title}: {p.impact}")
            elif p.description:
                talking_points.append(f"{p.title}: {p.description[:100]}")

        areas_to_prepare = []
        for g in gaps[:3]:
            areas_to_prepare.append(f"Prepare examples addressing: {g}")
        for s in list(matched_skills)[:3]:
            areas_to_prepare.append(f"Deep dive into {s} experience and results")

        interview_strategy = {
            "key_themes": key_themes,
            "potential_questions": potential_questions,
            "talking_points": talking_points,
            "areas_to_prepare": areas_to_prepare,
        }

        return {
            "match_id": base_result.get("match_id"),
            "match_score": match_score,
            "score_breakdown": {
                "skills_match": {"score": skills_score, "max": 100, "weight": 0.30, "weighted": skills_weighted},
                "experience_match": {"score": experience_score, "max": 100, "weight": 0.25, "weighted": experience_weighted},
                "industry_relevance": {"score": industry_score, "max": 100, "weight": 0.20, "weighted": industry_weighted},
                "leadership_signals": {"score": leadership_score, "max": 100, "weight": 0.25, "weighted": leadership_weighted},
            },
            "strengths": strengths,
            "gaps": gaps,
            "evidence": base_result.get("evidence", []),
            "explanation": explanation,
            "recommendation": recommendation,
            "improvement_recommendations": improvement_recommendations,
            "interview_strategy": interview_strategy,
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

        projects_result = await db_session.execute(
            select(Project).where(Project.profile_id == profile_id)
        )
        projects = projects_result.scalars().all()

        skills_result = await db_session.execute(
            select(SkillModel).where(SkillModel.profile_id == profile_id)
        )
        skills = skills_result.scalars().all()

        certs_result = await db_session.execute(
            select(CareerProfile.certifications.property.mapper.class_).where(
                CareerProfile.certifications.property.mapper.class_.profile_id == profile_id
            )
        )
        from app.db.models import Certification
        certs_result = await db_session.execute(
            select(Certification).where(Certification.profile_id == profile_id)
        )
        certs = certs_result.scalars().all()

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

        profile_structured = {
            "full_name": profile.full_name,
            "email": profile.email or "",
            "summary": profile.summary or "",
            "resume_text": profile.raw_resume_text or resume_text,
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
            "skills": {},
            "certifications": [
                {"name": c.name, "issuer": c.issuer or ""}
                for c in certs
            ],
        }

        for skill in skills:
            cat = skill.category or "General"
            if cat not in profile_structured["skills"]:
                profile_structured["skills"][cat] = []
            profile_structured["skills"][cat].append(skill.name)

        job_structured = {
            "title": job.title,
            "company": job.company,
            "seniority_level": job.seniority_level,
        }

        resume_html = render_resume_html(profile_structured, job_structured)
        cover_letter_html = render_cover_letter_html(profile_structured, job_structured, cover_letter_text)

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
            "resume_html": resume_html,
            "cover_letter_html": cover_letter_html,
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
