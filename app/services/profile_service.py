import re
import time
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import CareerProfile, Project, Skill, Certification, ResumeParseRun
from app.rag.career_rag import CareerRAG
from app.ingestion.career_expander import CareerExpander
from app.ingestion.resume_parser import ResumeParser
from app.ingestion.profile_validator import validate_parsed_resume
from app.services.document_service import render_resume_html, generate_resume_docx

logger = logging.getLogger(__name__)


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

    async def upload_resume(self, file_path: str, db_session: AsyncSession, user_id: int | None = None, original_file_data: bytes | None = None, original_file_name: str | None = None, parse_model: str | None = None, parse_api_key: str | None = None) -> dict:
        start_time = time.time()

        # Stage 1: Extract text (with OCR fallback handled internally)
        raw_text = self.parser.parse(file_path)

        # Stage 2: Parse with chunked AI parser (v1.0 schema)
        from app.ingestion.ai_resume_parser import parse_resume_with_ai, chunk_resume
        parsed = parse_resume_with_ai(raw_text, model=parse_model, api_key=parse_api_key)
        chunks_processed = len(chunk_resume(raw_text))

        # Extract full v1.0 schema
        full_schema = parsed.pop("_full_schema", None)

        # Stage 3: Validate
        validation = validate_parsed_resume(parsed)

        # Stage 4: Expand from parsed (not raw text)
        expanded = self.expander.expand_from_parsed(parsed)

        # Calculate processing time
        processing_time = time.time() - start_time

        name = parsed.get("full_name") or "Unknown"
        email = parsed.get("email") or None
        phone = parsed.get("phone") or None
        location = parsed.get("location") or None
        linkedin = parsed.get("linkedin") or None

        # Extract v1.0 specific fields
        v1_resume = (full_schema or {}).get("resume", {})
        v1_pi = v1_resume.get("personal_info", {})
        v1_ps = v1_resume.get("professional_summary", {})

        profile = CareerProfile(
            full_name=name,
            email=email,
            phone=phone,
            linkedin_url=linkedin,
            summary=parsed.get("summary") or expanded.get("summary", ""),
            raw_resume_text=raw_text,
            original_file_data=original_file_data,
            original_file_name=original_file_name,
            interests=parsed.get("interests") or None,
            education=parsed.get("education") or None,
            # v1.0 schema fields
            parsed_resume_v1=full_schema,
            preferred_name=v1_pi.get("preferred_name") or None,
            headline=v1_pi.get("headline") or None,
            github_url=v1_pi.get("github") or None,
            portfolio_url=v1_pi.get("portfolio") or None,
            years_experience=v1_ps.get("years_experience") or None,
            seniority_level=v1_ps.get("seniority_level") or None,
            languages=v1_resume.get("languages") or None,
            preferences=v1_resume.get("preferences") or None,
            ats_metadata=v1_resume.get("ats_metadata") or None,
        )
        profile.user_id = user_id
        db_session.add(profile)
        await db_session.flush()

        # Stage 5: Store audit record
        parse_status = "success" if validation["is_valid"] else "partial"
        if not parsed.get("full_name"):
            parse_status = "failed"

        validation_status = "valid"
        if validation["errors"]:
            validation_status = "errors"
        elif validation["warnings"]:
            validation_status = "warnings"

        # Get confidence scores
        confidence_scores = {}
        try:
            from app.ingestion.ai_resume_parser import get_confidence_scores
            confidence_scores = get_confidence_scores(raw_text)
        except Exception:
            pass

        audit_record = ResumeParseRun(
            profile_id=profile.id,
            model_name=settings.OLLAMA_MODEL,
            prompt_version="v2_chunked",
            processing_time_seconds=round(processing_time, 2),
            parse_status=parse_status,
            validation_status=validation_status,
            validation_details=validation,
            confidence_scores=confidence_scores,
            chunks_processed=chunks_processed,
        )
        db_session.add(audit_record)

        # --- Store Projects ---
        # If career expander produced projects, use those.
        # FALLBACK: If no projects found, create project entries from work experience
        # (preserves original CV structure rather than leaving projects empty)
        projects_to_store = expanded.get("detailed_projects", [])

        if not projects_to_store:
            logger.info("No projects from expander — creating from work experience (fallback)")
            for exp in parsed.get("experience", []):
                if not isinstance(exp, dict):
                    continue
                role = exp.get("role", exp.get("role_title", ""))
                company = exp.get("company", "")
                achievements = exp.get("achievements", [])
                # Each experience entry becomes a project
                if role or company:
                    projects_to_store.append({
                        "title": f"{role} at {company}" if company else role,
                        "description": "; ".join(achievements[:3]) if achievements else "",
                        "role": role,
                        "technologies": exp.get("tech_stack", []),
                        "impact": achievements[0] if achievements else "",
                        "star_stories": [],
                    })

        for project in projects_to_store:
            star_stories = project.get("star_stories", [])
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

            proj = Project(
                profile_id=profile.id,
                title=project.get("title", ""),
                description=project.get("description", ""),
                role=project.get("role", ""),
                technologies=", ".join(project.get("technologies", [])) if isinstance(project.get("technologies"), list) else str(project.get("technologies", "")),
                impact=project.get("impact", ""),
                star_situation=star_situation,
                star_task=star_task,
                star_action=star_action,
                star_result=star_result,
            )
            db_session.add(proj)

        # Store skills — prefer AI-parsed skills, fall back to expander
        skills_data = parsed.get("skills", {}) or expanded.get("skills_by_category", {})
        if isinstance(skills_data, dict):
            for category, skills_list in skills_data.items():
                if isinstance(skills_list, list):
                    for skill_name in skills_list:
                        skill = Skill(
                            profile_id=profile.id,
                            name=skill_name,
                            category=category,
                        )
                        db_session.add(skill)

        # Store certifications from AI parser
        for cert_name in parsed.get("certifications", []):
            if cert_name and str(cert_name).strip():
                cert = Certification(
                    profile_id=profile.id,
                    name=str(cert_name).strip(),
                )
                db_session.add(cert)

        await db_session.flush()

        # Build skills dict for HTML: prefer v1.0 categorised skills, fall back to expander
        v1_skills = v1_resume.get("core_skills", {})
        # Map v1.0 keys to readable display names for the template
        skills_for_html = {}
        category_map = {
            "technical_skills": "Technical Skills",
            "tools_platforms": "Tools & Platforms",
            "functional_skills": "Functional / Management Skills",
            "methodologies": "Methodologies & Frameworks",
            "domains": "Industry Domains",
        }
        for key, label in category_map.items():
            items = v1_skills.get(key, [])
            if items:
                skills_for_html[label] = items

        # Fall back to expander skills if v1.0 has nothing
        if not skills_for_html:
            for category, skills_list in expanded.get("skills_by_category", {}).items():
                if skills_list:
                    skills_for_html[category] = skills_list

        nz_profile_data = {
            "full_name": name,
            "email": email or "",
            "phone": profile.phone or "",
            "location": ", ".join(p for p in [
                v1_resume.get("personal_info", {}).get("location", {}).get("city", ""),
                v1_resume.get("personal_info", {}).get("location", {}).get("country", ""),
            ] if p),
            "linkedin": v1_resume.get("personal_info", {}).get("linkedin", "") or "",
            "headline": v1_resume.get("personal_info", {}).get("headline", "") or "",
            "summary": expanded.get("summary", "") or parsed.get("summary", ""),
            "resume_text": raw_text,
            "projects": [
                {
                    "title": p.get("title", ""),
                    "description": p.get("description", ""),
                    "role": p.get("role", ""),
                    "technologies": ", ".join(p.get("technologies", [])) if isinstance(p.get("technologies"), list) else str(p.get("technologies", "")),
                    "impact": p.get("impact", ""),
                }
                for p in expanded.get("detailed_projects", [])
            ],
            "skills": skills_for_html,
            "certifications": [
                {"name": c.name, "issuer": c.issuer or ""}
                for c in (await db_session.execute(
                    select(Certification).where(Certification.profile_id == profile.id)
                )).scalars().all()
            ],
        }
        formatted_html = render_resume_html(nz_profile_data)
        profile.formatted_resume_html = formatted_html
        await db_session.flush()

        # Stage 6: Granular RAG ingestion
        self.career_rag.ingest_granular(profile.id, parsed, expanded)

        projects_count = len(expanded.get("detailed_projects", []))
        skills_count = sum(len(v) for v in (skills_data if isinstance(skills_data, dict) else {}).values())

        return {
            "profile_id": profile.id,
            "summary": expanded.get("summary", ""),
            "projects_count": projects_count,
            "skills_count": skills_count,
            "raw_resume_text": raw_text,
            "formatted_resume_html": formatted_html,
        }

    async def get_profile(self, profile_id: int, db_session: AsyncSession, user_id: int) -> dict:
        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id, CareerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {}

        try:
            chunks = self.career_rag.get_all_chunks()
        except Exception:
            chunks = []

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
            "profile": {
                "id": profile.id,
                "full_name": profile.full_name,
                "email": profile.email,
                "phone": profile.phone,
                "linkedin_url": profile.linkedin_url,
                "summary": profile.summary,
                "raw_resume_text": profile.raw_resume_text or "",
                "formatted_resume_html": profile.formatted_resume_html or "",
                "interests": profile.interests or [],
                "education": profile.education or [],
                "certifications": [
                    {"name": c.name, "issuer": c.issuer or ""}
                    for c in certs
                ],
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                # v1.0 schema fields
                "parsed_resume_v1": profile.parsed_resume_v1,
                "headline": profile.headline,
                "preferred_name": profile.preferred_name,
                "github_url": profile.github_url,
                "portfolio_url": profile.portfolio_url,
                "years_experience": profile.years_experience,
                "seniority_level": profile.seniority_level,
                "languages": profile.languages,
                "preferences": profile.preferences,
                "ats_metadata": profile.ats_metadata,
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

    async def update_profile(self, profile_id: int, updates: dict, db_session: AsyncSession, user_id: int) -> dict:
        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id, CareerProfile.user_id == user_id)
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

    async def add_project(self, profile_id: int, project_data: dict, db_session: AsyncSession, user_id: int) -> dict:
        result = await db_session.execute(
            select(CareerProfile).where(CareerProfile.id == profile_id, CareerProfile.user_id == user_id)
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
