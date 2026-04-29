"""Generate mock tax form PDFs and images for integration testing.

All PII data in these fixtures is FAKE — generated for testing only.
Uses PyMuPDF (fitz) for reliable PDF generation with round-trip validation.

Run standalone:
    python tests/fixtures/generate_fixtures.py
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path(__file__).parent

# ============================================================================
# Mock PII Data — ALL FAKE, for testing only
# ============================================================================

MOCK_W2 = {
    "form_type": "W-2",
    "tax_year": "2024",
    "employee_ssn": "234-56-7890",
    "employee_name": "Maria Elena Rodriguez",
    "employee_address": "742 Evergreen Terrace, Springfield IL 62704",
    "employer_ein": "45-6789012",
    "employer_name": "Acme Technology Solutions Inc",
    "employer_address": "100 Corporate Blvd, Chicago IL 60601",
    "wages": "92,450.00",
    "federal_tax": "16,200.00",
    "ss_wages": "92,450.00",
    "ss_tax": "5,731.90",
    "medicare_wages": "92,450.00",
    "medicare_tax": "1,340.53",
    "state": "IL",
    "state_wages": "92,450.00",
    "state_tax": "5,100.00",
    "phone": "(555) 867-5309",
    "email": "maria.rodriguez@example.com",
}

MOCK_1099_INT = {
    "form_type": "1099-INT",
    "tax_year": "2024",
    "recipient_ssn": "345-67-8901",
    "recipient_name": "Robert James Chen",
    "recipient_address": "456 Oak Avenue, San Francisco CA 94102",
    "payer_ein": "56-7890123",
    "payer_name": "First National Bank",
    "payer_address": "200 Financial District, San Francisco CA 94104",
    "interest_income": "1,245.67",
    "early_withdrawal_penalty": "0.00",
    "us_savings_bond_interest": "0.00",
    "federal_tax_withheld": "0.00",
    "account_number": "78901234567",
}

MOCK_1099_NEC = {
    "form_type": "1099-NEC",
    "tax_year": "2024",
    "recipient_ssn": "456-78-9012",
    "recipient_name": "Aisha Fatima Patel",
    "recipient_address": "789 Maple Street, Austin TX 78701",
    "payer_ein": "67-8901234",
    "payer_name": "Global Consulting Group LLC",
    "payer_address": "500 Business Park, Dallas TX 75201",
    "nonemployee_compensation": "45,000.00",
    "federal_tax_withheld": "0.00",
    "state": "TX",
    "email": "aisha.patel@example.com",
}

MOCK_UNICODE_NAMES = {
    "form_type": "W-2",
    "tax_year": "2024",
    "employee_ssn": "567-89-0123",
    "employee_name": "José García-López",
    "employee_address": "321 Elm Street, Miami FL 33101",
    "employer_ein": "78-9012345",
    "employer_name": "François Müller & Associates",
    "employer_address": "150 International Ave, Miami FL 33102",
    "wages": "78,500.00",
    "federal_tax": "13,200.00",
    "state": "FL",
    "state_tax": "0.00",
}

MOCK_DENSE_PII = {
    "ssns": ["234-56-7890", "345-67-8901", "456-78-9012", "567-89-0123", "678-90-1234"],
    "names": [
        "Maria Elena Rodriguez", "Robert James Chen", "Aisha Fatima Patel",
        "José García-López", "Sarah Elizabeth Johnson",
    ],
    "eins": ["45-6789012", "56-7890123", "67-8901234", "78-9012345"],
    "emails": [
        "maria@example.com", "robert@example.com",
        "aisha@example.com", "jose@example.com",
    ],
    "phones": ["(555) 867-5309", "(555) 123-4567", "(555) 999-8888"],
    "addresses": [
        "742 Evergreen Terrace, Springfield IL 62704",
        "456 Oak Avenue, San Francisco CA 94102",
        "789 Maple Street, Austin TX 78701",
    ],
    "bank_routing": "021000021",
    "bank_account": "9876543210",
}

# All PII values that should NEVER appear in redacted output
ALL_PII_VALUES = {
    "234-56-7890", "345-67-8901", "456-78-9012", "567-89-0123", "678-90-1234",
    "Maria Elena Rodriguez", "Robert James Chen", "Aisha Fatima Patel",
    "José García-López", "Sarah Elizabeth Johnson",
    "45-6789012", "56-7890123", "67-8901234", "78-9012345",
    "maria.rodriguez@example.com", "aisha.patel@example.com",
    "maria@example.com", "robert@example.com", "aisha@example.com", "jose@example.com",
    "(555) 867-5309", "(555) 123-4567", "(555) 999-8888",
    "742 Evergreen Terrace", "456 Oak Avenue", "789 Maple Street",
    "321 Elm Street", "100 Corporate Blvd", "150 International Ave",
    "78901234567", "9876543210", "021000021",
}

# Values that SHOULD be preserved (financial data, states)
PRESERVED_VALUES = {
    "92,450.00", "16,200.00", "1,245.67", "45,000.00", "78,500.00",
    "5,731.90", "1,340.53", "5,100.00", "13,200.00",
    "IL", "CA", "TX", "FL",
}


def _create_text_pdf(text_lines: list[str], output_path: Path, font_size: float = 11) -> None:
    """Create a PDF with the given text lines using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Letter size

    y = 50  # Starting Y position
    for line in text_lines:
        if y > 740:  # Near bottom, create new page
            page = doc.new_page(width=612, height=792)
            y = 50
        page.insert_text(
            (50, y),
            line,
            fontsize=font_size,
            fontname="helv",
        )
        y += font_size + 4

    doc.save(str(output_path))
    doc.close()


