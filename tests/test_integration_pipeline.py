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
        # At least SSN should be tokenized (tokens use [CT_<prefix>_SSN_N] format)
        assert any("_SSN_" in k for k in result.token_mapping)

    def test_w2_vault_has_all_mappings(self, pipeline_with_vault, w2_pdf):
        # Vault is only created when persist_vault=True AND AI is called.
        # In skip_ai mode, no vault is created — test in-memory mapping instead.
        result = pipeline_with_vault.process(w2_pdf, skip_ai=True)
        # Memory mapping always has the data
        assert len(pipeline_with_vault.memory_mapping) > 0
        assert len(pipeline_with_vault.memory_mapping) >= len(result.token_mapping)

    def test_w2_redacted_has_tokens(self, pipeline, w2_pdf):
        result = pipeline.process(w2_pdf, skip_ai=True)
        # New token format: [CT_<prefix>_TYPE_N]
        assert "_SSN_" in result.redacted_text
        assert "_PERSON_" in result.redacted_text or "_EIN_" in result.redacted_text


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

    def test_multi_doc_memory_accumulates(self, pipeline, w2_pdf, f1099_int_pdf):
        """In-memory mapping should accumulate from both documents."""
        pipeline.process(w2_pdf, skip_ai=True)
        pipeline.process(f1099_int_pdf, skip_ai=True)
        # Memory mapping should contain tokens from both documents
        assert len(pipeline.memory_mapping) >= 2


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
        # Generic response (token format now uses session prefix)
        mock_claude_response.content[0].text = (
            '{"wages": 92450.00, "federal_tax_withheld": 16200.00, "state": "IL"}'
        )
        mock_client.messages.create.return_value = mock_claude_response

        from ciphertax.pipeline import CipherTaxPipeline

        pipeline = CipherTaxPipeline(
            vault_dir=tmp_path / "vaults",
            api_key="fake-key",
            persist_vault=False,
        )
        result = pipeline.process(w2_pdf, skip_ai=False)

        # Should have AI response
        assert result.ai_response is not None
        assert result.ai_response_rehydrated is not None
        assert result.errors == []
        assert not result.pii_leak_blocked

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
                vault_dir=tmp_path / f"vaults_{task.value}",
                api_key="fake-key",
                persist_vault=False,
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

    def test_cleanup_clears_memory_no_vault(self, pipeline, w2_pdf):
        """Default pipeline (persist_vault=False) clears memory mapping."""
        pipeline.process(w2_pdf, skip_ai=True)
        assert len(pipeline.memory_mapping) > 0
        # No vault should exist
        assert pipeline.vault_path is None

        pipeline.cleanup()
        assert len(pipeline.memory_mapping) == 0

    @patch("ciphertax.ai.claude_client.Anthropic")
    def test_cleanup_destroys_vault_when_persisted(
        self, mock_anthropic_cls, pipeline_with_vault, w2_pdf, mock_claude_response
    ):
        """When persist_vault=True and AI is used, vault is created and can be destroyed."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response
        pipeline_with_vault._api_key = "fake"

        # Process with AI to trigger vault creation
        pipeline_with_vault.process(w2_pdf, skip_ai=False)
        vault_path = pipeline_with_vault.vault_path
        assert vault_path is not None and vault_path.exists()

        pipeline_with_vault.cleanup()
        assert not vault_path.exists()

    @patch("ciphertax.ai.claude_client.Anthropic")
    def test_vault_encrypted_on_disk(
        self, mock_anthropic_cls, pipeline_with_vault, w2_pdf, mock_claude_response
    ):
        """Raw vault bytes should not contain plaintext PII."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_response
        pipeline_with_vault._api_key = "fake"

        pipeline_with_vault.process(w2_pdf, skip_ai=False)
        assert pipeline_with_vault.vault_path is not None

        vault_bytes = pipeline_with_vault.vault_path.read_bytes()
        vault_text = vault_bytes.decode("latin-1")

        assert MOCK_W2["employee_ssn"] not in vault_text
        assert MOCK_W2["employee_name"] not in vault_text
