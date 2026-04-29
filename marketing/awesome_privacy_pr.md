# Awesome Privacy — Pull Request Draft

## Target repos:
- https://github.com/pluja/awesome-privacy
- https://github.com/Lissy93/awesome-privacy
- https://github.com/humanetech-community/awesome-humane-tech

## PR Title
Add CipherTax — PII redaction for safely using AI with tax documents

## Entry to add (under "AI Privacy" or "Finance" section):

### CipherTax
- **[CipherTax](https://github.com/z26zheng/CipherTax)** — Safely use AI for tax filing by redacting PII locally before sending to cloud APIs. Replaces SSNs, names, addresses with tokens; keeps financial amounts. Encrypted local vault, 152 tests, MIT license. `Python`

## PR Description:
CipherTax is an open-source privacy tool that lets users safely leverage AI (Claude) for tax assistance without exposing personally identifiable information to cloud servers.

Key features:
- Microsoft Presidio + custom recognizers for tax-specific PII (SSN, EIN, ITIN, bank accounts)
- Smart tokenization: identity → tokens, financial amounts → preserved
- AES-encrypted local vault for PII storage
- 5-level Data Sensitivity classification framework
- 152 tests including 29 PII leak prevention tests
- Supports PDFs, scanned documents, phone photos (OCR)