def _pdf_to_image_pdf(input_path: Path, output_path: Path, dpi: int = 200) -> None:
    """Convert a text PDF to an image-based PDF (simulates scanning)."""
    doc = fitz.open(str(input_path))
    image_doc = fitz.open()

    for page_num in range(len(doc)):
        page = doc[page_num]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Create a new page with same dimensions
        img_page = image_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Insert the rendered image
        img_bytes = pix.tobytes("png")
        img_page.insert_image(img_page.rect, stream=img_bytes)

    image_doc.save(str(output_path))
    image_doc.close()
    doc.close()


def _pdf_to_image(input_path: Path, output_path: Path, dpi: int = 200, fmt: str = "PNG") -> None:
    """Render the first page of a PDF to an image file."""
    doc = fitz.open(str(input_path))
    page = doc[0]
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img = Image.open(io.BytesIO(pix.tobytes("png")))
    img.save(str(output_path), fmt)

    doc.close()


def generate_w2_pdf(output_path: Path | None = None) -> Path:
    """Generate a mock W-2 PDF."""
    output_path = output_path or FIXTURES_DIR / "mock_w2.pdf"
    d = MOCK_W2
    lines = [
        "Form W-2  Wage and Tax Statement  2024",
        "",
        f"a  Employee's social security number: {d['employee_ssn']}",
        "",
        f"b  Employer identification number (EIN): {d['employer_ein']}",
        "",
        f"c  Employer's name: {d['employer_name']}",
        f"   Employer's address: {d['employer_address']}",
        "",
        f"e  Employee's name: {d['employee_name']}",
        f"   Employee's email: {d['email']}",
        f"   Employee's phone: {d['phone']}",
        f"f  Employee's address: {d['employee_address']}",
        "",
        f"1  Wages, tips, other compensation:    ${d['wages']}",
        f"2  Federal income tax withheld:         ${d['federal_tax']}",
        f"3  Social security wages:               ${d['ss_wages']}",
        f"4  Social security tax withheld:        ${d['ss_tax']}",
        f"5  Medicare wages and tips:             ${d['medicare_wages']}",
        f"6  Medicare tax withheld:               ${d['medicare_tax']}",
        "",
        f"15 State: {d['state']}",
        f"16 State wages:                         ${d['state_wages']}",
        f"17 State income tax:                    ${d['state_tax']}",
    ]
    _create_text_pdf(lines, output_path)
    return output_path


