# LinkedIn Post

## Post

🔐 Excited to share an open-source project I've been working on: **CipherTax**

**The problem:** AI tools are incredibly powerful for tax assistance — calculating deductions, optimizing filing strategies, extracting data from tax forms. But using them means uploading documents containing SSNs, bank accounts, home addresses, and other sensitive PII to cloud servers.

**The solution:** CipherTax is a local-first privacy layer that sits between your tax documents and AI. It:

✅ Extracts text from PDFs and photos (including scanned docs via OCR)
✅ Detects all PII using Microsoft Presidio + custom tax recognizers
✅ Replaces identity data with tokens while preserving financial amounts
✅ Stores real values in a locally encrypted vault (AES/Fernet, PBKDF2)
✅ Sends only sanitized text to the AI
✅ Restores real PII in the AI's response locally

**The key insight:** AI doesn't need your SSN to calculate your taxes. It needs income amounts, filing status, and state — but not your identity.

The project includes:
📊 A 5-level Data Sensitivity framework (adapted from enterprise security policies)
🧮 A complete federal tax calculator (2024 brackets, SE tax, capital gains, credits)
🔒 152 automated tests including 29 dedicated PII leak prevention tests
📄 Support for digital PDFs, scanned documents, and phone photos

Built with Python, Microsoft Presidio, spaCy, and the Anthropic API.

MIT license — contributions welcome!

🔗 https://github.com/z26zheng/CipherTax

#Privacy #AI #OpenSource #TaxTech #Security #Python #MachineLearning
