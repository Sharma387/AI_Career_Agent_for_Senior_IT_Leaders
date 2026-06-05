import re
from pathlib import Path

import docx2txt
from pypdf import PdfReader


class ResumeParser:

    def parse_pdf(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    def parse_docx(self, file_path: str) -> str:
        return docx2txt.process(file_path) or ""

    def parse_text(self, file_path: str) -> str:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")

    def parse(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        parsers = {
            ".pdf": self.parse_pdf,
            ".docx": self.parse_docx,
            ".txt": self.parse_text,
            ".md": self.parse_text,
        }
        parser = parsers.get(ext)
        if not parser:
            raise ValueError(f"Unsupported file format: {ext}")
        return parser(file_path)

    def extract_sections(self, text: str) -> dict:
        sections = {
            "contact_info": "",
            "summary": "",
            "experience": "",
            "education": "",
            "skills": "",
            "certifications": "",
        }

        contact_pattern = (
            r"(?:[\w.-]+@[\w.-]+\.[\w]+|"
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}|"
            r"linkedin\.com/in/[\w-]+|"
            r"github\.com/[\w-]+)"
        )
        contact_matches = re.findall(contact_pattern, text, re.IGNORECASE)
        if contact_matches:
            first_lines = text.split("\n")[:5]
            name_line = ""
            for line in first_lines:
                if not re.search(r"[@\d]", line) and len(line.strip().split()) <= 4:
                    name_line = line.strip()
                    break
            parts = [name_line] + contact_matches if name_line else contact_matches
            sections["contact_info"] = "\n".join(parts)

        section_headers = [
            "summary",
            "professional summary",
            "profile",
            "about",
            "objective",
            "experience",
            "work experience",
            "employment history",
            "professional experience",
            "education",
            "academic background",
            "skills",
            "technical skills",
            "core competencies",
            "technologies",
            "certifications",
            "licenses",
            "certifications & licenses",
            "awards",
            "projects",
        ]

        header_positions = []
        lower_text = text.lower()
        for header in section_headers:
            pattern = rf"^\s*{re.escape(header)}\s*$"
            for match in re.finditer(pattern, lower_text, re.MULTILINE | re.IGNORECASE):
                header_positions.append((match.start(), header))

        header_positions.sort(key=lambda x: x[0])

        summary_aliases = {"summary", "professional summary", "profile", "about", "objective"}
        experience_aliases = {"experience", "work experience", "employment history", "professional experience"}
        education_aliases = {"education", "academic background"}
        skills_aliases = {"skills", "technical skills", "core competencies", "technologies"}
        cert_aliases = {"certifications", "licenses", "certifications & licenses", "awards"}

        alias_map = {}
        for h, group in [
            (summary_aliases, "summary"),
            (experience_aliases, "experience"),
            (education_aliases, "education"),
            (skills_aliases, "skills"),
            (cert_aliases, "certifications"),
        ]:
            for alias in h:
                alias_map[alias] = group

        for i, (pos, header) in enumerate(header_positions):
            end_pos = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(text)
            content = text[pos:end_pos].strip()
            content = re.sub(rf"^{re.escape(header)}\s*\n*", "", content, flags=re.IGNORECASE).strip()

            section_key = alias_map.get(header)
            if section_key:
                sections[section_key] = content

        return sections
