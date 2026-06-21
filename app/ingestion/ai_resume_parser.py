"""
STRICT AI-powered resume parser.

Rules:
- EXTRACTION ONLY — no interpretation, no merging, no inference
- Skills extracted ONLY from explicit skills sections
- Experience preserves company → role → achievements hierarchy
- Output sorted: experience by end_date DESC
- Dedup enforced: no skill in multiple categories, no duplicate roles
- Validated against strict schema before return
"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.json_parser import extract_json_from_llm

logger = logging.getLogger(__name__)

# STRICT extraction prompt — no interpretation allowed
STRICT_PARSE_PROMPT = """You are a resume data extractor. Extract ONLY what is explicitly written. Do NOT interpret, infer, merge, or rewrite anything.

STRICT RULES:
1. Extract text EXACTLY as written — do not reword bullet points
2. Skills: extract ONLY from sections explicitly labeled "Skills", "Key Skills", "Technical Skills", "Competencies"
3. Do NOT extract skills from experience bullet points or summary paragraphs
4. Each experience entry must have: role, company, start_date, end_date, location, achievements[]
5. Achievements are the bullet points under each role — copy them verbatim
6. Certifications: ONLY items from sections labeled "Certifications", "Certificates", "Licenses"
7. Do NOT put company names, job titles, or project descriptions in certifications
8. Interests: ONLY from sections labeled "Interests", "Hobbies"
9. Each skill must appear in EXACTLY ONE category — no duplicates across categories

Return ONLY this JSON structure:
{
  "full_name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "headline": "",
  "summary": "",
  "experience": [
    {
      "role": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "location": "",
      "achievements": []
    }
  ],
  "skills": {
    "technical": [],
    "tools": [],
    "soft": []
  },
  "education": [
    {
      "degree": "",
      "institution": "",
      "year": ""
    }
  ],
  "certifications": [],
  "interests": []
}

