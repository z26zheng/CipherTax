"""Custom Presidio recognizers for tax-specific PII entities.

These recognizers detect PII patterns commonly found in US tax documents
(W-2, 1099, 1040, etc.) that are not covered by Presidio's built-in recognizers.
"""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


def create_ssn_recognizer() -> PatternRecognizer:
    """Social Security Number (SSN) — format: XXX-XX-XXXX or XXXXXXXXX.

    Detects ANY 9-digit number in SSN format, including invalid SSNs
    (000/666/9XX area, 00 group, 0000 serial). We DETECT first, then
    optionally validate. This prevents leaking SSN-formatted numbers
    that happen to match invalid groupings (e.g., 123-00-4567).

    Supplements Presidio's built-in US_SSN recognizer for better coverage
    in tax document contexts.
    """
    return PatternRecognizer(
        supported_entity="US_SSN",
        name="Tax SSN Recognizer",
        patterns=[
            # Detect ALL SSN-formatted strings — we redact first, validate never.
            # Invalid SSN groupings (000-XX-XXXX, XXX-00-XXXX, XXX-XX-0000) are
            # still PII-shaped data that should NEVER leak to AI.
            Pattern(
                name="ssn_with_dashes",
                regex=r"\b\d{3}-\d{2}-\d{4}\b",
                score=0.7,
            ),
            # 9-digit SSN without dashes — lower score because it could be
            # other 9-digit numbers; relies on context boost.
            Pattern(
                name="ssn_no_dashes",
                regex=r"\b\d{9}\b",
                score=0.3,
            ),
        ],
        context=[
            "ssn",
            "social security",
            "social sec",
            "taxpayer id",
            "taxpayer identification",
            "employee's social security number",
            "tin",
        ],
        supported_language="en",
    )


def create_ein_recognizer() -> PatternRecognizer:
    """Employer Identification Number (EIN) — format: XX-XXXXXXX."""
    return PatternRecognizer(
        supported_entity="EIN",
        name="EIN Recognizer",
        patterns=[
            Pattern(
                name="ein_pattern",
                regex=r"\b\d{2}-\d{7}\b",
                score=0.7,
            ),
        ],
        context=[
            "ein",
            "employer identification",
            "employer id",
            "federal id",
            "fein",
            "tax id",
            "employer's identification number",
        ],
        supported_language="en",
    )


def create_bank_account_recognizer() -> PatternRecognizer:
    """Bank account numbers — typically 8-17 digits."""
    return PatternRecognizer(
        supported_entity="BANK_ACCOUNT",
        name="Bank Account Recognizer",
        patterns=[
            Pattern(
                name="bank_account_pattern",
                regex=r"\b\d{8,17}\b",
                score=0.3,  # Low base score — needs context to boost
            ),
        ],
        context=[
            "account",
            "bank account",
            "checking",
            "savings",
            "deposit",
            "direct deposit",
            "account number",
        ],
        supported_language="en",
    )


def create_routing_number_recognizer() -> PatternRecognizer:
    """Bank routing numbers — exactly 9 digits, ABA format."""
    return PatternRecognizer(
        supported_entity="ROUTING_NUMBER",
        name="Routing Number Recognizer",
        patterns=[
            Pattern(
                name="routing_number_pattern",
                regex=r"\b\d{9}\b",
                score=0.3,  # Low base score — needs context
            ),
        ],
        context=[
            "routing",
            "routing number",
            "aba",
            "transit",
            "bank routing",
        ],
        supported_language="en",
    )


def create_itin_recognizer() -> PatternRecognizer:
    """Individual Taxpayer Identification Number (ITIN) — format: 9XX-XX-XXXX."""
    return PatternRecognizer(
        supported_entity="ITIN",
        name="ITIN Recognizer",
        patterns=[
            Pattern(
                name="itin_pattern",
                regex=r"\b9\d{2}-?\d{2}-?\d{4}\b",
                score=0.6,
            ),
        ],
        context=[
            "itin",
            "individual taxpayer",
            "taxpayer identification",
        ],
        supported_language="en",
    )


def create_tax_control_number_recognizer() -> PatternRecognizer:
    """W-2 control number — alphanumeric, varies by employer."""
    return PatternRecognizer(
        supported_entity="CONTROL_NUMBER",
        name="W2 Control Number Recognizer",
        patterns=[
            Pattern(
                name="control_number_pattern",
                regex=r"\b[A-Za-z0-9]{5,15}\b",
                score=0.2,  # Very low — relies heavily on context
            ),
        ],
        context=[
            "control number",
            "control no",
            "box d",
        ],
        supported_language="en",
    )


def get_all_tax_recognizers() -> list[PatternRecognizer]:
    """Return all custom tax-specific PII recognizers."""
    return [
        create_ssn_recognizer(),
        create_ein_recognizer(),
        create_bank_account_recognizer(),
        create_routing_number_recognizer(),
        create_itin_recognizer(),
        create_tax_control_number_recognizer(),
    ]
