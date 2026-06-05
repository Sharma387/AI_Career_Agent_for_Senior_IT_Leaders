import pytest
from datetime import datetime, date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    Base,
    CareerProfile,
    Project,
    Skill,
    Application,
    JobPosting,
    MatchResult,
    ApplicationStatus,
)


@pytest.fixture
def sync_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test_models.db'}", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(sync_engine):
    with Session(sync_engine) as s:
        yield s
        s.rollback()


def test_career_profile_create(session: Session):
    profile = CareerProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="555-0000",
        summary="Experienced leader",
        linkedin_url="https://linkedin.com/in/janedoe",
    )
    session.add(profile)
    session.flush()

    assert profile.id is not None
    assert profile.full_name == "Jane Doe"
    assert profile.email == "jane@example.com"
    assert profile.phone == "555-0000"
    assert profile.summary == "Experienced leader"
    assert profile.linkedin_url == "https://linkedin.com/in/janedoe"
    assert profile.created_at is not None
    assert profile.updated_at is not None


def test_project_create(session: Session):
    profile = CareerProfile(full_name="Bob", email="bob@test.com")
    session.add(profile)
    session.flush()

    project = Project(
        profile_id=profile.id,
        title="Cloud Migration",
        description="Migrated to AWS",
        role="Lead Architect",
        technologies="AWS, Terraform, Kubernetes",
        impact="40% cost reduction",
        star_situation="Legacy data center",
        star_task="Plan migration",
        star_action="Executed phased migration",
        star_result="Completed ahead of schedule",
    )
    session.add(project)
    session.flush()

    assert project.id is not None
    assert project.profile_id == profile.id
    assert project.title == "Cloud Migration"
    assert project.description == "Migrated to AWS"
    assert project.technologies == "AWS, Terraform, Kubernetes"


def test_skill_create(session: Session):
    profile = CareerProfile(full_name="Alice", email="alice@test.com")
    session.add(profile)
    session.flush()

    skill = Skill(
        profile_id=profile.id,
        name="Python",
        category="technical",
        proficiency="expert",
        years_experience=10.0,
    )
    session.add(skill)
    session.flush()

    assert skill.id is not None
    assert skill.profile_id == profile.id
    assert skill.name == "Python"
    assert skill.category == "technical"
    assert skill.proficiency == "expert"
    assert skill.years_experience == 10.0


def test_application_status_enum():
    expected = {
        "applied",
        "reviewing",
        "phone_screen",
        "technical_interview",
        "final_interview",
        "offered",
        "rejected",
        "withdrawn",
        "accepted",
    }
    actual = {status.value for status in ApplicationStatus}
    assert actual == expected


def test_cascade_delete(session: Session):
    profile = CareerProfile(full_name="Cascade", email="cascade@test.com")
    session.add(profile)
    session.flush()

    p1 = Project(profile_id=profile.id, title="P1")
    p2 = Project(profile_id=profile.id, title="P2")
    session.add_all([p1, p2])
    session.flush()

    project_ids = [p1.id, p2.id]

    session.delete(profile)
    session.flush()

    remaining = session.query(Project).filter(Project.id.in_(project_ids)).all()
    assert len(remaining) == 0


def test_match_result_create(session: Session):
    profile = CareerProfile(full_name="Match", email="match@test.com")
    session.add(profile)
    session.flush()

    job = JobPosting(title="CTO", company="TestCo", description="Lead tech org")
    session.add(job)
    session.flush()

    match = MatchResult(
        job_id=job.id,
        profile_id=profile.id,
        match_score=87.5,
        strengths=["Cloud expertise", "Team leadership"],
        gaps=["AI/ML experience"],
        evidence=["Led AWS migration", "Managed 50 engineers"],
        explanation_text="Strong candidate with relevant background.",
    )
    session.add(match)
    session.flush()

    assert match.id is not None
    assert match.match_score == 87.5
    assert match.strengths == ["Cloud expertise", "Team leadership"]
    assert match.gaps == ["AI/ML experience"]
    assert match.evidence == ["Led AWS migration", "Managed 50 engineers"]
    assert match.explanation_text == "Strong candidate with relevant background."
    assert match.job_id == job.id
    assert match.profile_id == profile.id
