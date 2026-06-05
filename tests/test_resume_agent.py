from unittest.mock import patch, MagicMock

import pytest

from app.agents.resume_agent import ResumeAgent


@pytest.fixture
def mock_llm():
    with patch("app.agents.resume_agent.get_llm") as mock:
        llm = MagicMock()
        mock.return_value = llm
        yield llm


@pytest.fixture
def agent(mock_llm):
    return ResumeAgent()


def _make_llm_response(content):
    resp = MagicMock()
    resp.content = content
    return resp


@pytest.mark.asyncio
async def test_generate_resume_returns_string(agent, mock_llm):
    mock_llm.invoke.return_value = _make_llm_response("Tailored resume content")

    result = agent.generate_resume(
        career_chunks=[{"content": "CTO with 15 years"}],
        job_chunks=[{"content": "Seeking cloud expert"}],
        job_data={"title": "CTO", "company": "Acme", "seniority_level": "Executive"},
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert result == "Tailored resume content"


@pytest.mark.asyncio
async def test_generate_cover_letter_returns_string(agent, mock_llm):
    mock_llm.invoke.return_value = _make_llm_response("Dear Hiring Manager, ...")

    result = agent.generate_cover_letter(
        career_chunks=[{"content": "CTO with 15 years"}],
        job_chunks=[{"content": "Seeking cloud expert"}],
        job_data={"title": "CTO", "company": "Acme", "seniority_level": "Executive"},
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert result == "Dear Hiring Manager, ..."


@pytest.mark.asyncio
async def test_prompt_includes_career_chunks(agent, mock_llm):
    mock_llm.invoke.return_value = _make_llm_response("Resume text")
    career_chunks = [
        {"content": "Led digital transformation at Fortune 500"},
        {"content": "Built and scaled engineering org to 200 people"},
    ]
    job_chunks = [{"content": "Cloud architecture role"}]
    job_data = {"title": "VP Eng", "company": "TechCo", "seniority_level": "Senior"}

    agent.generate_resume(career_chunks, job_chunks, job_data)

    call_args = mock_llm.invoke.call_args
    prompt = call_args[0][0][0].content
    assert "Led digital transformation at Fortune 500" in prompt
    assert "Built and scaled engineering org to 200 people" in prompt


@pytest.mark.asyncio
async def test_prompt_includes_job_chunks(agent, mock_llm):
    mock_llm.invoke.return_value = _make_llm_response("Resume text")
    career_chunks = [{"content": "CTO experience"}]
    job_chunks = [
        {"content": "Must have AWS expertise"},
        {"content": "Experience with microservices required"},
    ]
    job_data = {"title": "CTO", "company": "Acme", "seniority_level": "Executive"}

    agent.generate_resume(career_chunks, job_chunks, job_data)

    call_args = mock_llm.invoke.call_args
    prompt = call_args[0][0][0].content
    assert "Must have AWS expertise" in prompt
    assert "Experience with microservices required" in prompt
