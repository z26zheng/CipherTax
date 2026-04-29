"""Rehydrator — restores original PII values from tokenized text.

Takes AI responses containing tokens like [SSN_1], [PERSON_1] and replaces
them with the original PII values from the secure vault mapping.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Pattern to match tokens like [CT_a3f9_SSN_1], [CT_test_PERSON_2], etc.
# Prefix can be any alphanumeric string. Also matches legacy [SSN_1] format.
TOKEN_PATTERN = re.compile(r"\[(?:CT_[a-zA-Z0-9]+_)?[A-Z_]+_\d+\]")


class Rehydrator:
    """Restore original PII values in AI responses.

    Takes text containing placeholder tokens and replaces them with
    the original PII values using the token mapping from the vault.

    Usage:
        rehydrator = Rehydrator(mapping={"[SSN_1]": "123-45-6789"})
        original = rehydrator.rehydrate("Your SSN [SSN_1] was reported")
        # "Your SSN 123-45-6789 was reported"
    """

    def __init__(self, mapping: dict[str, str]):
        """Initialize with the token → PII mapping.

        Args:
            mapping: Dictionary mapping tokens to original PII values.
                     e.g., {"[SSN_1]": "123-45-6789", "[PERSON_1]": "John Smith"}
        """
        self._mapping = mapping

    def rehydrate(self, text: str) -> str:
        """Replace all tokens in text with their original PII values.

        Args:
            text: Text containing placeholder tokens.

        Returns:
            Text with tokens replaced by original PII values.
        """
        if not text:
            return text

        result = text
        replaced_count = 0
        missing_tokens: list[str] = []

        for token_match in TOKEN_PATTERN.finditer(text):
            token = token_match.group()
            if token in self._mapping:
                result = result.replace(token, self._mapping[token])
                replaced_count += 1
            else:
                missing_tokens.append(token)

        if missing_tokens:
            logger.warning(
                "Found %d tokens in AI response with no mapping: %s",
                len(missing_tokens),
                missing_tokens,
            )

        logger.info(
            "Rehydrated %d tokens in text (%d unmapped)",
            replaced_count,
            len(missing_tokens),
        )

        return result

    def find_tokens(self, text: str) -> list[str]:
        """Find all tokens present in the text.

        Args:
            text: Text to search for tokens.

        Returns:
            List of token strings found.
        """
        return TOKEN_PATTERN.findall(text)

    def validate_mapping(self, text: str) -> dict[str, bool]:
        """Check which tokens in the text have valid mappings.

        Args:
            text: Text containing tokens.

        Returns:
            Dict mapping each found token to whether it has a mapping.
        """
        tokens = self.find_tokens(text)
        return {token: token in self._mapping for token in tokens}

    def update_mapping(self, additional_mapping: dict[str, str]) -> None:
        """Add more token → PII mappings.

        Args:
            additional_mapping: New mappings to add.
        """
        self._mapping.update(additional_mapping)
