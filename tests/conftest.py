import pytest
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.models import Base, get_db
from app.main import app


@pytest.fixture
def tmp_db_url(tmp_path):
    db_file = tmp_path / "test.db"
    return f"sqlite+aiosqlite:///{db_file}"


@pytest.fixture
def override_settings(tmp_db_url, tmp_path):
    test_chroma_dir = str(tmp_path / "chroma")
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.DATABASE_URL = tmp_db_url
        mock_settings.CHROMA_PERSIST_DIR = test_chroma_dir
        mock_settings.DEBUG = True
        mock_settings.LLM_PROVIDER = "nvidia"
        mock_settings.TOP_K_RETRIEVAL = 5
        mock_settings.MATCH_SCORE_THRESHOLD = 60.0
        mock_settings.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        mock_settings.NVIDIA_API_KEY = "test-key"
        mock_settings.NVIDIA_BASE_URL = "https://test.api.com/v1"
        mock_settings.NVIDIA_MODEL = "test-model"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_MODEL = "llama3.1:8b"
        yield mock_settings


@pytest_asyncio.fixture
async def db_engine(tmp_db_url):
    engine = create_async_engine(tmp_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_resume_text():
    return (
        "John Smith\nSenior IT Leader\nEmail: john.smith@example.com\nPhone: 555-0123\n\n"
        "SUMMARY\nExperienced CTO with 15+ years in enterprise technology leadership. "
        "Led digital transformation initiatives across Fortune 500 companies. "
        "Expert in cloud architecture, DevOps, and team building.\n\n"
        "EXPERIENCE\nVP of Engineering, TechCorp (2019-Present)\n"
        "- Led a team of 50+ engineers\n"
        "- Migrated legacy systems to AWS, reducing costs by 40%\n"
        "- Implemented CI/CD pipelines reducing deployment time by 60%\n\n"
        "Director of IT, GlobalFin (2015-2019)\n"
        "- Managed $10M annual IT budget\n"
        "- Oversaw SOX compliance and security audits\n"
        "- Built and mentored team of 25 professionals\n\n"
        "SKILLS\nCloud Architecture: AWS, Azure, GCP\n"
        "Leadership: Team Building, Strategic Planning, Budget Management\n"
        "Technical: Python, Kubernetes, Terraform, SQL\n\n"
        "CERTIFICATIONS\nAWS Solutions Architect Professional (2022)\n"
        "PMP Certification (2018)\n\n"
        "EDUCATION\nMBA, Stanford University (2014)\n"
        "BS Computer Science, MIT (2008)"
    )


@pytest.fixture
def sample_job_text():
    return (
        "Chief Technology Officer\nInnovateTech Inc.\nSan Francisco, CA (Hybrid)\n\n"
        "About the Role\nWe are seeking a visionary CTO to lead our technology organization "
        "through its next phase of growth. You will oversee a team of 100+ engineers and "
        "drive our cloud-native transformation strategy.\n\n"
        "Responsibilities\n"
        "- Define and execute technology strategy aligned with business goals\n"
        "- Lead architectural decisions for microservices platform\n"
        "- Build and scale engineering teams across multiple locations\n"
        "- Oversee $15M technology budget\n"
        "- Ensure security, compliance, and reliability of systems\n"
        "- Drive adoption of AI/ML capabilities across products\n\n"
        "Requirements\n"
        "- 15+ years of technology leadership experience\n"
        "- Track record of scaling engineering organizations\n"
        "- Deep expertise in cloud platforms (AWS preferred)\n"
        "- Experience with microservices and distributed systems\n"
        "- Strong background in DevOps and CI/CD practices\n"
        "- MBA or equivalent experience preferred\n\n"
        "Benefits\n"
        "- Competitive salary: $250K-$350K + equity\n"
        "- Health, dental, and vision insurance\n"
        "- 401(k) matching\n"
        "- Flexible work arrangement"
    )


@pytest.fixture
def mock_llm_response():
    mock_response = MagicMock()
    mock_response.content = (
        '{"match_score": 85.0, '
        '"strengths": ["Cloud architecture expertise", "Team leadership experience", "Budget management"], '
        '"gaps": ["AI/ML experience", "Startup experience"], '
        '"evidence": ["Led AWS migration saving 40%", "Managed 50+ engineer team"], '
        '"explanation": "Strong candidate with relevant leadership and technical background."}'
    )
    with patch("app.core.llm_factory.ChatOpenAI") as mock_chat:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_response
        mock_chat.return_value = mock_instance
        yield mock_chat
