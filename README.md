# 🔐 CipherTax

**Safely use AI for tax filing — your personal data never leaves your machine.**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-152%20passing-brightgreen.svg)](#tests)

---

## The Problem: AI + Tax Documents = Privacy Risk

You want to use AI to help with your taxes. You upload your W-2. The AI now has:

- Your **Social Security Number**
- Your **full legal name and home address**
- Your **employer's EIN**
- Your **bank account and routing numbers**
- Your **income, phone number, email**

This data is sent to cloud servers. It may be logged, cached, stored for model training, or exposed in a data breach. Under GDPR, CCPA, and other regulations, this creates real compliance risk. For individuals, it creates identity theft risk.

**The irony:** AI doesn't actually need your SSN to calculate your taxes. It needs your *income amounts*, *filing status*, and *state* — but not your identity.

## The Solution: CipherTax

CipherTax is a **local-first privacy layer** that sits between your tax documents and AI. It:

1. **Extracts** text from your tax PDFs and photos (digital + scanned/OCR)
2. **Detects** all personally identifiable information using [Microsoft Presidio](https://github.com/microsoft/presidio) + custom tax recognizers
3. **Replaces** identity data with tokens (`John Smith` → `[PERSON_1]`, `123-45-6789` → `[SSN_1]`) while **keeping financial amounts** the AI needs
4. **Stores** the real values in a locally encrypted vault (AES-256, never uploaded)
5. **Sends** only the sanitized text to Claude
6. **Restores** real PII in the AI's response locally

**Zero PII ever leaves your machine.**

```
Your Tax PDF (W-2, 1099, etc.)
        │
        ▼
┌──────────────────────────┐
│  1. EXTRACT TEXT          │  ← Runs locally (PyMuPDF + Tesseract OCR)
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  2. DETECT PII            │  ← Runs locally (Presidio + custom recognizers)
│  SSN, EIN, names, emails, │
│  phone, addresses, bank   │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│  3. SMART TOKENIZATION    │  ← Runs locally
│  "John Smith" → [PERSON_1]│
│  "123-45-6789" → [SSN_1]  │
│  "$75,000" → kept as-is ✓ │  Financial data preserved for tax math
└──────────┬───────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌────────────────┐
│ VAULT   │  │ CLAUDE API     │  ← Only tokenized text sent
│ (AES    │  │ (zero PII)     │
│ encrypt)│  │                │
└─────────┘  └───────┬────────┘
     │               │
     └───────┬───────┘
             ▼
┌──────────────────────────┐
│  4. REHYDRATE             │  ← Runs locally — restores real PII
│  [PERSON_1] → John Smith  │
│  [SSN_1] → 123-45-6789    │
└──────────────────────────┘
```

---

## What AI Sees vs What You See

### Before (Original W-2 — contains PII):
```
Form W-2  Wage and Tax Statement  2024
a  Employee's social security number: 234-56-7890
b  Employer identification number (EIN): 45-6789012
c  Employer's name: Acme Technology Solutions Inc
e  Employee's name: Maria Elena Rodriguez
   Employee's email: maria.rodriguez@example.com
   Employee's phone: (555) 867-5309
1  Wages, tips, other compensation:    $92,450.00
2  Federal income tax withheld:         $16,200.00
15 State: IL
```

### After (What Claude receives — zero PII):
```
Form W-2  Wage and Tax Statement  2024
a  [ADDRESS_1]'s social security number: [SSN_1]
b  [ORGANIZATION_6] identification number ([ORGANIZATION_8]): [EIN_1]
c  [ORGANIZATION_6]'s name: [ORGANIZATION_7]
e  [ADDRESS_1]'s name: [PERSON_1]
   [ADDRESS_1]'s email: [EMAIL_1]
   [ADDRESS_1]'s phone: [PHONE_1]
1  Wages, tips, other compensation:    $92,450.00    ← KEPT (AI needs this)
2  Federal income tax withheld:         $16,200.00    ← KEPT
15 State: IL                                          ← KEPT
```

**Notice:** SSN, name, EIN, email, phone are all replaced with tokens. But financial amounts ($92,450, $16,200) and state (IL) are preserved — Claude needs these to compute your taxes.

---

## Security In Depth

CipherTax uses **multiple layers of defense** to prevent PII leakage:

### Layer 1: PII Detection (Microsoft Presidio + Custom Recognizers)
- **Microsoft Presidio** — Industry-standard PII detection engine (7,900+ ⭐ on GitHub), used by enterprises worldwide
- **spaCy NER** — Named Entity Recognition for person names, organizations, addresses
- **Custom tax recognizers** — Purpose-built regex patterns with context awareness for:
  - SSN (with IRS-valid format validation)
  - EIN (Employer Identification Number)
  - ITIN (Individual Taxpayer Identification Number)
  - Bank account numbers (with context: "account", "deposit", etc.)
  - Routing numbers (with context: "routing", "ABA", etc.)
  - W-2 control numbers

### Layer 2: Smart Tokenization
- Identity data → deterministic tokens (`[SSN_1]`, `[PERSON_1]`)
- Same value always maps to the same token (preserves relationships)
- Financial data → kept as-is (AI needs amounts for tax calculations)
- State abbreviations → kept as-is (needed for state tax determination)

### Layer 3: Encrypted Vault
- Token ↔ PII mappings stored in **Fernet-encrypted local files**
- Encryption: **AES-128-CBC + HMAC-SHA256**
- Key derivation: **PBKDF2 with 600,000 iterations** (OWASP recommended minimum)
- Each processing session gets its own vault file
- **Secure deletion**: vault files are overwritten with random data before deletion

### Layer 4: Pre-Send Safety Check
- Last-resort regex scan for SSN patterns (`XXX-XX-XXXX`) in the text about to be sent
- If any SSN is detected in the "redacted" text, **the API call is blocked** with an error
- This catches edge cases where detection might have missed something

### Layer 5: Comprehensive Test Suite
- **152 tests** including dedicated PII leak prevention tests
- Tests process mock W-2s, 1099s, multi-page documents, and dense PII documents
- Each test verifies that **no known PII value appears in the redacted output**
- Mocked Claude API tests capture the exact payload and assert zero PII
- Image-based (scanned) PDF and phone photo (PNG/JPG) tests

### What CipherTax Does NOT Protect Against
We believe in transparency about limitations:
- **No automated system guarantees 100% PII detection.** Unusual PII formats, misspelled names, or PII embedded in unusual contexts may be missed. Always review the redacted output before sending.
- **Financial data is intentionally NOT redacted.** Income amounts, tax figures, and state abbreviations are sent to the AI because it needs them for calculations.
- **The Anthropic API key is stored locally.** Protect your `.env` file.
- **CipherTax is not tax advice software.** The tax calculator is for estimation. Consult a CPA for filing.

---

## Tax Data Sensitivity Levels (DSL)

CipherTax classifies every piece of tax data by sensitivity level, adapted from enterprise data security frameworks. This classification **drives all redaction decisions** — it's not guesswork, it's a formal policy.

| DSL | Level | Description | CipherTax Action | Risk if Exposed |
|-----|-------|-------------|------------------|-----------------|
| **1** | 🟢 **PUBLIC** | Data with no privacy risk | ✅ Send to AI as-is | None |
| **2** | 🔵 **INTERNAL** | De-identified financial data | ✅ Send to AI as-is | Low — no identity context |
| **3** | 🟡 **CONFIDENTIAL** | Personal identifiers | 🔒 Redact → token | Identity correlation |
| **4** | 🔴 **RESTRICTED** | Government IDs, bank accounts | 🔐 Redact + AES encrypt | Identity theft, financial fraud |
| **5** | ⛔ **CRITICAL** | Filing credentials, legal authority | ⛔ Never store or transmit | Catastrophic — full account takeover |

### DSL 1 — PUBLIC (Safe to share)

| Data | Examples | IRS Form Fields |
|------|----------|-----------------|
| Tax year | 2024 | 1040 header |
| Form type | W-2, 1099-INT, Schedule C | All form headers |
| Filing status | Single, MFJ, HoH | 1040 lines 1-5 |
| Number of dependents | 2, 0 | 1040 line 6d |

### DSL 2 — INTERNAL (Financial data — safe for AI)

| Data | Examples | Why AI Needs It |
|------|----------|-----------------|
| Income amounts | $75,000, $1,245.67 | Tax bracket calculation |
| Tax withheld | $12,000, $5,100 | Refund/owed computation |
| Deduction amounts | $14,000 mortgage interest | Itemized vs standard comparison |
| State abbreviation | CA, IL, TX | State tax determination |
| Business expenses | Advertising: $5,000 | Schedule C calculation |

**Key insight:** These amounts are NOT personally identifying without the identity data from DSL 3-4. The number "$75,000" doesn't tell you *who* earned it.

### DSL 3 — CONFIDENTIAL (Personal identifiers — REDACT)

| Data | Examples | Redaction | Risk |
|------|----------|-----------|------|
| Person name | John Smith, Maria Rodriguez | → `[PERSON_1]` | Identity correlation |
| Email address | john@example.com | → `[EMAIL_1]` | Phishing, spam |
| Phone number | (555) 123-4567 | → `[PHONE_1]` | Social engineering, SIM swap |
| Street address | 742 Evergreen Terrace | → `[ADDRESS_1]` | Physical location exposure |
| Date of birth | 03/15/1985 | → `[DATE_1]` | Identity verification factor |
| Employer name | Acme Corp, Google LLC | → `[ORGANIZATION_1]` | Employment verification |

### DSL 4 — RESTRICTED (Government IDs & bank info — REDACT + ENCRYPT)

| Data | Examples | Redaction | Risk |
|------|----------|-----------|------|
| **SSN** | 123-45-6789 | → `[SSN_1]` + AES vault | **Identity theft, fraudulent tax filing, credit fraud** |
| **EIN** | 12-3456789 | → `[EIN_1]` + AES vault | Business identity fraud |
| **ITIN** | 912-34-5678 | → `[ITIN_1]` + AES vault | Tax identity theft |
| **Bank account** | 1234567890 | → `[BANK_ACCT_1]` + AES vault | Unauthorized bank transactions |
| **Routing number** | 021000021 | → `[ROUTING_1]` + AES vault | ACH fraud |
| **W-2 control number** | A1B2C3D4E5 | → `[CONTROL_NUM_1]` + AES vault | W-2 forgery |

These are stored **only** in the locally encrypted vault (Fernet/AES-128-CBC + HMAC-SHA256, PBKDF2 with 600,000 iterations). The vault file is overwritten with random data before deletion.

### DSL 5 — CRITICAL (Never store or transmit)

| Data | Risk | CipherTax Policy |
|------|------|-------------------|
| **IRS e-File PIN / IP PIN** | Enables fraudulent tax return filing | ⛔ Never stored — user warned if detected |
| **Tax portal credentials** | Full account takeover | ⛔ Never stored — not processed |
| **Power of Attorney (Form 2848)** | Legal authority over tax matters | ⛔ Never stored — flagged for manual review |

> **If CipherTax detects DSL 5 data in your documents, it will warn you and refuse to process it.** These credentials should be entered directly into IRS systems, never shared with any third party including AI.

### How DSL Drives Redaction

```python
from ciphertax.tax.data_sensitivity import get_fields_safe_for_ai, get_fields_to_redact

# What's safe to send to Claude?
for field in get_fields_safe_for_ai():
    print(f"✅ {field.field_name} (DSL {field.dsl})")

# What must be redacted?
for field in get_fields_to_redact():
    print(f"🔒 {field.field_name} (DSL {field.dsl}) → {field.ai_action}")
```

---

## Tax Calculation Engine

CipherTax includes a **complete federal tax calculator** for tax year 2024 that follows the IRS Form 1040 flow:

### Example Output: Single W-2 Employee ($75,000)

```
  Filing Status:          Single
  Total Wages:            $   75,000.00
  Gross Income:           $   75,000.00
  Adjustments:            $    1,800.00    (student loan interest)
  AGI:                    $   73,200.00
  Deduction (standard):  $   14,600.00
  Taxable Income:         $   58,600.00

  Ordinary Tax:           $    7,945.00    (10% + 12% + 22% brackets)
  ─────────────────────────────────────
  TOTAL TAX:              $    7,945.00

  Federal Withholding:    $   10,500.00
  ✅ REFUND:              $    2,555.00

  Effective Tax Rate:           10.6%
  Marginal Tax Rate:              22%
```

### Example: Complex Scenario (MFJ, W-2 + Freelance + Investments + Rental)

```
  Income Summary:
  W-2 Wages:              $  135,000.00
  Self-Employment:        $   35,000.00
  Interest:               $    2,200.00
  Dividends:              $    4,500.00
  Capital Gains:          $    9,200.00
  Rental Income:          $    3,220.00
  GROSS INCOME:           $  189,120.00

  Deduction (itemized):   $   31,000.00
  QBI Deduction:          $    7,000.00
  TAXABLE INCOME:         $  148,157.33

  Ordinary Tax:           $   20,940.61
  Capital Gains Tax:      $    1,200.00
  Child Tax Credit:      -$    4,000.00    (2 children)
  Self-Employment Tax:    $    4,945.34
  TOTAL TAX:              $   23,085.95

  Withholding + Est:      $   30,000.00
  ✅ REFUND:              $    6,914.05    Effective: 12.2%
```

### What the Calculator Handles

| Feature | Details |
|---------|---------|
| **Tax Brackets** | All 7 marginal rates (10%–37%) × 4 filing statuses |
| **Standard Deduction** | Including age 65+ and blindness additions |
| **Itemized Deductions** | SALT cap ($10K), medical (7.5% AGI floor), mortgage interest, charitable |
| **Capital Gains** | Short-term (ordinary rates) + long-term (0%/15%/20%) |
| **Self-Employment Tax** | Schedule SE: 15.3% (SS + Medicare) on 92.35% of net income |
| **QBI Deduction** | Section 199A: 20% deduction with income phaseout |
| **Child Tax Credit** | $2,000/child with phaseout above $200K/$400K |
| **NIIT** | 3.8% Net Investment Income Tax above $200K/$250K |
| **Additional Medicare** | 0.9% above $200K/$250K |
| **Retirement** | IRA deduction phaseouts, 401(k) limits |

### Tax Optimization Suggestions

After computing your tax, CipherTax analyzes your return and suggests:

```
  1. [HIGH] Maximize 401(k) contributions
     You contributed $6,000. The limit is $23,000 — you have $17,000 of room.
     💰 Potential savings: $3,740

  2. [HIGH] Open a SEP-IRA for self-employment income
     You can contribute up to $7,000 to a SEP-IRA.
     💰 Potential savings: $1,540

  3. [MEDIUM] Consider tax-loss harvesting
     You have net capital gains of $9,200. Selling losers can offset gains.
     💰 Potential savings: $1,380

  4. [MEDIUM] Consider an HSA contribution
     Triple tax advantage: deductible, tax-free growth, tax-free withdrawals.
     💰 Potential savings: $913
```

---

## How to Use the Output

### 1. Review the Redacted Text
Before CipherTax sends anything to AI, review what will be sent:
```bash
ciphertax inspect w2.pdf    # Dry run — shows redacted text, nothing sent
```

### 2. Process Your Documents
```bash
ciphertax process w2.pdf --task extract     # Extract structured data
ciphertax process w2.pdf --task advise -q "Am I eligible for EITC?"
ciphertax process w2.pdf 1099-int.pdf --task file   # Filing preparation
```

### 3. Understand AI Responses
Claude's response uses the same tokens. CipherTax **automatically restores** your real PII:

**What Claude says:** `"[PERSON_1] earned $92,450.00 at [ORGANIZATION_7] (EIN [EIN_1])"`

**What you see (after rehydration):** `"Maria Elena Rodriguez earned $92,450.00 at Acme Technology Solutions Inc (EIN 45-6789012)"`

### 4. Use Tax Calculations
```python
from ciphertax.tax.calculator import TaxCalculator
from ciphertax.tax.forms import FilingStatus, TaxInput, W2Income

calc = TaxCalculator(tax_year=2024)
result = calc.compute(TaxInput(
    filing_status=FilingStatus.SINGLE,
    w2s=[W2Income(wages=75_000, federal_tax_withheld=10_500)],
))

print(f"Tax: ${result.total_tax:,.2f}")
print(f"Refund: ${result.refund:,.2f}")
print(f"Effective rate: {result.effective_tax_rate:.1%}")
```

### 5. Before Filing
- ✅ Review the AI's output for accuracy
- ✅ Cross-check tax calculations against your expectations
- ✅ Verify all income sources are included
- ✅ Consider the optimization suggestions
- ⚠️ **Consult a qualified tax professional** — CipherTax provides estimates, not tax advice
- 📝 Use the structured data to fill out your actual tax forms or input into tax filing software

---

## Installation

### Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for scanned PDFs and photos)

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows — download from https://github.com/UB-Mannheim/tesseract/wiki
```

### Install

```bash
git clone https://github.com/z26zheng/CipherTax.git
cd CipherTax

python -m venv .venv
source .venv/bin/activate    # macOS/Linux

pip install -e ".[dev]"
python -m spacy download en_core_web_sm

cp .env.example .env
# Edit .env → add your ANTHROPIC_API_KEY
```

### Run the Demo

```bash
python examples/demo_tax_filing.py
```

This runs 4 scenarios end-to-end: simple W-2 filing, complex multi-income filing, PII redaction pipeline, and CPA questionnaire.

---

## Supported Input Formats

| Format | Type | Support |
|--------|------|---------|
| Digital PDF | Text-selectable PDFs | ✅ PyMuPDF extraction |
| Scanned PDF | Image-based PDFs | ✅ Tesseract OCR |
| PNG images | Phone photos | ✅ Direct OCR |
| JPG/JPEG images | Phone photos | ✅ Direct OCR |
| TIFF images | Scanner output | ✅ Direct OCR |
| BMP, WebP | Other image formats | ✅ Direct OCR |

## Supported Tax Forms

| Form | Description |
|------|-------------|
| **W-2** | Wage and Tax Statement |
| **1099-INT** | Interest Income |
| **1099-DIV** | Dividends (qualified + ordinary) |
| **1099-NEC** | Nonemployee Compensation |
| **1099-B** | Brokerage Proceeds (stocks, crypto) |
| **1099-R** | Retirement Distributions |
| **K-1** | Partnership / S-Corp Income |
| **SSA-1099** | Social Security Benefits |
| **Schedule C** | Business Profit/Loss |
| **Schedule E** | Rental Income |
| **1040** | Individual Income Tax Return |

## PII Entities Detected

| Entity | Detection Method | Example | Action |
|--------|-----------------|---------|--------|
| SSN | Custom regex + validation | 123-45-6789 | 🔴 Always redact |
| EIN | Custom regex + context | 98-7654321 | 🔴 Always redact |
| ITIN | Custom regex | 912-34-5678 | 🔴 Always redact |
| Person names | spaCy NER | John Smith | 🔴 Always redact |
| Email | Presidio built-in | john@example.com | 🔴 Always redact |
| Phone | Presidio built-in | (555) 123-4567 | 🔴 Always redact |
| Bank account | Custom + context | 12345678901 | 🔴 Always redact |
| Routing number | Custom + context | 021000021 | 🔴 Always redact |
| Addresses | spaCy NER | 123 Main St | 🔴 Always redact |
| Income amounts | — | $75,000 | 🟢 **Kept** for tax math |
| State | — | CA, IL, TX | 🟢 **Kept** for state tax |
| Filing status | — | Single, MFJ | 🟢 **Kept** for calculations |

---

## Tests

152 tests covering:

| Category | Count | What's Tested |
|----------|-------|---------------|
| PII Detection | 10 | SSN, EIN, names, emails, phones, overlap resolution |
| Tokenization | 9 | Redaction, consistency, roundtrip, normalization |
| Rehydration | 7 | Token restoration, unknown tokens, formatting |
| Vault | 12 | Encryption, load/store, wrong password, secure delete |
| **PII Leak Prevention** | **29** | **No SSN/name/EIN/email/phone in redacted output across all form types** |
| Pipeline | 22 | End-to-end, multi-doc, scanned PDF, images, Claude mock |
| Edge Cases | 26 | Empty PDF, Unicode, duplicate PII, ZIP codes, file routing |
| Tax Calculator | 37 | Brackets, SE tax, QBI, credits, optimizer, questionnaire |

```bash
pytest                    # Run all 152 tests
pytest -v                 # Verbose output
pytest --cov=ciphertax    # With coverage report
```

---

## Project Structure

```
CipherTax/
├── src/ciphertax/
│   ├── extraction/          # PDF + image text extraction (PyMuPDF, Tesseract)
│   ├── detection/           # PII detection (Presidio + custom tax recognizers)
│   ├── redaction/           # Tokenizer (PII → tokens) + Rehydrator (tokens → PII)
│   ├── vault/               # Encrypted local storage (Fernet/AES-256)
│   ├── ai/                  # Claude API client (sends only redacted text)
│   ├── tax/                 # Tax calculation engine
│   │   ├── data/            # Federal tax constants by year
│   │   ├── calculator.py    # Full 1040 computation
│   │   ├── forms.py         # Data models for all tax forms
│   │   ├── questionnaire.py # CPA-style intake
│   │   └── optimizer.py     # Tax optimization suggestions
│   ├── pipeline.py          # Orchestrates the full workflow
│   └── cli.py               # Command-line interface
├── examples/
│   └── demo_tax_filing.py   # End-to-end demo with 4 scenarios
├── tests/                   # 152 tests (pytest)
├── pyproject.toml
└── README.md
```

## Contributing

Contributions welcome! Areas that need help:

- **State tax support** — Currently federal-only
- **Tax year 2025 data** — Adding new year's brackets and limits
- **Additional form recognizers** — Better detection for specific form layouts
- **UI/Web interface** — Currently CLI + Python API only

## License

MIT — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

CipherTax is a **privacy tool and tax estimation tool**, not a certified tax preparation product.

- **PII detection is not guaranteed to be 100% complete.** Always review the redacted output before sending to any AI service. Unusual formats or embedded PII may not be detected.
- **Tax calculations are estimates** based on 2024 IRS data. They do not account for every edge case, state taxes, or AMT in all scenarios.
- **This is not tax advice.** Consult a qualified tax professional (CPA or Enrolled Agent) before filing your return.
- **You are responsible** for reviewing all output and ensuring accuracy before filing.
