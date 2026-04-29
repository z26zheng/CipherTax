"""Unified text extraction — auto-detects digital PDFs, scanned PDFs, and images."""

from __future__ import annotations

import logging
from pathlib import Path

from ciphertax.extraction.pdf_extractor import extract_text_digital
from ciphertax.extraction.ocr_extractor import extract_text_ocr_from_pdf, is_tesseract_available
from ciphertax.extraction.image_extractor import extract_text_from_image, is_image_file

logger = logging.getLogger(__name__)


def extract_text_from_pdf(
    pdf_path: str | Path,
    force_ocr: bool = False,
    ocr_lang: str = "eng",
) -> list[dict]:
    """Extract text from a PDF, automatically choosing digital or OCR extraction.

    Strategy:
    1. Try digital extraction first (fast, accurate for text-selectable PDFs).
    2. For pages with little/no text, fall back to OCR (if Tesseract is available).
    3. If force_ocr=True, skip digital extraction and use OCR for all pages.

    Args:
        pdf_path: Path to the PDF file.
        force_ocr: If True, use OCR for all pages regardless of text content.
        ocr_lang: Tesseract language code for OCR.

    Returns:
        List of dicts, one per page:
        [{"page": 1, "text": "...", "method": "digital"|"ocr"}, ...]
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if force_ocr:
        logger.info("Force OCR mode for %s", pdf_path.name)
        pages = extract_text_ocr_from_pdf(pdf_path, lang=ocr_lang)
        return [
            {"page": p["page"], "text": p["text"], "method": "ocr"}
            for p in pages
        ]

    # Try digital extraction first
    digital_pages = extract_text_digital(pdf_path)

    results: list[dict] = []
    ocr_needed = []

    for page_info in digital_pages:
        if page_info["has_text"]:
            results.append(
                {
                    "page": page_info["page"],
                    "text": page_info["text"],
                    "method": "digital",
                }
            )
        else:
            ocr_needed.append(page_info["page"])
            results.append(None)  # Placeholder for OCR pages

    # OCR fallback for pages without sufficient text
    if ocr_needed:
        if not is_tesseract_available():
            logger.warning(
                "Pages %s appear to be scanned but Tesseract is not installed. "
                "Text extraction may be incomplete. Install with: brew install tesseract",
                ocr_needed,
            )
            # Fill placeholders with empty text
            for i, result in enumerate(results):
                if result is None:
                    results[i] = {
                        "page": digital_pages[i]["page"],
                        "text": digital_pages[i]["text"],  # Use whatever we got
                        "method": "digital_incomplete",
                    }
        else:
            logger.info("Running OCR on pages: %s", ocr_needed)
            ocr_pages = extract_text_ocr_from_pdf(pdf_path, lang=ocr_lang)
            ocr_by_page = {p["page"]: p["text"] for p in ocr_pages}

            for i, result in enumerate(results):
                if result is None:
                    page_num = digital_pages[i]["page"]
                    results[i] = {
                        "page": page_num,
                        "text": ocr_by_page.get(page_num, ""),
                        "method": "ocr",
                    }

    total_chars = sum(len(p["text"]) for p in results)
    methods = set(p["method"] for p in results)
    logger.info(
        "Extracted %d pages (%d chars) from %s using %s",
        len(results),
        total_chars,
        pdf_path.name,
        methods,
    )

    return results


def extract_text_from_file(
    file_path: str | Path,
    force_ocr: bool = False,
    ocr_lang: str = "eng",
) -> list[dict]:
    """Extract text from any supported file (PDF or image).

    Auto-detects file type and routes to the appropriate extractor.

    Args:
        file_path: Path to a PDF or image file.
        force_ocr: If True, force OCR even for digital PDFs.
        ocr_lang: Tesseract language code.

    Returns:
        List of dicts, one per page/image:
        [{"page": 1, "text": "...", "method": "digital"|"ocr"}, ...]
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_image_file(file_path):
        logger.info("Detected image file: %s", file_path.name)
        return extract_text_from_image(file_path, lang=ocr_lang)
    elif file_path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path, force_ocr=force_ocr, ocr_lang=ocr_lang)
    else:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported: .pdf, .png, .jpg, .jpeg, .tiff, .tif, .bmp, .webp"
        )
