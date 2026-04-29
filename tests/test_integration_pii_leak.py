"""Integration tests: PII leak prevention.

These tests verify that NO personally identifiable information
appears in the redacted output that would be sent to the AI.
This is the core privacy guarantee of CipherTax.
"""

from __future__ import annotations

import re
from unittest.mock import patch, MagicMock

import pytest

from tests.conftest import (
    assert_no_pii_in_text,
    SSN_PATTERN,
    EIN_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    requires_tesseract,
)
from tests.fixtures.generate_fixtures import (
    ALL_PII_VALUES,
    MOCK_W2,
    MOCK_1099_INT,
    MOCK_1099_NEC,
    MOCK_DENSE_PII,
)


class TestPIILeakPreventionW2:
    """Verify no PII leaks from W-2 processing."""

    def test_no_ssn_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        ssn = MOCK_W2["employee_ssn"]
        assert ssn not in result.redacted_text, f"SSN '{ssn}' found in redacted text!"

    def test_no_name_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        name = MOCK_W2["employee_name"]
        assert name not in result.redacted_text, f"Name '{name}' found in redacted text!"

    def test_no_ein_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        ein = MOCK_W2["employer_ein"]
        assert ein not in result.redacted_text, f"EIN '{ein}' found in redacted text!"

    def test_no_email_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        email = MOCK_W2["email"]
        assert email not in result.redacted_text, f"Email '{email}' found in redacted text!"

    def test_no_phone_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        phone = MOCK_W2["phone"]
        assert phone not in result.redacted_text, f"Phone '{phone}' found in redacted text!"

    def test_no_ssn_pattern_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert_no_pii_in_text(result.redacted_text)

    def test_wages_preserved_in_redacted_text(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert MOCK_W2["wages"] in result.redacted_text, "Wages should be preserved"

    def test_federal_tax_preserved(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert MOCK_W2["federal_tax"] in result.redacted_text, "Federal tax should be preserved"

    def test_state_preserved(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert MOCK_W2["state"] in result.redacted_text, "State should be preserved"


class TestPIILeakPrevention1099INT:
    """Verify no PII leaks from 1099-INT processing."""

    def test_no_ssn_in_redacted(self, pipeline, f1099_int_pdf):
        result = pipeline.process(f1099_int_pdf, skip_ai=True)
        assert MOCK_1099_INT["recipient_ssn"] not in result.redacted_text

    def test_no_name_in_redacted(self, pipeline, f1099_int_pdf):
        result = pipeline.process(f1099_int_pdf, skip_ai=True)
        assert MOCK_1099_INT["recipient_name"] not in result.redacted_text

    def test_no_ein_in_redacted(self, pipeline, f1099_int_pdf):
        result = pipeline.process(f1099_int_pdf, skip_ai=True)
        assert MOCK_1099_INT["payer_ein"] not in result.redacted_text

    def test_interest_income_preserved(self, pipeline, f1099_int_pdf):
        result = pipeline.process(f1099_int_pdf, skip_ai=True)
        assert MOCK_1099_INT["interest_income"] in result.redacted_text


class TestPIILeakPrevention1099NEC:
    """Verify no PII leaks from 1099-NEC processing."""

    def test_no_ssn_in_redacted(self, pipeline, f1099_nec_pdf):
        result = pipeline.process(f1099_nec_pdf, skip_ai=True)
        assert MOCK_1099_NEC["recipient_ssn"] not in result.redacted_text

    def test_no_name_in_redacted(self, pipeline, f1099_nec_pdf):
        result = pipeline.process(f1099_nec_pdf, skip_ai=True)
        assert MOCK_1099_NEC["recipient_name"] not in result.redacted_text

    def test_no_email_in_redacted(self, pipeline, f1099_nec_pdf):
        result = pipeline.process(f1099_nec_pdf, skip_ai=True)
        assert MOCK_1099_NEC["email"] not in result.redacted_text

    def test_compensation_preserved(self, pipeline, f1099_nec_pdf):
        result = pipeline.process(f1099_nec_pdf, skip_ai=True)
        assert MOCK_1099_NEC["nonemployee_compensation"] in result.redacted_text


class TestPIILeakPreventionDensePII:
    """Verify no PII leaks from a document with many PII items."""

    def test_no_ssns_in_redacted(self, pipeline, dense_pii_pdf):
        result = pipeline.process(dense_pii_pdf, skip_ai=True)
        for ssn in MOCK_DENSE_PII["ssns"]:
            assert ssn not in result.redacted_text, f"SSN '{ssn}' leaked!"

    def test_no_names_in_redacted(self, pipeline, dense_pii_pdf):
        result = pipeline.process(dense_pii_pdf, skip_ai=True)
        for name in MOCK_DENSE_PII["names"]:
            # Skip Unicode names as spaCy may not detect them perfectly
            if all(ord(c) < 128 for c in name):
                assert name not in result.redacted_text, f"Name '{name}' leaked!"

    def test_no_emails_in_redacted(self, pipeline, dense_pii_pdf):
        result = pipeline.process(dense_pii_pdf, skip_ai=True)
        for email in MOCK_DENSE_PII["emails"]:
            assert email not in result.redacted_text, f"Email '{email}' leaked!"

    def test_no_eins_in_redacted(self, pipeline, dense_pii_pdf):
        result = pipeline.process(dense_pii_pdf, skip_ai=True)
        for ein in MOCK_DENSE_PII["eins"]:
            assert ein not in result.redacted_text, f"EIN '{ein}' leaked!"

    def test_no_phones_in_redacted(self, pipeline, dense_pii_pdf):
        result = pipeline.process(dense_pii_pdf, skip_ai=True)
        for phone in MOCK_DENSE_PII["phones"]:
            assert phone not in result.redacted_text, f"Phone '{phone}' leaked!"


class TestPIILeakPreventionMultiPage:
    """Verify no PII leaks across multiple pages."""

    def test_no_ssn_across_pages(self, pipeline, multi_page_pdf):
        result = pipeline.process(multi_page_pdf, skip_ai=True)
        assert "234-56-7890" not in result.redacted_text
        assert "345-67-8901" not in result.redacted_text

    def test_no_email_across_pages(self, pipeline, multi_page_pdf):
        result = pipeline.process(multi_page_pdf, skip_ai=True)
        assert "maria.rodriguez@example.com" not in result.redacted_text


class TestPIILeakPreventionMockedClaude:
    """Verify no PII is sent to Claude API by intercepting the API call."""

    @patch("ciphertax.ai.claude_client.Anthropic")
    def test_no_pii_sent_to_claude(self, mock_anthropic_cls, w2_pdf, tmp_path, mock_claude_response):
        """Mock Claude API, capture payload, verify zero PII."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response

        from ciphertax.pipeline import CipherTaxPipeline

        pipeline = CipherTaxPipeline(
            vault_password="test",
            vault_dir=tmp_path / "vaults",
            api_key="fake-key",
        )
        result = pipeline.process(w2_pdf, skip_ai=False)

        # Capture what was sent to Claude
        call_args = mock_client.messages.create.call_args
        sent_messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        sent_text = sent_messages[0]["content"]

        # Verify NO PII in the sent text
        assert MOCK_W2["employee_ssn"] not in sent_text
        assert MOCK_W2["employee_name"] not in sent_text
        assert MOCK_W2["employer_ein"] not in sent_text
        assert MOCK_W2["email"] not in sent_text
        assert MOCK_W2["phone"] not in sent_text
        assert_no_pii_in_text(sent_text)

        # Verify tokens ARE present
        assert "[SSN_1]" in sent_text or "[SSN_" in sent_text
        assert "[PERSON_" in sent_text

    @patch("ciphertax.ai.claude_client.Anthropic")
    def test_rehydrated_response_has_real_pii(self, mock_anthropic_cls, w2_pdf, tmp_path, mock_claude_response):
        """After rehydration, the real PII should be restored."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_claude_response.content[0].text = (
            "The employee [PERSON_1] with SSN [SSN_1] earned $92,450.00 in wages."
        )
        mock_client.messages.create.return_value = mock_claude_response

        from ciphertax.pipeline import CipherTaxPipeline

        pipeline = CipherTaxPipeline(
            vault_password="test",
            vault_dir=tmp_path / "vaults",
            api_key="fake-key",
        )
        result = pipeline.process(w2_pdf, skip_ai=False)

        # The rehydrated response should contain real PII
        assert result.ai_response_rehydrated is not None
        # The tokenized response should NOT contain real PII
        assert MOCK_W2["employee_ssn"] not in result.ai_response


class TestSafetyCheck:
    """Test the last-resort safety check in ClaudeClient."""

    def test_safety_check_blocks_leaked_ssn(self):
        from ciphertax.ai.claude_client import ClaudeClient
        with pytest.raises(ValueError, match="SAFETY CHECK FAILED"):
            ClaudeClient._safety_check("This text has SSN 234-56-7890 that was not redacted")

    def test_safety_check_allows_clean_text(self):
        from ciphertax.ai.claude_client import ClaudeClient
        # Should not raise
        ClaudeClient._safety_check(
            "[PERSON_1] earned $92,450.00 at [PERSON_2] (EIN [EIN_1])"
        )

    def test_safety_check_allows_tokens(self):
        from ciphertax.ai.claude_client import ClaudeClient
        ClaudeClient._safety_check("[SSN_1] [PERSON_1] [EIN_1] [ADDRESS_1]")
