# Changelog

All notable changes to CipherTax will be documented in this file.

## [0.1.0] — 2025-04-29

### Added
- **PII Redaction Pipeline**: Extract text from PDFs/images → detect PII → tokenize → encrypted vault → send sanitized text to Claude → rehydrate response
- **Microsoft Presidio integration**: Industry-standard PII detection with custom tax recognizers (SSN, EIN, ITIN, bank accounts, routing numbers)
- **Smart tokenization**: Identity data redacted, financial amounts preserved for tax calculations
- **Encrypted vault**: Fernet/AES-128-CBC with PBKDF2 (600K iterations) for PII storage
- **Safety check**: Pre-send SSN pattern detection blocks API calls if PII leaks through
- **Image support**: Direct OCR for PNG, JPG, TIFF, BMP, WebP files
- **Scanned PDF support**: Tesseract OCR for image-based PDFs
- **Tax calculation engine**: Full Form 1040 flow for tax year 2024
  - 7 marginal tax brackets × 4 filing statuses
  - Standard and itemized deductions (SALT cap, medical threshold, charitable limits)
  - Self-employment tax (Schedule SE)
  - Capital gains (short-term/long-term, $3K loss limit)
  - QBI deduction (Section 199A)
  - Child Tax Credit with phaseout
  - NIIT (3.8%) and Additional Medicare Tax (0.9%)
- **Tax Data Sensitivity Levels (DSL)**: 5-level classification framework
- **CPA-style questionnaire**: Document checklist, filing status determination, applicable forms
- **Tax optimizer**: Retirement contribution, SEP-IRA, HSA, tax-loss harvesting suggestions
- **CLI**: `ciphertax process`, `ciphertax inspect`, `ciphertax vault` commands
- **152 tests**: Unit, integration, PII leak prevention, edge cases, tax calculations
- **Sample documents**: Mock W-2, 1099-INT, 1099-NEC, scanned PDFs, phone photos, CSV
- **Example outputs**: Redacted text, tax calculation JSON, optimization report
