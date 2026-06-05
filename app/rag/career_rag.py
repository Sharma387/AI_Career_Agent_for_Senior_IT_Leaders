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

    def ingest_profile(self, profile_data: dict):
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
