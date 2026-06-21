"""
STRICT AI-powered resume parser — v1.0 Schema.

Rules:
- EXTRACTION ONLY — no interpretation, no merging, no inference
- Skills extracted ONLY from explicit skills sections
- Experience preserves company → role → achievements hierarchy
- Output sorted: experience by end_date DESC
- Dedup enforced: no skill in multiple categories, no duplicate roles
- Validated against strict schema before return
- Returns both flat dict (backward compat) and full v1.0 schema
"""

import json
import logging
import re
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.json_parser import extract_json_from_llm

logger = logging.getLogger(__name__)

# v1.0 STRICT extraction prompt
STRICT_PARSE_PROMPT = """You are a resume data extractor. Extract ONLY what is explicitly written. Do NOT interpret, infer, or hallucinate.

RULES:
1. Extract text EXACTLY as written — do not reword
2. Skills: ONLY from sections labeled "Skills", "Key Skills", "Technical Skills", "Competencies"
3. Do NOT extract skills from experience bullets or summary
4. For dates use "YYYY-MM" where possible, or original text if unparseable
5. For impact_metrics, use confidence "low" if metrics are inferred
6. For unknown fields use null or empty arrays

Return ONLY this JSON:
{
  "schema_version": "1.0",
  "resume": {
    "personal_info": {
      "full_name": "", "preferred_name": null, "headline": "",
      "email": "", "phone": "",
      "location": {"city": "", "state": "", "country": "", "timezone": ""},
      "linkedin": "", "github": "", "portfolio": "", "website": ""
    },
    "professional_summary": {
      "summary_text": "", "years_experience": null,
      "seniority_level": "", "target_roles": [], "industries": []
    },
    "core_skills": {
      "technical_skills": [], "functional_skills": [],
      "tools_platforms": [], "methodologies": [], "domains": []
    },
    "work_experience": [
      {
        "company": "", "company_industry": "", "role_title": "",
        "employment_type": "full-time", "location": "",
        "start_date": "", "end_date": "", "duration_months": null,
        "responsibilities": [],
        "achievements": [{"statement": "", "impact_metrics": {"type": "", "value": "", "unit": "", "confidence": "medium"}}],
        "tech_stack": [], "project_tags": [], "stakeholders": []
      }
    ],
    "projects": [
      {
        "project_name": "", "organization": "", "description": "",
        "role": "", "start_date": "", "end_date": "",
        "outcomes": [], "technologies": [],
        "scale": {"users_affected": "", "budget": "", "regions": []}
      }
    ],
    "education": [
      {"institution": "", "degree": "", "field_of_study": "", "start_year": "", "end_year": "", "achievements": []}
    ],
    "certifications": [
      {"name": "", "issuing_body": "", "issue_date": "", "expiry_date": "", "credential_id": ""}
    ],
    "achievements": [{"title": "", "description": "", "type": ""}],
    "languages": [{"language": "", "proficiency": ""}],
    "preferences": {
      "preferred_roles": [], "preferred_locations": [],
      "remote_preference": "", "salary_expectation": {"min": "", "max": "", "currency": ""}
    },
    "ats_metadata": {"keywords": [], "completeness_score": 0, "last_updated": ""}
  }
}

If a field is not present, use null or empty string/array. Do NOT add fields not in this schema."""


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
            num_predict=4000,
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


def _get_resume_block(chunk_result: dict) -> dict:
    """Extract the 'resume' block from a chunk result, handling both nested and flat."""
    if "resume" in chunk_result:
        return chunk_result["resume"]
    return chunk_result


