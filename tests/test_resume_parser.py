import pytest

from app.ingestion.resume_parser import ResumeParser


@pytest.fixture
def parser():
    return ResumeParser()


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


def test_parse_text_file(tmp_path, parser):
    resume_content = (
        "Jane Doe\n"
        "jane@example.com\n"
        "+1-555-123-4567\n\n"
        "SUMMARY\n"
        "Experienced IT leader with 10+ years.\n\n"
        "SKILLS\n"
        "Python, AWS, Kubernetes\n\n"
        "EXPERIENCE\n"
        "Director of Engineering, Acme Corp (2020-Present)\n"
        "Led team of 30 engineers.\n\n"
        "EDUCATION\n"
        "MS Computer Science, Stanford (2012)\n"
    )
    file_path = tmp_path / "resume.txt"
    file_path.write_text(resume_content)
    result = parser.parse(str(file_path))
    assert "Jane Doe" in result
    assert "SUMMARY" in result
    assert "SKILLS" in result
    assert "Python" in result


def test_extract_sections(parser, sample_resume_text):
    sections = parser.extract_sections(sample_resume_text)
    assert "contact_info" in sections
    assert "summary" in sections
    assert "skills" in sections
    assert sections["contact_info"] != ""
    assert "CTO" in sections["summary"] or "cto" in sections["summary"].lower()
    assert len(sections["skills"]) > 0


def test_parse_nonexistent_file(parser):
    with pytest.raises(Exception):
        parser.parse("/nonexistent/path/to/resume.pdf")
