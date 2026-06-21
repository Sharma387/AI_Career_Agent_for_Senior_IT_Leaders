import json
import logging
import re
import warnings

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert career coach and resume analyst for senior IT leaders.
Your task is to expand a resume into a detailed career profile.

CRITICAL: Extract projects from ALL parts of the resume. Projects may appear as:
- Dedicated "Projects" or "Key Projects" sections
- Under job experience as major initiatives or accomplishments
- As bullet points describing deliverables, implementations, or transformations
- As section headers like "Notable Initiatives", "Program Highlights", "Major Deliverables"

For senior IT leaders, look for:
- Digital transformation programs
- System implementations or migrations
- Team building and organizational changes
- Strategy development and execution
- Budget and vendor management
- Cloud adoption, security initiatives
- Process improvements and automation

RULES:
- Only expand on what is explicitly stated in the resume. Do NOT hallucinate or invent details.
- If the resume mentions a bullet point briefly, expand it into a richer narrative by elaborating on the themes present in the text.
- Generate STAR (Situation, Task, Action, Result) stories ONLY from the experience described in the resume.
- Group skills into logical categories based on what appears in the resume.
- Extract key achievements that are clearly stated or strongly implied by the resume text.
- If you cannot find explicit projects, create project entries from the most significant accomplishments described in each role.

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


STRUCTURED_EXPAND_PROMPT = """You are a career content enricher. You receive ALREADY PARSED structured career data.

YOUR ONLY JOB: Expand achievements into STAR stories and create project summaries.

YOU MUST NOT:
- Re-extract skills (skills are already parsed — do not touch them)
- Re-detect job titles or companies (already parsed)
- Re-parse resume structure (already done)
- Add skills, certifications, or experience not in the input
- Change any factual information

YOU MUST:
- For each experience entry's achievements, create expanded STAR stories
- Identify major projects from achievements
- Create a 3-4 sentence professional summary from the headline + experience
- Preserve the experience ORDER exactly as given

INPUT: Structured JSON with experience[], skills{}, certifications[]
OUTPUT: Enriched JSON with projects[] and STAR stories

Respond with ONLY this JSON:
{
  "summary": "3-4 sentence professional summary",
  "detailed_projects": [
    {
      "title": "project name (from an achievement)",
      "description": "expanded narrative",
      "role": "the role held during this project",
      "technologies": ["only technologies mentioned"],
      "impact": "measurable outcome",
      "star_stories": [{"situation": "", "task": "", "action": "", "result": ""}]
    }
  ],
  "key_achievements": ["verbatim achievements from input"],
  "interview_stories": [{"situation": "", "task": "", "action": "", "result": ""}]
}

Do NOT include a skills_by_category field — skills are already handled.
Respond ONLY with JSON. No markdown, no explanation."""


class CareerExpander:

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm(temperature=0.3)
        return self._llm

    def expand_from_parsed(self, parsed_resume: dict) -> dict:
        """
        Expand pre-parsed structured resume into projects with STAR stories.

        This is a TRANSFORMER, not a parser:
        - Input: structured parsed data (experience, skills already extracted)
        - Output: projects, STAR stories, achievements
        - Does NOT re-extract skills or re-parse structure
        """
        # Only pass experience data — skills are already handled by parser
        structured_input = {
            "name": parsed_resume.get("full_name", ""),
            "headline": parsed_resume.get("headline", ""),
            "summary": parsed_resume.get("summary", ""),
            "experience": parsed_resume.get("experience", []),
            "certifications": parsed_resume.get("certifications", []),
        }

        user_content = f"STRUCTURED CAREER DATA:\n\n{json.dumps(structured_input, indent=2)}"

        messages = [
            SystemMessage(content=STRUCTURED_EXPAND_PROMPT),
            HumanMessage(content=user_content),
        ]

        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip()

            if "```" in raw:
                parts = raw.split("```")
                if len(parts) >= 3:
                    json_part = parts[1]
                    if json_part.startswith("json"):
                        json_part = json_part[4:]
                    raw = json_part.strip()

            profile = json.loads(raw)

            # CRITICAL: Do not let expander override skills — use parser's skills
            profile["skills_by_category"] = parsed_resume.get("skills", {})

        except json.JSONDecodeError:
            logger.warning("Career expander returned non-JSON, using fallback")
            profile = self._fallback_from_parsed(parsed_resume)
        except Exception as e:
            logger.error(f"Career expansion failed: {e}")
            profile = self._fallback_from_parsed(parsed_resume)

        return self._ensure_defaults(profile)

    def expand_profile(self, resume_text: str, projects_raw: list[dict] = None) -> dict:
        """
        Expand raw resume text into a detailed career profile.

        .. deprecated::
            Use expand_from_parsed() with pre-parsed structured data for
            faster processing and fewer tokens.
        """
        warnings.warn(
            "expand_profile(raw_text) is deprecated. Use expand_from_parsed(parsed_resume) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        user_content = f"RESUME:\n\n{resume_text}"

        if projects_raw:
            project_notes = json.dumps(projects_raw, indent=2)
            user_content += f"\n\nADDITIONAL PROJECT NOTES:\n\n{project_notes}"

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip()

            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)

            profile = json.loads(raw)
        except json.JSONDecodeError:
            # LLM returned non-JSON — fall back to basic profile
            profile = {
                "summary": resume_text[:500] if resume_text else "",
                "detailed_projects": [],
                "skills_by_category": {},
                "key_achievements": [],
                "interview_stories": [],
            }
        except Exception:
            # LLM call failed entirely (timeout, connection error, etc.)
            profile = {
                "summary": resume_text[:500] if resume_text else "",
                "detailed_projects": [],
                "skills_by_category": {},
                "key_achievements": [],
                "interview_stories": [],
            }

        return self._ensure_defaults(profile)

    def _fallback_from_parsed(self, parsed_resume: dict) -> dict:
        """Create basic expanded profile from parsed data without LLM."""
        projects = []
        for exp in parsed_resume.get("experience", []):
            if isinstance(exp, dict):
                projects.append({
                    "title": exp.get("title", "") or exp.get("company", ""),
                    "description": exp.get("description", ""),
                    "role": exp.get("title", ""),
                    "technologies": [],
                    "impact": "",
                    "star_stories": [],
                })

        return {
            "summary": parsed_resume.get("summary", ""),
            "detailed_projects": projects,
            "skills_by_category": parsed_resume.get("skills", {}),
            "key_achievements": [],
            "interview_stories": [],
        }

    def _ensure_defaults(self, profile: dict) -> dict:
        """Ensure all expected keys exist with correct types."""
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
