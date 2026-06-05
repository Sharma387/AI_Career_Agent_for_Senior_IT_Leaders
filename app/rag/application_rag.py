from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class ApplicationRAG:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.client = Chroma(
            persist_directory=f"{settings.CHROMA_PERSIST_DIR}/applications",
            embedding_function=self.embeddings,
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    def ingest_application(self, app_data: dict):
        docs = []

        text = (
            f"Job Title: {app_data.get('job_title', '')}\n"
            f"Company: {app_data.get('company', '')}\n"
            f"Status: {app_data.get('status', '')}\n"
            f"Date Applied: {app_data.get('date_applied', '')}\n"
            f"Rejection Stage: {app_data.get('rejection_stage', '')}\n"
            f"Feedback: {app_data.get('feedback', '')}"
        )

        chunks = self.splitter.split_text(text)
        metadata = {
            "type": "application",
            "company": app_data.get("company", ""),
            "status": app_data.get("status", ""),
            "job_title": app_data.get("job_title", ""),
        }
        for chunk in chunks:
            docs.append(Document(page_content=chunk, metadata=metadata))

        if docs:
            self.client.add_documents(documents=docs)

    def query(self, query_text: str, k: int = settings.TOP_K_RETRIEVAL):
        return self.client.similarity_search_with_relevance_scores(query_text, k=k)

    def get_analytics_chunks(self):
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
