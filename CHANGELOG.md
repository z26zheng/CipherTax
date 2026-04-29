# Changelog

All notable changes to CipherTax will be documented in this file.

## [0.2.0] — 2025-04-29 (Security Hardening Release)

This release addresses critical security findings from a third-party review.
**All users of v0.1.0 should upgrade immediately.**

### 🔴 Security — HIGH severity fixes

- **H4: Comprehensive safety check** — The pre-send safety check now runs the
  full PII detector on text about to be sent to AI. Previously only checked
  for SSN patterns. Now catches SSN, EIN, ITIN, names, emails, phone numbers,
  addresses, bank accounts, and routing numbers. Raises new `PIILeakError`
  on detection.
- **H6: Fixed SSN detection bug** — Removed broken negative-lookahead regex
  that caused SSNs with 00 group or 0000 serial (e.g., `123-00-4567`) to
  NOT be detected. They are now properly redacted.
- **H7: Token collision protection** — Tokens now use random session prefixes
  (e.g., `[CT_a3f9_SSN_1]` instead of `[SSN_1]`). Pre-existing token-like
  patterns in input documents are escaped to prevent rehydration substitution
  attacks.
- **M5: Strict redaction** — Token format `[CT_<prefix>_TYPE_N]` is now
  collision-proof against literal text in input.
- **M6: Fatal safety failures** — `PIILeakError` is now raised (not silently
  caught). The redacted_text is replaced with a placeholder when a leak is
  detected, preventing accidental display of leaked PII.

### 🟠 Vault hygiene fixes

- **H1: Vault password no longer printed to stdout** — The CLI now uses
  `click.prompt(hide_input=True)` for password entry. Passwords never appear
  in terminal scrollback, logs, or screenshots.
- **H2: Vault is now lazy and opt-in** — `persist_vault=False` is the new
  default. The vault file is only created if the user explicitly opts in
  with `--persist-vault`. In-memory mappings are cleared on process exit.
- **H3: Inspect mode never creates a vault** — Dry-run mode no longer leaves
  encrypted PII files on disk.
- **M7: --output no longer dumps PII** — The `--output` flag now writes only
  the sanitized output (redacted text, tokens). To include the PII↔token
  mapping, users must explicitly pass `--include-secrets` (with warnings).
- **M8: Password via CLI argument removed** — Passwords are now only accepted
  via interactive prompt or `vault_password` parameter (Python API).

### 📚 Documentation

- **M4: Reconciled AES references** — README consistently says
  "Fernet/AES-128-CBC + HMAC-SHA256" (matches actual implementation).
- Updated test count (159 tests) and Layer 4 description.

### Test Coverage

- Added tests for SSN edge cases (123-00-4567, etc.)
- Added tests for token collision protection
- Added tests for safety check catching email, phone, etc.
- Total: **159 tests passing** (up from 152).

---

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
- **CPA-style questionnaire**: Document checklist, applicable forms determination, filing status
- **Tax optimizer**: Retirement contribution, SEP-IRA, HSA, tax-loss harvesting suggestions
- **CLI**: `ciphertax process`, `ciphertax inspect`, `ciphertax vault` commands
- **152 tests**: Unit, integration, PII leak prevention, edge cases, tax calculations
- **Sample documents**: Mock W-2, 1099-INT, 1099-NEC, scanned PDFs, phone photos, CSV
- **Example outputs**: Redacted text, tax calculation JSON, optimization report
