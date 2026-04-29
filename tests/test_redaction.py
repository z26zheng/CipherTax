"""Tests for tokenizer and rehydrator."""

import pytest

from ciphertax.redaction.tokenizer import Tokenizer
from ciphertax.redaction.rehydrator import Rehydrator
from ciphertax.detection.detector import PIIEntity


class TestTokenizer:
    """Test PII tokenization (redaction)."""

    @pytest.fixture
    def tokenizer(self):
        return Tokenizer()

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
        assert "[SSN_1]" in redacted
        assert mapping["[SSN_1]"] == "123-45-6789"

    def test_redact_multiple_entities(self, tokenizer):
        text = "John Smith SSN 123-45-6789"
        entities = [
            self._make_entity("PERSON", "John Smith", 0, 10),
            self._make_entity("US_SSN", "123-45-6789", 15, 26),
        ]
        redacted, mapping = tokenizer.redact(text, entities)
        assert "John Smith" not in redacted
        assert "123-45-6789" not in redacted
        assert "[PERSON_1]" in redacted
        assert "[SSN_1]" in redacted

    def test_consistent_mapping(self, tokenizer):
        """Same PII text should always map to the same token."""
        text1 = "Name: John Smith"
        text2 = "Taxpayer: John Smith"
        e1 = [self._make_entity("PERSON", "John Smith", 6, 16)]
        e2 = [self._make_entity("PERSON", "John Smith", 10, 20)]

        redacted1, _ = tokenizer.redact(text1, e1)
        redacted2, _ = tokenizer.redact(text2, e2)

        # Both should use the same token
        assert "[PERSON_1]" in redacted1
        assert "[PERSON_1]" in redacted2

    def test_different_values_get_different_tokens(self, tokenizer):
        text = "John Smith and Jane Doe"
        entities = [
            self._make_entity("PERSON", "John Smith", 0, 10),
            self._make_entity("PERSON", "Jane Doe", 15, 23),
        ]
        redacted, mapping = tokenizer.redact(text, entities)
        assert "[PERSON_1]" in redacted
        assert "[PERSON_2]" in redacted
        # Both values should be in the mapping (order depends on processing direction)
        assert set(mapping.values()) == {"John Smith", "Jane Doe"}
        assert "John Smith" not in redacted
        assert "Jane Doe" not in redacted

    def test_skip_non_redactable_entities(self, tokenizer):
        text = "Amount: $75,000"
        entities = [self._make_entity("AMOUNT", "$75,000", 8, 15, should_redact=False)]
        redacted, mapping = tokenizer.redact(text, entities)
        assert redacted == text  # Nothing should be redacted
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
        assert "[SSN_1]" in full_mapping
        assert full_mapping["[SSN_1]"] == "123-45-6789"

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
        assert "[EMAIL_1]" in redacted


class TestRehydrator:
    """Test token rehydration (restoring PII)."""

    def test_rehydrate_single_token(self):
        mapping = {"[SSN_1]": "123-45-6789"}
        rehydrator = Rehydrator(mapping)
        text = "Your SSN is [SSN_1]"
        result = rehydrator.rehydrate(text)
        assert result == "Your SSN is 123-45-6789"

    def test_rehydrate_multiple_tokens(self):
        mapping = {
            "[SSN_1]": "123-45-6789",
            "[PERSON_1]": "John Smith",
            "[EIN_1]": "98-7654321",
        }
        rehydrator = Rehydrator(mapping)
        text = "[PERSON_1] with SSN [SSN_1] works at employer EIN [EIN_1]"
        result = rehydrator.rehydrate(text)
        assert "John Smith" in result
        assert "123-45-6789" in result
        assert "98-7654321" in result

    def test_rehydrate_preserves_non_token_text(self):
        mapping = {"[SSN_1]": "123-45-6789"}
        rehydrator = Rehydrator(mapping)
        text = "Wages: $75,000. SSN: [SSN_1]. Tax: $12,500."
        result = rehydrator.rehydrate(text)
        assert "$75,000" in result
        assert "$12,500" in result
        assert "123-45-6789" in result

    def test_rehydrate_empty_text(self):
        rehydrator = Rehydrator({"[SSN_1]": "123-45-6789"})
        assert rehydrator.rehydrate("") == ""
        assert rehydrator.rehydrate(None) is None

    def test_find_tokens(self):
        rehydrator = Rehydrator({})
        tokens = rehydrator.find_tokens("Hello [PERSON_1], your SSN is [SSN_1]")
        assert "[PERSON_1]" in tokens
        assert "[SSN_1]" in tokens

    def test_validate_mapping(self):
        mapping = {"[SSN_1]": "123-45-6789"}
        rehydrator = Rehydrator(mapping)
        validation = rehydrator.validate_mapping("[SSN_1] and [PERSON_1]")
        assert validation["[SSN_1]"] is True
        assert validation["[PERSON_1]"] is False

    def test_roundtrip_tokenize_rehydrate(self):
        """Tokenize then rehydrate should restore original text."""
        tokenizer = Tokenizer()
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
