import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _parse_resume_text(text: str) -> dict:
    """Parse raw resume text into structured sections."""
    sections = {
        "summary": "",
        "experience": [],
        "education": [],
        "skills": {},
        "certifications": [],
        "interests": [],
    }

    if not text:
        return sections

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    current_section = "summary"
    current_item = None

    # Section headers with improved detection
    section_keywords = {
        "summary": ["professional summary", "executive summary", "profile", "objective", "about", "summary"],
        "experience": ["professional experience", "work experience", "employment", "career history", "experience"],
        "education": ["education", "academic", "qualifications", "academic qualifications"],
        "skills": ["skills", "competencies", "technical skills", "core competencies", "key skills"],
        "certifications": ["certifications", "certificates", "licenses", "professional certifications"],
        "projects": ["projects", "key projects", "notable projects"],
        "interests": ["interests", "hobbies", "personal interests"],
    }

    def detect_section(line_lower: str) -> str | None:
        """Detect section header and return section name."""
        for section, keywords in section_keywords.items():
            for kw in keywords:
                if line_lower == kw or (line_lower.startswith(kw) and len(line_lower) < len(kw) + 10):
                    return section
        
        # Handle combined headers like "EDUCATION & CERTIFICATIONS"
        if "education" in line_lower and ("certification" in line_lower or "credential" in line_lower):
            return "education"
        if "skill" in line_lower and "project" in line_lower:
            return "skills"
        
        return None

    import re as _re
    
    for line in lines:
        lower = line.lower().strip()

        # Try to detect section header
        detected_section = detect_section(lower)
        if detected_section:
            # Save the current item before switching sections
            if current_item and current_section == "experience":
                sections["experience"].append(current_item)
            current_section = detected_section
            current_item = None
            continue

        # Add content to current section
        if current_section == "summary":
            sections["summary"] += line + " "
        
        elif current_section == "experience":
            # Check if this line looks like a job title (contains job title keywords and separators)
            is_job_title = False
            if "|" in line or "—" in line or "–" in line:
                # Check if it looks like: "Job Title | Company | Dates"
                parts = _re.split(r'\s*[|—–]\s*', line)
                if len(parts) >= 2:
                    is_job_title = True
            elif any(title_keyword in lower for title_keyword in ["cto", "director", "manager", "engineer", "architect", "lead", "head", "vp ", "principal", "senior"]):
                # If line contains known titles and isn't starting with bullet
                if not line.startswith(("-", "•", "·")) and len(line) < 100:
                    is_job_title = True
            
            if is_job_title or (not current_item and not line.startswith(("-", "•", "·"))):
                if current_item:
                    sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif current_item:
                # This is a bullet point or description
                clean = line.lstrip("-•· ")
                if line.startswith(("-", "•", "·")):
                    current_item["bullets"].append(clean)
                elif len(line) < 150 and not line[0].isupper():
                    current_item["bullets"].append(clean)
                else:
                    current_item["description"] += line + " "
        
        elif current_section == "education":
            if not current_item:
                current_item = {"degree": line, "institution": "", "year": ""}
            elif not current_item["institution"]:
                current_item["institution"] = line
                # Check if this might be a certification instead
                if any(cert_kw in lower for cert_kw in ["certification", "credential", "certificate", "certified"]):
                    sections["certifications"].append({"name": current_item["degree"], "issuer": line})
                    current_item = None
                else:
                    sections["education"].append(current_item)
                    current_item = None
            else:
                current_item["year"] = line
                sections["education"].append(current_item)
                current_item = None
        
        elif current_section == "skills":
            if ":" in line:
                cat, skills_str = line.split(":", 1)
                skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]
                sections["skills"][cat.strip()] = skills_list
            else:
                # Standalone skill without category
                if "General" not in sections["skills"]:
                    sections["skills"]["General"] = []
                sections["skills"]["General"].extend([s.strip() for s in line.split(",") if s.strip()])
        
        elif current_section == "certifications":
            # Each line is typically a certification
            if line and not line.startswith("-"):
                sections["certifications"].append({"name": line, "issuer": ""})
        
        elif current_section == "projects":
            # Similar to experience
            is_project_title = "|" in line or "—" in line or "–" in line or (len(line) < 100 and not line.startswith("-"))
            if is_project_title and current_item:
                sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif is_project_title:
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif current_item:
                clean = line.lstrip("-•· ")
                current_item["bullets"].append(clean)
        
        elif current_section == "interests":
            # Interests are typically 2-4 short items. Stop at job-like content.
            import re as _re
            if len(sections["interests"]) >= 5:
                # Too many — likely leaked into experience
                current_section = "experience"
                if current_item:
                    sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif _re.search(r'\d{2}/\d{4}|\d{4}\s*[-–]\s*\d{4}|\d{4}\s*[-–]\s*present', line, _re.IGNORECASE):
                current_section = "experience"
                if current_item:
                    sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif len(line) > 80:
                current_section = "experience"
                if current_item:
                    sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif _re.match(r'^(project manager|senior|lead|director|analyst|engineer|developer|programmer|consultant|manager)\b', line, _re.IGNORECASE):
                current_section = "experience"
                if current_item:
                    sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif _re.search(r'\b(ltd|inc|pty|limited|technologies|services|consulting|solutions|group|corp)\b', line, _re.IGNORECASE):
                current_section = "experience"
                if current_item:
                    sections["experience"].append(current_item)
                current_item = {"title": line, "company": "", "dates": "", "bullets": [], "description": ""}
            elif _re.match(r'^(achievements|tasks|responsibilities)', line, _re.IGNORECASE):
                current_section = "experience"
                current_item = None
            elif line and len(line) < 80:
                sections["interests"].append(line)

    # Finalize last item
    if current_item:
        if current_section == "experience":
            sections["experience"].append(current_item)
        elif current_section == "education":
            sections["education"].append(current_item)

    sections["summary"] = sections["summary"].strip()
    return sections


