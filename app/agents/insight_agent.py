from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm_factory import get_llm


class InsightAgent:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.3)
        return self._llm

    def analyze_patterns(
        self, application_chunks: list, career_chunks: list
    ) -> dict:
        app_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in application_chunks]
        )
        career_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in career_chunks]
        )

        prompt = f"""You are a career analytics expert specializing in job application pattern analysis for senior IT leaders.

Analyze the following application history and career profile to identify patterns and provide actionable insights.

APPLICATION HISTORY (retrieved context):
---
{app_context}
---

CAREER PROFILE (retrieved context):
---
{career_context}
---

ANALYSIS TASKS:
1. Identify rejection patterns - what types of roles, companies, or stages consistently lead to rejection.
2. Identify success patterns - what types of applications progress furthest or convert to interviews.
3. Calculate interview conversion rate from the available data.
4. Generate improvement suggestions based on observed patterns.
5. Provide specific insights about the candidate's job search trajectory.

CRITICAL RULES:
- Base your analysis ONLY on the data provided in the application and career chunks.
- Do not invent application records or outcomes not present in the data.
- If insufficient data exists for certain calculations, note this clearly.

Provide your response as a JSON object with exactly these fields:
{{
    "rejection_patterns": [<list of identified rejection pattern strings>],
    "success_patterns": [<list of identified success pattern strings>],
    "improvement_suggestions": [<list of actionable suggestion strings>],
    "interview_conversion_rate": <float between 0.0 and 1.0, or 0.0 if data insufficient>,
    "insights": [<list of insight strings, e.g., "You get more interviews for infrastructure roles">]
}}"""

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
                "rejection_patterns": [],
                "success_patterns": [],
                "improvement_suggestions": [],
                "interview_conversion_rate": 0.0,
                "insights": [content],
            }

        result["rejection_patterns"] = result.get("rejection_patterns", [])
        result["success_patterns"] = result.get("success_patterns", [])
        result["improvement_suggestions"] = result.get("improvement_suggestions", [])
        rate = result.get("interview_conversion_rate", 0.0)
        result["interview_conversion_rate"] = max(0.0, min(1.0, float(rate)))
        result["insights"] = result.get("insights", [])

        return result

    def generate_interview_prep(
        self, job_chunks: list, career_chunks: list
    ) -> dict:
        job_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in job_chunks]
        )
        career_context = "\n\n".join(
            [chunk.get("content", str(chunk)) for chunk in career_chunks]
        )

        prompt = f"""You are an executive interview coach specializing in preparing senior IT leaders for high-stakes interviews.

Generate comprehensive interview preparation materials for the following job opportunity.

JOB REQUIREMENTS (retrieved context):
---
{job_context}
---

CANDIDATE CAREER PROFILE (retrieved context):
---
{career_context}
---

GENERATE:
1. Likely interview questions (8-12 questions) that a hiring manager would ask for this senior IT role.
2. STAR-format answers for each question using ONLY experience from the career context.
3. Key themes the candidate should emphasize throughout the interview.

CRITICAL RULES:
- Use ONLY experiences explicitly mentioned in the career context chunks.
- Do not fabricate stories, achievements, or experiences.
- Each STAR answer must have all five components: Situation, Task, Action, Result.
- Tailor questions to the specific seniority level and requirements of the job.

Provide your response as a JSON object with exactly these fields:
{{
    "likely_questions": [<list of interview question strings>],
    "star_answers": [
        {{
            "question": "<the interview question>",
            "situation": "<context from career chunks>",
            "task": "<responsibility or challenge>",
            "action": "<specific steps taken>",
            "result": "<measurable outcome>"
        }}
    ],
    "key_themes": [<list of theme strings to emphasize>]
}}"""

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
                "likely_questions": [],
                "star_answers": [],
                "key_themes": [content] if content else [],
            }

        result["likely_questions"] = result.get("likely_questions", [])
        result["star_answers"] = result.get("star_answers", [])
        result["key_themes"] = result.get("key_themes", [])

        return result
