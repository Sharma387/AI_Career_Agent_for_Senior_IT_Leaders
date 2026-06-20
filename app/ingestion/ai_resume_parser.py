"""
Chunked AI-powered resume parser with confidence scoring.

Splits resume into logical chunks, parses each independently,
then merges results with deduplication and confidence scores.
"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.json_parser import extract_json_from_llm

logger = logging.getLogger(__name__)

CHUNK_PARSE_PROMPT = """Parse this resume section into JSON. Return ONLY valid JSON.
Fields: full_name, email, phone, location, linkedin, headline, summary, experience[], skills{}, certifications[], interests[], education[]
For each field include confidence (0-1). Use format: {"value": "...", "confidence": 0.9}
For arrays, each item gets confidence. If a field is not present in this chunk, omit it."""


def chunk_resume(raw_text: str, max_chunk_size: int = 3000) -> list[str]:
    """
    Split resume into logical chunks at paragraph boundaries.

    Strategy:
    1. Split by double newlines (paragraph boundaries)
    2. Group paragraphs until max_chunk_size reached
    3. Never split mid-paragraph
    """
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

        # If a single paragraph exceeds max_chunk_size, it gets its own chunk
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
        current_size += para_size + 2  # account for \n\n separator

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def parse_chunk(chunk: str, chunk_index: int, total_chunks: int) -> dict:
    """
    Parse a single resume chunk using AI with confidence scoring.

    Settings: temperature=0, num_predict=3000, num_ctx=8192
    """
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

        context_note = f"[Chunk {chunk_index + 1} of {total_chunks}]"

        response = llm.invoke([
            SystemMessage(content=CHUNK_PARSE_PROMPT),
            HumanMessage(content=f"{context_note}\n\n{chunk}")
        ])

        content = response.content.strip()
        logger.debug(f"Chunk {chunk_index + 1}/{total_chunks} response: {len(content)} chars")

        result = extract_json_from_llm(content)
        if result is None:
            logger.warning(f"Chunk {chunk_index + 1} returned unparseable response")
            return {}

        return result

    except Exception as e:
        logger.error(f"Failed to parse chunk {chunk_index + 1}: {e}")
        return {}


def merge_parsed_chunks(chunks: list[dict]) -> dict:
    """
    Merge results from multiple chunk parses.

    - Dedup experience by title+company
    - Union all skill categories
    - Dedup certifications by name
    - Take first non-empty scalar fields (name, email, phone, etc.)
    """
    merged = {
        "full_name": {"value": "", "confidence": 0.0},
        "email": {"value": "", "confidence": 0.0},
        "phone": {"value": "", "confidence": 0.0},
        "location": {"value": "", "confidence": 0.0},
        "linkedin": {"value": "", "confidence": 0.0},
        "headline": {"value": "", "confidence": 0.0},
        "summary": {"value": "", "confidence": 0.0},
        "experience": [],
        "skills": {},
        "certifications": [],
        "interests": [],
        "education": [],
    }

    seen_experience = set()  # (title_lower, company_lower)
    seen_certs = set()  # cert_name_lower
    seen_interests = set()
    seen_education = set()

    for chunk_result in chunks:
        if not chunk_result:
            continue

        # Merge scalar fields — take first non-empty or highest confidence
        for field in ["full_name", "email", "phone", "location", "linkedin", "headline", "summary"]:
            value = chunk_result.get(field)
            if value is None:
                continue

            if isinstance(value, dict):
                v = value.get("value", "")
                c = value.get("confidence", 0.5)
            else:
                v = str(value)
                c = 0.5

            if v and c > merged[field]["confidence"]:
                merged[field] = {"value": v, "confidence": c}

        # Merge experience (dedup by title+company)
        for exp in chunk_result.get("experience", []):
            if isinstance(exp, dict):
                title = _extract_value(exp.get("title", ""))
                company = _extract_value(exp.get("company", ""))
                key = (title.lower().strip(), company.lower().strip())
                if key not in seen_experience and (title or company):
                    seen_experience.add(key)
                    merged["experience"].append(exp)

        # Merge skills (union of categories)
        skills = chunk_result.get("skills", {})
        if isinstance(skills, dict):
            for category, skill_list in skills.items():
                cat_key = _extract_value(category) if isinstance(category, dict) else str(category)
                if cat_key not in merged["skills"]:
                    merged["skills"][cat_key] = []
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        skill_name = _extract_value(skill) if isinstance(skill, dict) else str(skill)
                        if skill_name and skill_name not in merged["skills"][cat_key]:
                            merged["skills"][cat_key].append(skill_name)

        # Merge certifications (dedup by name)
        for cert in chunk_result.get("certifications", []):
            cert_name = _extract_value(cert) if isinstance(cert, dict) else str(cert)
            if cert_name and cert_name.lower() not in seen_certs:
                seen_certs.add(cert_name.lower())
                merged["certifications"].append(cert)

        # Merge interests
        for interest in chunk_result.get("interests", []):
            interest_name = _extract_value(interest) if isinstance(interest, dict) else str(interest)
            if interest_name and interest_name.lower() not in seen_interests:
                seen_interests.add(interest_name.lower())
                merged["interests"].append(interest)

        # Merge education (dedup by degree+institution)
        for edu in chunk_result.get("education", []):
            if isinstance(edu, dict):
                degree = _extract_value(edu.get("degree", ""))
                institution = _extract_value(edu.get("institution", ""))
                key = (degree.lower().strip(), institution.lower().strip())
                if key not in seen_education and (degree or institution):
                    seen_education.add(key)
                    merged["education"].append(edu)

    return merged


def _extract_value(item) -> str:
    """Extract value from either a plain string or a confidence-annotated dict."""
    if isinstance(item, dict):
        return str(item.get("value", ""))
    return str(item) if item else ""


def parse_resume_with_ai(raw_text: str) -> dict:
    """
    Parse resume text using chunked AI approach with confidence scoring.

    Orchestrates:
    1. Chunk the text
    2. Parse each chunk
    3. Merge results
    4. Return normalized result with confidence scores

    Returns flat dict compatible with the existing pipeline.
    """
    if not raw_text or not raw_text.strip():
        return _empty_result()

    try:
        # Chunk the resume
        chunks = chunk_resume(raw_text)
        if not chunks:
            return _fallback_parse(raw_text)

        logger.info(f"Resume split into {len(chunks)} chunks")

        # Parse each chunk
        parsed_chunks = []
        for i, chunk in enumerate(chunks):
            result = parse_chunk(chunk, i, len(chunks))
            parsed_chunks.append(result)

        # Merge all chunk results
        merged = merge_parsed_chunks(parsed_chunks)

        # Normalize to flat structure for backward compatibility
        return _normalize_merged(merged, raw_text)

    except Exception as e:
        logger.error(f"Chunked AI resume parsing failed: {e}")
        return _fallback_parse(raw_text)


def get_confidence_scores(raw_text: str) -> dict:
    """
    Parse and return confidence scores from the chunked parsing.
    Used by the profile service to store in audit records.
    """
    if not raw_text or not raw_text.strip():
        return {}

    try:
        chunks = chunk_resume(raw_text)
        if not chunks:
            return {}

        parsed_chunks = []
        for i, chunk in enumerate(chunks):
            result = parse_chunk(chunk, i, len(chunks))
            parsed_chunks.append(result)

        merged = merge_parsed_chunks(parsed_chunks)

        # Extract confidence scores
        scores = {}
        for field in ["full_name", "email", "phone", "location", "linkedin", "headline", "summary"]:
            if isinstance(merged.get(field), dict):
                scores[field] = merged[field].get("confidence", 0.0)

        return scores
    except Exception:
        return {}


def _normalize_merged(merged: dict, raw_text: str) -> dict:
    """Convert confidence-annotated merged result to flat dict for backward compat."""
    result = {
        "full_name": _extract_value(merged.get("full_name", "")) or _extract_name_fallback(raw_text),
        "email": _extract_value(merged.get("email", "")),
        "phone": _extract_value(merged.get("phone", "")),
        "location": _extract_value(merged.get("location", "")),
        "linkedin": _extract_value(merged.get("linkedin", "")),
        "headline": _extract_value(merged.get("headline", "")),
        "summary": _extract_value(merged.get("summary", "")),
        "experience": [],
        "skills": {},
        "certifications": [],
        "interests": [],
        "education": [],
    }

    # Normalize experience
    for exp in merged.get("experience", []):
        if isinstance(exp, dict):
            result["experience"].append({
                "title": _extract_value(exp.get("title", "")),
                "company": _extract_value(exp.get("company", "")),
                "dates": _extract_value(exp.get("dates", "")),
                "location": _extract_value(exp.get("location", "")),
                "description": _extract_value(exp.get("description", "")),
                "bullets": [
                    _extract_value(b) for b in exp.get("bullets", []) if b
                ],
            })

    # Normalize skills
    for category, skill_list in merged.get("skills", {}).items():
        cat_name = str(category)
        if isinstance(skill_list, list):
            result["skills"][cat_name] = [
                _extract_value(s) if isinstance(s, dict) else str(s)
                for s in skill_list if s
            ]

    # Normalize certifications
    for cert in merged.get("certifications", []):
        cert_name = _extract_value(cert)
        if cert_name and len(cert_name) > 2:
            result["certifications"].append(cert_name)

    # Normalize interests
    for interest in merged.get("interests", []):
        interest_name = _extract_value(interest)
        if interest_name and len(interest_name) > 1:
            result["interests"].append(interest_name)

    # Normalize education
    for edu in merged.get("education", []):
        if isinstance(edu, dict):
            result["education"].append({
                "degree": _extract_value(edu.get("degree", "")),
                "institution": _extract_value(edu.get("institution", "")),
                "year": _extract_value(edu.get("year", "")),
            })

    return result


def _extract_name_fallback(raw_text: str) -> str:
    """Extract name from first few lines as fallback."""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line in lines[:3]:
        if not re.search(r'[@\d]', line) and len(line.split()) <= 4 and len(line) > 2:
            return line
    return "Unknown"


def _fallback_parse(raw_text: str) -> dict:
    """Basic regex fallback if AI fails entirely."""
    result = _empty_result()

    # Try to extract name from first lines
    result["full_name"] = _extract_name_fallback(raw_text)

    # Try to extract email
    email_match = re.search(r'[\w.-]+@[\w.-]+\.[\w]+', raw_text)
    if email_match:
        result["email"] = email_match.group(0)

    # Try to extract phone
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', raw_text)
    if phone_match:
        result["phone"] = phone_match.group(0)

    # Use raw text as summary
    result["summary"] = raw_text[:500]

    return result


def _empty_result() -> dict:
    """Return empty structured result."""
    return {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "headline": "",
        "summary": "",
        "experience": [],
        "skills": {},
        "certifications": [],
        "interests": [],
        "education": [],
    }
