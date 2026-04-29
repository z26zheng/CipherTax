"""PII Detector — wraps Microsoft Presidio with tax-specific recognizers.

Provides a unified interface for detecting PII in tax document text.
Uses Presidio's AnalyzerEngine with built-in recognizers (SSN, names, addresses,
phone numbers, emails) plus custom tax recognizers (EIN, ITIN, bank accounts).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from ciphertax.detection.tax_recognizers import get_all_tax_recognizers

logger = logging.getLogger(__name__)

# Entity types that should NEVER be sent to AI — always redacted
ALWAYS_REDACT_ENTITIES = frozenset(
    {
        "US_SSN",
        "EIN",
        "ITIN",
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "US_BANK_NUMBER",
        "BANK_ACCOUNT",
        "ROUTING_NUMBER",
        "CONTROL_NUMBER",
        "CREDIT_CARD",
        "US_PASSPORT",
        "US_DRIVER_LICENSE",
        "IBAN_CODE",
        "IP_ADDRESS",
    }
)

# Entity types that are kept as-is (AI needs them for tax calculations)
KEEP_ENTITIES = frozenset(
    {
        # Income amounts, filing status, state — needed for tax math
        # These are NOT detected as PII by Presidio anyway,
        # but listed here for documentation purposes.
    }
)

# Entity types where we only redact specific parts
PARTIAL_REDACT_ENTITIES = frozenset(
    {
        "LOCATION",  # Keep state abbreviation, redact street address
        "DATE_TIME",  # Keep year, redact full DOB
    }
)


@dataclass
class PIIEntity:
    """A detected PII entity with its location and metadata."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float
    should_redact: bool

    def __repr__(self) -> str:
        masked = self.text[:2] + "***" if len(self.text) > 2 else "***"
        return f"PIIEntity({self.entity_type}, '{masked}', score={self.score:.2f})"


class PIIDetector:
    """Detect PII in text using Presidio with tax-specific enhancements.

    Usage:
        detector = PIIDetector()
        entities = detector.detect("My SSN is 123-45-6789")
        for entity in entities:
            print(entity.entity_type, entity.text, entity.should_redact)
    """

    def __init__(
        self,
        score_threshold: float = 0.25,
        language: str = "en",
    ):
        """Initialize the PII detector.

        Args:
            score_threshold: Minimum confidence score to consider a detection valid.
            language: Language code for NLP processing.
        """
        self.score_threshold = score_threshold
        self.language = language
        self._analyzer = self._create_analyzer()

    def _create_analyzer(self) -> AnalyzerEngine:
        """Create and configure the Presidio analyzer engine."""
        # Configure NLP engine with spaCy
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": self.language, "model_name": "en_core_web_sm"}],
        }

        nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=[self.language])

        # Register custom tax recognizers
        for recognizer in get_all_tax_recognizers():
            analyzer.registry.add_recognizer(recognizer)
            logger.debug("Registered tax recognizer: %s", recognizer.name)

        logger.info(
            "PII Detector initialized with %d recognizers",
            len(analyzer.registry.recognizers),
        )
        return analyzer

    def detect(self, text: str) -> list[PIIEntity]:
        """Detect PII entities in the given text.

        Args:
            text: The text to analyze for PII.

        Returns:
            List of PIIEntity objects found in the text.
        """
        if not text or not text.strip():
            return []

        results: list[RecognizerResult] = self._analyzer.analyze(
            text=text,
            language=self.language,
            score_threshold=self.score_threshold,
        )

        entities: list[PIIEntity] = []
        for result in results:
            entity = PIIEntity(
                entity_type=result.entity_type,
                text=text[result.start : result.end],
                start=result.start,
                end=result.end,
                score=result.score,
                should_redact=self._should_redact(result.entity_type),
            )
            entities.append(entity)

        # Sort by position (start index) for consistent processing
        entities.sort(key=lambda e: e.start)

        # Remove overlapping detections (keep highest score)
        entities = self._resolve_overlaps(entities)

        logger.info("Detected %d PII entities in text (%d chars)", len(entities), len(text))
        return entities

    def _should_redact(self, entity_type: str) -> bool:
        """Determine if an entity type should be redacted before sending to AI.

        Tax-smart redaction strategy:
        - Always redact: SSN, EIN, names, emails, phone numbers, bank info
        - Keep as-is: Income amounts, filing status (not detected as PII)
        - Partial: Addresses (keep state), dates (keep year)
        """
        if entity_type in ALWAYS_REDACT_ENTITIES:
            return True
        if entity_type in PARTIAL_REDACT_ENTITIES:
            return True  # Will be partially redacted by the tokenizer
        # Default: redact unknown entity types for safety
        return True

    @staticmethod
    def _resolve_overlaps(entities: list[PIIEntity]) -> list[PIIEntity]:
        """Remove overlapping detections, keeping the highest-scoring one."""
        if not entities:
            return entities

        resolved: list[PIIEntity] = []
        for entity in entities:
            # Check if this entity overlaps with any already-resolved entity
            overlapping = False
            for i, existing in enumerate(resolved):
                if entity.start < existing.end and entity.end > existing.start:
                    # Overlap detected — keep the one with higher score
                    if entity.score > existing.score:
                        resolved[i] = entity
                    overlapping = True
                    break

            if not overlapping:
                resolved.append(entity)

        return resolved

    def get_supported_entities(self) -> list[str]:
        """Return list of all entity types this detector can find."""
        return self._analyzer.get_supported_entities(language=self.language)
