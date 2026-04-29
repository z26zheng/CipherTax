# Twitter/X Post

## Post 1 (Main announcement)
🔐 Just open-sourced CipherTax — safely use AI for tax filing without exposing your SSN, name, or address.

It redacts PII locally, sends only sanitized text to Claude, then restores your real data in the response.

AI doesn't need your SSN to calculate your taxes. It needs your income amounts.

🔗 https://github.com/z26zheng/CipherTax

## Post 2 (Thread continuation)
How it works:
📄 Extract text from tax PDFs/photos
🔍 Detect PII (Microsoft Presidio + custom tax recognizers)
🔒 Replace: "John Smith" → [PERSON_1], "123-45-6789" → [SSN_1]
💰 Keep: "$75,000 wages" (AI needs this for tax math)
🔐 Store real data in encrypted local vault
📤 Send only tokens to Claude

## Post 3
Built with a 5-level Data Sensitivity framework:
🟢 DSL 1: Tax year, filing status → safe to share
🔵 DSL 2: Income amounts → safe (no identity context)
🟡 DSL 3: Names, emails → REDACT
🔴 DSL 4: SSN, bank accounts → REDACT + ENCRYPT
⛔ DSL 5: e-File PIN → NEVER store

152 tests. MIT license. Python.

## Hashtags
#opensource #privacy #ai #tax #security #python #llm #pii
