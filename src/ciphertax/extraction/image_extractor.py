"""Extract text from image files (PNG, JPG, TIFF) using Tesseract OCR.

Supports direct image inputs — common when users photograph tax forms
with a phone or scanner.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"})


def is_image_file(file_path: str | Path) -> bool:
    """Check if a file is a supported image format."""
    return Path(file_path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def extract_text_from_image(
    image_path: str | Path,
    lang: str = "eng",
) -> list[dict]:
    """Extract text from an image file using OCR.

    Args:
        image_path: Path to the image file (PNG, JPG, TIFF, etc.).
        lang: Tesseract language code.

    Returns:
        List with a single dict (images are single-page):
        [{"page": 1, "text": "...", "method": "ocr"}]
    """
    from ciphertax.extraction.ocr_extractor import is_tesseract_available

    import pytesseract

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if not is_image_file(image_path):
        raise ValueError(
            f"Unsupported image format: {image_path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    if not is_tesseract_available():
        raise RuntimeError(
            "Tesseract OCR is not installed. "
            "Install it with: brew install tesseract (macOS) "
            "or apt-get install tesseract-ocr (Linux)"
        )

    logger.info("OCR processing image: %s", image_path.name)
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang=lang).strip()

    logger.info("Extracted %d chars from image %s", len(text), image_path.name)

    return [{"page": 1, "text": text, "method": "ocr"}]
