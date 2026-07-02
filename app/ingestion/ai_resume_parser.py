"""
Two-pass resume parser with progress logging.

Pass 1 (FAST): Extract raw data using qwen3.5 (fast model)
Pass 2 (OPTIONAL): Rewrite/enrich using gemma4 (high-quality model)

Includes real-time chunk progress logging and request timing.
"""

import json
import logging
import re
import time
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.json_parser import extract_json_from_llm

logger = logging.getLogger(__name__)

# ─── PASS 1 PROMPT: Fast extraction ──────────────────────────────────────────
EXTRACT_PROMPT = """You are a resume data extractor. Output ONLY raw JSON — no markdown, no code blocks, no explanation.

IMPORTANT: The resume text may contain a "--- RIGHT COLUMN ---" marker. This means the resume has a two-column layout:
- Content BEFORE the marker = left column (usually projects, work experience, career history)
- Content AFTER the marker = right column (usually skills, certifications, education, interests, personal details)
Treat both columns as part of the same resume. Extract ALL sections from BOTH columns.

Schema:
{"schema_version":"1.0","resume":{"personal_info":{"full_name":"","preferred_name":null,"headline":"","email":"","phone":"","location":{"city":"","state":"","country":""},"linkedin":"","github":""},"professional_summary":{"summary_text":"","years_experience":null,"seniority_level":"","industries":[]},"core_skills":{"technical_skills":[],"functional_skills":[],"tools_platforms":[],"methodologies":[],"domains":[]},"work_experience":[{"company":"","role_title":"","employment_type":"full-time","location":"","start_date":"","end_date":"","responsibilities":[],"achievements":[{"statement":"","impact_metrics":{"type":"","value":"","unit":""}}],"tech_stack":[]}],"projects":[{"project_name":"","description":"","role":"","technologies":[],"outcomes":[]}],"education":[{"institution":"","degree":"","field_of_study":"","end_year":""}],"certifications":[{"name":"","issuing_body":""}],"languages":[{"language":"","proficiency":""}],"ats_metadata":{"keywords":[]}}}

Rules:
- Output ONLY the JSON object starting with { and ending with }
- Do NOT wrap in ```json blocks
- Do NOT add any text before or after the JSON
- Extract ALL data from BOTH columns (before AND after the --- RIGHT COLUMN --- marker)
- Skills found in the right column go into core_skills (categorize: technical_skills, functional_skills, tools_platforms, methodologies, domains)
- Certifications in the right column go into certifications[]
- Interests/hobbies in the right column: ignore (not in schema)
- Use null/empty for missing fields
- /no_think"""


def chunk_resume(raw_text: str, max_chunk_size: int = 4000) -> list[str]:
    """Split resume into chunks at paragraph boundaries."""
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
            chunks.append(paragraph[:max_chunk_size])
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


def parse_chunk_fast(chunk: str, chunk_index: int, total_chunks: int, model: str | None = None, api_key: str | None = None) -> dict:
    """Parse a single chunk using the specified model (or default FAST model) with timing and debug output."""
    start = time.time()
    logger.info(f"⏳ Chunk {chunk_index + 1}/{total_chunks}: Starting parse ({len(chunk)} chars)...")

    try:
        from app.core.config import settings

        # Determine which LLM to use based on model parameter
        if model and model.startswith("openai:") and api_key:
            from langchain_openai import ChatOpenAI
            model_name = model.split(":", 1)[1]
            llm = ChatOpenAI(model=model_name, api_key=api_key, temperature=0)
        elif model and model.startswith("anthropic:") and api_key:
            from langchain_anthropic import ChatAnthropic
            model_name = model.split(":", 1)[1]
            llm = ChatAnthropic(model=model_name, api_key=api_key, temperature=0)
        else:
            # Default: local Ollama
            from langchain_ollama import ChatOllama
            ollama_model = model.split(":", 1)[1] if model and model.startswith("ollama:") else settings.OLLAMA_MODEL
            llm = ChatOllama(
                model=ollama_model,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0,
                num_predict=16000,
                num_ctx=32768,
            )

        response = llm.invoke([
            SystemMessage(content=EXTRACT_PROMPT),
            HumanMessage(content=chunk)
        ])

        elapsed = time.time() - start
        content = response.content.strip()

        # DEBUG: Print raw LLM output
        logger.info(f"📝 Chunk {chunk_index + 1} RAW OUTPUT ({len(content)} chars):")
        logger.info(f"   First 200: {content[:200]}")
        logger.info(f"   Last 100: {content[-100:]}")

        result = extract_json_from_llm(content)

        if result is None:
            # EXTRA DEBUG: Write full response to file for inspection
            debug_file = f"/tmp/chunk_{chunk_index + 1}_response.txt"
            with open(debug_file, "w") as f:
                f.write(content)
            logger.warning(f"⚠️  Chunk {chunk_index + 1}/{total_chunks}: Unparseable ({elapsed:.1f}s) — saved to {debug_file}")
            return {}

        logger.info(f"✓  Chunk {chunk_index + 1}/{total_chunks}: Parsed in {elapsed:.1f}s")
        return result

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"✗  Chunk {chunk_index + 1}/{total_chunks}: Failed in {elapsed:.1f}s — {e}")
        return {}


