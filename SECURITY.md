# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in CipherTax, please report it responsibly:

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainers directly or use [GitHub's private vulnerability reporting](https://github.com/z26zheng/CipherTax/security/advisories/new)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work to patch critical issues promptly.

## Security Model

CipherTax's security is built on these principles:

### What We Protect
- **PII never leaves your machine** — SSNs, names, addresses, bank accounts are redacted locally before any API call
- **Encrypted vault** — PII↔token mappings encrypted with Fernet (AES-128-CBC + HMAC-SHA256, PBKDF2 600K iterations)
- **Secure deletion** — Vault files overwritten with random data before deletion
- **Safety check** — Last-resort SSN pattern detection before API calls

### What We Don't Protect
- **Financial amounts** — Income, deductions, tax amounts are intentionally sent to AI (needed for calculations)
- **API keys** — Your Anthropic API key is stored in a local `.env` file
- **100% PII detection** — No automated system catches everything; always review redacted output

### Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Current |

## Dependencies

CipherTax relies on these security-critical dependencies:
- [Microsoft Presidio](https://github.com/microsoft/presidio) — PII detection
- [cryptography](https://github.com/pyca/cryptography) — Fernet encryption
- [spaCy](https://github.com/explosion/spaCy) — NER model

We monitor these for security advisories and update promptly.