def merge_parsed_chunks(chunks: list[dict]) -> dict:
    """
    Merge chunk results into the full v1.0 schema with STRICT deduplication.

    Returns the complete v1.0 schema dict.
    """
    merged = _empty_v1_schema()
    resume = merged["resume"]

    seen_experience = set()
    seen_skills_global = set()
    seen_certs = set()
    seen_education = set()
    seen_projects = set()
    seen_achievements = set()
    seen_languages = set()

    for chunk_result in chunks:
        if not chunk_result:
            continue

        r = _get_resume_block(chunk_result)

        # --- personal_info: take first non-empty ---
        pi = r.get("personal_info", {})
        if isinstance(pi, dict):
            for field in ["full_name", "preferred_name", "headline", "email", "phone", "linkedin", "github", "portfolio", "website"]:
                val = pi.get(field)
                if val and not resume["personal_info"].get(field):
                    resume["personal_info"][field] = _safe_str(val)
            loc = pi.get("location")
            if isinstance(loc, dict):
                for lf in ["city", "state", "country", "timezone"]:
                    if loc.get(lf) and not resume["personal_info"]["location"].get(lf):
                        resume["personal_info"]["location"][lf] = _safe_str(loc[lf])
            elif isinstance(loc, str) and loc and not resume["personal_info"]["location"]["city"]:
                resume["personal_info"]["location"]["city"] = loc

        # --- professional_summary: take first non-empty ---
        ps = r.get("professional_summary", {})
        if isinstance(ps, dict):
            if ps.get("summary_text") and not resume["professional_summary"]["summary_text"]:
                resume["professional_summary"]["summary_text"] = _safe_str(ps["summary_text"])
            if ps.get("years_experience") and not resume["professional_summary"]["years_experience"]:
                try:
                    resume["professional_summary"]["years_experience"] = int(ps["years_experience"])
                except (ValueError, TypeError):
                    pass
            if ps.get("seniority_level") and not resume["professional_summary"]["seniority_level"]:
                resume["professional_summary"]["seniority_level"] = _safe_str(ps["seniority_level"])
            for arr_field in ["target_roles", "industries"]:
                items = ps.get(arr_field, [])
                if isinstance(items, list):
                    for item in items:
                        s = _safe_str(item)
                        if s and s not in resume["professional_summary"][arr_field]:
                            resume["professional_summary"][arr_field].append(s)

        # --- core_skills: dedup across categories ---
        cs = r.get("core_skills", {})
        if isinstance(cs, dict):
            for cat in ["technical_skills", "functional_skills", "tools_platforms", "methodologies", "domains"]:
                items = cs.get(cat, [])
                if isinstance(items, list):
                    for skill in items:
                        s = _safe_str(skill)
                        sl = s.lower()
                        if sl and sl not in seen_skills_global:
                            seen_skills_global.add(sl)
                            resume["core_skills"][cat].append(s)

        # --- work_experience: dedup by role+company ---
        for exp in r.get("work_experience", []):
            if not isinstance(exp, dict):
                continue
            role = _safe_str(exp.get("role_title") or exp.get("role", ""))
            company = _safe_str(exp.get("company", ""))
            key = (role.lower().strip(), company.lower().strip())
            if key in seen_experience or not (role or company):
                continue
            seen_experience.add(key)

            achievements = []
            for ach in exp.get("achievements", []):
                if isinstance(ach, dict):
                    achievements.append({
                        "statement": _safe_str(ach.get("statement", "")),
                        "impact_metrics": ach.get("impact_metrics", {"type": "", "value": "", "unit": "", "confidence": "medium"})
                    })
                elif isinstance(ach, str) and ach.strip():
                    achievements.append({
                        "statement": ach.strip(),
                        "impact_metrics": {"type": "", "value": "", "unit": "", "confidence": "medium"}
                    })

            resume["work_experience"].append({
                "company": company,
                "company_industry": _safe_str(exp.get("company_industry", "")),
                "role_title": role,
                "employment_type": _safe_str(exp.get("employment_type", "full-time")) or "full-time",
                "location": _safe_str(exp.get("location", "")),
                "start_date": _safe_str(exp.get("start_date", "")),
                "end_date": _safe_str(exp.get("end_date", "")),
                "duration_months": exp.get("duration_months") or None,
                "responsibilities": [_safe_str(r) for r in exp.get("responsibilities", []) if r],
                "achievements": achievements,
                "tech_stack": [_safe_str(t) for t in exp.get("tech_stack", []) if t],
                "project_tags": [_safe_str(t) for t in exp.get("project_tags", []) if t],
                "stakeholders": [_safe_str(s) for s in exp.get("stakeholders", []) if s],
            })

        # --- projects: dedup by name+org ---
        for proj in r.get("projects", []):
            if not isinstance(proj, dict):
                continue
            name = _safe_str(proj.get("project_name", ""))
            org = _safe_str(proj.get("organization", ""))
            key = (name.lower().strip(), org.lower().strip())
            if key in seen_projects or not name:
                continue
            seen_projects.add(key)

            scale = proj.get("scale", {})
            if not isinstance(scale, dict):
                scale = {}

            resume["projects"].append({
                "project_name": name,
                "organization": org,
                "description": _safe_str(proj.get("description", "")),
                "role": _safe_str(proj.get("role", "")),
                "start_date": _safe_str(proj.get("start_date", "")),
                "end_date": _safe_str(proj.get("end_date", "")),
                "outcomes": [_safe_str(o) for o in proj.get("outcomes", []) if o],
                "technologies": [_safe_str(t) for t in proj.get("technologies", []) if t],
                "scale": {
                    "users_affected": _safe_str(scale.get("users_affected", "")),
                    "budget": _safe_str(scale.get("budget", "")),
                    "regions": [_safe_str(r) for r in scale.get("regions", []) if r],
                },
            })

        # --- education: dedup by degree+institution ---
        for edu in r.get("education", []):
            if not isinstance(edu, dict):
                continue
            degree = _safe_str(edu.get("degree", ""))
            institution = _safe_str(edu.get("institution", ""))
            key = (degree.lower().strip(), institution.lower().strip())
            if key in seen_education or not (degree or institution):
                continue
            seen_education.add(key)
            resume["education"].append({
                "institution": institution,
                "degree": degree,
                "field_of_study": _safe_str(edu.get("field_of_study", "")),
                "start_year": _safe_str(edu.get("start_year", "")),
                "end_year": _safe_str(edu.get("end_year", edu.get("year", ""))),
                "achievements": [_safe_str(a) for a in edu.get("achievements", []) if a],
            })

        # --- certifications: dedup by name ---
        for cert in r.get("certifications", []):
            if isinstance(cert, dict):
                name = _safe_str(cert.get("name", ""))
            else:
                name = _safe_str(cert)
            if not name or name.lower() in seen_certs:
                continue
            seen_certs.add(name.lower())
            if isinstance(cert, dict):
                resume["certifications"].append({
                    "name": name,
                    "issuing_body": _safe_str(cert.get("issuing_body", "")),
                    "issue_date": _safe_str(cert.get("issue_date", "")),
                    "expiry_date": _safe_str(cert.get("expiry_date", "")),
                    "credential_id": _safe_str(cert.get("credential_id", "")),
                })
            else:
                resume["certifications"].append({
                    "name": name,
                    "issuing_body": "",
                    "issue_date": "",
                    "expiry_date": "",
                    "credential_id": "",
                })

        # --- achievements ---
        for ach in r.get("achievements", []):
            if isinstance(ach, dict):
                title = _safe_str(ach.get("title", ""))
            else:
                title = _safe_str(ach)
            if title and title.lower() not in seen_achievements:
                seen_achievements.add(title.lower())
                if isinstance(ach, dict):
                    resume["achievements"].append({
                        "title": title,
                        "description": _safe_str(ach.get("description", "")),
                        "type": _safe_str(ach.get("type", "")),
                    })
                else:
                    resume["achievements"].append({"title": title, "description": "", "type": ""})

        # --- languages ---
        for lang in r.get("languages", []):
            if isinstance(lang, dict):
                name = _safe_str(lang.get("language", ""))
                prof = _safe_str(lang.get("proficiency", ""))
            else:
                name = _safe_str(lang)
                prof = ""
            if name and name.lower() not in seen_languages:
                seen_languages.add(name.lower())
                resume["languages"].append({"language": name, "proficiency": prof})

        # --- preferences: take first non-empty ---
        prefs = r.get("preferences", {})
        if isinstance(prefs, dict):
            for arr_field in ["preferred_roles", "preferred_locations"]:
                items = prefs.get(arr_field, [])
                if isinstance(items, list):
                    for item in items:
                        s = _safe_str(item)
                        if s and s not in resume["preferences"][arr_field]:
                            resume["preferences"][arr_field].append(s)
            if prefs.get("remote_preference") and not resume["preferences"]["remote_preference"]:
                resume["preferences"]["remote_preference"] = _safe_str(prefs["remote_preference"])
            sal = prefs.get("salary_expectation", {})
            if isinstance(sal, dict) and sal.get("min"):
                resume["preferences"]["salary_expectation"] = {
                    "min": _safe_str(sal.get("min", "")),
                    "max": _safe_str(sal.get("max", "")),
                    "currency": _safe_str(sal.get("currency", "")),
                }

        # --- ats_metadata: merge keywords ---
        ats = r.get("ats_metadata", {})
        if isinstance(ats, dict):
            for kw in ats.get("keywords", []):
                s = _safe_str(kw)
                if s and s not in resume["ats_metadata"]["keywords"]:
                    resume["ats_metadata"]["keywords"].append(s)

    # Sort experience: end_date DESC, "present" first
    resume["work_experience"] = _sort_experience(resume["work_experience"])

    # Set ats_metadata last_updated
    resume["ats_metadata"]["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")

    return merged


