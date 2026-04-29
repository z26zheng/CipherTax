"""Tests for PII detection layer."""

import pytest


class TestPIIDetector:
    """Test PII detection with Presidio + custom tax recognizers."""

    @pytest.fixture
    def detector(self):
        from ciphertax.detection.detector import PIIDetector
        return PIIDetector()

    def test_detect_ssn_with_dashes(self, detector):
        text = "Employee SSN: 123-45-6789"
        entities = detector.detect(text)
        ssn_entities = [e for e in entities if e.entity_type == "US_SSN"]
        assert len(ssn_entities) >= 1
        assert ssn_entities[0].text == "123-45-6789"
        assert ssn_entities[0].should_redact is True

    def test_detect_person_name(self, detector):
        text = "Taxpayer name: John Michael Smith works at Acme Corporation"
        entities = detector.detect(text)
        person_entities = [e for e in entities if e.entity_type == "PERSON"]
        assert len(person_entities) >= 1
        assert any("John" in e.text for e in person_entities)

    def test_detect_ein(self, detector):
        text = "Employer's identification number (EIN): 12-3456789"
        entities = detector.detect(text)
        ein_entities = [e for e in entities if e.entity_type == "EIN"]
        assert len(ein_entities) >= 1
        assert ein_entities[0].text == "12-3456789"

    def test_detect_phone_number(self, detector):
        text = "Contact phone: (555) 123-4567"
        entities = detector.detect(text)
        phone_entities = [e for e in entities if e.entity_type == "PHONE_NUMBER"]
        assert len(phone_entities) >= 1

    def test_detect_email(self, detector):
        text = "Email: taxpayer@example.com"
        entities = detector.detect(text)
        email_entities = [e for e in entities if e.entity_type == "EMAIL_ADDRESS"]
        assert len(email_entities) == 1
        assert email_entities[0].text == "taxpayer@example.com"

    def test_empty_text_returns_empty(self, detector):
        assert detector.detect("") == []
        assert detector.detect("   ") == []

    def test_no_pii_text(self, detector):
        text = "Total wages: $75,000.00. Federal tax withheld: $12,500.00"
        entities = detector.detect(text)
        # Financial amounts should NOT be detected as PII
        ssn_entities = [e for e in entities if e.entity_type == "US_SSN"]
        assert len(ssn_entities) == 0

    def test_all_entities_have_should_redact(self, detector):
        text = "John Smith SSN 123-45-6789 email john@example.com"
        entities = detector.detect(text)
        for entity in entities:
            assert isinstance(entity.should_redact, bool)

    def test_resolve_overlaps(self, detector):
        """Overlapping detections should be resolved (keep highest score)."""
        text = "SSN: 123-45-6789"
        entities = detector.detect(text)
        # Check no two entities overlap
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i != j:
                    assert not (e1.start < e2.end and e1.end > e2.start), (
                        f"Overlap: {e1} and {e2}"
                    )

    def test_w2_sample_text(self, detector):
        """Test detection on realistic W-2 text content."""
        w2_text = """
        Form W-2 Wage and Tax Statement 2024
        a Employee's social security number: 123-45-6789
        b Employer identification number (EIN): 98-7654321
        c Employer's name, address: Acme Corp, 123 Main St, Anytown CA 90210
        e Employee's name: Jane Marie Doe
        f Employee's address: 456 Oak Ave, Somecity CA 91234
        1 Wages, tips, other compensation: 85000.00
        2 Federal income tax withheld: 15200.00
        """
        entities = detector.detect(w2_text)
        entity_types = set(e.entity_type for e in entities)

        # Should detect SSN
        assert any(e.entity_type == "US_SSN" for e in entities)
        # Should detect at least one person
        assert any(e.entity_type == "PERSON" for e in entities)
        # Should detect EIN
        assert any(e.entity_type == "EIN" for e in entities)
