"""Extract text from digital (text-selectable) PDFs using PyMuPDF."""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_digital(pdf_path: str | Path) -> list[dict]:
    """Extract text from a digital PDF page by page.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of dicts, one per page:
        [{"page": 1, "text": "...", "has_text": True}, ...]
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages: list[dict] = []
    doc = fitz.open(str(pdf_path))

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            pages.append(
                {
                    "page": page_num + 1,
                    "text": text,
                    "has_text": len(text) > 20,  # Heuristic: <20 chars = likely scanned
                }
            )
    finally:
        doc.close()

    logger.info("Extracted %d pages from %s (digital)", len(pages), pdf_path.name)
    return pages


def render_page_to_image(pdf_path: str | Path, page_num: int, dpi: int = 300) -> bytes:
    """Render a single PDF page to a PNG image (for OCR fallback).

    Args:
        pdf_path: Path to the PDF file.
        page_num: 0-based page number.
        dpi: Resolution for rendering.

    Returns:
        PNG image bytes.
    """
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_num]
        zoom = dpi / 72  # 72 is default DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    finally:
        doc.close()
