import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm_factory import get_llm


SYSTEM_PROMPT = """You are an expert career coach and resume analyst for senior IT leaders.
Your task is to expand a resume into a detailed career profile.

RULES:
- Only expand on what is explicitly stated in the resume. Do NOT hallucinate or invent details, companies, projects, skills, or achievements that are not present.
- If the resume mentions a bullet point briefly, expand it into a richer narrative by elaborating on the themes present in the text.
- Generate STAR (Situation, Task, Action, Result) stories ONLY from the experience described in the resume.
- Group skills into logical categories based on what appears in the resume.
- Extract key achievements that are clearly stated or strongly implied by the resume text.

You must respond with valid JSON matching this structure:
{
  "summary": "A comprehensive 3-4 sentence professional summary",
  "detailed_projects": [
    {
      "title": "project or initiative name",
      "description": "expanded narrative of the project",
      "role": "your role",
      "technologies": ["tech1", "tech2"],
      "impact": "measurable business impact",
      "star_stories": ["STAR-formatted story"]
    }
  ],
  "skills_by_category": {
    "leadership": ["skill1"],
    "technical": ["skill1"],
    "methodologies": ["skill1"],
    "platforms": ["skill1"]
  },
  "key_achievements": ["achievement1"],
  "interview_stories": ["STAR-formatted story"]
}

Respond ONLY with the JSON object. No other text."""


class CareerExpander:

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.3)
        return self._llm

    def expand_profile(self, resume_text: str, projects_raw: list[dict] = None) -> dict:
        user_content = f"RESUME:\n\n{resume_text}"

        if projects_raw:
            project_notes = json.dumps(projects_raw, indent=2)
            user_content += f"\n\nADDITIONAL PROJECT NOTES:\n\n{project_notes}"

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        response = self.llm.invoke(messages)
        raw = response.content.strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        profile = json.loads(raw)

        profile.setdefault("summary", "")
        profile.setdefault("detailed_projects", [])
        profile.setdefault("skills_by_category", {})
        profile.setdefault("key_achievements", [])
        profile.setdefault("interview_stories", [])

        for project in profile["detailed_projects"]:
            project.setdefault("title", "")
            project.setdefault("description", "")
            project.setdefault("role", "")
            project.setdefault("technologies", [])
            project.setdefault("impact", "")
            project.setdefault("star_stories", [])

        return profile
