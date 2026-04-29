"""Shared fixtures and helpers for CipherTax integration tests."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.fixtures.generate_fixtures import (
    ALL_PII_VALUES,
    PRESERVED_VALUES,
    MOCK_W2,
    MOCK_1099_INT,
    MOCK_1099_NEC,
    MOCK_DENSE_PII,
    generate_all_fixtures,
    validate_all_fixtures,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# SSN regex pattern (XXX-XX-XXXX)
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# EIN regex pattern (XX-XXXXXXX)
EIN_PATTERN = re.compile(r"\b\d{2}-\d{7}\b")
# Email pattern
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
# Phone pattern
PHONE_PATTERN = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")


def has_tesseract() -> bool:
    """Check if Tesseract is available."""
    from ciphertax.extraction.ocr_extractor import is_tesseract_available
    return is_tesseract_available()


requires_tesseract = pytest.mark.skipif(
    not has_tesseract(),
    reason="Tesseract OCR not installed"
)


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Generate fixtures if they don't exist."""
    w2_path = FIXTURES_DIR / "mock_w2.pdf"
    if not w2_path.exists():
        generate_all_fixtures()
        validate_all_fixtures()


@pytest.fixture
def w2_pdf():
    return FIXTURES_DIR / "mock_w2.pdf"


@pytest.fixture
def f1099_int_pdf():
    return FIXTURES_DIR / "mock_1099_int.pdf"


@pytest.fixture
def f1099_nec_pdf():
    return FIXTURES_DIR / "mock_1099_nec.pdf"


@pytest.fixture
def unicode_pdf():
    return FIXTURES_DIR / "mock_unicode_names.pdf"


@pytest.fixture
def dense_pii_pdf():
    return FIXTURES_DIR / "mock_dense_pii.pdf"


@pytest.fixture
def multi_page_pdf():
    return FIXTURES_DIR / "mock_multi_page.pdf"


@pytest.fixture
def empty_pdf():
    return FIXTURES_DIR / "mock_empty.pdf"


@pytest.fixture
def scanned_w2_pdf():
    return FIXTURES_DIR / "mock_w2_scanned.pdf"


@pytest.fixture
def w2_photo_png():
    return FIXTURES_DIR / "mock_w2_photo.png"


@pytest.fixture
def w2_photo_jpg():
    return FIXTURES_DIR / "mock_w2_photo.jpg"


@pytest.fixture
def all_pii_values():
    return ALL_PII_VALUES


@pytest.fixture
def preserved_values():
    return PRESERVED_VALUES


@pytest.fixture
def pipeline(tmp_path):
    """Create a CipherTaxPipeline with temp vault directory."""
    from ciphertax.pipeline import CipherTaxPipeline
    return CipherTaxPipeline(
        vault_password="test-password",
        vault_dir=tmp_path / "vaults",
    )


@pytest.fixture
def mock_claude_response():
    """Create a mock Claude API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = (
        '{"form_type": "W-2", "employee": {"name": "[PERSON_1]", "ssn": "[SSN_1]"}, '
        '"wages": 92450.00, "federal_tax_withheld": 16200.00, "state": "IL"}'
    )
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 500
    mock_response.usage.output_tokens = 200
    return mock_response


def assert_no_pii_in_text(text: str, pii_values: set[str] | None = None) -> None:
    """Assert that no PII values appear in the given text.

    Args:
        text: The text to check.
        pii_values: Set of PII values to check for. Defaults to ALL_PII_VALUES.
    """
    pii_values = pii_values or ALL_PII_VALUES

    # Check for known PII values
    for pii in pii_values:
        assert pii not in text, f"PII LEAK: '{pii}' found in text"

    # Check for SSN patterns
    ssn_matches = SSN_PATTERN.findall(text)
    for ssn in ssn_matches:
        # Allow tokens like [SSN_1] but not bare SSNs
        # Check if the SSN is inside a token
        idx = text.find(ssn)
        if idx > 0 and text[idx - 1] == "[":
            continue  # Part of a token
        assert False, f"PII LEAK: SSN pattern '{ssn}' found in text"
