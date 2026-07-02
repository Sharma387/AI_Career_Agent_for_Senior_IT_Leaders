import logging
import re
from pathlib import Path

import docx2txt
from pypdf import PdfReader

from app.ingestion.ocr_extractor import extract_text_with_ocr

logger = logging.getLogger(__name__)


def _extract_pdf_column_aware(file_path: str) -> str:
    """
    Extract text from PDFs with multi-column layouts using pdfplumber.

    Strategy:
    1. Use pdfplumber to detect text bounding boxes
    2. For pages with two clear columns (left/right split), extract each
       column top-to-bottom separately, then concatenate left then right
    3. For single-column pages, extract normally top-to-bottom
    4. Fall back to pypdf if pdfplumber fails or isn't installed

    This handles the common resume format where the left half has project
    details and the right half has skills, interests, certifications.
    """
    try:
        import pdfplumber

        all_pages_text = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=False,
                )

                if not words:
                    # Try simple extraction for this page
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    all_pages_text.append(text)
                    continue

                page_width = page.width

                # Detect if page has two columns by checking x-distribution
                x_coords = [w["x0"] for w in words]
                # Find the mid-gap: if there's a significant gap in x-coords near page center
                # indicating a column separator
                mid = page_width / 2
                left_words = [w for w in words if w["x0"] < mid - 10]
                right_words = [w for w in words if w["x0"] >= mid - 10]

                # Determine if it's truly 2-column:
                # Left column ends before mid and right column starts near/after mid
                if left_words and right_words:
                    left_max_x = max(w["x1"] for w in left_words)
                    right_min_x = min(w["x0"] for w in right_words)
                    gap = right_min_x - left_max_x
                    is_two_column = gap > 15  # 15pt gap = real column separator
                else:
                    is_two_column = False

                if is_two_column:
                    logger.info(f"Page detected as 2-column (gap={gap:.1f}pt, width={page_width:.1f}pt)")

                    # Sort each column top-to-bottom
                    left_sorted = sorted(left_words, key=lambda w: (round(w["top"] / 5) * 5, w["x0"]))
                    right_sorted = sorted(right_words, key=lambda w: (round(w["top"] / 5) * 5, w["x0"]))

                    def words_to_text(word_list):
                        """Convert word list to readable text, grouping by line."""
                        if not word_list:
                            return ""
                        lines = []
                        current_line = []
                        current_top = None
                        LINE_TOLERANCE = 5  # words within 5pt vertically = same line

                        for w in word_list:
                            top = round(w["top"] / LINE_TOLERANCE) * LINE_TOLERANCE
                            if current_top is None or abs(top - current_top) <= LINE_TOLERANCE:
                                current_line.append(w["text"])
                                current_top = top
                            else:
                                lines.append(" ".join(current_line))
                                current_line = [w["text"]]
                                current_top = top

                        if current_line:
                            lines.append(" ".join(current_line))

                        return "\n".join(lines)

                    left_text = words_to_text(left_sorted)
                    right_text = words_to_text(right_sorted)

                    # Concatenate: left column first (usually projects/experience),
                    # then right column (skills, certs, interests)
                    # Add clear section separator so the AI knows these are different areas
                    page_text = left_text
                    if right_text:
                        page_text += "\n\n--- RIGHT COLUMN ---\n\n" + right_text
                    all_pages_text.append(page_text)
                else:
                    # Single-column: use normal extraction
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    all_pages_text.append(text)

        result = "\n\n--- PAGE BREAK ---\n\n".join(all_pages_text)
        logger.info(f"pdfplumber extracted {len(result)} chars from {len(all_pages_text)} pages")
        return result

    except ImportError:
        logger.warning("pdfplumber not installed, falling back to pypdf")
        return ""
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}, falling back to pypdf")
        return ""


class ResumeParser:

    def parse_pdf(self, file_path: str) -> str:
        # Try column-aware extraction first (handles multi-column layouts)
        text = _extract_pdf_column_aware(file_path)
        if text and len(text.strip()) > 200:
            return text

        # Fall back to pypdf
        logger.info("Falling back to pypdf extraction")
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

        text = parser(file_path)

        # OCR fallback for scanned PDFs with minimal text extraction
        if len(text.strip()) < 300 and ext == ".pdf":
            logger.info(
                f"Normal extraction yielded {len(text.strip())} chars, attempting OCR fallback"
            )
            ocr_text = extract_text_with_ocr(file_path)
            if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text

        return text

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
