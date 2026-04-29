# Microsoft Presidio Community — Discussion Post

## Post at: https://github.com/microsoft/presidio/discussions

## Title
CipherTax — Using Presidio for privacy-preserving AI tax assistance

## Body
Hi Presidio team and community!

I wanted to share a project that uses Microsoft Presidio as its core PII detection engine: **[CipherTax](https://github.com/z26zheng/CipherTax)**.

### What it does
CipherTax is a privacy layer for safely using AI (Claude) with tax documents. It extracts text from W-2s, 1099s, and other tax forms, uses Presidio to detect all PII, replaces identity data with tokens, and sends only the sanitized text to the AI.

### How we use Presidio
- **AnalyzerEngine** with spaCy `en_core_web_sm` for NER (names, organizations, addresses)
- **Built-in recognizers** for emails, phone numbers, credit cards
- **Custom PatternRecognizers** for tax-specific entities not in Presidio's defaults:
  - SSN (with IRS-valid format validation and context words like "social security")
  - EIN (Employer Identification Number)
  - ITIN (Individual Taxpayer Identification Number)
  - Bank account numbers (with context: "account", "deposit")
  - Routing numbers (with context: "routing", "ABA")
  - W-2 control numbers

### What we learned
1. Presidio's built-in US_SSN recognizer didn't detect some valid SSN patterns in our testing, so we supplemented it with a custom recognizer. The context-aware boosting is great for reducing false positives.
2. The `score_threshold` needed to be lowered to 0.25 for our use case (tax documents have lots of context).
3. The architecture (detection → anonymization as separate steps) was perfect for our "smart redaction" approach where we keep financial amounts but redact identity data.

### Results
- 152 tests including 29 PII leak prevention tests across W-2, 1099-INT, 1099-NEC, multi-page, and dense-PII documents
- All SSNs, names, EINs, emails, and phone numbers successfully redacted in every test

Thanks for building such a solid PII detection framework! Open to any feedback from the community.

MIT license: https://github.com/z26zheng/CipherTax
