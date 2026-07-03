import logging
import re
from pathlib import Path

import docx2txt
from pypdf import PdfReader

from app.ingestion.ocr_extractor import extract_text_with_ocr

logger = logging.getLogger(__name__)


def _find_column_split(words: list, page_width: float) -> float | None:
    """
    Find the x-coordinate of the gap between two columns by analysing
    the distribution of word start positions (x0).

    Returns the split x-coordinate if a clear 2-column gap is found,
    otherwise returns None (single column).
    """
    if not words:
        return None

    # Collect all right-edges (x1) and left-edges (x0)
    x1_vals = sorted(set(round(w["x1"]) for w in words))
    x0_vals = sorted(set(round(w["x0"]) for w in words))

    # Look for the largest horizontal gap between end of text in one region
    # and start of text in the next, within the central 20-80% of page width
    zone_start = page_width * 0.20
    zone_end = page_width * 0.80

    # Build a set of x positions that are "occupied" by text
    # A gap is a range of x-values where no word starts AND no word ends
    # We scan for gaps by combining x0 and x1 values
    all_x = sorted(x1_vals + x0_vals)

    best_gap_center = None
    best_gap_size = 0

    for i in range(len(all_x) - 1):
        gap_left = all_x[i]
        gap_right = all_x[i + 1]
        gap_size = gap_right - gap_left

        # Only consider gaps in the central zone and of meaningful size
        gap_center = (gap_left + gap_right) / 2
        if zone_start < gap_center < zone_end and gap_size > best_gap_size:
            best_gap_size = gap_size
            best_gap_center = gap_center

    # Require at least 20pt gap to be considered a real column separator
    if best_gap_size >= 20:
        logger.debug(f"Column gap detected: {best_gap_size:.1f}pt at x={best_gap_center:.1f}")
        return best_gap_center

    return None


def _extract_pdf_column_aware(file_path: str) -> str:
    """
    Extract text from PDFs with multi-column layouts using pdfplumber.

    Strategy:
    1. Use pdfplumber to detect text bounding boxes per page
    2. Find the actual column gap (largest horizontal whitespace gap in
       the central zone) — NOT a fixed page midpoint
    3. For two-column pages: extract left column top-to-bottom, then
       right column top-to-bottom, separated by a clear marker
    4. For single-column pages: use normal top-to-bottom extraction
    5. Fall back to pypdf if pdfplumber unavailable or fails

    This correctly handles resumes like Sharma's where the left column
    (~60% width) has work experience and the right column (~35% width)
    has skills, certs, and interests.
    """
    try:
        import pdfplumber

        def words_to_text(word_list: list) -> str:
            """Convert a sorted word list to readable text by grouping into lines."""
            if not word_list:
                return ""
            lines = []
            current_line = []
            current_top = None
            LINE_TOLERANCE = 4  # words within 4pt vertically = same line

            for w in word_list:
                top = round(w["top"] / LINE_TOLERANCE) * LINE_TOLERANCE
                if current_top is None or abs(top - current_top) <= LINE_TOLERANCE:
                    current_line.append(w["text"])
                    current_top = top
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [w["text"]]
                    current_top = top

            if current_line:
                lines.append(" ".join(current_line))

            return "\n".join(lines)

        all_pages_text = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=False,
                )

                if not words:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    all_pages_text.append(text)
                    continue

                page_width = page.width
                split_x = _find_column_split(words, page_width)

                if split_x is not None:
                    logger.info(
                        f"Page {page_num + 1}: 2-column layout detected "
                        f"(split at x={split_x:.1f}, page width={page_width:.1f})"
                    )

                    # Split words into left and right columns at the gap
                    left_words = [w for w in words if w["x1"] <= split_x]
                    right_words = [w for w in words if w["x0"] >= split_x]

                    # Sort each column top-to-bottom, then left-to-right within a line
                    left_sorted = sorted(left_words, key=lambda w: (round(w["top"] / 4) * 4, w["x0"]))
                    right_sorted = sorted(right_words, key=lambda w: (round(w["top"] / 4) * 4, w["x0"]))

                    left_text = words_to_text(left_sorted)
                    right_text = words_to_text(right_sorted)

                    page_text = left_text
                    if right_text:
                        page_text += "\n\n--- RIGHT COLUMN ---\n\n" + right_text
                    all_pages_text.append(page_text)
                else:
                    # Single-column page — standard top-to-bottom extraction
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
