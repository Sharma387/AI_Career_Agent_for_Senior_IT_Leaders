"""
AI-powered resume parser using Ollama (qwen2.5-coder).

Replaces the brittle regex-based parser with LLM-powered section detection.
Handles complex formats like 2-column layouts, multi-page resumes, and
non-standard section ordering.
"""

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm_factory import get_llm
from app.agents.json_parser import extract_json_from_llm

logger = logging.getLogger(__name__)

PARSE_PROMPT = """You are an expert resume parser. Parse the following resume text and extract ALL information into a structured JSON format.

IMPORTANT CONTEXT:
- This text was extracted from a PDF/DOCX which may have had a multi-column layout
- In multi-column PDFs, text from different columns may be interleaved
- Use your understanding of context to determine what belongs where
- A company name like "NTT Data" or "Ness Technologies" is an EMPLOYER, not a certification
- Dates like "06/2009 – 06/2012" indicate employment periods
- Items like "Prince2 Practitioner", "PMP", "ITIL", "Scrum Master" are CERTIFICATIONS
- Items like "Cricket", "Travel", "Blockchain" under an Interests section are INTERESTS/HOBBIES

Extract into this EXACT JSON structure:
{
  "full_name": "candidate's full name",
  "email": "email address or empty string",
  "phone": "phone number or empty string",
  "location": "city/country or empty string",
  "linkedin": "linkedin URL or empty string",
  "headline": "job title or professional headline",
  "summary": "professional summary paragraph (2-4 sentences)",
  "experience": [
    {
      "title": "job title",
      "company": "company name",
      "dates": "start – end dates",
      "location": "city, country",
      "description": "brief role overview",
      "bullets": ["achievement 1", "achievement 2"]
    }
  ],
  "skills": {
    "category_name": ["skill1", "skill2"]
  },
  "certifications": ["cert name 1", "cert name 2"],
  "interests": ["interest 1", "interest 2"],
  "education": [
    {
      "degree": "degree name",
      "institution": "university/school",
      "year": "graduation year"
    }
  ]
}

RULES:
- Extract ONLY what is in the resume. Do not invent or hallucinate.
- Each work experience entry should be a separate object in the array
- Group skills into logical categories (e.g., "Project Management", "Technical", "Cloud", "Leadership")
- Certifications are professional qualifications (PMP, Prince2, ITIL, AWS certified, Scrum Master, etc.)
- Interests/hobbies are personal activities (sports, technology interests, etc.)
- If a section is not present, use an empty array [] or empty string ""
- Respond with ONLY the JSON object, nothing else."""


def parse_resume_with_ai(raw_text: str) -> dict:
    """
    Parse resume text using AI (gemma4 via Ollama).
    
    Returns structured dict with all resume sections correctly identified.
    Falls back to basic extraction if AI fails.
    """
    if not raw_text or not raw_text.strip():
        return _empty_result()

    try:
        # Use a dedicated LLM instance with higher token limit for parsing
        from langchain_ollama import ChatOllama
        from app.core.config import settings
        
        llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,
            num_predict=8192,  # Large response needed for full resume JSON
            num_ctx=16384,     # Larger context window for long resumes
        )
        
        # Truncate very long resumes to avoid context overflow
        text_to_parse = raw_text[:8000] if len(raw_text) > 8000 else raw_text
        
        response = llm.invoke([
            SystemMessage(content=PARSE_PROMPT),
            HumanMessage(content=f"RESUME TEXT:\n\n{text_to_parse}")
        ])
        
        content = response.content.strip()
        
        # Log for debugging
        logger.info(f"AI parser response length: {len(content)} chars")
        if len(content) < 50:
            logger.warning(f"AI parser response too short: {content}")
        
        result = extract_json_from_llm(content)
        
        if result is None:
            logger.warning("AI parser returned unparseable response, using fallback")
            return _fallback_parse(raw_text)
        
        # Validate and normalize the result
        return _normalize_result(result, raw_text)
        
    except Exception as e:
        logger.error(f"AI resume parsing failed: {e}")
        return _fallback_parse(raw_text)


def _normalize_result(result: dict, raw_text: str) -> dict:
    """Ensure all expected fields exist and have correct types."""
    normalized = {
        "full_name": str(result.get("full_name", "")).strip() or _extract_name_fallback(raw_text),
        "email": str(result.get("email", "")).strip(),
        "phone": str(result.get("phone", "")).strip(),
        "location": str(result.get("location", "")).strip(),
        "linkedin": str(result.get("linkedin", "")).strip(),
        "headline": str(result.get("headline", "")).strip(),
        "summary": str(result.get("summary", "")).strip(),
        "experience": [],
        "skills": {},
        "certifications": [],
        "interests": [],
        "education": [],
    }
    
    # Experience
    for exp in result.get("experience", []):
        if isinstance(exp, dict):
            normalized["experience"].append({
                "title": str(exp.get("title", "")),
                "company": str(exp.get("company", "")),
                "dates": str(exp.get("dates", "")),
                "location": str(exp.get("location", "")),
                "description": str(exp.get("description", "")),
                "bullets": [str(b) for b in exp.get("bullets", []) if b],
            })
    
    # Skills
    skills = result.get("skills", {})
    if isinstance(skills, dict):
        for cat, skill_list in skills.items():
            if isinstance(skill_list, list):
                normalized["skills"][str(cat)] = [str(s) for s in skill_list if s]
            else:
                normalized["skills"][str(cat)] = [str(skill_list)]
    elif isinstance(skills, list):
        normalized["skills"]["General"] = [str(s) for s in skills if s]
    
    # Certifications
    certs = result.get("certifications", [])
    if isinstance(certs, list):
        normalized["certifications"] = [str(c) for c in certs if c and len(str(c)) > 2]
    
    # Interests
    interests = result.get("interests", [])
    if isinstance(interests, list):
        normalized["interests"] = [str(i) for i in interests if i and len(str(i)) > 1]
    
    # Education
    for edu in result.get("education", []):
        if isinstance(edu, dict):
            normalized["education"].append({
                "degree": str(edu.get("degree", "")),
                "institution": str(edu.get("institution", "")),
                "year": str(edu.get("year", "")),
            })
    
    return normalized


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
    
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    
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