def generate_1099_int_pdf(output_path: Path | None = None) -> Path:
    """Generate a mock 1099-INT PDF."""
    output_path = output_path or FIXTURES_DIR / "mock_1099_int.pdf"
    d = MOCK_1099_INT
    lines = [
        "Form 1099-INT  Interest Income  2024",
        "",
        f"PAYER'S name: {d['payer_name']}",
        f"PAYER'S address: {d['payer_address']}",
        f"PAYER'S TIN (EIN): {d['payer_ein']}",
        "",
        f"RECIPIENT'S name: {d['recipient_name']}",
        f"RECIPIENT'S address: {d['recipient_address']}",
        f"RECIPIENT'S TIN (SSN): {d['recipient_ssn']}",
        f"Account number: {d['account_number']}",
        "",
        f"1  Interest income:                     ${d['interest_income']}",
        f"2  Early withdrawal penalty:            ${d['early_withdrawal_penalty']}",
        f"3  Interest on U.S. Savings Bonds:      ${d['us_savings_bond_interest']}",
        f"4  Federal income tax withheld:          ${d['federal_tax_withheld']}",
    ]
    _create_text_pdf(lines, output_path)
    return output_path


def generate_1099_nec_pdf(output_path: Path | None = None) -> Path:
    """Generate a mock 1099-NEC PDF."""
    output_path = output_path or FIXTURES_DIR / "mock_1099_nec.pdf"
    d = MOCK_1099_NEC
    lines = [
        "Form 1099-NEC  Nonemployee Compensation  2024",
        "",
        f"PAYER'S name: {d['payer_name']}",
        f"PAYER'S address: {d['payer_address']}",
        f"PAYER'S TIN (EIN): {d['payer_ein']}",
        "",
        f"RECIPIENT'S name: {d['recipient_name']}",
        f"RECIPIENT'S address: {d['recipient_address']}",
        f"RECIPIENT'S TIN (SSN): {d['recipient_ssn']}",
        f"RECIPIENT'S email: {d['email']}",
        "",
        f"1  Nonemployee compensation:            ${d['nonemployee_compensation']}",
        f"4  Federal income tax withheld:          ${d['federal_tax_withheld']}",
        f"State: {d['state']}",
    ]
    _create_text_pdf(lines, output_path)
    return output_path


def generate_unicode_pdf(output_path: Path | None = None) -> Path:
    """Generate a mock W-2 with Unicode/accented names."""
    output_path = output_path or FIXTURES_DIR / "mock_unicode_names.pdf"
    d = MOCK_UNICODE_NAMES
    lines = [
        "Form W-2  Wage and Tax Statement  2024",
        "",
        f"a  Employee's social security number: {d['employee_ssn']}",
        f"b  Employer identification number (EIN): {d['employer_ein']}",
        f"c  Employer's name: {d['employer_name']}",
        f"   Employer's address: {d['employer_address']}",
        f"e  Employee's name: {d['employee_name']}",
        f"f  Employee's address: {d['employee_address']}",
        "",
        f"1  Wages:                               ${d['wages']}",
        f"2  Federal income tax withheld:          ${d['federal_tax']}",
        f"15 State: {d['state']}",
        f"17 State income tax:                     ${d['state_tax']}",
    ]
    _create_text_pdf(lines, output_path)
    return output_path


