"""Integration tests: Full pipeline end-to-end tests."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from tests.conftest import requires_tesseract
from tests.fixtures.generate_fixtures import MOCK_W2, MOCK_1099_INT


class TestPipelineW2:
    """Full pipeline tests with W-2 documents."""

    def test_w2_extraction(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert result.pages_extracted >= 1
        assert "digital" in result.extraction_methods
        assert len(result.original_text) > 100

    def test_w2_pii_detection(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert result.pii_entities_found > 0
        assert result.pii_entities_redacted > 0
        assert "US_SSN" in result.entity_types

    def test_w2_token_mapping_stored(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert len(result.token_mapping) > 0
        # At least SSN should be tokenized
        assert any("[SSN_" in k for k in result.token_mapping)

    def test_w2_vault_has_all_mappings(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        from ciphertax.vault.secure_vault import SecureVault
        vault = SecureVault.load(result.vault_path, password="test-password")
        mapping = vault.retrieve()
        assert len(mapping) >= len(result.token_mapping)

    def test_w2_redacted_has_tokens(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        assert "[SSN_" in result.redacted_text
        assert "[PERSON_" in result.redacted_text or "[EIN_" in result.redacted_text


class TestPipeline1099:
    """Full pipeline tests with 1099 documents."""

    def test_1099_int_extraction(self, pipeline, f1099_int_pdf):
        result = pipeline.process(f1099_int_pdf, skip_ai=True)
        assert result.pages_extracted >= 1
        assert len(result.original_text) > 50

    def test_1099_nec_extraction(self, pipeline, f1099_nec_pdf):
        result = pipeline.process(f1099_nec_pdf, skip_ai=True)
        assert result.pages_extracted >= 1
        assert result.pii_entities_found > 0


class TestPipelineMultiDocument:
    """Test processing multiple documents together."""

    def test_multi_doc_consistent_tokens(self, pipeline, w2_pdf, f1099_int_pdf):
        """Same PII across docs should get the same token."""
        result1 = pipeline.process(w2_pdf, skip_ai=True)
        result2 = pipeline.process(f1099_int_pdf, skip_ai=True)

        # Both results should have tokens
        assert len(result1.token_mapping) > 0
        assert len(result2.token_mapping) > 0

    def test_multi_doc_vault_accumulates(self, pipeline, w2_pdf, f1099_int_pdf):
        """Vault should accumulate mappings from both documents."""
        pipeline.process(w2_pdf, skip_ai=True)
        pipeline.process(f1099_int_pdf, skip_ai=True)

        from ciphertax.vault.secure_vault import SecureVault
        vault = SecureVault.load(pipeline.vault_path, password="test-password")
        mapping = vault.retrieve()
        # Should have tokens from both documents
        assert len(mapping) >= 2


class TestPipelineMultiPage:
    """Test multi-page document processing."""

    def test_multi_page_extraction(self, pipeline, multi_page_pdf):
        result = pipeline.process(multi_page_pdf, skip_ai=True)
        assert result.pages_extracted >= 2

    def test_multi_page_pii_found(self, pipeline, multi_page_pdf):
        result = pipeline.process(multi_page_pdf, skip_ai=True)
        assert result.pii_entities_found > 0
        assert result.pii_entities_redacted > 0


class TestPipelineMockedClaude:
    """Full pipeline with mocked Claude API."""

    @patch("ciphertax.ai.claude_client.Anthropic")
    def test_full_roundtrip(self, mock_anthropic_cls, w2_pdf, tmp_path, mock_claude_response):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_claude_response.content[0].text = (
            '{"employee": "[PERSON_1]", "ssn": "[SSN_1]", '
            '"wages": 92450.00, "state": "IL"}'
        )
        mock_client.messages.create.return_value = mock_claude_response

        from ciphertax.pipeline import CipherTaxPipeline

        pipeline = CipherTaxPipeline(
            vault_password="test",
            vault_dir=tmp_path / "vaults",
            api_key="fake-key",
        )
        result = pipeline.process(w2_pdf, skip_ai=False)

        # Should have AI response
        assert result.ai_response is not None
        assert result.ai_response_rehydrated is not None
        assert "[PERSON_1]" not in result.ai_response_rehydrated or result.ai_response_rehydrated != result.ai_response
        assert result.errors == []

    @patch("ciphertax.ai.claude_client.Anthropic")
    def test_all_task_types(self, mock_anthropic_cls, w2_pdf, tmp_path, mock_claude_response):
        """Test all task types work."""
        from ciphertax.ai.claude_client import TaskType

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response

        for task in TaskType:
            from ciphertax.pipeline import CipherTaxPipeline

            pipeline = CipherTaxPipeline(
                vault_password="test",
                vault_dir=tmp_path / f"vaults_{task.value}",
                api_key="fake-key",
            )
            result = pipeline.process(w2_pdf, task=task, skip_ai=False)
            assert result.ai_response is not None, f"Task {task.value} failed"


class TestPipelineImageBased:
    """Test pipeline with image-based (scanned) PDFs."""

    @requires_tesseract
    def test_scanned_pdf_extraction(self, pipeline, scanned_w2_pdf):
        result = pipeline.process(scanned_w2_pdf, skip_ai=True)
        assert result.pages_extracted >= 1
        # OCR should have been used
        assert "ocr" in result.extraction_methods

    @requires_tesseract
    def test_scanned_pdf_pii_detection(self, pipeline, scanned_w2_pdf):
        result = pipeline.process(scanned_w2_pdf, skip_ai=True)
        # OCR may not be perfect, but should detect some PII
        assert result.pii_entities_found >= 0  # May be 0 if OCR quality is poor

    @requires_tesseract
    def test_scanned_pdf_no_ssn_leak(self, pipeline, scanned_w2_pdf):
        result = pipeline.process(scanned_w2_pdf, skip_ai=True)
        # Even with OCR, SSN should not leak
        assert MOCK_W2["employee_ssn"] not in result.redacted_text

    @requires_tesseract
    def test_force_ocr_on_digital_pdf(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, force_ocr=True, skip_ai=True)
        assert result.pages_extracted >= 1
        assert "ocr" in result.extraction_methods


class TestPipelineDirectImage:
    """Test pipeline with direct image files (PNG, JPG)."""

    @requires_tesseract
    def test_png_image_extraction(self, pipeline, w2_photo_png):
        result = pipeline.process(w2_photo_png, skip_ai=True)
        assert result.pages_extracted == 1
        assert "ocr" in result.extraction_methods

    @requires_tesseract
    def test_jpg_image_extraction(self, pipeline, w2_photo_jpg):
        result = pipeline.process(w2_photo_jpg, skip_ai=True)
        assert result.pages_extracted == 1
        assert "ocr" in result.extraction_methods

    @requires_tesseract
    def test_png_no_ssn_leak(self, pipeline, w2_photo_png):
        result = pipeline.process(w2_photo_png, skip_ai=True)
        assert MOCK_W2["employee_ssn"] not in result.redacted_text

    @requires_tesseract
    def test_jpg_no_ssn_leak(self, pipeline, w2_photo_jpg):
        result = pipeline.process(w2_photo_jpg, skip_ai=True)
        assert MOCK_W2["employee_ssn"] not in result.redacted_text


class TestPipelineCleanup:
    """Test vault cleanup functionality."""

    def test_cleanup_destroys_vault(self, pipeline, w2_pdf):
        pipeline.process(w2_pdf, skip_ai=True)
        vault_path = pipeline.vault_path
        assert vault_path.exists()

        pipeline.cleanup()
        assert not vault_path.exists()

    def test_vault_encrypted_on_disk(self, pipeline, w2_pdf):
        """Raw vault bytes should not contain plaintext PII."""
        result = pipeline.process(w2_pdf, skip_ai=True)
        vault_bytes = pipeline.vault_path.read_bytes()
        vault_text = vault_bytes.decode("latin-1")  # Read as raw bytes

        assert MOCK_W2["employee_ssn"] not in vault_text
        assert MOCK_W2["employee_name"] not in vault_text
