# Reddit r/tax Post

## Title
Open-source tool: Use AI to help with your taxes without giving it your SSN or personal info

## Body
I'm a developer, not a CPA — but I wanted to use AI (Claude) to help me understand my tax situation, calculate deductions, and optimize my filing. The problem? I'd have to upload my W-2, which has my SSN, name, address, and bank info.

So I built **CipherTax** — it reads your tax documents, automatically replaces all personal identifiers with anonymous tokens, keeps the financial numbers intact (because AI needs those for calculations), and sends only the sanitized version to the AI.

**Example of what AI sees:**
```
Employee's SSN: [SSN_1]
Employee's name: [PERSON_1]
Wages: $92,450.00  ← kept
Federal tax withheld: $16,200.00  ← kept
State: IL  ← kept
```

It also includes a **tax calculator** (2024 federal brackets, SE tax, capital gains, QBI deduction, CTC) and a **tax optimizer** that suggests things like maxing your 401(k), opening a SEP-IRA, or tax-loss harvesting.

**Important caveat:** This is NOT tax preparation software and NOT a substitute for a CPA. It's a privacy tool + estimation tool. Always consult a professional before filing.

Free, open source (MIT): https://github.com/z26zheng/CipherTax
