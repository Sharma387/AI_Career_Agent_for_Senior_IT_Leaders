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

    # Use v1.0 work_experience if available (richer structured data)
    v1_schema = profile_data.get("parsed_resume_v1") or {}
    v1_resume = v1_schema.get("resume", {}) if v1_schema else {}
    v1_experience = v1_resume.get("work_experience", [])

    if v1_experience:
        # Map v1.0 experience to template-friendly format
        experience = []
        for exp in v1_experience:
            achievements = [
                a.get("statement", "") if isinstance(a, dict) else str(a)
                for a in exp.get("achievements", [])
                if a
            ]
            responsibilities = [r for r in exp.get("responsibilities", []) if r]
            bullets = achievements + responsibilities
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")
            dates = f"{start} – {end}" if start or end else ""
            experience.append({
                "company": exp.get("company", ""),
                "company_about": exp.get("company_industry", ""),
                "title": exp.get("role_title", ""),
                "dates": dates,
                "location": exp.get("location", ""),
                "bullets": [b for b in bullets if b],
                "description": "",
            })
    else:
        experience = resume["experience"]

    # Use v1.0 education if available
    v1_education = v1_resume.get("education", [])
    if v1_education:
        education = [
            {
                "degree": e.get("degree", ""),
                "institution": e.get("institution", ""),
                "year": e.get("end_year", e.get("year", "")),
            }
            for e in v1_education
        ]
    else:
        education = resume["education"]

    context = {
        "candidate_name": profile_data.get("full_name", "Candidate"),
        "headline": profile_data.get("headline", ""),
        "email": profile_data.get("email", ""),
        "phone": profile_data.get("phone", ""),
        "location": profile_data.get("location", ""),
        "linkedin": profile_data.get("linkedin", ""),
        "summary": profile_data.get("summary") or resume["summary"],
        "experience": experience,
        "skills": profile_data.get("skills") or resume["skills"],
        "education": education,
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
    """Generate a clean professional DOCX resume matching the HTML template style."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt as _Pt

    doc = Document()

    # A4 page with 2cm margins
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    NAVY = RGBColor(0x1a, 0x52, 0x76)
    DARK = RGBColor(0x2d, 0x2d, 0x2d)
    GREY = RGBColor(0x77, 0x77, 0x77)

    name        = profile_data.get("full_name", "Candidate")
    email       = profile_data.get("email", "")
    phone       = profile_data.get("phone", "")
    location    = profile_data.get("location", "")
    linkedin    = profile_data.get("linkedin", "")
    headline    = profile_data.get("headline", "")
    summary_text = profile_data.get("summary", "")
    skills_data = profile_data.get("skills", {})
    certifications = profile_data.get("certifications", [])

    # Use v1.0 structured data for experience & education if available
    v1_schema  = profile_data.get("parsed_resume_v1") or {}
    v1_resume  = v1_schema.get("resume", {}) if v1_schema else {}
    v1_exp     = v1_resume.get("work_experience", [])
    v1_edu     = v1_resume.get("education", [])

    if v1_exp:
        experience = []
        for exp in v1_exp:
            achievements = [
                a.get("statement", "") if isinstance(a, dict) else str(a)
                for a in exp.get("achievements", []) if a
            ]
            responsibilities = [r for r in exp.get("responsibilities", []) if r]
            bullets = achievements + responsibilities
            start = exp.get("start_date", "")
            end   = exp.get("end_date", "")
            dates = f"{start} – {end}" if (start or end) else ""
            experience.append({
                "company":       exp.get("company", ""),
                "company_about": exp.get("company_industry", ""),
                "title":         exp.get("role_title", ""),
                "dates":         dates,
                "location":      exp.get("location", ""),
                "bullets":       [b for b in bullets if b],
            })
    else:
        raw = _parse_resume_text(profile_data.get("resume_text", ""))
        experience = raw.get("experience", [])

    if v1_edu:
        education = [
            {"degree": e.get("degree",""), "institution": e.get("institution",""), "year": e.get("end_year", e.get("year",""))}
            for e in v1_edu
        ]
    else:
        raw = _parse_resume_text(profile_data.get("resume_text", ""))
        education = raw.get("education", [])

    # ── helpers ──────────────────────────────────────────────────────────────

    def add_section_heading(text: str):
        """Navy uppercase heading with bottom border line."""
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after  = Pt(4)
        run = p.add_run(text.upper())
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = NAVY
        pPr  = p._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bot  = OxmlElement('w:bottom')
        bot.set(qn('w:val'),   'single')
        bot.set(qn('w:sz'),    '6')
        bot.set(qn('w:space'), '1')
        bot.set(qn('w:color'), '1a5276')
        pBdr.append(bot)
        pPr.append(pBdr)
        return p

    def set_cell_no_borders(cell):
        """Make a table cell have no visible borders."""
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement(f'w:{side}')
            el.set(qn('w:val'),   'none')
            el.set(qn('w:sz'),    '0')
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), 'auto')
            tcBorders.append(el)
        tcPr.append(tcBorders)

    # ── NAME ─────────────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(name)
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = NAVY

    if headline:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(headline)
        run.font.size = Pt(11)
        run.font.color.rgb = NAVY
        run.italic = True

    # Contact: location | phone | email | linkedin
    contact_parts = [x for x in [location, phone, email, linkedin] if x]
    if contact_parts:
        p = doc.add_paragraph(" | ".join(contact_parts))
        p.paragraph_format.space_after = Pt(8)
        for r in p.runs:
            r.font.size = Pt(9.5)
            r.font.color.rgb = DARK

    # ── SUMMARY ──────────────────────────────────────────────────────────────
    if summary_text:
        add_section_heading("Summary")
        p = doc.add_paragraph(summary_text)
        p.paragraph_format.space_after = Pt(4)
        for r in p.runs:
            r.font.size = Pt(10.5)

    # ── SKILLS — 2-column borderless table ───────────────────────────────────
    if skills_data and isinstance(skills_data, dict):
        categories = [(cat, lst) for cat, lst in skills_data.items() if lst]
        if categories:
            add_section_heading("Key Skills")
            # Pair up categories into rows of 2
            rows_data = [categories[i:i+2] for i in range(0, len(categories), 2)]
            tbl = doc.add_table(rows=len(rows_data), cols=2)
            tbl.style = 'Table Grid'
            # Remove all table-level borders via XML
            tblPr = tbl._tbl.find(qn('w:tblPr'))
            if tblPr is None:
                tblPr = OxmlElement('w:tblPr')
                tbl._tbl.insert(0, tblPr)
            tblBorders = OxmlElement('w:tblBorders')
            for side in ('top','left','bottom','right','insideH','insideV'):
                el = OxmlElement(f'w:{side}')
                el.set(qn('w:val'),   'none')
                el.set(qn('w:sz'),    '0')
                el.set(qn('w:space'), '0')
                el.set(qn('w:color'), 'auto')
                tblBorders.append(el)
            tblPr.append(tblBorders)

            for r_idx, row_cats in enumerate(rows_data):
                row = tbl.rows[r_idx]
                for c_idx, (cat, skill_list) in enumerate(row_cats):
                    cell = row.cells[c_idx]
                    set_cell_no_borders(cell)
                    # Category heading
                    p = cell.paragraphs[0]
                    p.clear()
                    run = p.add_run(cat)
                    run.bold = True
                    run.font.size = Pt(10)
                    run.font.color.rgb = NAVY
                    p.paragraph_format.space_after = Pt(2)
                    # Skill bullets
                    items = skill_list if isinstance(skill_list, list) else [str(skill_list)]
                    for skill in items:
                        if skill:
                            bp = cell.add_paragraph(f"• {skill}")
                            bp.paragraph_format.left_indent = Cm(0.3)
                            bp.paragraph_format.space_after = Pt(1)
                            for r in bp.runs:
                                r.font.size = Pt(10.5)
                # Fill empty cell if odd number of categories
                if len(row_cats) == 1:
                    set_cell_no_borders(row.cells[1])

    # ── WORK EXPERIENCE ──────────────────────────────────────────────────────
    if experience:
        add_section_heading("Work Experience")
        for exp in experience:
            company      = exp.get("company", "")
            company_about = exp.get("company_about", "") or exp.get("description", "")
            dates        = exp.get("dates", "")
            exp_loc      = exp.get("location", "")
            title        = exp.get("title", "")
            bullets      = exp.get("bullets", [])

            # Company name — large navy bold
            if company:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after  = Pt(1)
                run = p.add_run(company)
                run.bold = True
                run.font.size = Pt(12)
                run.font.color.rgb = NAVY

            # About company — small italic grey
            if company_about:
                p = doc.add_paragraph(company_about)
                p.paragraph_format.space_after = Pt(2)
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = GREY
                    r.italic = True

            # Dates | Location
            meta = " | ".join(x for x in [dates, exp_loc] if x)
            if meta:
                p = doc.add_paragraph(meta)
                p.paragraph_format.space_after = Pt(3)
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = GREY

            # Role title — bold dark
            if title:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(3)
                run = p.add_run(title)
                run.bold = True
                run.font.size = Pt(11)
                run.font.color.rgb = DARK

            # Achievement/responsibility bullets
            for bullet in bullets:
                if bullet:
                    p = doc.add_paragraph(style='List Bullet')
                    p.paragraph_format.left_indent = Cm(0.5)
                    p.paragraph_format.space_after = Pt(2)
                    run = p.add_run(bullet)
                    run.font.size = Pt(10.5)

    # ── EDUCATION ────────────────────────────────────────────────────────────
    if education:
        add_section_heading("Education")
        for edu in education:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after  = Pt(1)
            run = p.add_run(edu.get("degree", ""))
            run.bold = True
            run.font.size = Pt(11)

            meta = " • ".join(x for x in [edu.get("institution",""), edu.get("year","")] if x)
            if meta:
                p = doc.add_paragraph(meta)
                p.paragraph_format.space_after = Pt(2)
                for r in p.runs:
                    r.font.size = Pt(10)
                    r.font.color.rgb = GREY

    # ── CERTIFICATIONS ───────────────────────────────────────────────────────
    if certifications:
        add_section_heading("Certifications")
        for cert in certifications:
            cert_name = cert.get("name","") if isinstance(cert, dict) else str(cert)
            issuer    = cert.get("issuer","") if isinstance(cert, dict) else ""
            text      = f"{cert_name} — {issuer}" if issuer else cert_name
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(text)
            run.font.size = Pt(10.5)

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
