import pytest

from app.ingestion.job_parser import JobParser


@pytest.fixture
def parser():
    return JobParser()


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


def test_parse_job_description(parser, sample_job_text):
    result = parser.parse_job_description(sample_job_text)
    assert result["title"] == "Chief Technology Officer"
    assert result["company"] == "InnovateTech Inc."
    assert result["seniority_level"] in ("director", "lead")
    assert len(result["skills_detected"]) > 0


def test_extract_seniority(parser):
    assert parser._extract_seniority("Senior Software Engineer") == "senior"
    assert parser._extract_seniority("Director of Engineering") == "director"
    assert parser._extract_seniority("Lead Architect") == "lead"
    assert parser._extract_seniority("VP of Technology") == "vp"
    assert parser._extract_seniority("Principal Engineer") == "principal"
    assert parser._extract_seniority("Junior Developer") == "junior"
    assert parser._extract_seniority("Mid-level Engineer") == "mid"


def test_extract_skills(parser):
    text = (
        "Experience with AWS, Kubernetes, Python, and Terraform required. "
        "Familiarity with Docker, React, and PostgreSQL preferred."
    )
    skills = parser._extract_skills(text)
    assert "aws" in skills
    assert "kubernetes" in skills
    assert "python" in skills
    assert "terraform" in skills
    assert "docker" in skills


def test_parse_empty_text(parser):
    result = parser.parse_job_description("")
    assert result["title"] == ""
    assert result["company"] == ""
    assert result["seniority_level"] == "mid"
    assert result["skills_detected"] == []
