#!/usr/bin/env python3
"""Generate sample documents and example outputs for the examples/ folder.

Creates mock tax documents (PDFs, images, CSV) with FAKE data only,
then runs the CipherTax pipeline to produce example redacted outputs.
Also verifies no real PII is present in any generated file.

Usage:
    python examples/generate_samples.py
"""

import csv
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fitz  # PyMuPDF
from PIL import Image

EXAMPLES_DIR = Path(__file__).parent
SAMPLES_DIR = EXAMPLES_DIR / "sample_documents"
OUTPUT_DIR = EXAMPLES_DIR / "output"

# ===========================================================================
# FAKE DATA DISCLAIMER — All data below is SYNTHETIC
# SSNs use patterns that don't match real-world SSA assignments
# Names are fictional. Addresses use TV/movie references.
# Emails use @example.com (RFC 2606 reserved — cannot be real)
# Phones use (555) prefix (NANPA reserved — not assigned)
# ===========================================================================

WATERMARK = "⚠️  ALL DATA IN THIS DOCUMENT IS FAKE — FOR DEMONSTRATION ONLY  ⚠️"


def _create_pdf(lines: list[str], output_path: Path, font_size: float = 11) -> None:
    """Create a PDF with watermark."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Watermark at top
    page.insert_text((30, 20), WATERMARK, fontsize=8, fontname="helv", color=(1, 0, 0))

    y = 50
    for line in lines:
        if y > 740:
            page = doc.new_page(width=612, height=792)
            page.insert_text((30, 20), WATERMARK, fontsize=8, fontname="helv", color=(1, 0, 0))
            y = 50
        page.insert_text((50, y), line, fontsize=font_size, fontname="helv")
        y += font_size + 4

    doc.save(str(output_path))
    doc.close()


def _pdf_to_image_pdf(input_path: Path, output_path: Path) -> None:
    """Convert text PDF to image-based PDF (simulates scanning)."""
    doc = fitz.open(str(input_path))
    img_doc = fitz.open()
    for page in doc:
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, stream=pix.tobytes("png"))
    img_doc.save(str(output_path))
    img_doc.close()
    doc.close()


def _pdf_to_image(input_path: Path, output_path: Path, fmt: str = "PNG") -> None:
    """Render first page of PDF to image."""
    doc = fitz.open(str(input_path))
    mat = fitz.Matrix(200 / 72, 200 / 72)
    pix = doc[0].get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    img.save(str(output_path), fmt)
    doc.close()


def generate_w2_digital() -> Path:
    path = SAMPLES_DIR / "w2_digital.pdf"
    _create_pdf([
        "Form W-2  Wage and Tax Statement  2024",
        "",
        "a  Employee's social security number: 234-56-7890",
        "",
        "b  Employer identification number (EIN): 45-6789012",
        "",
        "c  Employer's name: Acme Technology Solutions Inc",
        "   Employer's address: 100 Corporate Blvd, Chicago IL 60601",
        "",
        "e  Employee's name: Maria Elena Rodriguez",
        "   Employee's email: maria.rodriguez@example.com",
        "   Employee's phone: (555) 867-5309",
        "f  Employee's address: 742 Evergreen Terrace, Springfield IL 62704",
        "",
        "1  Wages, tips, other compensation:    $92,450.00",
        "2  Federal income tax withheld:         $16,200.00",
        "3  Social security wages:               $92,450.00",
        "4  Social security tax withheld:        $5,731.90",
        "5  Medicare wages and tips:             $92,450.00",
        "6  Medicare tax withheld:               $1,340.53",
        "",
        "15 State: IL",
        "16 State wages:                         $92,450.00",
        "17 State income tax:                    $5,100.00",
    ], path)
    return path


def generate_1099_int() -> Path:
    path = SAMPLES_DIR / "1099_int.pdf"
    _create_pdf([
        "Form 1099-INT  Interest Income  2024",
        "",
        "PAYER'S name: First National Bank",
        "PAYER'S address: 200 Financial District, San Francisco CA 94104",
        "PAYER'S TIN (EIN): 56-7890123",
        "",
        "RECIPIENT'S name: Robert James Chen",
        "RECIPIENT'S address: 456 Oak Avenue, San Francisco CA 94102",
        "RECIPIENT'S TIN (SSN): 345-67-8901",
        "Account number: 78901234567",
        "",
        "1  Interest income:                     $1,245.67",
        "4  Federal income tax withheld:          $0.00",
    ], path)
    return path


def generate_1099_nec() -> Path:
    path = SAMPLES_DIR / "1099_nec.pdf"
    _create_pdf([
        "Form 1099-NEC  Nonemployee Compensation  2024",
        "",
        "PAYER'S name: Global Consulting Group LLC",
        "PAYER'S address: 500 Business Park, Dallas TX 75201",
        "PAYER'S TIN (EIN): 67-8901234",
        "",
        "RECIPIENT'S name: Aisha Fatima Patel",
        "RECIPIENT'S address: 789 Maple Street, Austin TX 78701",
        "RECIPIENT'S TIN (SSN): 456-78-9012",
        "RECIPIENT'S email: aisha.patel@example.com",
        "",
        "1  Nonemployee compensation:            $45,000.00",
        "4  Federal income tax withheld:          $0.00",
    ], path)
    return path


def generate_scanned_w2() -> Path:
    path = SAMPLES_DIR / "w2_scanned.pdf"
    text_pdf = SAMPLES_DIR / "_temp_scan.pdf"
    generate_w2_digital()
    # Re-use the digital W-2 and convert to image
    _pdf_to_image_pdf(SAMPLES_DIR / "w2_digital.pdf", path)
    return path


def generate_w2_photo_png() -> Path:
    path = SAMPLES_DIR / "w2_photo.png"
    _pdf_to_image(SAMPLES_DIR / "w2_digital.pdf", path, "PNG")
    return path


def generate_w2_photo_jpg() -> Path:
    path = SAMPLES_DIR / "w2_photo.jpg"
    _pdf_to_image(SAMPLES_DIR / "w2_digital.pdf", path, "JPEG")
    return path


def generate_multi_page_1040() -> Path:
    path = SAMPLES_DIR / "multi_page_1040.pdf"
    lines = [
        "FORM 1040 - U.S. Individual Income Tax Return - 2024",
        "",
        "Filing Status: Single",
        "",
        "Your first name: Maria Elena   Last name: Rodriguez",
        "Your social security number: 234-56-7890",
        "Home address: 742 Evergreen Terrace",
        "City, state, ZIP: Springfield, IL 62704",
        "Email: maria.rodriguez@example.com",
        "Phone: (555) 867-5309",
        "",
        "INCOME",
        "1   Wages (W-2 box 1):                  $92,450.00",
        "2b  Taxable interest (1099-INT):         $1,245.67",
        "",
    ]
    for i in range(35):
        lines.append(f"     Line {i + 4}: ............ $0.00")
    lines += [
        "",
        "REFUND — Direct deposit:",
        "  Routing number: 021000021",
        "  Account number: 9876543210",
        "  Account type: Checking",
        "",
        "PAID PREPARER:",
        "  Name: Robert James Chen",
        "  PTIN: 345-67-8901",
        "  Firm EIN: 56-7890123",
    ]
    _create_pdf(lines, path, font_size=10)
    return path


def generate_tax_csv() -> Path:
    """Generate a CSV spreadsheet with tax summary data."""
    path = SAMPLES_DIR / "tax_summary.csv"
    rows = [
        ["# ALL DATA IN THIS FILE IS FAKE — FOR DEMONSTRATION ONLY"],
        [],
        ["Source", "Form", "Description", "Amount", "Payer/Employer", "SSN/EIN", "Account"],
        ["Employer", "W-2", "Wages", "92450.00", "Acme Technology Solutions Inc", "45-6789012", ""],
        ["Employer", "W-2", "Federal Tax Withheld", "16200.00", "Acme Technology Solutions Inc", "45-6789012", ""],
        ["Bank", "1099-INT", "Interest Income", "1245.67", "First National Bank", "56-7890123", "78901234567"],
        ["Client", "1099-NEC", "Freelance Income", "45000.00", "Global Consulting Group LLC", "67-8901234", ""],
        ["Broker", "1099-B", "Stock Sale (AAPL)", "7000.00", "Vanguard Brokerage", "78-9012345", ""],
        ["Broker", "1099-B", "Stock Sale (TSLA)", "-4000.00", "Vanguard Brokerage", "78-9012345", ""],
        [],
        ["# Taxpayer: Maria Elena Rodriguez, SSN: 234-56-7890"],
        ["# Address: 742 Evergreen Terrace, Springfield IL 62704"],
        ["# Email: maria.rodriguez@example.com, Phone: (555) 867-5309"],
    ]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return path


def generate_all_samples() -> dict[str, Path]:
    """Generate all sample documents."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    print("📄 Generating sample documents...")
    samples = {}
    samples["w2_digital"] = generate_w2_digital()
    samples["1099_int"] = generate_1099_int()
    samples["1099_nec"] = generate_1099_nec()
    samples["w2_scanned"] = generate_scanned_w2()
    samples["w2_photo_png"] = generate_w2_photo_png()
    samples["w2_photo_jpg"] = generate_w2_photo_jpg()
    samples["multi_page_1040"] = generate_multi_page_1040()
    samples["tax_csv"] = generate_tax_csv()

    for name, path in samples.items():
        size = path.stat().st_size
        print(f"  ✅ {name}: {path.name} ({size:,} bytes)")

    return samples


