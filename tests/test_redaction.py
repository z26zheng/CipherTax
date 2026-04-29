"""Tests for tokenizer and rehydrator."""

import pytest
import re

from ciphertax.redaction.tokenizer import Tokenizer
from ciphertax.redaction.rehydrator import Rehydrator
from ciphertax.detection.detector import PIIEntity


# Token pattern matching new format: [CT_<prefix>_TYPE_N]
TOKEN_RE = re.compile(r"\[CT_[a-zA-Z0-9]+_([A-Z_]+)_(\d+)\]")


def find_token(text: str, type_label: str, idx: int) -> str | None:
    """Find a token of the given type and index in text. Returns the actual
    token string (with session prefix) or None if not found."""
    for match in TOKEN_RE.finditer(text):
        if match.group(1) == type_label and int(match.group(2)) == idx:
            return match.group(0)
    return None


def has_token_type(text: str, type_label: str) -> bool:
    """Check if any token of the given type exists in text."""
    return any(m.group(1) == type_label for m in TOKEN_RE.finditer(text))


class TestTokenizer:
    """Test PII tokenization (redaction)."""

    @pytest.fixture
    def tokenizer(self):
        # Use fixed prefix for predictable testing
        return Tokenizer(session_prefix="test")

    def _make_entity(self, entity_type, text, start, end, score=0.9, should_redact=True):
        return PIIEntity(
            entity_type=entity_type,
            text=text,
            start=start,
            end=end,
            score=score,
            should_redact=should_redact,
        )

    def test_redact_single_ssn(self, tokenizer):
        text = "SSN is 123-45-6789 here"
        entities = [self._make_entity("US_SSN", "123-45-6789", 7, 18)]
        redacted, mapping = tokenizer.redact(text, entities)
        assert "123-45-6789" not in redacted
        assert "[CT_test_SSN_1]" in redacted
        assert mapping["[CT_test_SSN_1]"] == "123-45-6789"

    def test_redact_multiple_entities(self, tokenizer):
        text = "John Smith SSN 123-45-6789"
        entities = [
            self._make_entity("PERSON", "John Smith", 0, 10),
            self._make_entity("US_SSN", "123-45-6789", 15, 26),
        ]
        redacted, mapping = tokenizer.redact(text, entities)
        assert "John Smith" not in redacted
        assert "123-45-6789" not in redacted
        assert has_token_type(redacted, "PERSON")
        assert has_token_type(redacted, "SSN")

    def test_consistent_mapping(self, tokenizer):
        """Same PII text should always map to the same token."""
        text1 = "Name: John Smith"
        text2 = "Taxpayer: John Smith"
        e1 = [self._make_entity("PERSON", "John Smith", 6, 16)]
        e2 = [self._make_entity("PERSON", "John Smith", 10, 20)]

        redacted1, _ = tokenizer.redact(text1, e1)
        redacted2, _ = tokenizer.redact(text2, e2)

        assert "[CT_test_PERSON_1]" in redacted1
        assert "[CT_test_PERSON_1]" in redacted2

    def test_different_values_get_different_tokens(self, tokenizer):
        text = "John Smith and Jane Doe"
        entities = [
            self._make_entity("PERSON", "John Smith", 0, 10),
            self._make_entity("PERSON", "Jane Doe", 15, 23),
        ]
        redacted, mapping = tokenizer.redact(text, entities)
        # Both PERSON tokens (1 and 2) should be present
        assert "[CT_test_PERSON_1]" in redacted
        assert "[CT_test_PERSON_2]" in redacted
        assert set(mapping.values()) == {"John Smith", "Jane Doe"}
        assert "John Smith" not in redacted
        assert "Jane Doe" not in redacted

    def test_skip_non_redactable_entities(self, tokenizer):
        text = "Amount: $75,000"
        entities = [self._make_entity("AMOUNT", "$75,000", 8, 15, should_redact=False)]
        redacted, mapping = tokenizer.redact(text, entities)
        assert redacted == text
        assert mapping == {}

    def test_empty_entities(self, tokenizer):
        text = "No PII here"
        redacted, mapping = tokenizer.redact(text, [])
        assert redacted == text
        assert mapping == {}

    def test_get_full_mapping(self, tokenizer):
        text = "SSN: 123-45-6789"
        entities = [self._make_entity("US_SSN", "123-45-6789", 5, 16)]
        tokenizer.redact(text, entities)
        full_mapping = tokenizer.get_full_mapping()
        assert "[CT_test_SSN_1]" in full_mapping
        assert full_mapping["[CT_test_SSN_1]"] == "123-45-6789"

    def test_reset(self, tokenizer):
        text = "SSN: 123-45-6789"
        entities = [self._make_entity("US_SSN", "123-45-6789", 5, 16)]
        tokenizer.redact(text, entities)
        tokenizer.reset()
        assert tokenizer.get_full_mapping() == {}

    def test_entity_type_normalization(self, tokenizer):
        text = "Email: test@example.com"
        entities = [self._make_entity("EMAIL_ADDRESS", "test@example.com", 7, 23)]
        redacted, mapping = tokenizer.redact(text, entities)
        assert "[CT_test_EMAIL_1]" in redacted

    def test_session_prefix_random(self):
        """Different tokenizer instances should get different prefixes."""
        t1 = Tokenizer()
        t2 = Tokenizer()
        assert t1.session_prefix != t2.session_prefix

    def test_collision_escape(self):
        """Pre-existing tokens in input should be escaped."""
        tokenizer = Tokenizer(session_prefix="abcd")
        # Input contains a token-like pattern matching our prefix
        text = "Document contains [CT_abcd_SSN_1] which should not be substituted"
        entities = []
        redacted, _ = tokenizer.redact(text, entities)
        # The collision should be escaped (e.g., to [~CT_abcd_SSN_1])
        assert "[CT_abcd_SSN_1]" not in redacted
        assert "[~CT_abcd_SSN_1]" in redacted


