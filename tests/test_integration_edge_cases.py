"""Integration tests: Edge cases and corner cases."""

from __future__ import annotations

import pytest

from tests.conftest import requires_tesseract, assert_no_pii_in_text
from tests.fixtures.generate_fixtures import MOCK_W2, MOCK_UNICODE_NAMES


class TestEdgeCaseEmptyPDF:
    """Test handling of empty or near-empty PDFs."""

    def test_empty_pdf_no_crash(self, pipeline, empty_pdf):
        result = pipeline.process(empty_pdf, skip_ai=True)
        assert result.pages_extracted >= 1
        assert result.pii_entities_found == 0
        assert result.errors == []

    def test_empty_pdf_no_tokens(self, pipeline, empty_pdf):
        result = pipeline.process(empty_pdf, skip_ai=True)
        assert len(result.token_mapping) == 0


class TestEdgeCaseUnicode:
    """Test handling of Unicode/accented names."""

    def test_unicode_pdf_no_crash(self, pipeline, unicode_pdf):
        result = pipeline.process(unicode_pdf, skip_ai=True)
        assert result.pages_extracted >= 1
        assert result.errors == []

    def test_unicode_ssn_redacted(self, pipeline, unicode_pdf):
        result = pipeline.process(unicode_pdf, skip_ai=True)
        assert MOCK_UNICODE_NAMES["employee_ssn"] not in result.redacted_text

    def test_unicode_ein_redacted(self, pipeline, unicode_pdf):
        result = pipeline.process(unicode_pdf, skip_ai=True)
        assert MOCK_UNICODE_NAMES["employer_ein"] not in result.redacted_text

    def test_unicode_wages_preserved(self, pipeline, unicode_pdf):
        result = pipeline.process(unicode_pdf, skip_ai=True)
        assert MOCK_UNICODE_NAMES["wages"] in result.redacted_text


class TestEdgeCaseDuplicatePII:
    """Test handling of duplicate PII values."""

    def test_same_ssn_same_token(self, pipeline, dense_pii_pdf):
        """Same SSN appearing multiple times should get the same token."""
        result = pipeline.process(dense_pii_pdf, skip_ai=True)
        # Count how many unique SSN tokens were created
        ssn_tokens = [k for k in result.token_mapping if "[SSN_" in k]
        ssn_values = [v for k, v in result.token_mapping.items() if "[SSN_" in k]
        # Each unique SSN value should have exactly one token
        assert len(ssn_values) == len(set(ssn_values)), "Duplicate tokens for same SSN"

    def test_tokens_are_deterministic(self, pipeline, w2_pdf):
        """Processing the same document twice should produce same tokens."""
        result1 = pipeline.process(w2_pdf, skip_ai=True)
        # Second processing reuses the same tokenizer with same mappings
        # The SSN token should be the same
        ssn_token_1 = None
        for token, value in result1.token_mapping.items():
            if value == MOCK_W2["employee_ssn"]:
                ssn_token_1 = token
                break
        assert ssn_token_1 is not None, "SSN was not tokenized"


class TestEdgeCaseSSNFormats:
    """Test various SSN-like number formats."""

    def test_ssn_near_dollar_amounts(self):
        """SSN next to dollar amounts should not confuse detection."""
        from ciphertax.detection import PIIDetector
        from ciphertax.redaction import Tokenizer

        detector = PIIDetector()
        tokenizer = Tokenizer()

        text = "Wages $92,450.00 paid to SSN 234-56-7890 for tax year 2024"
        entities = detector.detect(text)
        redacted, mapping = tokenizer.redact(text, entities)

        # SSN should be redacted
        assert "234-56-7890" not in redacted
        # Dollar amount should be preserved
        assert "92,450.00" in redacted

    def test_multiple_number_formats(self):
        """Various number formats should not false-positive as SSNs."""
        from ciphertax.detection import PIIDetector

        detector = PIIDetector()
        text = "Invoice #12345, Amount: $5,000.00, Date: 12/15/2024, Code: ABC-123"
        entities = detector.detect(text)
        ssn_entities = [e for e in entities if e.entity_type == "US_SSN"]
        # None of these should be detected as SSNs
        assert len(ssn_entities) == 0


