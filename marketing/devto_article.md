---
title: "How I Built a Privacy Layer to Safely Use AI for Tax Filing"
published: false
description: "CipherTax redacts PII from tax documents before sending to Claude — here's the architecture and Data Sensitivity Level framework behind it"
tags: privacy, ai, python, security
cover_image: 
---

# How I Built a Privacy Layer to Safely Use AI for Tax Filing

## The Problem

I wanted to use Claude to help with my taxes. But my W-2 contains:
- My Social Security Number
- My full legal name and home address
- My employer's EIN
- My bank account and routing numbers

Uploading this to a cloud API felt wrong. Under GDPR, CCPA, and common sense — I shouldn't be sending my SSN to a server I don't control.

**But here's the thing:** AI doesn't need my SSN to calculate my taxes. It needs my income amounts, filing status, and state — but not my identity.

## The Solution: CipherTax

I built [CipherTax](https://github.com/z26zheng/CipherTax), an open-source Python tool that acts as a privacy layer between tax documents and AI.

### The Pipeline

```
Tax PDF → Extract Text → Detect PII → Tokenize → Encrypted Vault
                                                 → Send redacted text to AI
                                                 → Rehydrate response locally
```

### Before (What my W-2 says):
```
Employee's SSN: 234-56-7890
Employee's name: Maria Elena Rodriguez
Wages: $92,450.00
```

### After (What Claude receives):
```
[ADDRESS_1]'s SSN: [SSN_1]
[ADDRESS_1]'s name: [PERSON_1]
Wages: $92,450.00    ← KEPT
```

Notice: SSN and name → tokens. Wages → kept as-is.

## The Data Sensitivity Level Framework

This is the part I'm most proud of. Instead of ad-hoc redaction rules, I created a formal 5-level classification:

| Level | Name | Action | Examples |
|-------|------|--------|----------|
| DSL 1 | 🟢 PUBLIC | Send to AI | Tax year, form type, filing status |
| DSL 2 | 🔵 INTERNAL | Send to AI | Income amounts, deductions, state |
| DSL 3 | 🟡 CONFIDENTIAL | Redact → token | Names, emails, phones, addresses |
| DSL 4 | 🔴 RESTRICTED | Redact + encrypt | SSN, EIN, bank accounts |
| DSL 5 | ⛔ CRITICAL | Never store | e-File PIN, tax portal credentials |

**The key insight for DSL 2:** Financial amounts ($75,000 wages) are NOT personally identifying without identity context. The number alone doesn't tell you who earned it.

## The Security Layers

I didn't want to rely on a single detection method:

1. **Microsoft Presidio** — Enterprise-grade PII detection (7,900+ ⭐)
2. **Custom tax recognizers** — Regex + context for SSN, EIN, ITIN, bank accounts
3. **Smart tokenization** — Same PII always gets the same token
4. **AES encrypted vault** — PBKDF2 with 600K iterations
5. **Pre-send safety check** — Last-resort SSN regex before API call
6. **152 automated tests** — 29 specifically test for PII leaks

## The Tax Calculator

Since I was building tax tooling anyway, I added a complete federal tax calculator (2024):
- 7 marginal brackets × 4 filing statuses
- Self-employment tax (Schedule SE)
- Capital gains (short/long-term)
- QBI deduction (Section 199A)
- Child Tax Credit with phaseout
- NIIT (3.8%)

Verified: Single filer, $75K → Tax: $7,945, Refund: $2,555 (exact match with manual IRS bracket math).

## What I Learned

1. **Presidio's built-in SSN recognizer missed some patterns** — I had to add a custom one with context-aware boosting
2. **The "what to redact vs keep" decision is harder than detection** — The DSL framework solved this cleanly
3. **Testing PII redaction is critical** — Without the 29 leak prevention tests, I wouldn't trust the system
4. **Financial amounts are the key insight** — Realizing AI needs amounts but not identity was the design breakthrough

## Try It

```bash
pip install ciphertax
# or
git clone https://github.com/z26zheng/CipherTax.git
python examples/demo_tax_filing.py
```

MIT license. Contributions welcome — especially state tax support and additional form recognizers.

---

*CipherTax is a privacy tool, not tax advice software. Always consult a CPA before filing.*
