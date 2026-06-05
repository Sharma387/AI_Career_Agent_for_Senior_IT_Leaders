from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "career_agent.db"
CHROMA_DIR = DATA_DIR / "embeddings"
RESUMES_DIR = DATA_DIR / "resumes"
JOBS_DIR = DATA_DIR / "jobs"
PROMPTS_DIR = BASE_DIR / "prompts"


class Settings(BaseSettings):
    APP_NAME: str = "AI Career Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    NVIDIA_API_KEY: str = Field(default="", description="Nvidia NIM API key")
    NVIDIA_BASE_URL: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="Nvidia NIM API base URL",
    )
    NVIDIA_MODEL: str = Field(
        default="meta/llama-3.1-8b-instruct",
        description="Nvidia NIM model name",
    )

    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.1:8b",
        description="Ollama model name",
    )

    LLM_PROVIDER: str = Field(
        default="nvidia",
        description="LLM provider: 'nvidia' (remote) or 'ollama' (local fallback)",
    )
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence-transformers model"
    )

    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"
    CHROMA_PERSIST_DIR: str = str(CHROMA_DIR)

    TOP_K_RETRIEVAL: int = 5
    MATCH_SCORE_THRESHOLD: float = 60.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

for d in [DATA_DIR, CHROMA_DIR, RESUMES_DIR, JOBS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
