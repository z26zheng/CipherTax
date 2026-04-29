"""Tokenizer — replaces PII with deterministic placeholder tokens.

Implements tax-smart redaction:
- Identity PII (SSN, names, etc.) → replaced with tokens like [SSN_1], [PERSON_1]
- Financial data (income, amounts) → kept as-is for AI tax calculations
- Same PII value always maps to the same token within a session
"""

from __future__ import annotations

import logging
from collections import defaultdict

from ciphertax.detection.detector import PIIEntity

logger = logging.getLogger(__name__)


class Tokenizer:
    """Replace PII entities with deterministic placeholder tokens.

    The mapping is consistent: the same PII text always gets the same token.
    The mapping is stored for later rehydration (restoring original values).

    Usage:
        tokenizer = Tokenizer()
        redacted_text, mapping = tokenizer.redact(text, entities)
        # mapping = {"[SSN_1]": "123-45-6789", "[PERSON_1]": "John Smith", ...}
    """

    def __init__(self):
        """Initialize the tokenizer with empty mappings."""
        # Maps entity_type → counter (for generating unique tokens)
        self._counters: dict[str, int] = defaultdict(int)

        # Maps original PII text → token (for consistency)
        self._text_to_token: dict[str, str] = {}

        # Maps token → original PII text (for rehydration)
        self._token_to_text: dict[str, str] = {}

    def redact(self, text: str, entities: list[PIIEntity]) -> tuple[str, dict[str, str]]:
        """Replace PII entities in text with placeholder tokens.

        Args:
            text: Original text containing PII.
            entities: List of detected PII entities (sorted by position).

        Returns:
            Tuple of (redacted_text, token_mapping).
            token_mapping maps token → original PII text.
        """
        if not entities:
            return text, {}

        # Process entities from right to left to preserve positions
        entities_to_redact = [e for e in entities if e.should_redact]
        entities_to_redact.sort(key=lambda e: e.start, reverse=True)

        redacted = text
        session_mapping: dict[str, str] = {}

        for entity in entities_to_redact:
            token = self._get_or_create_token(entity)
            redacted = redacted[: entity.start] + token + redacted[entity.end :]
            session_mapping[token] = entity.text

        # Merge into global mapping
        self._token_to_text.update(session_mapping)

        redact_count = len(entities_to_redact)
        skip_count = len(entities) - redact_count
        logger.info(
            "Redacted %d entities (%d kept as-is) in text (%d chars → %d chars)",
            redact_count,
            skip_count,
            len(text),
            len(redacted),
        )

        return redacted, session_mapping

    def _get_or_create_token(self, entity: PIIEntity) -> str:
        """Get existing token for this PII text, or create a new one.

        Ensures the same PII text always maps to the same token.
        """
        # Normalize the PII text for consistent matching
        normalized = entity.text.strip()

        if normalized in self._text_to_token:
            return self._text_to_token[normalized]

        # Create a new token
        entity_label = self._normalize_entity_type(entity.entity_type)
        self._counters[entity_label] += 1
        token = f"[{entity_label}_{self._counters[entity_label]}]"

        self._text_to_token[normalized] = token
        self._token_to_text[token] = normalized

        return token

    @staticmethod
    def _normalize_entity_type(entity_type: str) -> str:
        """Normalize entity type to a clean token label.

        Examples:
            US_SSN → SSN
            EMAIL_ADDRESS → EMAIL
            PHONE_NUMBER → PHONE
            PERSON → PERSON
        """
        label_map = {
            "US_SSN": "SSN",
            "EMAIL_ADDRESS": "EMAIL",
            "PHONE_NUMBER": "PHONE",
            "US_BANK_NUMBER": "BANK_ACCT",
            "BANK_ACCOUNT": "BANK_ACCT",
            "ROUTING_NUMBER": "ROUTING",
            "CREDIT_CARD": "CREDIT_CARD",
            "US_PASSPORT": "PASSPORT",
            "US_DRIVER_LICENSE": "DRIVERS_LICENSE",
            "IBAN_CODE": "IBAN",
            "IP_ADDRESS": "IP",
            "DATE_TIME": "DATE",
            "LOCATION": "ADDRESS",
            "CONTROL_NUMBER": "CONTROL_NUM",
        }
        return label_map.get(entity_type, entity_type)

    def get_full_mapping(self) -> dict[str, str]:
        """Return the complete token → original PII mapping."""
        return dict(self._token_to_text)

    def reset(self) -> None:
        """Reset all mappings (start a new session)."""
        self._counters.clear()
        self._text_to_token.clear()
        self._token_to_text.clear()
