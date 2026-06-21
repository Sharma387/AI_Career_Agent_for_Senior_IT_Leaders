from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class CareerRAG:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.client = Chroma(
            persist_directory=f"{settings.CHROMA_PERSIST_DIR}/career",
            embedding_function=self.embeddings,
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    def ingest_granular(self, profile_id: int, parsed: dict, expanded: dict):
        """
        Ingest profile data as granular, section-level chunks for better RAG retrieval.

        Creates separate embeddings for:
        - Each experience entry (with impact metrics from v1.0 schema)
        - Each project (with scale info from v1.0 schema)
        - Skills summary
        - Certifications
        - ATS keywords (if available from v1.0 schema)

        Each chunk gets metadata: candidate_id, section, title
        """
        docs = []
        candidate_id = str(profile_id)

        # Check if we have v1.0 full schema for richer data
        full_schema = parsed.get("_full_schema")
        v1_resume = (full_schema or {}).get("resume", {}) if full_schema else {}

        # One document per experience entry — prefer v1.0 data if available
        v1_experiences = v1_resume.get("work_experience", [])
        if v1_experiences:
            for exp in v1_experiences:
                if not isinstance(exp, dict):
                    continue
                role = exp.get("role_title", "")
                company = exp.get("company", "")

                # Build achievements text with impact metrics
                achievements_text = []
                for ach in exp.get("achievements", []):
                    if isinstance(ach, dict):
                        stmt = ach.get("statement", "")
                        metrics = ach.get("impact_metrics", {})
                        if metrics and metrics.get("value"):
                            stmt += f" [Impact: {metrics.get('type', '')} {metrics.get('value', '')} {metrics.get('unit', '')}]"
                        if stmt:
                            achievements_text.append(stmt)

                responsibilities_text = "; ".join(exp.get("responsibilities", []))
                tech_stack_text = ", ".join(exp.get("tech_stack", []))

                text = (
                    f"Role: {role} at {company}\n"
                    f"Dates: {exp.get('start_date', '')} - {exp.get('end_date', '')}\n"
                    f"Location: {exp.get('location', '')}\n"
                    f"Industry: {exp.get('company_industry', '')}\n"
                    f"Responsibilities: {responsibilities_text}\n"
                    f"Achievements: {'; '.join(achievements_text)}\n"
                    f"Tech Stack: {tech_stack_text}\n"
                    f"Stakeholders: {', '.join(exp.get('stakeholders', []))}"
                )
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "candidate_id": candidate_id,
                            "section": "experience",
                            "title": f"{role} at {company}",
                        }
                    ))
        else:
            # Fallback to flat experience format
            for exp in parsed.get("experience", []):
                if isinstance(exp, dict):
                    role = exp.get("role", exp.get("title", ""))
                    company = exp.get("company", "")
                    text = (
                        f"Role: {role} at {company}\n"
                        f"Dates: {exp.get('start_date', '')} - {exp.get('end_date', '')}\n"
                        f"Location: {exp.get('location', '')}\n"
                        f"Achievements: {'; '.join(exp.get('achievements', []))}"
                    )
                    if text.strip():
                        docs.append(Document(
                            page_content=text,
                            metadata={
                                "candidate_id": candidate_id,
                                "section": "experience",
                                "title": f"{role} at {company}",
                            }
                        ))

        # One document per project — prefer v1.0 projects with scale data
        v1_projects = v1_resume.get("projects", [])
        if v1_projects:
            for proj in v1_projects:
                if not isinstance(proj, dict):
                    continue
                name = proj.get("project_name", "")
                scale = proj.get("scale", {})
                scale_text = ""
                if isinstance(scale, dict):
                    parts = []
                    if scale.get("users_affected"):
                        parts.append(f"Users: {scale['users_affected']}")
                    if scale.get("budget"):
                        parts.append(f"Budget: {scale['budget']}")
                    if scale.get("regions"):
                        parts.append(f"Regions: {', '.join(scale['regions'])}")
                    scale_text = "; ".join(parts)

                text = (
                    f"Project: {name}\n"
                    f"Organization: {proj.get('organization', '')}\n"
                    f"Role: {proj.get('role', '')}\n"
                    f"Description: {proj.get('description', '')}\n"
                    f"Technologies: {', '.join(proj.get('technologies', []))}\n"
                    f"Outcomes: {'; '.join(proj.get('outcomes', []))}\n"
                    f"Scale: {scale_text}"
                )
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "candidate_id": candidate_id,
                            "section": "project",
                            "title": name,
                        }
                    ))

        # Also ingest expanded projects (STAR stories) from expander
        for project in expanded.get("detailed_projects", []):
            if isinstance(project, dict):
                title = project.get("title", "")
                star_stories = project.get("star_stories", [])
                star_text = ""
                if star_stories:
                    for story in star_stories:
                        if isinstance(story, dict):
                            star_text += (
                                f"Situation: {story.get('situation', '')} "
                                f"Task: {story.get('task', '')} "
                                f"Action: {story.get('action', '')} "
                                f"Result: {story.get('result', '')}\n"
                            )
                        else:
                            star_text += str(story) + "\n"

                text = (
                    f"Project: {title}\n"
                    f"Role: {project.get('role', '')}\n"
                    f"Description: {project.get('description', '')}\n"
                    f"Technologies: {', '.join(project.get('technologies', []))}\n"
                    f"Impact: {project.get('impact', '')}\n"
                    f"STAR Stories: {star_text}"
                )
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "candidate_id": candidate_id,
                            "section": "project",
                            "title": title,
                        }
                    ))

        # Skills summary — prefer v1.0 core_skills structure
        v1_skills = v1_resume.get("core_skills", {})
        if v1_skills and any(v1_skills.get(c) for c in ["technical_skills", "functional_skills", "tools_platforms", "methodologies", "domains"]):
            skills_text_parts = []
            for category in ["technical_skills", "functional_skills", "tools_platforms", "methodologies", "domains"]:
                skill_list = v1_skills.get(category, [])
                if skill_list:
                    skills_text_parts.append(f"{category.replace('_', ' ').title()}: {', '.join(skill_list)}")
            if skills_text_parts:
                docs.append(Document(
                    page_content="Skills:\n" + "\n".join(skills_text_parts),
                    metadata={
                        "candidate_id": candidate_id,
                        "section": "skills",
                        "title": "Skills Summary",
                    }
                ))
        else:
            # Fallback to flat skills
            skills = parsed.get("skills", {})
            if isinstance(skills, dict) and skills:
                skills_text_parts = []
                for category, skill_list in skills.items():
                    if isinstance(skill_list, list) and skill_list:
                        skills_text_parts.append(f"{category}: {', '.join(skill_list)}")
                if skills_text_parts:
                    docs.append(Document(
                        page_content="Skills:\n" + "\n".join(skills_text_parts),
                        metadata={
                            "candidate_id": candidate_id,
                            "section": "skills",
                            "title": "Skills Summary",
                        }
                    ))

        # Certifications — prefer v1.0 structured certs
        v1_certs = v1_resume.get("certifications", [])
        if v1_certs:
            cert_parts = []
            for c in v1_certs:
                if isinstance(c, dict) and c.get("name"):
                    part = c["name"]
                    if c.get("issuing_body"):
                        part += f" ({c['issuing_body']})"
                    cert_parts.append(part)
            if cert_parts:
                docs.append(Document(
                    page_content="Certifications: " + ", ".join(cert_parts),
                    metadata={
                        "candidate_id": candidate_id,
                        "section": "certifications",
                        "title": "Certifications",
                    }
                ))
        else:
            certs = parsed.get("certifications", [])
            if certs:
                cert_names = [str(c) for c in certs if c]
                if cert_names:
                    docs.append(Document(
                        page_content="Certifications: " + ", ".join(cert_names),
                        metadata={
                            "candidate_id": candidate_id,
                            "section": "certifications",
                            "title": "Certifications",
                        }
                    ))

        # ATS Keywords as a separate chunk (v1.0 only)
        v1_ats = v1_resume.get("ats_metadata", {})
        if isinstance(v1_ats, dict) and v1_ats.get("keywords"):
            keywords = v1_ats["keywords"]
            if keywords:
                docs.append(Document(
                    page_content="ATS Keywords: " + ", ".join(keywords),
                    metadata={
                        "candidate_id": candidate_id,
                        "section": "ats_keywords",
                        "title": "ATS Keywords",
                    }
                ))

        if docs:
            self.client.add_documents(documents=docs)

    def ingest_profile(self, profile_data: dict):
        """Legacy ingestion method — creates one big set of chunks."""
        docs = []

        if profile_data.get("resume_text"):
            chunks = self.splitter.split_text(profile_data["resume_text"])
            for chunk in chunks:
                docs.append(Document(page_content=chunk, metadata={"type": "resume"}))

        for project in profile_data.get("projects", []):
            text = (
                f"Project: {project.get('title', '')}\n"
                f"Role: {project.get('role', '')}\n"
                f"Description: {project.get('description', '')}\n"
                f"Technologies: {', '.join(project.get('technologies', []))}\n"
                f"Impact: {project.get('impact', '')}\n"
                f"STAR Stories: {project.get('star_stories', '')}"
            )
            chunks = self.splitter.split_text(text)
            for chunk in chunks:
                docs.append(Document(page_content=chunk, metadata={"type": "project"}))

        for skill in profile_data.get("skills", []):
            text = (
                f"Skill: {skill.get('name', '')}\n"
                f"Category: {skill.get('category', '')}\n"
                f"Level: {skill.get('level', '')}\n"
                f"Years: {skill.get('years_experience', '')}"
            )
            docs.append(Document(page_content=text, metadata={"type": "skill"}))

        for cert in profile_data.get("certifications", []):
            text = (
                f"Certification: {cert.get('name', '')}\n"
                f"Issuer: {cert.get('issuer', '')}\n"
                f"Date: {cert.get('date_obtained', '')}\n"
                f"Expiry: {cert.get('expiry_date', '')}"
            )
            docs.append(Document(page_content=text, metadata={"type": "cert"}))

        if docs:
            self.client.add_documents(documents=docs)

    def query(self, query_text: str, k: int = settings.TOP_K_RETRIEVAL):
        return self.client.similarity_search_with_relevance_scores(query_text, k=k)

    def get_all_chunks(self):
        collection = self.client._collection
        results = collection.get(include=["documents", "metadatas"])
        return [
            {"content": doc, "metadata": meta}
            for doc, meta in zip(results["documents"], results["metadatas"])
        ]

    def clear(self):
        ids = self.client._collection.get()["ids"]
        if ids:
            self.client._collection.delete(ids=ids)
