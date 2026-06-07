from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field


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

    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Anthropic model name",
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
        default="anthropic",
        description="LLM provider: 'anthropic' (Claude), 'nvidia' (remote), or 'ollama' (local fallback)",
    )
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence-transformers model"
    )

    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"
    CHROMA_PERSIST_DIR: str = str(CHROMA_DIR)

    TOP_K_RETRIEVAL: int = 5
    MATCH_SCORE_THRESHOLD: float = 60.0

    JWT_SECRET_KEY: str = Field(default="", description="Secret key for JWT tokens. Empty = auth disabled.")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    REDIS_URL: str = Field(default="", description="Redis URL. Empty = in-memory fallback.")
    REDIS_CACHE_TTL: int = 300  # 5 minutes

    RATE_LIMIT_PER_MINUTE: int = 60

    # LinkedIn scraping configuration
    LINKEDIN_SCRAPING_ENABLED: bool = Field(default=False, description="Enable LinkedIn job scraping")
    LINKEDIN_EMAIL: str = Field(default="", description="LinkedIn email for authentication")
    LINKEDIN_PASSWORD: str = Field(default="", description="LinkedIn password for authentication")

    # Scraping schedule configuration (NZ time)
    BUSINESS_HOURS_START: int = Field(default=8, description="Start hour for business hours scraping (NZ time, 24-hour format)")
    BUSINESS_HOURS_END: int = Field(default=18, description="End hour for business hours scraping (NZ time, 24-hour format)")
    INCREMENTAL_SCRAPE_HOURS: int = Field(default=2, description="Hours back for incremental scrape during business hours")
    FULL_SCRAPE_TIME_HOUR: int = Field(default=2, description="Hour for daily full scrape (NZ time, 24-hour format)")
    FULL_SCRAPE_TIME_MINUTE: int = Field(default=0, description="Minute for daily full scrape (NZ time)")
    SCHEDULER_TIMEZONE: str = Field(default="Pacific/Auckland", description="Timezone for scheduler (NZ time)")
    SCHEDULER_INCREMENTAL_ENABLED: bool = Field(default=True, description="Enable incremental scraping scheduler")
    SCHEDULER_FULL_ENABLED: bool = Field(default=True, description="Enable full scraping scheduler")
    SEEK_SCRAPING_ENABLED: bool = Field(default=True, description="Enable Seek job scraping via Playwright")
    SEEK_DEFAULT_KEYWORDS: str = Field(default="", description="Default keywords for Seek scraping")
    SEEK_DEFAULT_LOCATION: str = Field(default="", description="Default location for Seek scraping")
    SEEK_CHROME_PROFILE_PATH: str = Field(
        default="",
        description="Path to Chrome user data directory for Seek automation"
    )
    SEEK_HEADLESS: bool = Field(default=True, description="Run Playwright in headless mode")
    SEEK_MAX_PAGES_PER_SEARCH: int = Field(default=3, description="Max result pages per search (1-10)")
    SEEK_REQUEST_DELAY_MIN: float = Field(default=2.0, description="Min delay between requests (seconds)")
    SEEK_REQUEST_DELAY_MAX: float = Field(default=5.0, description="Max delay between requests (seconds)")
    SEEK_DAILY_SCRAPE_HOUR: int = Field(default=7, description="Hour for daily Seek scrape (NZ time, 24-hour format)")
    SEEK_DAILY_SCRAPE_MINUTE: int = Field(default=0, description="Minute for daily Seek scrape")
    SEEK_ROLE_PRESETS: str = Field(
        default="project-manager,sr-project-manager,it-manager,engineering-manager,it-director,cto",
        description="Comma-separated role preset IDs for scheduled scraping"
    )

    LINKEDIN_EXTENSION_ENABLED: bool = Field(default=True, description="Enable LinkedIn extension ingest endpoint")

    LINKEDIN_DEFAULT_KEYWORDS: str = Field(default="", description="Default keywords for LinkedIn scraping")
    LINKEDIN_DEFAULT_LOCATION: str = Field(default="", description="Default location for LinkedIn scraping")

    # Adzuna Job API configuration
    ADZUNA_APP_ID: str = Field(default="", description="Adzuna API app_id")
    ADZUNA_APP_KEY: str = Field(default="", description="Adzuna API app_key")
    ADZUNA_COUNTRY: str = Field(default="nz", description="Adzuna country code (nz, au, gb, us, etc.)")
    ADZUNA_RESULTS_PER_PAGE: int = Field(default=20, description="Number of results per Adzuna API call")
    ADZUNA_MONTHLY_LIMIT: int = Field(default=250, description="Monthly API call limit for Adzuna free tier")

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

for d in [DATA_DIR, CHROMA_DIR, RESUMES_DIR, JOBS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