class TestRehydrator:
    """Test token rehydration (restoring PII)."""

    def test_rehydrate_single_token(self):
        mapping = {"[CT_test_SSN_1]": "123-45-6789"}
        rehydrator = Rehydrator(mapping)
        text = "Your SSN is [CT_test_SSN_1]"
        result = rehydrator.rehydrate(text)
        assert result == "Your SSN is 123-45-6789"

    def test_rehydrate_multiple_tokens(self):
        mapping = {
            "[CT_test_SSN_1]": "123-45-6789",
            "[CT_test_PERSON_1]": "John Smith",
            "[CT_test_EIN_1]": "98-7654321",
        }
        rehydrator = Rehydrator(mapping)
        text = "[CT_test_PERSON_1] with SSN [CT_test_SSN_1] works at employer EIN [CT_test_EIN_1]"
        result = rehydrator.rehydrate(text)
        assert "John Smith" in result
        assert "123-45-6789" in result
        assert "98-7654321" in result

    def test_rehydrate_preserves_non_token_text(self):
        mapping = {"[CT_test_SSN_1]": "123-45-6789"}
        rehydrator = Rehydrator(mapping)
        text = "Wages: $75,000. SSN: [CT_test_SSN_1]. Tax: $12,500."
        result = rehydrator.rehydrate(text)
        assert "$75,000" in result
        assert "$12,500" in result
        assert "123-45-6789" in result

    def test_rehydrate_empty_text(self):
        rehydrator = Rehydrator({"[CT_test_SSN_1]": "123-45-6789"})
        assert rehydrator.rehydrate("") == ""
        assert rehydrator.rehydrate(None) is None

    def test_find_tokens(self):
        rehydrator = Rehydrator({})
        tokens = rehydrator.find_tokens("Hello [CT_test_PERSON_1], your SSN is [CT_test_SSN_1]")
        assert "[CT_test_PERSON_1]" in tokens
        assert "[CT_test_SSN_1]" in tokens

    def test_find_legacy_tokens(self):
        """Backward compat: should also match legacy [SSN_1] format."""
        rehydrator = Rehydrator({})
        tokens = rehydrator.find_tokens("Hello [PERSON_1], your SSN is [SSN_1]")
        assert "[PERSON_1]" in tokens
        assert "[SSN_1]" in tokens

    def test_validate_mapping(self):
        mapping = {"[CT_test_SSN_1]": "123-45-6789"}
        rehydrator = Rehydrator(mapping)
        validation = rehydrator.validate_mapping("[CT_test_SSN_1] and [CT_test_PERSON_1]")
        assert validation["[CT_test_SSN_1]"] is True
        assert validation["[CT_test_PERSON_1]"] is False

    def test_roundtrip_tokenize_rehydrate(self):
        """Tokenize then rehydrate should restore original text."""
        tokenizer = Tokenizer(session_prefix="rt")
        original = "John Smith SSN 123-45-6789 email john@example.com"
        entities = [
            PIIEntity("PERSON", "John Smith", 0, 10, 0.9, True),
            PIIEntity("US_SSN", "123-45-6789", 15, 26, 0.95, True),
            PIIEntity("EMAIL_ADDRESS", "john@example.com", 33, 49, 0.9, True),
        ]

        redacted, mapping = tokenizer.redact(original, entities)
        rehydrator = Rehydrator(mapping)
        restored = rehydrator.rehydrate(redacted)
        assert restored == original