def generate_dense_pii_pdf(output_path: Path | None = None) -> Path:
    """Generate a PDF with many PII items (stress test)."""
    output_path = output_path or FIXTURES_DIR / "mock_dense_pii.pdf"
    d = MOCK_DENSE_PII
    lines = [
        "CONSOLIDATED TAX DOCUMENT - MULTIPLE ENTITIES",
        "",
        "SECTION 1: TAXPAYER INFORMATION",
    ]
    for i, (ssn, name) in enumerate(zip(d["ssns"], d["names"])):
        lines.append(f"  Person {i+1}: {name}")
        lines.append(f"  SSN: {ssn}")
        if i < len(d["emails"]):
            lines.append(f"  Email: {d['emails'][i]}")
        if i < len(d["phones"]):
            lines.append(f"  Phone: {d['phones'][i]}")
        if i < len(d["addresses"]):
            lines.append(f"  Address: {d['addresses'][i]}")
        lines.append("")

    lines.extend([
        "SECTION 2: EMPLOYER INFORMATION",
    ])
    for i, ein in enumerate(d["eins"]):
        lines.append(f"  Employer {i+1} EIN: {ein}")

    lines.extend([
        "",
        "SECTION 3: BANK INFORMATION",
        f"  Routing Number: {d['bank_routing']}",
        f"  Account Number: {d['bank_account']}",
        "",
        "SECTION 4: INCOME SUMMARY",
        "  Total W-2 Wages:     $92,450.00",
        "  Interest Income:     $1,245.67",
        "  1099-NEC Income:     $45,000.00",
        "  Total Income:        $138,695.67",
    ])
    _create_text_pdf(lines, output_path)
    return output_path


def generate_multi_page_pdf(output_path: Path | None = None) -> Path:
    """Generate a multi-page PDF with PII spread across pages."""
    output_path = output_path or FIXTURES_DIR / "mock_multi_page.pdf"
    lines = []
    # Generate enough content for multiple pages
    lines.extend([
        "FORM 1040 - U.S. Individual Income Tax Return - 2024",
        "",
        "Filing Status: Single",
        "",
        f"Your first name and middle initial: Maria Elena",
        f"Last name: Rodriguez",
        f"Your social security number: 234-56-7890",
        f"Home address: 742 Evergreen Terrace",
        f"City, state, ZIP: Springfield, IL 62704",
        f"Email: maria.rodriguez@example.com",
        f"Phone: (555) 867-5309",
        "",
        "INCOME",
        "",
        "1   Wages, salaries, tips (W-2 box 1):      $92,450.00",
        "2a  Tax-exempt interest:                     $0.00",
        "2b  Taxable interest (1099-INT):             $1,245.67",
        "3a  Qualified dividends:                     $0.00",
        "3b  Ordinary dividends:                      $0.00",
        "",
    ])
    # Add more lines to push to page 2
    for i in range(30):
        lines.append(f"     Schedule item {i+1}:  various deduction details here")
    lines.extend([
        "",
        "REFUND",
        "Direct deposit information:",
        f"  Routing number: 021000021",
        f"  Account number: 9876543210",
        "  Account type: Checking",
        "",
        "PAID PREPARER USE ONLY",
        f"  Preparer: Robert James Chen",
        f"  Preparer SSN/PTIN: 345-67-8901",
        f"  Firm name: First Tax Services",
        f"  Firm EIN: 56-7890123",
    ])
    _create_text_pdf(lines, output_path, font_size=10)
    return output_path


def generate_empty_pdf(output_path: Path | None = None) -> Path:
    """Generate a nearly empty PDF."""
    output_path = output_path or FIXTURES_DIR / "mock_empty.pdf"
    _create_text_pdf(["", ""], output_path)
    return output_path


def generate_scanned_w2_pdf(output_path: Path | None = None) -> Path:
    """Generate an image-based (scanned) W-2 PDF."""
    output_path = output_path or FIXTURES_DIR / "mock_w2_scanned.pdf"
    # First generate a text PDF, then convert to image-based
    text_pdf = FIXTURES_DIR / "_temp_w2_text.pdf"
    generate_w2_pdf(text_pdf)
    _pdf_to_image_pdf(text_pdf, output_path, dpi=200)
    text_pdf.unlink()  # Clean up temp file
    return output_path


def generate_w2_photo_png(output_path: Path | None = None) -> Path:
    """Generate a PNG image of a W-2 (simulates phone photo)."""
    output_path = output_path or FIXTURES_DIR / "mock_w2_photo.png"
    text_pdf = FIXTURES_DIR / "_temp_w2_photo.pdf"
    generate_w2_pdf(text_pdf)
    _pdf_to_image(text_pdf, output_path, dpi=200, fmt="PNG")
    text_pdf.unlink()
    return output_path


