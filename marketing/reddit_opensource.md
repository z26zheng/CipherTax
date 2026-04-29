# Reddit r/opensource Post

## Title
CipherTax — Open-source tool to safely use AI for tax filing by redacting PII before sending to Claude

## Body
I open-sourced **CipherTax**, a privacy layer that lets you use AI for tax help without exposing your personal data.

**The problem:** You want AI to help calculate your taxes, but uploading your W-2 means sharing your SSN, name, address, bank info with a cloud API.

**The solution:** CipherTax extracts text from your tax documents, detects all PII (using Microsoft Presidio + custom tax recognizers), replaces identity data with tokens like `[SSN_1]` and `[PERSON_1]`, and sends only the sanitized text to Claude. Financial amounts ($75,000 wages, etc.) are kept because the AI needs them for calculations.

**What makes it interesting:**
- 5-level Data Sensitivity classification (DSL 1-5) that formally defines what's safe to send vs what must be redacted
- Encrypted local vault (AES/Fernet) for PII storage
- Pre-send safety check that blocks the API call if any SSN pattern leaks through
- 152 tests including 29 PII leak prevention tests
- Built-in federal tax calculator (2024 brackets, SE tax, capital gains, credits)
- Supports PDFs, scanned documents, and phone photos (PNG/JPG via OCR)

**Tech:** Python, Microsoft Presidio, spaCy, PyMuPDF, Tesseract, Anthropic Claude

**License:** MIT

GitHub: https://github.com/z26zheng/CipherTax
