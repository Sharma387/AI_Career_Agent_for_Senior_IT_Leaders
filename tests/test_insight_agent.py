import json
from unittest.mock import patch, MagicMock

import pytest

from app.agents.insight_agent import InsightAgent


@pytest.fixture
def mock_llm():
    with patch("app.agents.insight_agent.get_llm") as mock:
        llm = MagicMock()
        mock.return_value = llm
        yield llm


@pytest.fixture
def agent(mock_llm):
    return InsightAgent()


def _make_llm_response(payload):
    resp = MagicMock()
    resp.content = json.dumps(payload) if isinstance(payload, dict) else payload
    return resp


@pytest.mark.asyncio
async def test_analyze_patterns_returns_structure(agent, mock_llm):
    payload = {
        "rejection_patterns": ["Too senior for mid-market roles"],
        "success_patterns": ["Infrastructure roles convert well"],
        "improvement_suggestions": ["Tailor resume for startup culture"],
        "interview_conversion_rate": 0.35,
        "insights": ["Infrastructure roles have higher conversion"],
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.analyze_patterns(
        application_chunks=[{"content": "Applied to CTO roles, rejected at 3"}],
        career_chunks=[{"content": "15 years in enterprise IT"}],
    )

    assert "rejection_patterns" in result
    assert "success_patterns" in result
    assert "improvement_suggestions" in result
    assert "interview_conversion_rate" in result
    assert "insights" in result
    assert isinstance(result["rejection_patterns"], list)
    assert isinstance(result["success_patterns"], list)
    assert isinstance(result["improvement_suggestions"], list)
    assert isinstance(result["interview_conversion_rate"], float)
    assert isinstance(result["insights"], list)
    assert result["interview_conversion_rate"] == 0.35


@pytest.mark.asyncio
async def test_generate_interview_prep_returns_structure(agent, mock_llm):
    payload = {
        "likely_questions": [
            "Describe your experience scaling engineering teams",
            "How do you approach cloud migration strategy?",
        ],
        "star_answers": [
            {
                "question": "Describe your experience scaling engineering teams",
                "situation": "Company needed to double engineering capacity",
                "task": "Lead hiring and onboarding for 50 new engineers",
                "action": "Implemented structured hiring pipeline and mentorship program",
                "result": "Hired 50 engineers in 6 months, retention at 92%",
            }
        ],
        "key_themes": ["Cloud-first mindset", "Data-driven decisions"],
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.generate_interview_prep(
        job_chunks=[{"content": "Seeking CTO with scaling experience"}],
        career_chunks=[{"content": "Scaled team from 20 to 100 engineers"}],
    )

    assert "likely_questions" in result
    assert "star_answers" in result
    assert "key_themes" in result
    assert isinstance(result["likely_questions"], list)
    assert len(result["likely_questions"]) == 2
    assert isinstance(result["star_answers"], list)
    assert len(result["star_answers"]) == 1
    assert result["star_answers"][0]["question"] == "Describe your experience scaling engineering teams"
    assert result["star_answers"][0]["situation"] == "Company needed to double engineering capacity"
    assert result["star_answers"][0]["result"] == "Hired 50 engineers in 6 months, retention at 92%"
    assert isinstance(result["key_themes"], list)
    assert "Cloud-first mindset" in result["key_themes"]


@pytest.mark.asyncio
async def test_handles_empty_application_history(agent, mock_llm):
    payload = {
        "rejection_patterns": [],
        "success_patterns": [],
        "improvement_suggestions": ["Insufficient data for detailed analysis"],
        "interview_conversion_rate": 0.0,
        "insights": [],
    }
    mock_llm.invoke.return_value = _make_llm_response(payload)

    result = agent.analyze_patterns(
        application_chunks=[],
        career_chunks=[{"content": "Some career info"}],
    )

    assert result["rejection_patterns"] == []
    assert result["success_patterns"] == []
    assert result["interview_conversion_rate"] == 0.0
    assert isinstance(result["improvement_suggestions"], list)
    assert isinstance(result["insights"], list)
