# Hacker News — Show HN Post

## Title
Show HN: CipherTax – Safely use AI for tax filing by redacting PII locally before sending to Claude

## URL
https://github.com/z26zheng/CipherTax

## Text (for text post variant)
I built CipherTax because I wanted to use AI to help with my taxes but was uncomfortable uploading my W-2 (with SSN, address, bank info) to a cloud API.

CipherTax sits between your tax documents and AI. It:

1. Extracts text from PDFs and photos (including scanned docs via OCR)
2. Detects PII using Microsoft Presidio + custom tax recognizers
3. Replaces identity data with tokens ([SSN_1], [PERSON_1]) while keeping financial amounts the AI needs for calculations
4. Stores real values in a locally encrypted vault (AES/Fernet)
5. Sends only sanitized text to Claude
6. Restores real PII in the response locally

Key design decision: AI doesn't need your SSN to calculate your taxes. It needs your income amounts, filing status, and state — but not your identity. So we redact identity data and keep financial data.

Also includes a federal tax calculator (2024 brackets, SE tax, capital gains, QBI, CTC) and a 5-level Data Sensitivity Level framework adapted from enterprise security policies.

152 tests, including 29 dedicated PII leak prevention tests that verify no SSN/name/EIN/email/phone appears in redacted output.

Python, MIT license, open source.

Tech: Microsoft Presidio, spaCy NER, PyMuPDF, Tesseract OCR, Fernet encryption, Anthropic Claude API.
