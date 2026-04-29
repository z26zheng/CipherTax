# 🔐 CipherTax

**Privacy-preserving tax assistant — redacts PII locally before sending to AI.**

No personally identifiable information ever leaves your machine. CipherTax extracts data from tax documents (W-2, 1099, etc.), redacts all PII with placeholder tokens, sends only sanitized data to Claude for processing, then restores the real values locally.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)

---

## How It Works

```
Your Tax PDF (W-2, 1099, etc.)
        │
        ▼
┌─────────────────────────┐
│  1. EXTRACT TEXT         │  ← Local only (PyMuPDF + Tesseract OCR)
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  2. DETECT PII           │  ← Local only (Microsoft Presidio + custom recognizers)
│  SSN, EIN, names,        │
│  addresses, bank info    │
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  3. SMART TOKENIZATION   │  ← Local only
│  "John Smith" → [PERSON_1]│
│  "123-45-6789" → [SSN_1] │
│  "$75,000" → kept as-is  │  ← Income amounts preserved for tax math
└─────────┬───────────────┘
          │
    ┌─────┴──────┐
    ▼            ▼
┌────────┐  ┌──────────────┐
│ VAULT  │  │ CLAUDE API   │  ← Only redacted text sent
│ (AES)  │  │ (zero PII)   │
└────────┘  └──────┬───────┘
    │              │
    └──────┬───────┘
           ▼
┌─────────────────────────┐
│  4. REHYDRATE            │  ← Local only — restore real PII from vault
└─────────────────────────┘
```

### Key Design Decisions

- **Tax-smart redaction**: Identity data (SSN, names, addresses) is redacted, but financial amounts and state info are kept — Claude needs them for tax calculations
- **Microsoft Presidio**: Battle-tested PII detection (7,900+ ⭐) with custom tax recognizers for EIN, ITIN, bank accounts
- **Encrypted vault**: Token↔PII mapping stored locally with Fernet encryption (AES-128-CBC + HMAC-SHA256, PBKDF2 key derivation)
- **Safety check**: Last-resort SSN pattern detection before any data is sent to the API

## Installation

### Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for scanned PDFs)

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download installer from https://github.com/UB-Mannheim/tesseract/wiki
```

### Install CipherTax

```bash
# Clone the repository
git clone https://github.com/z26zheng/CipherTax.git
cd CipherTax

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install with dependencies
pip install -e ".[dev]"

# Download spaCy English model (required for name/address detection)
python -m spacy download en_core_web_sm
```

### Configuration

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

## Usage

### CLI

```bash
# Process a W-2 and extract structured data
ciphertax process w2.pdf --task extract

# Ask tax questions about your documents
ciphertax process w2.pdf --task advise -q "What deductions am I eligible for?"

# Process multiple documents for filing preparation
ciphertax process w2.pdf 1099-int.pdf --task file

# Review documents for completeness
ciphertax process w2.pdf --task review

# Inspect mode — see what PII would be redacted (no data sent to AI)
ciphertax inspect w2.pdf

# Force OCR for scanned documents
ciphertax process scanned-w2.pdf --ocr

# Save output to file
ciphertax process w2.pdf -o results.json

# Manage vault files
ciphertax vault list
ciphertax vault clean
```

### Python API

```python
from ciphertax.pipeline import CipherTaxPipeline
from ciphertax.ai.claude_client import TaskType

# Initialize the pipeline
pipeline = CipherTaxPipeline(vault_password="my-secure-password")

# Process a tax PDF
result = pipeline.process("w2.pdf", task=TaskType.EXTRACT)

# What was sent to AI (no PII)
print(result.redacted_text)
# "--- Page 1 ---
#  Form W-2 Wage and Tax Statement 2024
#  Employee SSN: [SSN_1]
#  Employee name: [PERSON_1]
#  Employer EIN: [EIN_1]
#  Wages: 75000.00 ..."

# AI response with real PII restored
print(result.ai_response_rehydrated)

# Token mapping (stored in encrypted vault)
print(result.token_mapping)
# {"[SSN_1]": "123-45-6789", "[PERSON_1]": "John Smith", ...}

