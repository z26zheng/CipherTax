"""Extract text from scanned/image-based PDFs using Tesseract OCR."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def is_tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and accessible."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_text_ocr(image_bytes: bytes, lang: str = "eng") -> str:
    """Run OCR on an image and return extracted text.

    Args:
        image_bytes: PNG image bytes (e.g., from render_page_to_image).
        lang: Tesseract language code.

    Returns:
        Extracted text string.
    """
    import pytesseract

    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang=lang)
    return text.strip()


def extract_text_ocr_from_pdf(pdf_path: str | Path, lang: str = "eng") -> list[dict]:
    """Extract text from a scanned PDF using OCR on each page.

    Uses PyMuPDF to render pages to images, then Tesseract for OCR.

    Args:
        pdf_path: Path to the PDF file.
        lang: Tesseract language code.

    Returns:
        List of dicts, one per page:
        [{"page": 1, "text": "...", "ocr": True}, ...]
    """
    from ciphertax.extraction.pdf_extractor import render_page_to_image

    import fitz

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not is_tesseract_available():
        raise RuntimeError(
            "Tesseract OCR is not installed. "
            "Install it with: brew install tesseract (macOS) "
            "or apt-get install tesseract-ocr (Linux)"
        )

    doc = fitz.open(str(pdf_path))
    num_pages = len(doc)
    doc.close()

    pages: list[dict] = []
    for page_num in range(num_pages):
        logger.info("OCR processing page %d/%d of %s", page_num + 1, num_pages, pdf_path.name)
        image_bytes = render_page_to_image(pdf_path, page_num)
        text = extract_text_ocr(image_bytes, lang=lang)
        pages.append(
            {
                "page": page_num + 1,
                "text": text,
                "ocr": True,
            }
        )

    logger.info("OCR extracted %d pages from %s", len(pages), pdf_path.name)
    return pages