def _parse_cover_letter_text(text: str) -> dict:
    """Parse cover letter text into structured data."""
    if not text:
        return {"body_paragraphs": []}

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    body = []
    for p in paragraphs:
        lower = p.lower()
        if lower.startswith("dear") or lower.startswith("yours") or lower.startswith("sincerely"):
            continue
        if "thank you" in lower and len(body) > 0:
            continue
        body.append(p)

    return {"body_paragraphs": body if body else [text]}


def render_resume_html(profile_data: dict, job_data: dict = None) -> str:
    """Render resume as styled HTML using template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("resume.html")

    resume = _parse_resume_text(profile_data.get("resume_text", ""))

    context = {
        "candidate_name": profile_data.get("full_name", "Candidate"),
        "headline": profile_data.get("headline", ""),
        "email": profile_data.get("email", ""),
        "phone": profile_data.get("phone", ""),
        "location": profile_data.get("location", ""),
        "linkedin": profile_data.get("linkedin", ""),
        "summary": profile_data.get("summary") or resume["summary"],
        "experience": resume["experience"],
        "projects": profile_data.get("projects", []),
        "skills": profile_data.get("skills") or resume["skills"],
        "education": resume["education"],
        "certifications": profile_data.get("certifications", []) or resume["certifications"],
    }

    if job_data:
        context["headline"] = job_data.get("target_role", context.get("headline", ""))

    return template.render(**context)


def render_cover_letter_html(profile_data: dict, job_data: dict, cover_letter_text: str) -> str:
    """Render cover letter as styled HTML using template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("cover_letter.html")

    parsed = _parse_cover_letter_text(cover_letter_text)

    context = {
        "candidate_name": profile_data.get("full_name", "Candidate"),
        "email": profile_data.get("email", ""),
        "phone": profile_data.get("phone", ""),
        "location": profile_data.get("location", ""),
        "date": datetime.now().strftime("%d %B %Y"),
        "company_name": job_data.get("company", "the company"),
        "recipient_name": job_data.get("recipient_name", ""),
        "recipient_title": job_data.get("recipient_title", ""),
        "company_address": job_data.get("company_address", ""),
        "body_paragraphs": parsed["body_paragraphs"],
    }

    return template.render(**context)


# --- Helper functions for Seek template DOCX generation ---


def _get_style(doc, style_name: str):
    """Safely get a style from the document, falling back to 'Normal'."""
    try:
        return doc.styles[style_name]
    except KeyError:
        return doc.styles["Normal"]


