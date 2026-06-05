from datetime import datetime, date
from enum import Enum as PyEnum
from typing import AsyncGenerator, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    Enum,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.core.config import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("CareerProfile", back_populates="user", uselist=False)
    secret_questions = relationship("SecretQuestion", back_populates="user", cascade="all, delete-orphan")


class ApplicationStatus(str, PyEnum):
    applied = "applied"
    reviewing = "reviewing"
    phone_screen = "phone_screen"
    technical_interview = "technical_interview"
    final_interview = "final_interview"
    offered = "offered"
    rejected = "rejected"
    withdrawn = "withdrawn"
    accepted = "accepted"


class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    raw_resume_text = Column(Text, nullable=True)
    formatted_resume_html = Column(Text, nullable=True)
    interests = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    projects = relationship("Project", back_populates="profile", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="profile", cascade="all, delete-orphan")
    certifications = relationship("Certification", back_populates="profile", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="profile", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="profile", cascade="all, delete-orphan")
    articulations = relationship("SkillArticulation", back_populates="profile", cascade="all, delete-orphan")
    user = relationship("User", back_populates="profile")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String(255), nullable=True)
    technologies = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)
    duration = Column(String(100), nullable=True)
    star_situation = Column(Text, nullable=True)
    star_task = Column(Text, nullable=True)
    star_action = Column(Text, nullable=True)
    star_result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("CareerProfile", back_populates="projects")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    proficiency = Column(String(50), nullable=True)
    years_experience = Column(Float, nullable=True)

    profile = relationship("CareerProfile", back_populates="skills")


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    issuer = Column(String(255), nullable=True)
    date_obtained = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

    profile = relationship("CareerProfile", back_populates="certifications")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    url = Column(String(1024), nullable=True)
    location = Column(String(255), nullable=True)
    seniority_level = Column(String(100), nullable=True)
    salary_range = Column(String(100), nullable=True)
    requirements_text = Column(Text, nullable=True)
    extracted_skills = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.applied, nullable=False)
    date_applied = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    feedback_notes = Column(Text, nullable=True)
    rejection_stage = Column(String(100), nullable=True)
    time_to_response_days = Column(Integer, nullable=True)
    cover_letter_text = Column(Text, nullable=True)
    resume_version_text = Column(Text, nullable=True)

    job = relationship("JobPosting", back_populates="applications")
    profile = relationship("CareerProfile", back_populates="applications")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)
    strengths = Column(JSON, nullable=True)
    gaps = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    explanation_text = Column(Text, nullable=True)
    recommendation = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("JobPosting", back_populates="match_results")
    profile = relationship("CareerProfile", back_populates="match_results")
    articulations = relationship("SkillArticulation", back_populates="match_result", cascade="all, delete-orphan")


class SkillArticulation(Base):
    __tablename__ = "skill_articulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_result_id = Column(Integer, ForeignKey("match_results.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    gap_text = Column(Text, nullable=False)
    has_skill = Column(Boolean, nullable=False, default=False)
    evidence = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    match_result = relationship("MatchResult", back_populates="articulations")
    profile = relationship("CareerProfile", back_populates="articulations")


class SecretQuestion(Base):
    __tablename__ = "secret_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    answer_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="secret_questions")


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