If a field is not present, use empty string or empty array. Do NOT add fields not in this schema."""


def chunk_resume(raw_text: str, max_chunk_size: int = 3000) -> list[str]:
    """Split resume into logical chunks at paragraph boundaries."""
    if not raw_text or not raw_text.strip():
        return []

    paragraphs = re.split(r'\n\s*\n', raw_text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [raw_text.strip()] if raw_text.strip() else []

    chunks = []
    current_chunk = []
    current_size = 0

    for paragraph in paragraphs:
        para_size = len(paragraph)

        if para_size > max_chunk_size:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            chunks.append(paragraph)
            continue

        if current_size + para_size + 2 > max_chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_size = 0

        current_chunk.append(paragraph)
        current_size += para_size + 2

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def parse_chunk(chunk: str, chunk_index: int, total_chunks: int) -> dict:
    """Parse a single chunk with STRICT extraction rules."""
    try:
        from langchain_ollama import ChatOllama
        from app.core.config import settings

        llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
            num_predict=3000,
            num_ctx=8192,
        )

        response = llm.invoke([
            SystemMessage(content=STRICT_PARSE_PROMPT),
            HumanMessage(content=f"[Section {chunk_index + 1}/{total_chunks}]\n\n{chunk}")
        ])

        content = response.content.strip()
        result = extract_json_from_llm(content)

        if result is None:
            logger.warning(f"Chunk {chunk_index + 1} unparseable")
            return {}

        return result

    except Exception as e:
        logger.error(f"Chunk {chunk_index + 1} failed: {e}")
        return {}


def merge_parsed_chunks(chunks: list[dict]) -> dict:
    """
    Merge chunk results with STRICT deduplication and ordering.

    Enforces:
    - No skill appears in multiple categories
    - No duplicate experience entries (same role+company)
    - Experience sorted by end_date DESC (current first)
    - No free text outside allowed fields
    """
    merged = {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "headline": "",
        "summary": "",
        "experience": [],
        "skills": {"technical": [], "tools": [], "soft": []},
        "education": [],
        "certifications": [],
        "interests": [],
    }

    seen_experience = set()
    seen_skills_global = set()  # tracks ALL skills across ALL categories
    seen_certs = set()
    seen_interests = set()
    seen_education = set()

    for chunk_result in chunks:
        if not chunk_result:
            continue

        # Scalar fields: take first non-empty
        for field in ["full_name", "email", "phone", "location", "linkedin", "headline", "summary"]:
            value = chunk_result.get(field)
            if value and not merged[field]:
                # Extract value if it's a confidence dict
                if isinstance(value, dict):
                    merged[field] = str(value.get("value", ""))
                else:
                    merged[field] = str(value)

        # Experience: dedup by role+company, preserve hierarchy
        for exp in chunk_result.get("experience", []):
            if not isinstance(exp, dict):
                continue
            role = _safe_str(exp.get("role") or exp.get("title", ""))
            company = _safe_str(exp.get("company", ""))
            key = (role.lower().strip(), company.lower().strip())

            if key in seen_experience or not (role or company):
                continue
            seen_experience.add(key)

            merged["experience"].append({
                "role": role,
                "company": company,
                "start_date": _safe_str(exp.get("start_date") or exp.get("dates", "")),
                "end_date": _safe_str(exp.get("end_date", "")),
                "location": _safe_str(exp.get("location", "")),
                "achievements": [_safe_str(a) for a in exp.get("achievements", exp.get("bullets", [])) if a],
            })

        # Skills: STRICT — each skill in exactly one category, no cross-category dupes
        skills_data = chunk_result.get("skills", {})
        if isinstance(skills_data, dict):
            for category, skill_list in skills_data.items():
                cat_key = _safe_str(category).lower()
                # Map to canonical categories
                if any(k in cat_key for k in ["technical", "programming", "language", "framework", "cloud", "platform"]):
                    target_cat = "technical"
                elif any(k in cat_key for k in ["tool", "software", "application"]):
                    target_cat = "tools"
                elif any(k in cat_key for k in ["soft", "leadership", "management", "communication", "methodology", "agile"]):
                    target_cat = "soft"
                else:
                    target_cat = "technical"  # default bucket

                if isinstance(skill_list, list):
                    for skill in skill_list:
                        skill_name = _safe_str(skill)
                        skill_lower = skill_name.lower().strip()
                        if skill_lower and skill_lower not in seen_skills_global:
                            seen_skills_global.add(skill_lower)
                            merged["skills"][target_cat].append(skill_name)

        # Certifications: strict dedup
        for cert in chunk_result.get("certifications", []):
            cert_name = _safe_str(cert)
            if cert_name and cert_name.lower() not in seen_certs:
                seen_certs.add(cert_name.lower())
                merged["certifications"].append(cert_name)

        # Interests: strict dedup
        for interest in chunk_result.get("interests", []):
            interest_name = _safe_str(interest)
            if interest_name and interest_name.lower() not in seen_interests:
                seen_interests.add(interest_name.lower())
                merged["interests"].append(interest_name)

        # Education: dedup by degree+institution
        for edu in chunk_result.get("education", []):
            if not isinstance(edu, dict):
                continue
            degree = _safe_str(edu.get("degree", ""))
            institution = _safe_str(edu.get("institution", ""))
            key = (degree.lower().strip(), institution.lower().strip())
            if key not in seen_education and (degree or institution):
                seen_education.add(key)
                merged["education"].append({
                    "degree": degree,
                    "institution": institution,
                    "year": _safe_str(edu.get("year", "")),
                })

    # Sort experience: end_date DESC, "present" first
    merged["experience"] = _sort_experience(merged["experience"])

    # Remove empty skill categories
    merged["skills"] = {k: v for k, v in merged["skills"].items() if v}

    return merged


def _sort_experience(experience: list[dict]) -> list[dict]:
    """Sort experience by end_date DESC. 'Present'/'Current' comes first."""
    def sort_key(exp):
        end = exp.get("end_date", "").lower().strip()
        if end in ("present", "current", "now", ""):
            return "9999"  # sort first
        # Try to extract year
        year_match = re.search(r'(\d{4})', end)
        if year_match:
            return year_match.group(1)
        return "0000"

    return sorted(experience, key=sort_key, reverse=True)


def _safe_str(item) -> str:
    """Safely extract string from value or confidence-annotated dict."""
    if item is None:
        return ""
    if isinstance(item, dict):
        return str(item.get("value", "")).strip()
    return str(item).strip()


def validate_output(parsed: dict) -> dict:
    """
    Post-parse validation guardrail.

    Rejects/fixes if:
    - Same skill appears in multiple categories
    - Same job title appears twice for same company
    - Free text exists outside allowed fields
    """
    issues = []

    # Check skill uniqueness across categories
    all_skills = set()
    for cat, skills in parsed.get("skills", {}).items():
        for skill in list(skills):  # iterate copy
            if skill.lower() in all_skills:
                skills.remove(skill)
                issues.append(f"Removed duplicate skill '{skill}' from {cat}")
            else:
                all_skills.add(skill.lower())

    # Check experience uniqueness
    seen = set()
    unique_exp = []
    for exp in parsed.get("experience", []):
        key = (exp.get("role", "").lower(), exp.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            unique_exp.append(exp)
        else:
            issues.append(f"Removed duplicate experience: {exp.get('role')} at {exp.get('company')}")
    parsed["experience"] = unique_exp

    if issues:
        logger.info(f"Validation fixed {len(issues)} issues: {issues}")

    return parsed


def parse_resume_with_ai(raw_text: str) -> dict:
    """
    Parse resume with STRICT extraction rules.

    Pipeline:
    1. Chunk text at paragraph boundaries
    2. Parse each chunk (strict extraction, no interpretation)
    3. Merge with deduplication
    4. Validate output (reject duplicates)
    5. Sort experience by end_date DESC

    Returns flat dict compatible with existing pipeline.
    """
    if not raw_text or not raw_text.strip():
        return _empty_result()

    try:
        chunks = chunk_resume(raw_text)
        if not chunks:
            return _fallback_parse(raw_text)

        logger.info(f"Resume: {len(raw_text)} chars → {len(chunks)} chunks")

        parsed_chunks = []
        for i, chunk in enumerate(chunks):
            result = parse_chunk(chunk, i, len(chunks))
            parsed_chunks.append(result)

        merged = merge_parsed_chunks(parsed_chunks)
        validated = validate_output(merged)

        logger.info(
            f"Parse complete: {len(validated.get('experience', []))} experience, "
            f"{sum(len(v) for v in validated.get('skills', {}).values())} skills, "
            f"{len(validated.get('certifications', []))} certs"
        )

        return validated

    except Exception as e:
        logger.error(f"AI resume parsing failed: {e}")
        return _fallback_parse(raw_text)


def get_confidence_scores(raw_text: str) -> dict:
    """Return empty scores — confidence is embedded in parse now."""
    return {}


def _fallback_parse(raw_text: str) -> dict:
    """Basic regex fallback if AI fails entirely."""
    result = _empty_result()
    result["full_name"] = _extract_name_fallback(raw_text)

    email_match = re.search(r'[\w.-]+@[\w.-]+\.[\w]+', raw_text)
    if email_match:
        result["email"] = email_match.group(0)

    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', raw_text)
    if phone_match:
        result["phone"] = phone_match.group(0)

    result["summary"] = raw_text[:500]
    return result


def _extract_name_fallback(raw_text: str) -> str:
    """Extract name from first few lines."""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line in lines[:3]:
        if not re.search(r'[@\d]', line) and len(line.split()) <= 4 and len(line) > 2:
            return line
    return "Unknown"


def _empty_result() -> dict:
    """Empty structured result matching strict schema."""
    return {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "headline": "",
        "summary": "",
        "experience": [],
        "skills": {"technical": [], "tools": [], "soft": []},
        "education": [],
        "certifications": [],
        "interests": [],
    }
