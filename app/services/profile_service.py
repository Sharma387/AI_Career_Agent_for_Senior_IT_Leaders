import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import CareerProfile, Project, Skill, Certification
from app.rag.career_rag import CareerRAG
from app.ingestion.career_expander import CareerExpander
from app.ingestion.resume_parser import ResumeParser


class ProfileService:
    def __init__(self):
        self._career_rag = None
        self._expander = None
        self._parser = None

    @property
    def career_rag(self):
        if self._career_rag is None:
            self._career_rag = CareerRAG()
        return self._career_rag

    @property
    def expander(self):
        if self._expander is None:
            self._expander = CareerExpander()
        return self._expander

    @property
    def parser(self):
        if self._parser is None:
            self._parser = ResumeParser()
        return self._parser

    async def upload_resume(self, file_path: str, db_session: AsyncSession) -> dict:
        raw_text = self.parser.parse(file_path)
        sections = self.parser.extract_sections(raw_text)
        expanded = self.expander.expand_profile(raw_text)

        contact = sections.get("contact_info", "")
        name = contact.split("\n")[0].strip() if contact else "Unknown"
        email_match = re.search(r"[\w.-]+@[\w.-]+\.[\w]+", contact)
        email = email_match.group(0) if email_match else None

        profile = CareerProfile(
            full_name=name,
            email=email,
            summary=expanded.get("summary", ""),
            raw_resume_text=raw_text,
        )
        db_session.add(profile)
        await db_session.flush()

        for project in expanded.get("detailed_projects", []):
            star_stories = project.get("star_stories", [])
            star_text = ""
            star_situation = ""
            star_task = ""
            star_action = ""
            star_result = ""
            if star_stories:
                first = star_stories[0] if isinstance(star_stories, list) else star_stories
                if isinstance(first, dict):
                    star_situation = first.get("situation", "")
                    star_task = first.get("task", "")
                    star_action = first.get("action", "")
                    star_result = first.get("result", "")
                    star_text = str(first)
                else:
                    star_text = str(first)

            proj = Project(
                profile_id=profile.id,
                title=project.get("title", ""),
                description=project.get("description", ""),
                role=project.get("role", ""),
                technologies=", ".join(project.get("technologies", [])),
                impact=project.get("impact", ""),
                star_situation=star_situation,
                star_task=star_task,
                star_action=star_action,
                star_result=star_result,
            )
            db_session.add(proj)

        for category, skills_list in expanded.get("skills_by_category", {}).items():
            for skill_name in skills_list:
                skill = Skill(
                    profile_id=profile.id,
                    name=skill_name,
                    category=category,
                )
                db_session.add(skill)

        for cert_text in sections.get("certifications", "").split("\n"):
            cert_text = cert_text.strip()
            if cert_text:
                cert = Certification(
                    profile_id=profile.id,
                    name=cert_text,
                )
                db_session.add(cert)

        await db_session.flush()

        profile_data = {
            "resume_text": raw_text,
            "projects": [
                {
                    "title": p.get("title", ""),
                    "description": p.get("description", ""),
                    "role": p.get("role", ""),
                    "technologies": p.get("technologies", []),
                    "impact": p.get("impact", ""),
                    "star_stories": "\n".join(
                        str(s) if not isinstance(s, dict) else s.get("situation", "") + " " + s.get("task", "") + " " + s.get("action", "") + " " + s.get("result", "")
                        for s in p.get("star_stories", [])
                    ),
                }
                for p in expanded.get("detailed_projects", [])
            ],
            "skills": [
                {
                    "name": s,
                    "category": cat,
                }
                for cat, skills_list in expanded.get("skills_by_category", {}).items()
                for s in skills_list
            ],
            "certifications": [
                {"name": c.name, "issuer": c.issuer or "", "date_obtained": "", "expiry_date": ""}
                for c in (await db_session.execute(
                    select(Certification).where(Certification.profile_id == profile.id)
                )).scalars().all()
            ],
        }
        self.career_rag.ingest_profile(profile_data)

        projects_count = len(expanded.get("detailed_projects", []))
        skills_count = sum(len(v) for v in expanded.get("skills_by_category", {}).values())

        return {
            "profile_id": profile.id,
            "summary": expanded.get("summary", ""),
            "projects_count": projects_count,
            "skills_count": skills_count,
        }

    async def get_profile(self, profile_id: int, db_session: AsyncSession) -> dict:
        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {}

        chunks = self.career_rag.get_all_chunks()

        projects_result = await db_session.execute(
            select(Project).where(Project.profile_id == profile_id)
        )
        projects = projects_result.scalars().all()

        skills_result = await db_session.execute(
            select(Skill).where(Skill.profile_id == profile_id)
        )
        skills = skills_result.scalars().all()

        return {
            "profile": {
                "id": profile.id,
                "full_name": profile.full_name,
                "email": profile.email,
                "summary": profile.summary,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
            },
            "projects": [
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "role": p.role,
                    "technologies": p.technologies,
                    "impact": p.impact,
                }
                for p in projects
            ],
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "proficiency": s.proficiency,
                }
                for s in skills
            ],
            "career_chunks": chunks,
        }

    async def update_profile(self, profile_id: int, updates: dict, db_session: AsyncSession) -> dict:
        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {}

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        await db_session.flush()

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

        self.career_rag.clear()
        profile_data = {
            "resume_text": profile.raw_resume_text or "",
            "projects": [
                {
                    "title": p.title,
                    "description": p.description,
                    "role": p.role,
                    "technologies": p.technologies.split(", ") if p.technologies else [],
                    "impact": p.impact,
                    "star_stories": "",
                }
                for p in projects
            ],
            "skills": [
                {"name": s.name, "category": s.category}
                for s in skills
            ],
            "certifications": [
                {"name": c.name, "issuer": c.issuer or "", "date_obtained": "", "expiry_date": ""}
                for c in certs
            ],
        }
        self.career_rag.ingest_profile(profile_data)

        return {
            "profile_id": profile.id,
            "full_name": profile.full_name,
            "summary": profile.summary,
        }

    async def add_project(self, profile_id: int, project_data: dict, db_session: AsyncSession) -> dict:
        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {}

        technologies = project_data.get("technologies", "")
        if isinstance(technologies, list):
            technologies = ", ".join(technologies)

        project = Project(
            profile_id=profile_id,
            title=project_data.get("title", ""),
            description=project_data.get("description", ""),
            role=project_data.get("role", ""),
            technologies=technologies,
            impact=project_data.get("impact", ""),
            star_situation=project_data.get("star_situation", ""),
            star_task=project_data.get("star_task", ""),
            star_action=project_data.get("star_action", ""),
            star_result=project_data.get("star_result", ""),
        )
        db_session.add(project)
        await db_session.flush()

        star_stories = ""
        if project.star_situation or project.star_task or project.star_action or project.star_result:
            star_stories = (
                f"Situation: {project.star_situation or ''}\n"
                f"Task: {project.star_task or ''}\n"
                f"Action: {project.star_action or ''}\n"
                f"Result: {project.star_result or ''}"
            )

        project_for_rag = {
            "resume_text": "",
            "projects": [
                {
                    "title": project.title,
                    "description": project.description,
                    "role": project.role,
                    "technologies": project.technologies.split(", ") if project.technologies else [],
                    "impact": project.impact,
                    "star_stories": star_stories,
                }
            ],
            "skills": [],
            "certifications": [],
        }
        self.career_rag.ingest_profile(project_for_rag)

        return {
            "project_id": project.id,
            "title": project.title,
            "profile_id": profile_id,
        }
