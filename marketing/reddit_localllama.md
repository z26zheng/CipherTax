# Reddit r/LocalLLaMA Post

## Title
CipherTax — PII redaction layer for safely using LLMs with tax documents (open source, works with any API)

## Body
Built a privacy-first tool for using LLMs with sensitive documents. Currently targets Claude but the redaction pipeline is API-agnostic — you could point it at any LLM.

**What it does:** Reads tax PDFs/images → detects PII with Microsoft Presidio → replaces identity data with tokens → keeps financial amounts → sends only sanitized text to the LLM → restores real PII in the response locally.

**Why r/LocalLLaMA would care:**
- The redaction pipeline works locally — no cloud dependency for the privacy layer
- Could easily swap Claude for a local model (Llama, Mistral, etc.) — just change the AI client
- The Data Sensitivity Level framework (5 levels from "safe to share" to "never store") could apply to any domain, not just taxes
- Encrypted vault stores PII locally with AES/Fernet

**For local model users:** You might not need the redaction layer at all if you're running everything locally. But the tax calculator, form parser, and DSL framework could still be useful components.

152 tests, Python, MIT: https://github.com/z26zheng/CipherTax
