# LinkedIn Post

## Post

For this year's tax filing, I used Claude Code as my consultant.

I gave it access to all our files — W-2s, 1099s, brokerage statements, the works. It was incredibly helpful: parsing forms, calculating deductions, optimizing our filing strategy. The kind of analysis that used to take a CPA hours took minutes.

But somewhere in the middle of it, I paused.

Claude now has my SSN. My spouse's SSN. Our home address. Our employer EINs. Our bank routing and account numbers. Years of income data. All sitting on someone else's servers, possibly logged, possibly cached, possibly used for training.

That's when it hit me: **the convenience of AI tax help is being paid for in privacy debt.**

The frustrating part? AI doesn't actually need any of that identity data to do tax math. It needs my income amounts, filing status, and state. The number "$92,450" doesn't tell you who earned it. But somehow the entire industry has settled on "just upload everything" as the default.

So I built **CipherTax** — an open-source privacy layer that sits between your tax documents and AI:

🔍 Extracts text from PDFs and photos (digital + scanned)
🛡️ Detects ALL PII using Microsoft Presidio + custom tax recognizers
🔒 Replaces identity data with tokens (SSN → `[SSN_1]`, name → `[PERSON_1]`)
✅ Keeps financial amounts (the AI needs those for calculations)
🔐 Stores real values in an AES-encrypted local vault
🚀 Sends ONLY the sanitized text to Claude
🔄 Restores real PII in the AI's response locally

**Zero personally identifiable information ever leaves your machine.**

The project includes:
📊 A 5-level Data Sensitivity framework (DSL) adapted from enterprise security
🧮 A complete federal tax calculator (2024 brackets, SE tax, capital gains, credits)
🔒 159 tests including 29 dedicated PII leak prevention tests
📄 Support for digital PDFs, scanned documents, and phone photos

It also went through a third-party security review and v0.2.0 just shipped with hardened protections (full-detector safety checks, session-random tokens to prevent collision attacks, lazy vault creation).

Built with Python, Microsoft Presidio, spaCy, and the Anthropic API.

MIT license — contributions welcome.

🔗 https://github.com/z26zheng/CipherTax
📦 `pip install ciphertax`

If you're a developer who's used AI for anything involving sensitive documents — tax forms, medical records, contracts — I'd love to hear how you've thought about this trade-off. The technology is too useful to abandon, but the privacy posture needs work.

#Privacy #AI #OpenSource #TaxTech #Security #Python #DataPrivacy #LLM