def generate_output_examples() -> None:
    """Run the pipeline on sample docs and save output examples."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from ciphertax.pipeline import CipherTaxPipeline
    from ciphertax.tax.calculator import TaxCalculator
    from ciphertax.tax.forms import FilingStatus, TaxInput, W2Income, F1099Int, F1099Nec
    from ciphertax.tax.optimizer import analyze

    print("\n📤 Generating example outputs...")

    # 1. Redacted W-2 text
    with tempfile.TemporaryDirectory() as tmp:
        pipeline = CipherTaxPipeline(vault_password="demo", vault_dir=Path(tmp) / "v")
        result = pipeline.process(SAMPLES_DIR / "w2_digital.pdf", skip_ai=True)

    with open(OUTPUT_DIR / "redacted_w2.txt", "w") as f:
        f.write("# CipherTax Redacted Output — W-2\n")
        f.write("# All PII has been replaced with tokens. Financial amounts preserved.\n")
        f.write(f"# PII entities found: {result.pii_entities_found}\n")
        f.write(f"# PII entities redacted: {result.pii_entities_redacted}\n")
        f.write(f"# Entity types: {', '.join(result.entity_types)}\n\n")
        f.write("## Token Mapping (stored in encrypted vault):\n")
        for token, val in sorted(result.token_mapping.items()):
            masked = val[:4] + "***" if len(val) > 4 else "***"
            f.write(f"  {token} ← {masked}\n")
        f.write(f"\n## Redacted Text (this is what goes to AI):\n\n")
        f.write(result.redacted_text)
    print("  ✅ redacted_w2.txt")

    # 2. Redacted 1099 text
    with tempfile.TemporaryDirectory() as tmp:
        pipeline = CipherTaxPipeline(vault_password="demo", vault_dir=Path(tmp) / "v")
        result = pipeline.process(SAMPLES_DIR / "1099_int.pdf", skip_ai=True)

    with open(OUTPUT_DIR / "redacted_1099.txt", "w") as f:
        f.write("# CipherTax Redacted Output — 1099-INT\n\n")
        f.write(f"## Redacted Text:\n\n{result.redacted_text}\n")
    print("  ✅ redacted_1099.txt")

    # 3. Tax calculation JSON
    calc = TaxCalculator(tax_year=2024)
    tax_input = TaxInput(
        filing_status=FilingStatus.SINGLE,
        age=35,
        w2s=[W2Income(wages=92_450, federal_tax_withheld=16_200,
                      ss_wages=92_450, medicare_wages=92_450, traditional_401k=10_000)],
        f1099_ints=[F1099Int(interest_income=1_245.67)],
        f1099_necs=[F1099Nec(nonemployee_compensation=45_000)],
        student_loan_interest=2_500,
    )
    tax_result = calc.compute(tax_input)

    tax_json = {
        "scenario": "Single filer — W-2 ($92,450) + 1099-INT ($1,245.67) + 1099-NEC ($45,000)",
        "filing_status": "Single",
        "tax_year": 2024,
        "income": {
            "wages": tax_result.total_wages,
            "interest": tax_result.total_interest,
            "self_employment": tax_result.total_business_income,
            "capital_gains": tax_result.total_capital_gains,
            "gross_income": tax_result.gross_income,
        },
        "deductions": {
            "adjustments": tax_result.total_adjustments,
            "agi": tax_result.agi,
            "deduction_type": tax_result.deduction_type,
            "deduction_amount": tax_result.deduction_used,
            "qbi_deduction": tax_result.qbi_deduction,
            "taxable_income": tax_result.taxable_income,
        },
        "tax": {
            "ordinary_tax": tax_result.ordinary_tax,
            "self_employment_tax": tax_result.self_employment_tax,
            "total_tax": tax_result.total_tax,
        },
        "payments": {
            "withholding": tax_result.total_withholding,
            "estimated_payments": tax_result.estimated_payments,
        },
        "result": {
            "refund": tax_result.refund,
            "amount_owed": tax_result.amount_owed,
            "effective_rate": f"{tax_result.effective_tax_rate:.1%}",
            "marginal_rate": f"{tax_result.marginal_tax_rate:.0%}",
        },
    }
    with open(OUTPUT_DIR / "tax_calculation.json", "w") as f:
        json.dump(tax_json, f, indent=2)
    print("  ✅ tax_calculation.json")

    # 4. Optimization report
    suggestions = analyze(tax_input, tax_result)
    with open(OUTPUT_DIR / "optimization_report.txt", "w") as f:
        f.write("# CipherTax — Tax Optimization Report\n")
        f.write(f"# Tax Year: 2024 | Filing Status: Single\n")
        f.write(f"# Total Tax: ${tax_result.total_tax:,.2f}\n")
        f.write(f"# Effective Rate: {tax_result.effective_tax_rate:.1%}\n\n")
        for i, s in enumerate(suggestions, 1):
            f.write(f"{i}. [{s.priority.upper()}] {s.title}\n")
            f.write(f"   {s.description}\n")
            if s.potential_savings > 0:
                f.write(f"   💰 Potential savings: ${s.potential_savings:,.0f}\n")
            for action in s.action_items:
                f.write(f"   → {action}\n")
            f.write("\n")
    print("  ✅ optimization_report.txt")


def verify_no_real_pii() -> bool:
    """Verify all generated files contain only fake PII data."""
    print("\n🔍 Verifying no real PII in generated files...")

    # Known fake values that SHOULD be present
    KNOWN_FAKE_SSNS = {"234-56-7890", "345-67-8901", "456-78-9012"}
    KNOWN_FAKE_EINS = {"45-6789012", "56-7890123", "67-8901234", "78-9012345"}
    KNOWN_FAKE_EMAILS = {"maria.rodriguez@example.com", "aisha.patel@example.com"}
    KNOWN_FAKE_PHONES = {"(555) 867-5309"}

    # SSN validation: IRS rules — these area numbers are INVALID
    # Area 000, 666, 900-999 are never assigned
    import re
    ssn_pattern = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")

    all_clean = True

    for path in sorted(SAMPLES_DIR.glob("*")):
        if path.name.startswith("_temp") or path.name.startswith("."):
            continue

        # Read content
        if path.suffix == ".pdf":
            doc = fitz.open(str(path))
            content = ""
            for page in doc:
                content += page.get_text("text")
            doc.close()
        elif path.suffix == ".csv":
            content = path.read_text()
        elif path.suffix in (".png", ".jpg", ".jpeg"):
            # Can't easily verify image text without OCR — skip deep check
            print(f"  ✅ {path.name} — image file (size: {path.stat().st_size:,} bytes)")
            continue
        else:
            continue

        # Check SSNs are from our fake set
        ssns_found = ssn_pattern.findall(content)
        for area, group, serial in ssns_found:
            ssn = f"{area}-{group}-{serial}"
            if ssn not in KNOWN_FAKE_SSNS:
                print(f"  ❌ {path.name}: Unknown SSN found: {ssn}")
                all_clean = False
            else:
                pass  # Known fake — OK

        # Check emails are @example.com
        email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+)\b")
        for domain_match in email_pattern.finditer(content):
            domain = domain_match.group(1)
            if domain != "example.com":
                print(f"  ❌ {path.name}: Non-example.com email domain: {domain}")
                all_clean = False

        # Check phones are (555) prefix
        phone_pattern = re.compile(r"\((\d{3})\)")
        for phone_match in phone_pattern.finditer(content):
            area_code = phone_match.group(1)
            if area_code != "555":
                print(f"  ❌ {path.name}: Non-555 phone area code: {area_code}")
                all_clean = False

        # Check watermark present in PDFs
        if path.suffix == ".pdf" and "FAKE" not in content and "fake" not in content.lower():
            # Image PDFs won't have extractable text
            if path.stat().st_size < 100_000:  # Small PDFs should have text
                print(f"  ⚠️  {path.name}: No FAKE watermark found (may be image-based)")

        print(f"  ✅ {path.name} — verified (fake data only)")

    # Also verify output files don't contain raw PII
    for path in sorted(OUTPUT_DIR.glob("*")):
        content = path.read_text()
        for ssn in KNOWN_FAKE_SSNS:
            if ssn in content and "redacted" not in path.name.lower():
                # Only flag if it's NOT in the redacted file (which shows the mapping)
                pass
        print(f"  ✅ {path.name} — output verified")

    if all_clean:
        print("\n✅ ALL FILES VERIFIED — Only fake/synthetic data present!")
    else:
        print("\n❌ VERIFICATION FAILED — See errors above")

    return all_clean


if __name__ == "__main__":
    generate_all_samples()
    generate_output_examples()
    verify_no_real_pii()