def generate_w2_photo_jpg(output_path: Path | None = None) -> Path:
    """Generate a JPG image of a W-2."""
    output_path = output_path or FIXTURES_DIR / "mock_w2_photo.jpg"
    text_pdf = FIXTURES_DIR / "_temp_w2_jpg.pdf"
    generate_w2_pdf(text_pdf)
    _pdf_to_image(text_pdf, output_path, dpi=200, fmt="JPEG")
    text_pdf.unlink()
    return output_path


def generate_all_fixtures() -> dict[str, Path]:
    """Generate all mock fixtures and return paths."""
    fixtures = {
        "w2": generate_w2_pdf(),
        "1099_int": generate_1099_int_pdf(),
        "1099_nec": generate_1099_nec_pdf(),
        "unicode": generate_unicode_pdf(),
        "dense_pii": generate_dense_pii_pdf(),
        "multi_page": generate_multi_page_pdf(),
        "empty": generate_empty_pdf(),
        "w2_scanned": generate_scanned_w2_pdf(),
        "w2_photo_png": generate_w2_photo_png(),
        "w2_photo_jpg": generate_w2_photo_jpg(),
    }
    return fixtures


def validate_fixture(path: Path, expected_strings: list[str] | None = None) -> bool:
    """Validate a generated PDF fixture by reading it back.

    Args:
        path: Path to the PDF file.
        expected_strings: Strings that must be present in extracted text.

    Returns:
        True if validation passes.
    """
    assert path.exists(), f"Fixture not found: {path}"
    assert path.stat().st_size > 0, f"Fixture is empty: {path}"

    if path.suffix.lower() == ".pdf":
        doc = fitz.open(str(path))
        assert len(doc) >= 1, f"PDF has no pages: {path}"
        text = ""
        for page in doc:
            text += page.get_text("text")
        doc.close()

        if expected_strings:
            for s in expected_strings:
                assert s in text, f"Expected '{s}' not found in {path.name}. Got: {text[:200]}..."

    return True


def validate_all_fixtures() -> None:
    """Validate all generated fixtures."""
    validate_fixture(
        FIXTURES_DIR / "mock_w2.pdf",
        ["234-56-7890", "Maria Elena Rodriguez", "45-6789012", "92,450.00"],
    )
    validate_fixture(
        FIXTURES_DIR / "mock_1099_int.pdf",
        ["345-67-8901", "Robert James Chen", "1,245.67"],
    )
    validate_fixture(
        FIXTURES_DIR / "mock_1099_nec.pdf",
        ["456-78-9012", "Aisha Fatima Patel", "45,000.00"],
    )
    validate_fixture(
        FIXTURES_DIR / "mock_unicode_names.pdf",
        ["567-89-0123", "78,500.00"],
    )
    validate_fixture(FIXTURES_DIR / "mock_dense_pii.pdf", ["234-56-7890", "678-90-1234"])
    validate_fixture(FIXTURES_DIR / "mock_multi_page.pdf", ["234-56-7890", "021000021"])
    validate_fixture(FIXTURES_DIR / "mock_empty.pdf")
    validate_fixture(FIXTURES_DIR / "mock_w2_scanned.pdf")  # Image PDF — no text extraction
    assert (FIXTURES_DIR / "mock_w2_photo.png").exists()
    assert (FIXTURES_DIR / "mock_w2_photo.png").stat().st_size > 0
    assert (FIXTURES_DIR / "mock_w2_photo.jpg").exists()
    assert (FIXTURES_DIR / "mock_w2_photo.jpg").stat().st_size > 0

    print("✅ All fixtures validated successfully!")


if __name__ == "__main__":
    print("Generating mock tax form fixtures...")
    fixtures = generate_all_fixtures()
    for name, path in fixtures.items():
        print(f"  ✓ {name}: {path} ({path.stat().st_size} bytes)")

    print("\nValidating fixtures...")
    validate_all_fixtures()
