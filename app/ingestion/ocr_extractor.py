"""
OCR fallback for scanned/image-based PDFs.

Uses pytesseract + pdf2image if available.
Gracefully returns empty string if dependencies are not installed.
"""

import logging

logger = logging.getLogger(__name__)


def extract_text_with_ocr(file_path: str) -> str:
    """
    Extract text from a PDF using OCR (Tesseract).

    Returns extracted text, or empty string if OCR dependencies
    are not available or extraction fails.
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning(
            "OCR dependencies not available (pytesseract and/or pdf2image not installed). "
            "Skipping OCR fallback. Install with: pip install pytesseract pdf2image"
        )
        return ""

    try:
        logger.info(f"Running OCR extraction on: {file_path}")
        images = convert_from_path(file_path)
        text_parts = []

        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            if page_text.strip():
                text_parts.append(page_text.strip())
            logger.debug(f"OCR page {i + 1}: extracted {len(page_text)} chars")

        combined = "\n\n".join(text_parts)
        logger.info(f"OCR extraction complete: {len(combined)} chars from {len(images)} pages")
        return combined

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""