def merge_chunks(chunks: list[dict]) -> dict:
    """Merge chunk results into v1.0 schema with strict dedup."""
    merged = _empty_v1_schema()
    resume = merged["resume"]

    seen_exp = set()
    seen_skills = set()
    seen_certs = set()
    seen_edu = set()

    for chunk in chunks:
        if not chunk:
            continue

        r = chunk.get("resume", chunk)  # handle nested or flat

        # Personal info: first non-empty wins
        pi = r.get("personal_info", {})
        if isinstance(pi, dict):
            for f in ["full_name", "preferred_name", "headline", "email", "phone", "linkedin", "github"]:
                val = pi.get(f)
                if val and not resume["personal_info"].get(f):
                    resume["personal_info"][f] = str(val).strip()
            loc = pi.get("location", {})
            if isinstance(loc, dict):
                for lf in ["city", "state", "country"]:
                    if loc.get(lf) and not resume["personal_info"]["location"].get(lf):
                        resume["personal_info"]["location"][lf] = str(loc[lf]).strip()

        # Professional summary
        ps = r.get("professional_summary", {})
        if isinstance(ps, dict):
            if ps.get("summary_text") and not resume["professional_summary"]["summary_text"]:
                resume["professional_summary"]["summary_text"] = str(ps["summary_text"]).strip()
            if ps.get("years_experience"):
                try:
                    resume["professional_summary"]["years_experience"] = int(ps["years_experience"])
                except (ValueError, TypeError):
                    pass
            if ps.get("seniority_level") and not resume["professional_summary"]["seniority_level"]:
                resume["professional_summary"]["seniority_level"] = str(ps["seniority_level"]).strip()
            for item in ps.get("industries", []):
                s = str(item).strip()
                if s and s not in resume["professional_summary"]["industries"]:
                    resume["professional_summary"]["industries"].append(s)

        # Core skills: strict dedup
        cs = r.get("core_skills", {})
        if isinstance(cs, dict):
            for cat in ["technical_skills", "functional_skills", "tools_platforms", "methodologies", "domains"]:
                for skill in cs.get(cat, []):
                    s = str(skill).strip() if skill else ""
                    sl = s.lower()
                    if sl and sl not in seen_skills:
                        seen_skills.add(sl)
                        resume["core_skills"][cat].append(s)

        # Work experience: dedup by role+company
        for exp in r.get("work_experience", []):
            if not isinstance(exp, dict):
                continue
            role = str(exp.get("role_title", "")).strip()
            company = str(exp.get("company", "")).strip()
            key = (role.lower(), company.lower())
            if key in seen_exp or not (role or company):
                continue
            seen_exp.add(key)

            achievements = []
            for ach in exp.get("achievements", []):
                if isinstance(ach, dict) and ach.get("statement"):
                    achievements.append(ach)
                elif isinstance(ach, str) and ach.strip():
                    achievements.append({"statement": ach.strip(), "impact_metrics": {"type": "", "value": "", "unit": ""}})

            resume["work_experience"].append({
                "company": company,
                "company_industry": str(exp.get("company_industry", "")).strip(),
                "role_title": role,
                "employment_type": str(exp.get("employment_type", "full-time")).strip() or "full-time",
                "location": str(exp.get("location", "")).strip(),
                "start_date": str(exp.get("start_date", "")).strip(),
                "end_date": str(exp.get("end_date", "")).strip(),
                "duration_months": exp.get("duration_months"),
                "responsibilities": [str(r).strip() for r in exp.get("responsibilities", []) if r],
                "achievements": achievements,
                "tech_stack": [str(t).strip() for t in exp.get("tech_stack", []) if t],
                "project_tags": [str(t).strip() for t in exp.get("project_tags", []) if t],
                "stakeholders": [str(s).strip() for s in exp.get("stakeholders", []) if s],
            })

        # Projects
        for proj in r.get("projects", []):
            if not isinstance(proj, dict):
                continue
            name = str(proj.get("project_name", "")).strip()
            if name and name.lower() not in {p["project_name"].lower() for p in resume["projects"]}:
                resume["projects"].append({
                    "project_name": name,
                    "organization": str(proj.get("organization", "")).strip(),
                    "description": str(proj.get("description", "")).strip(),
                    "role": str(proj.get("role", "")).strip(),
                    "start_date": str(proj.get("start_date", "")).strip(),
                    "end_date": str(proj.get("end_date", "")).strip(),
                    "outcomes": [str(o).strip() for o in proj.get("outcomes", []) if o],
                    "technologies": [str(t).strip() for t in proj.get("technologies", []) if t],
                    "scale": proj.get("scale", {"users_affected": "", "budget": "", "regions": []}),
                })

        # Education
        for edu in r.get("education", []):
            if not isinstance(edu, dict):
                continue
            degree = str(edu.get("degree", "")).strip()
            inst = str(edu.get("institution", "")).strip()
            key = (degree.lower(), inst.lower())
            if key not in seen_edu and (degree or inst):
                seen_edu.add(key)
                resume["education"].append({
                    "institution": inst,
                    "degree": degree,
                    "field_of_study": str(edu.get("field_of_study", "")).strip(),
                    "start_year": str(edu.get("start_year", "")).strip(),
                    "end_year": str(edu.get("end_year", edu.get("year", ""))).strip(),
                    "achievements": [str(a).strip() for a in edu.get("achievements", []) if a],
                })

        # Certifications
        for cert in r.get("certifications", []):
            name = str(cert.get("name", "") if isinstance(cert, dict) else cert).strip()
            if name and name.lower() not in seen_certs:
                seen_certs.add(name.lower())
                resume["certifications"].append({
                    "name": name,
                    "issuing_body": str(cert.get("issuing_body", "")).strip() if isinstance(cert, dict) else "",
                    "issue_date": str(cert.get("issue_date", "")).strip() if isinstance(cert, dict) else "",
                    "expiry_date": str(cert.get("expiry_date", "")).strip() if isinstance(cert, dict) else "",
                    "credential_id": str(cert.get("credential_id", "")).strip() if isinstance(cert, dict) else "",
                })

        # Languages
        for lang in r.get("languages", []):
            if isinstance(lang, dict) and lang.get("language"):
                name = str(lang["language"]).strip()
                if name.lower() not in {l["language"].lower() for l in resume["languages"]}:
                    resume["languages"].append({"language": name, "proficiency": str(lang.get("proficiency", "")).strip()})

        # ATS keywords
        ats = r.get("ats_metadata", {})
        if isinstance(ats, dict):
            for kw in ats.get("keywords", []):
                s = str(kw).strip()
                if s and s not in resume["ats_metadata"]["keywords"]:
                    resume["ats_metadata"]["keywords"].append(s)

    # Sort experience: end_date DESC
    resume["work_experience"].sort(
        key=lambda x: "9999" if (x.get("end_date", "").lower() in ("present", "current", "now", "")) else (re.search(r'(\d{4})', x.get("end_date", "")) or type('', (), {'group': lambda s, n: "0000"})()).group(1),
        reverse=True
    )

    resume["ats_metadata"]["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
    return merged


def _normalize_to_flat(v1_schema: dict) -> dict:
    """Convert v1.0 schema to flat dict for backward compat."""
    resume = v1_schema.get("resume", {})
    pi = resume.get("personal_info", {})
    ps = resume.get("professional_summary", {})
    cs = resume.get("core_skills", {})

    loc = pi.get("location", {})
    location_str = ", ".join(p for p in [loc.get("city", ""), loc.get("country", "")] if p) if isinstance(loc, dict) else ""

    experience = []
    for exp in resume.get("work_experience", []):
        achievements = [a.get("statement", "") for a in exp.get("achievements", []) if isinstance(a, dict)]
        achievements += exp.get("responsibilities", [])
        experience.append({
            "role": exp.get("role_title", ""),
            "company": exp.get("company", ""),
            "start_date": exp.get("start_date", ""),
            "end_date": exp.get("end_date", ""),
            "location": exp.get("location", ""),
            "achievements": [a for a in achievements if a],
        })

    skills = {}
    if cs.get("technical_skills"):
        skills["technical"] = cs["technical_skills"]
    if cs.get("tools_platforms"):
        skills["tools"] = cs["tools_platforms"]
    soft = (cs.get("functional_skills", []) or []) + (cs.get("methodologies", []) or [])
    if soft:
        skills["soft"] = soft
    if cs.get("domains"):
        skills["domains"] = cs["domains"]

    certifications = [c.get("name", "") for c in resume.get("certifications", []) if c.get("name")]

    return {
        "full_name": pi.get("full_name", ""),
        "email": pi.get("email", ""),
        "phone": pi.get("phone", ""),
        "location": location_str,
        "linkedin": pi.get("linkedin", ""),
        "headline": pi.get("headline", ""),
        "summary": ps.get("summary_text", ""),
        "experience": experience,
        "skills": skills,
        "education": [{"degree": e.get("degree", ""), "institution": e.get("institution", ""), "year": e.get("end_year", "")} for e in resume.get("education", [])],
        "certifications": certifications,
        "interests": [],
    }


def parse_resume_with_ai(raw_text: str, model: str | None = None, api_key: str | None = None) -> dict:
    """
    Two-pass resume parser with progress logging.

    Pass 1 (FAST): Extract raw data from chunks using the specified model (or default qwen3.5)
    Returns flat dict with _full_schema key for v1.0 storage.
    """
    total_start = time.time()

    if not raw_text or not raw_text.strip():
        result = _empty_flat()
        result["_full_schema"] = _empty_v1_schema()
        return result

    try:
        chunks = chunk_resume(raw_text)
        if not chunks:
            result = _fallback_parse(raw_text)
            result["_full_schema"] = _empty_v1_schema()
            return result

        logger.info(f"━━━ RESUME PARSE START ━━━ {len(raw_text)} chars → {len(chunks)} chunks (model={model or 'default'})")

        # Pass 1: Fast extraction
        parsed_chunks = []
        for i, chunk in enumerate(chunks):
            result = parse_chunk_fast(chunk, i, len(chunks), model=model, api_key=api_key)
            parsed_chunks.append(result)

        # Merge
        merge_start = time.time()
        v1_schema = merge_chunks(parsed_chunks)
        logger.info(f"✓  Merge complete in {time.time() - merge_start:.1f}s")

        # Normalize
        flat = _normalize_to_flat(v1_schema)
        flat["_full_schema"] = v1_schema

        total_elapsed = time.time() - total_start
        resume = v1_schema.get("resume", {})
        logger.info(
            f"━━━ PARSE COMPLETE ━━━ {total_elapsed:.1f}s total | "
            f"{len(resume.get('work_experience', []))} exp, "
            f"{sum(len(resume.get('core_skills', {}).get(c, [])) for c in ['technical_skills', 'functional_skills', 'tools_platforms', 'methodologies', 'domains'])} skills, "
            f"{len(resume.get('certifications', []))} certs"
        )

        return flat

    except Exception as e:
        total_elapsed = time.time() - total_start
        logger.error(f"━━━ PARSE FAILED ━━━ {total_elapsed:.1f}s — {e}")
        result = _fallback_parse(raw_text)
        result["_full_schema"] = _empty_v1_schema()
        return result


def get_confidence_scores(raw_text: str) -> dict:
    return {}


def _fallback_parse(raw_text: str) -> dict:
    result = _empty_flat()
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line in lines[:3]:
        if not re.search(r'[@\d]', line) and len(line.split()) <= 4 and len(line) > 2:
            result["full_name"] = line
            break
    email_match = re.search(r'[\w.-]+@[\w.-]+\.[\w]+', raw_text)
    if email_match:
        result["email"] = email_match.group(0)
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', raw_text)
    if phone_match:
        result["phone"] = phone_match.group(0)
    result["summary"] = raw_text[:500]
    return result


def _empty_flat() -> dict:
    return {"full_name": "", "email": "", "phone": "", "location": "", "linkedin": "", "headline": "", "summary": "", "experience": [], "skills": {"technical": [], "tools": [], "soft": []}, "education": [], "certifications": [], "interests": []}


def _empty_v1_schema() -> dict:
    return {"schema_version": "1.0", "resume": {"personal_info": {"full_name": "", "preferred_name": None, "headline": "", "email": "", "phone": "", "location": {"city": "", "state": "", "country": ""}, "linkedin": "", "github": ""}, "professional_summary": {"summary_text": "", "years_experience": None, "seniority_level": "", "industries": []}, "core_skills": {"technical_skills": [], "functional_skills": [], "tools_platforms": [], "methodologies": [], "domains": []}, "work_experience": [], "projects": [], "education": [], "certifications": [], "achievements": [], "languages": [], "preferences": {"preferred_roles": [], "preferred_locations": [], "remote_preference": "", "salary_expectation": {"min": "", "max": "", "currency": ""}}, "ats_metadata": {"keywords": [], "completeness_score": 0, "last_updated": ""}}}