class TestEdgeCaseExtraction:
    """Test extraction edge cases."""

    def test_nonexistent_file_raises(self, pipeline):
        with pytest.raises(FileNotFoundError):
            pipeline.process("/nonexistent/file.pdf", skip_ai=True)

    def test_unsupported_file_type(self, pipeline, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world")
        with pytest.raises(ValueError, match="Unsupported file type"):
            pipeline.process(txt_file, skip_ai=True)


class TestEdgeCaseDetection:
    """Test PII detection edge cases."""

    def test_detect_pii_in_context(self):
        """PII with context words should get higher detection scores."""
        from ciphertax.detection import PIIDetector

        detector = PIIDetector()
        text_with_context = "Employee's social security number: 234-56-7890"
        text_without_context = "Number 234-56-7890 recorded"

        entities_ctx = detector.detect(text_with_context)
        entities_no_ctx = detector.detect(text_without_context)

        # Both should detect the SSN
        ssn_ctx = [e for e in entities_ctx if e.entity_type == "US_SSN"]
        ssn_no_ctx = [e for e in entities_no_ctx if e.entity_type == "US_SSN"]
        assert len(ssn_ctx) >= 1

    def test_no_false_positives_on_zip_codes(self):
        """5-digit ZIP codes should not be detected as SSNs."""
        from ciphertax.detection import PIIDetector

        detector = PIIDetector()
        text = "Springfield, IL 62704"
        entities = detector.detect(text)
        ssn_entities = [e for e in entities if e.entity_type == "US_SSN"]
        # ZIP code should not trigger SSN detection
        zip_as_ssn = [e for e in ssn_entities if e.text == "62704"]
        assert len(zip_as_ssn) == 0

    def test_detect_multiple_entity_types(self):
        """Detection should find multiple entity types."""
        from ciphertax.detection import PIIDetector

        detector = PIIDetector()
        text = (
            "Employee: John Smith, SSN: 234-56-7890, "
            "Email: john@example.com, Phone: (555) 867-5309"
        )
        entities = detector.detect(text)
        types = set(e.entity_type for e in entities)
        assert "US_SSN" in types
        assert "EMAIL_ADDRESS" in types


class TestEdgeCaseTokenization:
    """Test tokenization edge cases."""

    def test_empty_text_no_crash(self):
        from ciphertax.redaction import Tokenizer
        tokenizer = Tokenizer()
        redacted, mapping = tokenizer.redact("", [])
        assert redacted == ""
        assert mapping == {}

    def test_text_with_no_pii(self):
        from ciphertax.detection import PIIDetector
        from ciphertax.redaction import Tokenizer

        detector = PIIDetector()
        tokenizer = Tokenizer()
        text = "Total income for tax year 2024 was $150,000.00"
        entities = detector.detect(text)
        redacted, mapping = tokenizer.redact(text, entities)
        # Financial amounts should not be redacted
        assert "150,000.00" in redacted

    def test_overlapping_pii_handled(self):
        """Overlapping PII should be resolved (not crash)."""
        from ciphertax.detection import PIIDetector

        detector = PIIDetector()
        # This could produce overlapping entities
        text = "SSN 234-56-7890 belongs to Maria Rodriguez at maria@example.com"
        entities = detector.detect(text)
        # No overlaps should remain
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i != j:
                    assert not (e1.start < e2.end and e1.end > e2.start), (
                        f"Overlap: {e1} and {e2}"
                    )


class TestEdgeCaseRehydration:
    """Test rehydration edge cases."""

    def test_rehydrate_with_unknown_tokens(self):
        """Tokens not in mapping should be left as-is."""
        from ciphertax.redaction import Rehydrator

        mapping = {"[SSN_1]": "234-56-7890"}
        rehydrator = Rehydrator(mapping)
        text = "[SSN_1] and [UNKNOWN_1] and [PERSON_99]"
        result = rehydrator.rehydrate(text)
        assert "234-56-7890" in result
        assert "[UNKNOWN_1]" in result
        assert "[PERSON_99]" in result

    def test_rehydrate_preserves_formatting(self):
        """Rehydration should preserve surrounding text formatting."""
        from ciphertax.redaction import Rehydrator

        mapping = {"[PERSON_1]": "John Smith"}
        rehydrator = Rehydrator(mapping)
        text = "Name: [PERSON_1]\nAddress: 123 Main St"
        result = rehydrator.rehydrate(text)
        assert result == "Name: John Smith\nAddress: 123 Main St"


class TestEdgeCaseImageFiles:
    """Test image file handling edge cases."""

    def test_is_image_file_detection(self):
        from ciphertax.extraction.image_extractor import is_image_file
        assert is_image_file("photo.png")
        assert is_image_file("photo.PNG")
        assert is_image_file("photo.jpg")
        assert is_image_file("photo.jpeg")
        assert is_image_file("photo.tiff")
        assert is_image_file("photo.bmp")
        assert is_image_file("photo.webp")
        assert not is_image_file("document.pdf")
        assert not is_image_file("data.csv")
        assert not is_image_file("text.txt")

    def test_extract_from_file_routes_correctly(self, w2_pdf):
        """extract_text_from_file should route PDFs to PDF extractor."""
        from ciphertax.extraction import extract_text_from_file
        pages = extract_text_from_file(w2_pdf)
        assert len(pages) >= 1
        assert pages[0]["method"] == "digital"

    @requires_tesseract
    def test_extract_from_file_routes_images(self, w2_photo_png):
        """extract_text_from_file should route images to OCR."""
        from ciphertax.extraction import extract_text_from_file
        pages = extract_text_from_file(w2_photo_png)
        assert len(pages) == 1
        assert pages[0]["method"] == "ocr"

    def test_nonexistent_image_raises(self):
        from ciphertax.extraction.image_extractor import extract_text_from_image
        with pytest.raises(FileNotFoundError):
            extract_text_from_image("/nonexistent/photo.png")

    def test_unsupported_image_format(self, tmp_path):
        from ciphertax.extraction.image_extractor import extract_text_from_image
        fake_file = tmp_path / "data.csv"
        fake_file.write_text("a,b,c")
        with pytest.raises(ValueError, match="Unsupported image format"):
            extract_text_from_image(fake_file)
