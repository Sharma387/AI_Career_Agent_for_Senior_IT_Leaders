from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class JobRAG:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.client = Chroma(
            persist_directory=f"{settings.CHROMA_PERSIST_DIR}/jobs",
            embedding_function=self.embeddings,
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    def ingest_job(self, job_data: dict):
        docs = []

        text = (
            f"Job ID: {job_data.get('job_id', '')}\n"
            f"Title: {job_data.get('title', '')}\n"
            f"Company: {job_data.get('company', '')}\n"
            f"Seniority Level: {job_data.get('seniority_level', '')}\n"
            f"Description: {job_data.get('description', '')}\n"
            f"Requirements: {job_data.get('requirements', '')}\n"
            f"Skills: {', '.join(job_data.get('skills', []))}"
        )

        chunks = self.splitter.split_text(text)
        metadata = {
            "type": "job",
            "job_id": job_data.get("job_id", ""),
            "company": job_data.get("company", ""),
            "title": job_data.get("title", ""),
        }
        for chunk in chunks:
            docs.append(Document(page_content=chunk, metadata=metadata))

        if docs:
            self.client.add_documents(documents=docs)

    def query(self, query_text: str, k: int = settings.TOP_K_RETRIEVAL):
        return self.client.similarity_search_with_relevance_scores(query_text, k=k)

    def clear(self):
        ids = self.client._collection.get()["ids"]
        if ids:
            self.client._collection.delete(ids=ids)
