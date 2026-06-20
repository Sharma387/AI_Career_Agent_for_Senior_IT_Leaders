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
        - Each experience entry
        - Each project
        - Skills summary
        - Certifications

        Each chunk gets metadata: candidate_id, section, title
        """
        docs = []
        candidate_id = str(profile_id)

        # One document per experience entry
        for exp in parsed.get("experience", []):
            if isinstance(exp, dict):
                title = exp.get("title", "")
                company = exp.get("company", "")
                text = (
                    f"Role: {title} at {company}\n"
                    f"Dates: {exp.get('dates', '')}\n"
                    f"Location: {exp.get('location', '')}\n"
                    f"Description: {exp.get('description', '')}\n"
                    f"Achievements: {'; '.join(exp.get('bullets', []))}"
                )
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "candidate_id": candidate_id,
                            "section": "experience",
                            "title": f"{title} at {company}",
                        }
                    ))

        # One document per project (from expanded data)
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

        # Skills summary as one document
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

        # Certifications as one document
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
