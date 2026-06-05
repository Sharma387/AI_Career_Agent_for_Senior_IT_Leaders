from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm_factory import get_llm


class JobMatcherAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.3)
        return self._llm

    def match_job(
        self, career_chunks: list, job_chunks: list, job_data: dict
    ) -> dict:
        career_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in career_chunks]
        )
        job_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in job_chunks]
        )

        prompt = f"""You are a career matching expert specializing in evaluating senior IT leaders against job opportunities.

Your task is to analyze the candidate's career profile against the job requirements and provide a comprehensive match assessment.

CANDIDATE CAREER PROFILE (retrieved context):
---
{career_context}
---

JOB REQUIREMENTS (retrieved context):
---
{job_context}
---

JOB METADATA:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Seniority Level: {job_data.get('seniority_level', 'N/A')}

SCORING CRITERIA (each weighted):
1. Skills Match (30%): How well do the candidate's technical and soft skills align with job requirements?
2. Experience Level Match (25%): Does the candidate have the right seniority and years of relevant experience?
3. Industry Relevance (20%): How relevant is the candidate's industry background to this role?
4. Leadership Signals (25%): Does the candidate demonstrate leadership, strategic thinking, and executive presence?

CRITICAL RULES:
- NEVER fabricate or assume experience that is not explicitly present in the provided career context chunks
- Only reference experiences, skills, and achievements that appear in the retrieved chunks
- If information is missing, note it as a gap rather than inventing it
- Be honest and objective in your assessment

Provide your response as a JSON object with exactly these fields:
{{
    "match_score": <integer 0-100>,
    "strengths": [<list of specific strength strings based on career context>],
    "gaps": [<list of specific gap strings where candidate falls short>],
    "evidence": [{{"career_chunk": "<exact or paraphrased text from career chunk>", "relevance": "<how this chunk relates to the job>"}}],
    "explanation": "<detailed 3-5 sentence explanation of the overall match quality, why the score was given>",
    "recommendation": "<one of: strong_match, moderate_match, weak_match>"
}}

Recommendation thresholds:
- strong_match: score >= 75
- moderate_match: score 50-74
- weak_match: score < 50"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[: -3]
            content = content.strip()

        import json

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {
                "match_score": 0,
                "strengths": [],
                "gaps": ["Unable to parse LLM response"],
                "evidence": [],
                "explanation": content,
                "recommendation": "weak_match",
            }

        result["match_score"] = max(0, min(100, int(result.get("match_score", 0))))
        result["strengths"] = result.get("strengths", [])
        result["gaps"] = result.get("gaps", [])
        result["evidence"] = result.get("evidence", [])
        result["explanation"] = result.get("explanation", "")
        result["recommendation"] = result.get("recommendation", "weak_match")

        if result["match_score"] >= 75:
            result["recommendation"] = "strong_match"
        elif result["match_score"] >= 50:
            result["recommendation"] = "moderate_match"
        else:
            result["recommendation"] = "weak_match"

        return result