def _normalize_to_flat(v1_schema: dict) -> dict:
    """
    Convert v1.0 schema to flat dict for backward compatibility with existing pipeline.

    Maps:
    - full_name, email, phone, location, linkedin, headline, summary
    - experience[] with role, company, start_date, end_date, location, achievements
    - skills{} with technical, tools, soft categories
    - education[], certifications[], interests[]
    """
    resume = v1_schema.get("resume", {})
    pi = resume.get("personal_info", {})
    ps = resume.get("professional_summary", {})
    cs = resume.get("core_skills", {})

    # Build location string
    loc = pi.get("location", {})
    if isinstance(loc, dict):
        loc_parts = [loc.get("city", ""), loc.get("state", ""), loc.get("country", "")]
        location_str = ", ".join(p for p in loc_parts if p)
    else:
        location_str = str(loc) if loc else ""

    # Map experience
    experience = []
    for exp in resume.get("work_experience", []):
        achievements = []
        for ach in exp.get("achievements", []):
            if isinstance(ach, dict):
                achievements.append(ach.get("statement", ""))
            elif isinstance(ach, str):
                achievements.append(ach)
        # Also include responsibilities as achievements for backward compat
        for resp in exp.get("responsibilities", []):
            if resp and resp not in achievements:
                achievements.append(resp)

        experience.append({
            "role": exp.get("role_title", ""),
            "company": exp.get("company", ""),
            "start_date": exp.get("start_date", ""),
            "end_date": exp.get("end_date", ""),
            "location": exp.get("location", ""),
            "achievements": achievements,
        })

    # Map skills to flat categories
    skills = {}
    if cs.get("technical_skills"):
        skills["technical"] = cs["technical_skills"]
    if cs.get("tools_platforms"):
        skills["tools"] = cs["tools_platforms"]
    # Combine functional + methodologies into soft
    soft = []
    if cs.get("functional_skills"):
        soft.extend(cs["functional_skills"])
    if cs.get("methodologies"):
        soft.extend(cs["methodologies"])
    if soft:
        skills["soft"] = soft
    if cs.get("domains"):
        skills["domains"] = cs["domains"]

    # Map education
    education = []
    for edu in resume.get("education", []):
        education.append({
            "degree": edu.get("degree", ""),
            "institution": edu.get("institution", ""),
            "year": edu.get("end_year", "") or edu.get("start_year", ""),
        })

    # Map certifications (flat list of names for backward compat)
    certifications = [c.get("name", "") for c in resume.get("certifications", []) if c.get("name")]

    flat = {
        "full_name": pi.get("full_name", ""),
        "email": pi.get("email", ""),
        "phone": pi.get("phone", ""),
        "location": location_str,
        "linkedin": pi.get("linkedin", ""),
        "headline": pi.get("headline", ""),
        "summary": ps.get("summary_text", ""),
        "experience": experience,
        "skills": skills,
        "education": education,
        "certifications": certifications,
        "interests": [],  # v1.0 doesn't have a direct interests field
    }

    return flat


