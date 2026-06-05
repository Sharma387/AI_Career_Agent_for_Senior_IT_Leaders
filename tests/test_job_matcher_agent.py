import json
from unittest.mock import patch, MagicMock

import pytest

from app.agents.job_matcher_agent import JobMatcherAgent


@pytest.fixture
def mock_llm():
    with patch("app.agents.job_matcher_agent.get_llm") as mock:
        llm = MagicMock()
        mock.return_value = llm
        yield llm


@pytest.fixture
def agent(mock_llm):
    return JobMatcherAgent()


def _make_llm_response(payload):
    resp = MagicMock()
    resp.content = json.dumps(payload) if isinstance(payload, dict) else payload
    return resp


@pytest.mark.asyncio
async def test_match_job_returns_valid_structure(agent, mock_llm):
    payload = {
        "match_score": 82,
        "strengths": ["Cloud architecture", "Leadership"],
        "gaps": ["AI/ML experience"],
        "evidence": [{"career_chunk": "Led AWS migration", "relevance": "Direct match"}],
        "explanation": "Strong candidate overall.",
        "recommendation": "strong_match",
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.match_job(
        career_chunks=[{"content": "CTO with 15 years experience"}],
        job_chunks=[{"content": "Seeking CTO with cloud expertise"}],
        job_data={"title": "CTO", "company": "Acme", "seniority_level": "Executive"},
    )

    assert "match_score" in result
    assert "strengths" in result
    assert "gaps" in result
    assert "evidence" in result
    assert "explanation" in result
    assert "recommendation" in result
    assert isinstance(result["strengths"], list)
    assert isinstance(result["gaps"], list)
    assert isinstance(result["evidence"], list)


@pytest.mark.asyncio
async def test_match_score_clamped(agent, mock_llm):
    payload = {
        "match_score": 150,
        "strengths": [],
        "gaps": [],
        "evidence": [],
        "explanation": "Over 100.",
        "recommendation": "strong_match",
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.match_job(
        career_chunks=[{"content": "Experience"}],
        job_chunks=[{"content": "Requirements"}],
        job_data={"title": "VP", "company": "X", "seniority_level": "Senior"},
    )

    assert result["match_score"] == 100


@pytest.mark.asyncio
async def test_match_score_floor(agent, mock_llm):
    payload = {
        "match_score": -20,
        "strengths": [],
        "gaps": [],
        "evidence": [],
        "explanation": "Negative.",
        "recommendation": "weak_match",
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.match_job(
        career_chunks=[{"content": "Experience"}],
        job_chunks=[{"content": "Requirements"}],
        job_data={"title": "VP", "company": "X", "seniority_level": "Senior"},
    )

    assert result["match_score"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "score,expected_rec",
    [
        (85, "strong_match"),
        (75, "strong_match"),
        (74, "moderate_match"),
        (50, "moderate_match"),
        (49, "weak_match"),
        (0, "weak_match"),
    ],
)
async def test_recommendation_logic(agent, mock_llm, score, expected_rec):
    payload = {
        "match_score": score,
        "strengths": [],
        "gaps": [],
        "evidence": [],
        "explanation": "",
        "recommendation": "weak_match",
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.match_job(
        career_chunks=[{"content": "Experience"}],
        job_chunks=[{"content": "Requirements"}],
        job_data={"title": "VP", "company": "X", "seniority_level": "Senior"},
    )

    assert result["recommendation"] == expected_rec


@pytest.mark.asyncio
async def test_handles_llm_parse_error(agent, mock_llm):
    mock_llm.invoke.return_value = _make_llm_response("this is not json at all")

    result = agent.match_job(
        career_chunks=[{"content": "Experience"}],
        job_chunks=[{"content": "Requirements"}],
        job_data={"title": "VP", "company": "X", "seniority_level": "Senior"},
    )

    assert result["match_score"] == 0
    assert result["recommendation"] == "weak_match"
    assert "Unable to parse LLM response" in result["gaps"]
    assert result["strengths"] == []
    assert result["evidence"] == []