# Clean up when done
pipeline.cleanup()
```

### Using Individual Components

```python
# Extract text from PDF
from ciphertax.extraction import extract_text_from_pdf
pages = extract_text_from_pdf("w2.pdf")

# Detect PII
from ciphertax.detection import PIIDetector
detector = PIIDetector()
entities = detector.detect(pages[0]["text"])

# Tokenize
from ciphertax.redaction import Tokenizer, Rehydrator
tokenizer = Tokenizer()
redacted_text, mapping = tokenizer.redact(text, entities)

# Secure vault
from ciphertax.vault import SecureVault
vault, password = SecureVault.create(password="my-password")
vault.store(mapping)
# ... later ...
mapping = vault.retrieve()
vault.destroy()  # Securely delete when done
```

## Supported Tax Forms

CipherTax works with any tax document, but has been optimized for:

| Form | Description | Status |
|------|-------------|--------|
| W-2 | Wage and Tax Statement | ✅ Tested |
| 1099-INT | Interest Income | ✅ Supported |
| 1099-DIV | Dividends and Distributions | ✅ Supported |
| 1099-NEC | Nonemployee Compensation | ✅ Supported |
| 1099-MISC | Miscellaneous Income | ✅ Supported |
| 1040 | Individual Income Tax Return | ✅ Supported |
| W-9 | Request for Taxpayer ID | ✅ Supported |
| K-1 | Partner's Share of Income | ✅ Supported |

## PII Entity Types

| Entity | Source | Example | Action |
|--------|--------|---------|--------|
| SSN | Presidio built-in | 123-45-6789 | 🔴 Always redact |
| EIN | Custom recognizer | 98-7654321 | 🔴 Always redact |
| ITIN | Custom recognizer | 912-34-5678 | 🔴 Always redact |
| Person names | spaCy NER | John Smith | 🔴 Always redact |
| Email | Presidio built-in | john@example.com | 🔴 Always redact |
| Phone | Presidio built-in | (555) 123-4567 | 🔴 Always redact |
| Bank account | Custom recognizer | 12345678901 | 🔴 Always redact |
| Routing number | Custom recognizer | 021000021 | 🔴 Always redact |
| Addresses | spaCy NER | 123 Main St | 🔴 Always redact |
| Income amounts | — | $75,000 | 🟢 Kept (needed for tax math) |
| State | — | CA | 🟢 Kept (needed for state tax) |
| Filing status | — | Single | 🟢 Kept (needed for tax calc) |

## Security

- **Zero PII to AI**: All personally identifiable information is replaced with tokens before any data leaves your machine
- **Encrypted vault**: Token↔PII mappings are encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
- **PBKDF2 key derivation**: 600,000 iterations (OWASP recommended minimum)
- **Secure deletion**: Vault files are overwritten with random data before deletion
- **Safety check**: Last-resort regex check for un-redacted SSN patterns before API calls
- **No database**: All data stored in local files — nothing to configure, nothing to leak

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=ciphertax

# Lint
ruff check src/
```

## Project Structure

```
CipherTax/
├── src/ciphertax/
│   ├── extraction/        # PDF text extraction (PyMuPDF + Tesseract OCR)
│   ├── detection/         # PII detection (Presidio + custom tax recognizers)
│   ├── redaction/         # Tokenizer (PII → tokens) + Rehydrator (tokens → PII)
│   ├── vault/             # Encrypted local storage (Fernet/AES)
│   ├── ai/                # Claude API client (sends only redacted text)
│   ├── pipeline.py        # Orchestrates the full workflow
│   └── cli.py             # Command-line interface
├── tests/                 # pytest test suite
├── pyproject.toml         # Project configuration
└── README.md
```

## License

MIT — see [LICENSE](LICENSE) for details.

## Disclaimer

CipherTax is a tool to help protect PII when using AI for tax-related tasks. It is **not** tax advice software. While it uses industry-standard PII detection (Microsoft Presidio), no automated system can guarantee 100% PII detection. Always review redacted output before sending to any external service. Consult a qualified tax professional for tax advice.
