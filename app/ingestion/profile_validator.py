"""
Profile validation layer for parsed resume data.

Validates email, phone, LinkedIn URL formats, checks for duplicate skills,
and ensures required fields are present.
"""

import re
import logging

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'^[\w.-]+@[\w.-]+\.\w+$')
LINKEDIN_PATTERN = re.compile(r'linkedin\.com', re.IGNORECASE)


def validate_parsed_resume(parsed: dict) -> dict:
    """
    Validate a parsed resume dict for data quality.

    Returns:
        {
            "is_valid": bool,
            "warnings": [{"field": str, "message": str}],
            "errors": [{"field": str, "message": str}],
            "field_status": {field_name: status_string}
        }
    """
    warnings = []
    errors = []
    field_status = {}

    # Validate name
    name = parsed.get("full_name", "").strip()
    if not name or name == "Unknown":
        errors.append({"field": "name", "message": "Name is missing or could not be extracted"})
        field_status["name"] = "missing"
    else:
        field_status["name"] = "valid"

    # Validate email
    email = parsed.get("email", "").strip()
    if email:
        if EMAIL_REGEX.match(email):
            field_status["email"] = "valid"
        else:
            warnings.append({"field": "email", "message": f"Non-standard email format: {email}"})
            field_status["email"] = "valid_with_warning"
    else:
        field_status["email"] = "empty"

    # Validate phone
    phone = parsed.get("phone", "").strip()
    if phone:
        digits = re.sub(r'\D', '', phone)
        if 7 <= len(digits) <= 15:
            field_status["phone"] = "valid"
        else:
            warnings.append({"field": "phone", "message": f"Phone number has unusual length ({len(digits)} digits): {phone}"})
            field_status["phone"] = "valid_with_warning"
    else:
        field_status["phone"] = "empty"

    # Validate LinkedIn URL
    linkedin = parsed.get("linkedin", "").strip()
    if linkedin:
        if LINKEDIN_PATTERN.search(linkedin):
            field_status["linkedin"] = "valid"
        else:
            warnings.append({"field": "linkedin", "message": f"URL does not appear to be a LinkedIn profile: {linkedin}"})
            field_status["linkedin"] = "valid_with_warning"
    else:
        field_status["linkedin"] = "empty"

    # Check for duplicate skills
    skills = parsed.get("skills", {})
    all_skills = []
    if isinstance(skills, dict):
        for category, skill_list in skills.items():
            if isinstance(skill_list, list):
                all_skills.extend(skill_list)

    seen_skills = set()
    duplicates = set()
    for skill in all_skills:
        normalized = skill.strip().lower()
        if normalized in seen_skills:
            duplicates.add(skill)
        seen_skills.add(normalized)

    if duplicates:
        warnings.append({"field": "skills", "message": f"Duplicate skills found: {', '.join(duplicates)}"})

    # Check for at least one experience or skill
    experience = parsed.get("experience", [])
    has_experience = bool(experience)
    has_skills = bool(all_skills)

    if not has_experience and not has_skills:
        errors.append({"field": "experience", "message": "No experience entries or skills found"})
        field_status["experience"] = "missing"
    else:
        field_status["experience"] = "valid"

    # Certifications status
    certs = parsed.get("certifications", [])
    field_status["certifications"] = "valid" if certs else "empty"

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "warnings": warnings,
        "errors": errors,
        "field_status": field_status,
    }