def _clear_cell(cell):
    """Clear all content from a table cell, keeping one empty paragraph."""
    for i in range(len(cell.paragraphs) - 1, 0, -1):
        p_element = cell.paragraphs[i]._element
        p_element.getparent().remove(p_element)
    # Clear the remaining first paragraph
    if cell.paragraphs:
        cell.paragraphs[0].clear()


def _add_heading_to_cell(cell, text: str, doc):
    """Add a section heading using the template's 'Heading with border' style."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["Heading with border"]
    except KeyError:
        p.style = doc.styles["Normal"]
        run = p.add_run(text)
        run.bold = True
        return p
    run = p.add_run(text)
    return p


def _add_bullet_to_cell(cell, text: str, doc):
    """Add a bullet point using bulletStyle."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["bulletStyle"]
    except KeyError:
        p.style = doc.styles["List Bullet"] if "List Bullet" in [s.name for s in doc.styles] else doc.styles["Normal"]
    run = p.add_run(text)
    return p


def _add_indented_bullet_to_cell(cell, text: str, doc):
    """Add an indented bullet point using indentedBulletListStyle."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["indentedBulletListStyle"]
    except KeyError:
        try:
            p.style = doc.styles["bulletStyle"]
        except KeyError:
            p.style = doc.styles["Normal"]
    run = p.add_run(text)
    return p


def _add_body_to_cell(cell, text: str, doc):
    """Add body text using indentedBodyStyle."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["indentedBodyStyle"]
    except KeyError:
        p.style = doc.styles["Normal"]
    run = p.add_run(text)
    return p


def _add_date_to_cell(cell, text: str, doc):
    """Add date text using roleDateStyle."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["roleDateStyle"]
    except KeyError:
        p.style = doc.styles["Normal"]
    run = p.add_run(text)
    return p


def _add_subheading_to_cell(cell, text: str, doc):
    """Add a sub-heading using roleSubHeadingBoldStyle."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["roleSubHeadingBoldStyle"]
    except KeyError:
        p.style = doc.styles["Normal"]
        run = p.add_run(text)
        run.bold = True
        return p
    run = p.add_run(text)
    return p


def _add_overview_to_cell(cell, text: str, doc):
    """Add overview text using roleOverviewStyle."""
    p = cell.add_paragraph()
    try:
        p.style = doc.styles["roleOverviewStyle"]
    except KeyError:
        p.style = doc.styles["Normal"]
    run = p.add_run(text)
    return p


