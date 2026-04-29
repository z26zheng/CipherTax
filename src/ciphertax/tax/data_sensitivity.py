"""Tax Data Sensitivity Levels (DSL) — Classification framework for tax filing data.

Adapted from enterprise Data Sensitivity Level frameworks for the personal
tax filing use case. Defines what data is safe to send to AI, what must be
redacted, and what should never leave local storage.

This classification drives CipherTax's redaction decisions:
- DSL 1-2: Safe to send to AI (public/anonymized tax data)
- DSL 3: Redact before sending (personal identifiers)
- DSL 4: Always redact + encrypt locally (government IDs, financial accounts)
- DSL 5: Never store digitally if possible (master credentials)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class DSL(IntEnum):
    """Data Sensitivity Level for tax filing data.

    Level 1: PUBLIC — Safe to share freely
    Level 2: INTERNAL — De-identified, safe for AI processing
    Level 3: CONFIDENTIAL — PII that identifies individuals
    Level 4: RESTRICTED — Highly regulated identifiers (SSN, bank accounts)
    Level 5: CRITICAL — Credentials that grant direct financial access
    """
    PUBLIC = 1
    INTERNAL = 2
    CONFIDENTIAL = 3
    RESTRICTED = 4
    CRITICAL = 5


@dataclass
class DataClassification:
    """Classification of a tax data field."""
    field_name: str
    dsl: DSL
    description: str
    examples: list[str]
    ai_action: str          # "send", "redact", "redact_encrypt", "never_store"
    risk_if_exposed: str
    irs_form_fields: list[str]  # Which IRS form fields contain this data


# =============================================================================
# TAX DATA SENSITIVITY CLASSIFICATIONS
# =============================================================================

TAX_DATA_CLASSIFICATIONS: list[DataClassification] = [
    # =========================================================================
    # DSL 1 — PUBLIC: Safe to share, no privacy risk
    # =========================================================================
    DataClassification(
        field_name="Tax Year",
        dsl=DSL.PUBLIC,
        description="The tax year being filed. Public information with no privacy risk.",
        examples=["2024", "2023"],
        ai_action="send",
        risk_if_exposed="None",
        irs_form_fields=["1040 header"],
    ),
    DataClassification(
        field_name="Form Type",
        dsl=DSL.PUBLIC,
        description="The type of IRS form. Public knowledge.",
        examples=["W-2", "1099-INT", "1040", "Schedule C"],
        ai_action="send",
        risk_if_exposed="None",
        irs_form_fields=["All form headers"],
    ),
    DataClassification(
        field_name="Filing Status",
        dsl=DSL.PUBLIC,
        description="Tax filing status. Needed by AI for bracket determination. "
                    "Not personally identifying on its own.",
        examples=["Single", "Married Filing Jointly", "Head of Household"],
        ai_action="send",
        risk_if_exposed="Minimal — does not identify an individual",
        irs_form_fields=["1040 line 1-5"],
    ),
    DataClassification(
        field_name="Number of Dependents",
        dsl=DSL.PUBLIC,
        description="Count of dependents. Needed for credits. Not identifying.",
        examples=["2", "0", "3"],
        ai_action="send",
        risk_if_exposed="Minimal",
        irs_form_fields=["1040 line 6d"],
    ),

    # =========================================================================
    # DSL 2 — INTERNAL: De-identified financial data safe for AI
    # =========================================================================
    DataClassification(
        field_name="Income Amounts",
        dsl=DSL.INTERNAL,
        description="Wages, salary, tips, business income, interest, dividends, "
                    "capital gains, rental income. Essential for tax calculations. "
                    "Not personally identifying without associated identity data.",
        examples=["$75,000.00", "$1,245.67", "$92,450.00"],
        ai_action="send",
        risk_if_exposed="Low — financial amount without identity context is not PII",
        irs_form_fields=[
            "W-2 Box 1", "1099-INT Box 1", "1099-DIV Box 1a",
            "1099-NEC Box 1", "1099-B proceeds", "Schedule C gross receipts",
        ],
    ),
    DataClassification(
        field_name="Tax Withheld Amounts",
        dsl=DSL.INTERNAL,
        description="Federal and state tax withheld. Needed for refund/owed calculation.",
        examples=["$12,000.00", "$5,100.00"],
        ai_action="send",
        risk_if_exposed="Low",
        irs_form_fields=["W-2 Box 2", "1099 Box 4"],
    ),
    DataClassification(
        field_name="Deduction Amounts",
        dsl=DSL.INTERNAL,
        description="Mortgage interest, charitable contributions, medical expenses, "
                    "student loan interest, IRA contributions.",
        examples=["$14,000 mortgage interest", "$5,000 charitable"],
        ai_action="send",
        risk_if_exposed="Low",
        irs_form_fields=["1098 Box 1", "Schedule A", "1098-E"],
    ),
    DataClassification(
        field_name="State Abbreviation",
        dsl=DSL.INTERNAL,
        description="State where income was earned. Needed for state tax determination. "
                    "Not identifying without other context.",
        examples=["CA", "IL", "TX", "NY"],
        ai_action="send",
        risk_if_exposed="Minimal",
        irs_form_fields=["W-2 Box 15"],
    ),
    DataClassification(
        field_name="Business Expense Categories",
        dsl=DSL.INTERNAL,
        description="Types and amounts of business expenses (advertising, supplies, etc.). "
                    "Needed for Schedule C calculations.",
        examples=["Advertising: $5,000", "Office supplies: $1,200"],
        ai_action="send",
        risk_if_exposed="Low",
        irs_form_fields=["Schedule C lines 8-27"],
    ),

    # =========================================================================
    # DSL 3 — CONFIDENTIAL: Personal identifiers — MUST REDACT before AI
    # =========================================================================
    DataClassification(
        field_name="Person Name",
        dsl=DSL.CONFIDENTIAL,
        description="Full legal name of taxpayer, spouse, dependents, or employer contacts. "
                    "Directly identifies an individual.",
        examples=["John Michael Smith", "Maria Elena Rodriguez"],
        ai_action="redact",
        risk_if_exposed="Identity correlation — can be linked to other leaked data",
        irs_form_fields=["W-2 Box e", "1040 header", "1099 recipient name"],
    ),
    DataClassification(
        field_name="Email Address",
        dsl=DSL.CONFIDENTIAL,
        description="Personal or business email. Directly identifies and enables phishing.",
        examples=["john.smith@example.com"],
        ai_action="redact",
        risk_if_exposed="Phishing, spam, identity correlation",
        irs_form_fields=["Not standard IRS — sometimes on employer forms"],
    ),
    DataClassification(
        field_name="Phone Number",
        dsl=DSL.CONFIDENTIAL,
        description="Personal or business phone. Can be used for social engineering.",
        examples=["(555) 123-4567"],
        ai_action="redact",
        risk_if_exposed="Social engineering, SIM swap attacks",
        irs_form_fields=["1040 page 1 (optional)"],
    ),
    DataClassification(
        field_name="Street Address",
        dsl=DSL.CONFIDENTIAL,
        description="Home or business street address. Physical location identifier.",
        examples=["742 Evergreen Terrace, Springfield IL 62704"],
        ai_action="redact",
        risk_if_exposed="Physical location exposure, combined with name enables identity theft",
        irs_form_fields=["W-2 Box f", "1040 address", "1099 recipient address"],
    ),
    DataClassification(
        field_name="Date of Birth",
        dsl=DSL.CONFIDENTIAL,
        description="Taxpayer or dependent birth date. Key identity verification factor.",
        examples=["03/15/1985"],
        ai_action="redact",
        risk_if_exposed="Identity verification factor — enables fraud with other data",
        irs_form_fields=["Dependent information"],
    ),
    DataClassification(
        field_name="Employer Name",
        dsl=DSL.CONFIDENTIAL,
        description="Name of employer. Can identify the taxpayer when combined with role/income.",
        examples=["Acme Technology Solutions Inc", "Google LLC"],
        ai_action="redact",
        risk_if_exposed="Employment verification, social engineering",
        irs_form_fields=["W-2 Box c"],
    ),

    # =========================================================================
    # DSL 4 — RESTRICTED: Government IDs and financial accounts
    #         MUST REDACT + ENCRYPT locally
    # =========================================================================
    DataClassification(
        field_name="Social Security Number (SSN)",
        dsl=DSL.RESTRICTED,
        description="Primary government identifier. Unauthorized access enables identity theft, "
                    "fraudulent tax filing, credit fraud, and government benefit fraud. "
                    "Subject to IRS Publication 1075, IRC §6103, and state privacy laws.",
        examples=["123-45-6789", "123456789"],
        ai_action="redact_encrypt",
        risk_if_exposed="CRITICAL — Identity theft, fraudulent tax returns, credit fraud, "
                       "government benefit fraud. Average identity theft cost: $1,100+ per victim",
        irs_form_fields=["W-2 Box a", "1040 header", "1099 recipient TIN"],
    ),
    DataClassification(
        field_name="Employer Identification Number (EIN)",
        dsl=DSL.RESTRICTED,
        description="Employer's federal tax ID. Can be used for business identity fraud "
                    "or fraudulent tax filings.",
        examples=["12-3456789"],
        ai_action="redact_encrypt",
        risk_if_exposed="Business identity fraud, fraudulent payroll tax filings",
        irs_form_fields=["W-2 Box b", "1099 payer TIN"],
    ),
    DataClassification(
        field_name="Individual Taxpayer ID (ITIN)",
        dsl=DSL.RESTRICTED,
        description="IRS-issued tax processing number for individuals without SSN. "
                    "Same sensitivity as SSN for tax purposes.",
        examples=["912-34-5678"],
        ai_action="redact_encrypt",
        risk_if_exposed="Identity theft, fraudulent tax filing",
        irs_form_fields=["1040 header (instead of SSN)"],
    ),
    DataClassification(
        field_name="Bank Account Number",
        dsl=DSL.RESTRICTED,
        description="Bank account number for direct deposit or payment. "
                    "Direct access to financial accounts.",
        examples=["1234567890", "98765432101"],
        ai_action="redact_encrypt",
        risk_if_exposed="Unauthorized bank transactions, ACH fraud",
        irs_form_fields=["1040 line 35b (direct deposit)"],
    ),
    DataClassification(
        field_name="Bank Routing Number",
        dsl=DSL.RESTRICTED,
        description="Bank routing/ABA number. Combined with account number enables transactions.",
        examples=["021000021", "121000358"],
        ai_action="redact_encrypt",
        risk_if_exposed="Combined with account number enables unauthorized transfers",
        irs_form_fields=["1040 line 35a (direct deposit)"],
    ),
    DataClassification(
        field_name="W-2 Control Number",
        dsl=DSL.RESTRICTED,
        description="Employer's internal tracking number. Can be used to impersonate "
                    "the employer or create fraudulent W-2s.",
        examples=["A1B2C3D4E5"],
        ai_action="redact_encrypt",
        risk_if_exposed="W-2 forgery, employer impersonation",
        irs_form_fields=["W-2 Box d"],
    ),

    # =========================================================================
    # DSL 5 — CRITICAL: Never store or transmit
    # =========================================================================
    DataClassification(
        field_name="IRS e-File PIN / Identity Protection PIN",
        dsl=DSL.CRITICAL,
        description="IRS-issued PIN that authorizes electronic tax filing. "
                    "With this PIN and an SSN, anyone can file a tax return in your name.",
        examples=["12345", "67890"],
        ai_action="never_store",
        risk_if_exposed="CATASTROPHIC — Enables fraudulent tax return filing. "
                       "Victim may not discover until their legitimate return is rejected.",
        irs_form_fields=["1040 signature section"],
    ),
    DataClassification(
        field_name="Tax Filing Credentials",
        dsl=DSL.CRITICAL,
        description="Login credentials for IRS.gov, state tax portals, or tax software. "
                    "Grants full access to tax filing and account history.",
        examples=["IRS Online Account password", "TurboTax login"],
        ai_action="never_store",
        risk_if_exposed="CATASTROPHIC — Full account takeover, fraudulent returns, "
                       "transcript access, identity theft",
        irs_form_fields=["N/A — system credentials, not form fields"],
    ),
    DataClassification(
        field_name="Power of Attorney (Form 2848)",
        dsl=DSL.CRITICAL,
        description="Signed authorization granting someone legal authority over your tax matters.",
        examples=["Signed Form 2848"],
        ai_action="never_store",
        risk_if_exposed="CATASTROPHIC — Legal authority to act on behalf of taxpayer "
                       "with the IRS",
        irs_form_fields=["Form 2848"],
    ),
]


def get_dsl_for_field(field_name: str) -> DSL | None:
    """Look up the DSL for a given field name."""
    for c in TAX_DATA_CLASSIFICATIONS:
        if c.field_name.lower() == field_name.lower():
            return c.dsl
    return None


def get_classifications_by_level(level: DSL) -> list[DataClassification]:
    """Get all classifications at a given DSL level."""
    return [c for c in TAX_DATA_CLASSIFICATIONS if c.dsl == level]


def get_fields_to_redact() -> list[DataClassification]:
    """Get all fields that must be redacted (DSL 3+)."""
    return [c for c in TAX_DATA_CLASSIFICATIONS if c.dsl >= DSL.CONFIDENTIAL]


def get_fields_safe_for_ai() -> list[DataClassification]:
    """Get all fields safe to send to AI (DSL 1-2)."""
    return [c for c in TAX_DATA_CLASSIFICATIONS if c.dsl <= DSL.INTERNAL]


def get_fields_to_encrypt() -> list[DataClassification]:
    """Get all fields that must be encrypted when stored locally (DSL 4+)."""
    return [c for c in TAX_DATA_CLASSIFICATIONS if c.dsl >= DSL.RESTRICTED]


def print_dsl_summary() -> None:
    """Print a formatted summary of all DSL classifications."""
    print("\n" + "="*90)
    print("  TAX DATA SENSITIVITY LEVELS (DSL)")
    print("="*90)

    for level in DSL:
        entries = get_classifications_by_level(level)
        if not entries:
            continue

        labels = {
            DSL.PUBLIC: ("🟢", "PUBLIC", "Safe to share — no privacy risk"),
            DSL.INTERNAL: ("🔵", "INTERNAL", "De-identified financial data — safe for AI"),
            DSL.CONFIDENTIAL: ("🟡", "CONFIDENTIAL", "Personal identifiers — REDACT before AI"),
            DSL.RESTRICTED: ("🔴", "RESTRICTED", "Government IDs & bank info — REDACT + ENCRYPT"),
            DSL.CRITICAL: ("⛔", "CRITICAL", "Filing credentials — NEVER store or transmit"),
        }
        icon, label, desc = labels[level]
        print(f"\n{icon} DSL {level.value} — {label}: {desc}")
        print("-" * 80)

        for c in entries:
            action_labels = {
                "send": "✅ Send to AI",
                "redact": "🔒 Redact → token",
                "redact_encrypt": "🔐 Redact → token + AES encrypt",
                "never_store": "⛔ Never store digitally",
            }
            print(f"  • {c.field_name}")
            print(f"    Action: {action_labels.get(c.ai_action, c.ai_action)}")
            print(f"    Risk:   {c.risk_if_exposed[:80]}")
            if c.examples:
                print(f"    Examples: {', '.join(c.examples[:3])}")
            print()


if __name__ == "__main__":
    print_dsl_summary()
