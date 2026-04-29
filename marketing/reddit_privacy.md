# Reddit r/privacy Post

## Title
I built an open-source tool that lets you use AI for tax help without sharing your SSN, name, or address with cloud servers

## Body
**The concern:** AI tools like ChatGPT and Claude are great for tax questions. But to get useful answers, you'd need to share your W-2 — which contains your SSN, full name, home address, employer info, and bank account numbers. That data goes to cloud servers you don't control.

**What I built:** CipherTax is a local privacy layer that:

1. Reads your tax PDFs (or photos of them)
2. Detects ALL personally identifiable information using Microsoft Presidio (enterprise-grade PII detection)
3. Replaces identity data with anonymous tokens: `John Smith` → `[PERSON_1]`, `123-45-6789` → `[SSN_1]`
4. **Keeps financial amounts** ($75,000 wages) because AI needs them for tax math
5. Stores the real values in a locally encrypted vault (AES, PBKDF2 with 600K iterations)
6. Sends ONLY the sanitized text to the AI
7. Restores your real data in the AI's response locally

**Key privacy features:**
- Zero PII leaves your machine
- 5-layer security (detection → tokenization → vault encryption → pre-send safety check → 152 automated tests)
- Formal Data Sensitivity Levels (DSL) classify every tax data field from "safe to share" to "never transmit"
- Vault files are overwritten with random data before deletion
- Last-resort SSN regex blocks the API call if anything leaks through

**What I DON'T claim:** No automated system is 100% perfect at PII detection. Always review the redacted output. Financial amounts ARE sent (AI needs them). This is a tool, not magic.

Open source, MIT license, Python: https://github.com/z26zheng/CipherTax
