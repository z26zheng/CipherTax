# CipherTax Examples

This folder contains sample documents, demo scripts, and example outputs to help you understand how CipherTax works.

> ⚠️ **All data in sample documents is FAKE** — synthetic SSNs, fictional names, TV/movie addresses, `@example.com` emails, and `(555)` phone numbers. No real PII is present.

## Quick Start

```bash
# Generate all sample documents and outputs
python examples/generate_samples.py

# Run the full demo (4 scenarios)
python examples/demo_tax_filing.py
```

## Sample Documents (`sample_documents/`)

| File | Type | Description |
|------|------|-------------|
| `w2_digital.pdf` | Digital PDF | Text-selectable W-2 form |
| `1099_int.pdf` | Digital PDF | 1099-INT (Interest Income) |
| `1099_nec.pdf` | Digital PDF | 1099-NEC (Freelance Income) |
| `w2_scanned.pdf` | Image-based PDF | Simulated scanned W-2 (requires OCR) |
| `w2_photo.png` | PNG image | Simulated phone photo of W-2 |
| `w2_photo.jpg` | JPG image | Simulated phone photo of W-2 |
| `multi_page_1040.pdf` | Digital PDF | Multi-page 1040 with bank info |
| `tax_summary.csv` | CSV spreadsheet | Tax data in tabular format |

### Regenerating Samples

```bash
python examples/generate_samples.py
```

This will:
1. Generate all sample documents with fake data
2. Run CipherTax pipeline to produce redacted outputs
3. Verify no real PII is present in any file

## Example Outputs (`output/`)

| File | Description |
|------|-------------|
| `redacted_w2.txt` | W-2 with all PII replaced by tokens — this is what gets sent to AI |
| `redacted_1099.txt` | 1099-INT with PII redacted |
| `tax_calculation.json` | Complete tax computation result as structured JSON |
| `optimization_report.txt` | Tax optimization suggestions with savings estimates |

### Example: Redacted W-2 Output

**Before (original):**
```
Employee's social security number: 234-56-7890
Employer identification number (EIN): 45-6789012
Employee's name: Maria Elena Rodriguez
Wages: $92,450.00
```

**After (redacted — sent to AI):**
```
[ADDRESS_1]'s social security number: [SSN_1]
[ORGANIZATION_6] identification number: [EIN_1]
[ADDRESS_1]'s name: [PERSON_1]
Wages: $92,450.00    ← Financial amounts KEPT
```

### Example: Tax Calculation JSON

```json
{
  "income": {
    "wages": 92450.0,
    "interest": 1245.67,
    "self_employment": 45000.0,
    "gross_income": 138695.67
  },
  "tax": {
    "ordinary_tax": 19438.01,
    "self_employment_tax": 6361.43,
    "total_tax": 25799.44
  },
  "result": {
    "refund": 0.0,
    "amount_owed": 9599.44,
    "effective_rate": "18.6%"
  }
}
```

## Demo Scripts

| Script | What It Does |
|--------|-------------|
| `demo_tax_filing.py` | Full 4-scenario demo: simple W-2, complex MFJ return, PII pipeline, CPA questionnaire |
| `generate_samples.py` | Generates all sample documents + output examples + verifies no real PII |

## How to Use These Examples

### 1. See What Gets Redacted
```bash
# Look at the sample W-2
open examples/sample_documents/w2_digital.pdf

# Look at the redacted output
cat examples/output/redacted_w2.txt
```

### 2. Run the Pipeline Yourself
```python
from ciphertax.pipeline import CipherTaxPipeline

pipeline = CipherTaxPipeline(vault_password="demo")
result = pipeline.process("examples/sample_documents/w2_digital.pdf", skip_ai=True)

print(result.redacted_text)     # What would be sent to AI
print(result.token_mapping)     # PII ↔ token mapping
```

### 3. Compute Taxes
```python
from ciphertax.tax.calculator import TaxCalculator
from ciphertax.tax.forms import FilingStatus, TaxInput, W2Income

calc = TaxCalculator(tax_year=2024)
result = calc.compute(TaxInput(
    filing_status=FilingStatus.SINGLE,
    w2s=[W2Income(wages=92_450, federal_tax_withheld=16_200)],
))
print(f"Tax: ${result.total_tax:,.2f}, Refund: ${result.refund:,.2f}")
```

### 4. Process a CSV
```python
import csv
# Read the tax_summary.csv, parse amounts, feed into TaxInput
```

## Fake Data Verification

All sample documents use provably fake data:
- **SSNs**: `234-56-7890`, `345-67-8901`, `456-78-9012` — IRS-valid format but synthetic
- **Names**: Fictional (Maria Elena Rodriguez, Robert James Chen, Aisha Fatima Patel)
- **Addresses**: TV references (742 Evergreen Terrace = The Simpsons)
- **Emails**: `@example.com` — RFC 2606 reserved domain (cannot be real)
- **Phones**: `(555)` prefix — NANPA reserved (never assigned to real numbers)
- **EINs**: Sequential pattern (`45-6789012`, etc.) — not assigned to real businesses

Each PDF includes a red watermark: `⚠️ ALL DATA IN THIS DOCUMENT IS FAKE`