def generate_resume_docx(profile_data: dict, job_data: dict = None) -> bytes:
    """Generate a professional resume DOCX using the Robert Half NZ IT template."""
    template_path = TEMPLATES_DIR / "IT Resume Template NZ - Robert Half.docx"
    doc = Document(str(template_path))

    resume = _parse_resume_text(profile_data.get("resume_text", ""))
    name = profile_data.get("full_name", "Candidate")
    email = profile_data.get("email", "")
    phone = profile_data.get("phone", "")
    location = profile_data.get("location", "")
    linkedin = profile_data.get("linkedin", "")
    summary_text = profile_data.get("summary") or resume.get("summary", "")
    skills_data = profile_data.get("skills") or resume.get("skills", {})
    experience = resume.get("experience", [])
    education = resume.get("education", [])
    certifications = profile_data.get("certifications", []) or resume.get("certifications", [])

    # Clear all existing content from the template
    for para in doc.paragraphs:
        p_element = para._element
        p_element.getparent().remove(p_element)

    # === Build the resume using standard Word styles ===

    # Name (Title style)
    title_para = doc.add_paragraph(name, style='Title')

    # Contact line
    contact_parts = []
    if location:
        contact_parts.append(location)
    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)
    if linkedin:
        contact_parts.append(linkedin)
    if contact_parts:
        doc.add_paragraph(" | ".join(contact_parts))

    doc.add_paragraph("")  # Spacer

    # Summary section
    if summary_text:
        doc.add_heading("Summary", level=1)
        doc.add_paragraph(summary_text)

    # Key Skills section
    if skills_data:
        doc.add_heading("Key Skills", level=1)
        if isinstance(skills_data, dict):
            for category, skill_list in skills_data.items():
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        doc.add_paragraph(skill, style="List Paragraph")
                else:
                    doc.add_paragraph(str(skill_list), style="List Paragraph")
        elif isinstance(skills_data, list):
            for skill in skills_data:
                skill_name = skill.get("name", str(skill)) if isinstance(skill, dict) else str(skill)
                doc.add_paragraph(skill_name, style="List Paragraph")

    # Work Experience section
    if experience:
        doc.add_heading("Work Experience", level=1)
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            dates = exp.get("dates", "")
            exp_location = exp.get("location", "")
            description = exp.get("description", "")
            bullets = exp.get("bullets", [])

            # Role title
            p = doc.add_paragraph()
            run = p.add_run(title)
            run.bold = True

            # Company
            if company:
                doc.add_paragraph(company)

            # Dates | Location
            meta_parts = []
            if dates:
                meta_parts.append(dates)
            if exp_location:
                meta_parts.append(exp_location)
            if meta_parts:
                doc.add_paragraph(" | ".join(meta_parts))

            # Description
            if description:
                doc.add_paragraph(description)

            # Bullets
            for bullet in bullets:
                doc.add_paragraph(bullet, style="List Paragraph")

            doc.add_paragraph("")  # Spacer between roles

    # Key Projects section
    if profile_data.get("projects"):
        doc.add_heading("Key Projects", level=1)
        for proj in profile_data["projects"]:
            p = doc.add_paragraph()
            run = p.add_run(proj.get("title", ""))
            run.bold = True
            if proj.get("role"):
                doc.add_paragraph(proj["role"])
            if proj.get("description"):
                doc.add_paragraph(proj["description"])
            if proj.get("technologies"):
                doc.add_paragraph(f"Technologies: {proj['technologies']}")
            if proj.get("impact"):
                doc.add_paragraph(f"Impact: {proj['impact']}")

    # Education section
    if education:
        doc.add_heading("Education", level=1)
        for edu in education:
            p = doc.add_paragraph()
            run = p.add_run(edu.get("degree", ""))
            run.bold = True
            meta = []
            if edu.get("institution"):
                meta.append(edu["institution"])
            if edu.get("year"):
                meta.append(edu["year"])
            if meta:
                doc.add_paragraph(" • ".join(meta))

    # Certifications section
    if certifications:
        doc.add_heading("Certifications", level=1)
        for cert in certifications:
            cert_name = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            text = f"{cert_name} — {issuer}" if issuer else cert_name
            doc.add_paragraph(text, style="List Paragraph")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def generate_cover_letter_docx(profile_data: dict, job_data: dict, cover_letter_text: str) -> bytes:
    """Generate a professional cover letter DOCX using the Seek template."""
    template_path = TEMPLATES_DIR / "SEEK-free-cover-letter-template.docx"
    doc = Document(str(template_path))

    name = profile_data.get("full_name", "Candidate")
    email = profile_data.get("email", "")
    phone = profile_data.get("phone", "")
    location = profile_data.get("location", "")
    date_str = datetime.now().strftime("%d %B %Y")
    company = job_data.get("company", "")
    recipient_name = job_data.get("recipient_name", "Hiring Manager")
    job_title = job_data.get("title", job_data.get("target_role", ""))

    parsed = _parse_cover_letter_text(cover_letter_text)

    # Define placeholder replacements
    replacements = {
        "<Your name here>": name,
        "<your name here>": name,
        "<Your Name Here>": name,
        "<Date>": date_str,
        "<date>": date_str,
        "<Hiring manager's name>": recipient_name,
        "<hiring manager's name>": recipient_name,
        "<Hiring Manager's Name>": recipient_name,
        "<Company name>": company,
        "<company name>": company,
        "<Company Name>": company,
        "<Job title>": job_title,
        "<job title>": job_title,
        "<Job Title>": job_title,
        "<Your email>": email,
        "<your email>": email,
        "<Your Email>": email,
        "<Your phone number>": phone,
        "<your phone number>": phone,
        "<Your Phone Number>": phone,
        "<Your address>": location,
        "<your address>": location,
        "<Your Address>": location,
        "<Suburb, State, Postcode>": location,
        "<suburb, state, postcode>": location,
    }

    # Track which paragraphs contain body placeholder text to replace with actual content
    body_placeholder_indices = []
    body_inserted = False

    for i, para in enumerate(doc.paragraphs):
        text = para.text

        # Check for body placeholder patterns (template typically has instructional text)
        if any(phrase in text.lower() for phrase in [
            "this is where you explain",
            "use this section",
            "in this paragraph",
            "write about",
            "outline your",
            "describe your",
            "mention your",
            "explain why",
            "highlight your",
        ]):
            body_placeholder_indices.append(i)
            continue

        # Apply direct placeholder replacements
        replaced = False
        for placeholder, value in replacements.items():
            if placeholder in text:
                text = text.replace(placeholder, value)
                replaced = True

        if replaced:
            # Preserve formatting: clear runs and set new text
            para.clear()
            para.add_run(text)

    # Replace body placeholder paragraphs with actual cover letter content
    if body_placeholder_indices and parsed["body_paragraphs"]:
        # Remove placeholder paragraphs (reverse order to maintain indices)
        for idx in sorted(body_placeholder_indices, reverse=True):
            if idx < len(doc.paragraphs):
                p_element = doc.paragraphs[idx]._element
                p_element.getparent().remove(p_element)

        # Find insertion point: after "Dear..." paragraph or midway through doc
        insert_after = None
        for i, para in enumerate(doc.paragraphs):
            text_lower = para.text.lower().strip()
            if text_lower.startswith("dear"):
                insert_after = i
                break

        if insert_after is not None:
            # Insert body paragraphs after the "Dear..." line
            insert_element = doc.paragraphs[insert_after]._element
            for body_para_text in reversed(parsed["body_paragraphs"]):
                from docx.oxml.ns import qn
                from docx.oxml import OxmlElement
                new_p = OxmlElement('w:p')
                new_r = OxmlElement('w:r')
                new_t = OxmlElement('w:t')
                new_t.text = body_para_text
                new_r.append(new_t)
                new_p.append(new_r)
                insert_element.addnext(new_p)
        else:
            # Fallback: append body paragraphs at the end
            for body_para_text in parsed["body_paragraphs"]:
                doc.add_paragraph(body_para_text)
    elif not body_placeholder_indices:
        # No body placeholders found — do a second pass looking for longer
        # template instructional paragraphs and replace them, or just append
        # the cover letter body before the sign-off
        sign_off_idx = None
        for i, para in enumerate(doc.paragraphs):
            text_lower = para.text.lower().strip()
            if any(s in text_lower for s in ["yours sincerely", "yours faithfully", "kind regards", "regards"]):
                sign_off_idx = i
                break

        if sign_off_idx is not None and parsed["body_paragraphs"]:
            # Remove any paragraphs between "Dear..." and sign-off that look like placeholders
            dear_idx = None
            for i, para in enumerate(doc.paragraphs):
                if para.text.lower().strip().startswith("dear"):
                    dear_idx = i
                    break

            if dear_idx is not None:
                # Remove paragraphs between dear and sign-off
                indices_to_remove = list(range(dear_idx + 1, sign_off_idx))
                for idx in sorted(indices_to_remove, reverse=True):
                    if idx < len(doc.paragraphs):
                        p_element = doc.paragraphs[idx]._element
                        p_element.getparent().remove(p_element)

                # Re-find dear paragraph after removals and insert body after it
                for i, para in enumerate(doc.paragraphs):
                    if para.text.lower().strip().startswith("dear"):
                        insert_element = para._element
                        for body_para_text in reversed(parsed["body_paragraphs"]):
                            from docx.oxml.ns import qn
                            from docx.oxml import OxmlElement
                            new_p = OxmlElement('w:p')
                            new_r = OxmlElement('w:r')
                            new_t = OxmlElement('w:t')
                            new_t.text = body_para_text
                            new_r.append(new_t)
                            new_p.append(new_r)
                            insert_element.addnext(new_p)
                        break
            else:
                # No dear found, just append
                for body_para_text in parsed["body_paragraphs"]:
                    doc.add_paragraph(body_para_text)
        else:
            # Last fallback: append body paragraphs
            for body_para_text in parsed["body_paragraphs"]:
                doc.add_paragraph(body_para_text)

    # Final pass: ensure name appears in sign-off area
    for para in doc.paragraphs:
        text = para.text.strip()
        # Replace any remaining placeholders that might have been missed
        for placeholder, value in replacements.items():
            if placeholder in text:
                text = text.replace(placeholder, value)
                para.clear()
                para.add_run(text)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