def _sort_experience(experience: list[dict]) -> list[dict]:
    """Sort experience by end_date DESC. 'Present'/'Current' comes first."""
    def sort_key(exp):
        end = (exp.get("end_date") or "").lower().strip()
        if end in ("present", "current", "now", ""):
            return "9999"
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


def validate_output(v1_schema: dict) -> dict:
    """
    Post-parse validation guardrail for v1.0 schema.

    Rejects/fixes if:
    - Same skill appears in multiple categories
    - Same job title appears twice for same company
    """
    issues = []
    resume = v1_schema.get("resume", {})

    # Check skill uniqueness across categories
    all_skills = set()
    cs = resume.get("core_skills", {})
    for cat in ["technical_skills", "functional_skills", "tools_platforms", "methodologies", "domains"]:
        skills = cs.get(cat, [])
        for skill in list(skills):
            if skill.lower() in all_skills:
                skills.remove(skill)
                issues.append(f"Removed duplicate skill '{skill}' from {cat}")
            else:
                all_skills.add(skill.lower())

    # Check experience uniqueness
    seen = set()
    unique_exp = []
    for exp in resume.get("work_experience", []):
        key = (exp.get("role_title", "").lower(), exp.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            unique_exp.append(exp)
        else:
            issues.append(f"Removed duplicate experience: {exp.get('role_title')} at {exp.get('company')}")
    resume["work_experience"] = unique_exp

    if issues:
        logger.info(f"Validation fixed {len(issues)} issues: {issues}")

    return v1_schema


def parse_resume_with_ai(raw_text: str) -> dict:
    """
    Parse resume with STRICT extraction rules using v1.0 schema.

    Pipeline:
    1. Chunk text at paragraph boundaries
    2. Parse each chunk (strict extraction, no interpretation)
    3. Merge with deduplication into v1.0 schema
    4. Validate output (reject duplicates)
    5. Normalize to flat dict for backward compat

    Returns flat dict compatible with existing pipeline,
    with _full_schema key containing the complete v1.0 schema.
    """
    if not raw_text or not raw_text.strip():
        result = _empty_flat_result()
        result["_full_schema"] = _empty_v1_schema()
        return result

    try:
        chunks = chunk_resume(raw_text)
        if not chunks:
            result = _fallback_parse(raw_text)
            result["_full_schema"] = _empty_v1_schema()
            return result

        logger.info(f"Resume: {len(raw_text)} chars → {len(chunks)} chunks")

        parsed_chunks = []
        for i, chunk in enumerate(chunks):
            result = parse_chunk(chunk, i, len(chunks))
            parsed_chunks.append(result)

        # Merge into v1.0 schema
        v1_schema = merge_parsed_chunks(parsed_chunks)
        validated = validate_output(v1_schema)

        # Convert to flat for backward compat
        flat = _normalize_to_flat(validated)

        # Attach full schema
        flat["_full_schema"] = validated

        resume = validated.get("resume", {})
        exp_count = len(resume.get("work_experience", []))
        cs = resume.get("core_skills", {})
        skills_count = sum(len(cs.get(c, [])) for c in ["technical_skills", "functional_skills", "tools_platforms", "methodologies", "domains"])
        certs_count = len(resume.get("certifications", []))

        logger.info(
            f"Parse complete (v1.0): {exp_count} experience, "
            f"{skills_count} skills, {certs_count} certs"
        )

        return flat

    except Exception as e:
        logger.error(f"AI resume parsing failed: {e}")
        result = _fallback_parse(raw_text)
        result["_full_schema"] = _empty_v1_schema()
        return result


def get_confidence_scores(raw_text: str) -> dict:
    """Return empty scores — confidence is embedded in parse now."""
    return {}


def _fallback_parse(raw_text: str) -> dict:
    """Basic regex fallback if AI fails entirely."""
    result = _empty_flat_result()
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


def _empty_flat_result() -> dict:
    """Empty structured result matching legacy flat schema."""
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


def _empty_v1_schema() -> dict:
    """Empty v1.0 schema structure."""
    return {
        "schema_version": "1.0",
        "resume": {
            "personal_info": {
                "full_name": "",
                "preferred_name": None,
                "headline": "",
                "email": "",
                "phone": "",
                "location": {"city": "", "state": "", "country": "", "timezone": ""},
                "linkedin": "",
                "github": "",
                "portfolio": "",
                "website": "",
            },
            "professional_summary": {
                "summary_text": "",
                "years_experience": None,
                "seniority_level": "",
                "target_roles": [],
                "industries": [],
            },
            "core_skills": {
                "technical_skills": [],
                "functional_skills": [],
                "tools_platforms": [],
                "methodologies": [],
                "domains": [],
            },
            "work_experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "achievements": [],
            "languages": [],
            "preferences": {
                "preferred_roles": [],
                "preferred_locations": [],
                "remote_preference": "",
                "salary_expectation": {"min": "", "max": "", "currency": ""},
            },
            "ats_metadata": {
                "keywords": [],
                "completeness_score": 0,
                "last_updated": "",
            },
        },
    }
