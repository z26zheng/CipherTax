"""Pipeline — orchestrates the full CipherTax workflow.

Ties together extraction, detection, tokenization, vault storage,
AI interaction, and rehydration into a single cohesive workflow.

Workflow:
    PDF → Extract Text → Detect PII → Tokenize → Store in Vault
    → Send Redacted Text to Claude → Rehydrate Response → Output
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ciphertax.ai.claude_client import ClaudeClient, TaskType
from ciphertax.detection.detector import PIIDetector, PIIEntity
from ciphertax.extraction import extract_text_from_file
from ciphertax.redaction.rehydrator import Rehydrator
from ciphertax.redaction.tokenizer import Tokenizer
from ciphertax.vault.secure_vault import SecureVault

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a tax document through the pipeline."""

    # Input
    source_file: str
    pages_extracted: int
    extraction_methods: list[str]

    # Detection
    pii_entities_found: int
    pii_entities_redacted: int
    entity_types: list[str]

    # Redaction
    original_text: str
    redacted_text: str
    token_mapping: dict[str, str]

    # AI response (if applicable)
    ai_response: str | None = None
    ai_response_rehydrated: str | None = None

    # Vault
    vault_path: str | None = None

    # Metadata
    errors: list[str] = field(default_factory=list)


class CipherTaxPipeline:
    """Main pipeline for privacy-preserving tax document processing.

    Usage:
        pipeline = CipherTaxPipeline(vault_password="my-password")

        # Process a tax PDF
        result = pipeline.process("w2.pdf", task=TaskType.EXTRACT)

        # result.redacted_text — what was sent to AI (no PII)
        # result.ai_response_rehydrated — AI response with real PII restored
        # result.token_mapping — token → PII mapping (stored in encrypted vault)
    """

    def __init__(
        self,
        vault_password: str | None = None,
        vault_dir: Path | None = None,
        api_key: str | None = None,
        model: str | None = None,
        score_threshold: float = 0.25,
    ):
        """Initialize the pipeline.

        Args:
            vault_password: Password for the encrypted vault. Auto-generated if None.
            vault_dir: Directory for vault files. Defaults to ~/.ciphertax/
            api_key: Anthropic API key. If None, reads from env.
            model: Claude model to use.
            score_threshold: Minimum PII detection confidence score.
        """
        self._detector = PIIDetector(score_threshold=score_threshold)
        self._tokenizer = Tokenizer()

        # Create vault
        self._vault, self._vault_password = SecureVault.create(
            password=vault_password,
            vault_dir=vault_dir,
        )

        # Initialize Claude client (may fail if no API key — that's OK for inspect-only mode)
        self._claude: ClaudeClient | None = None
        self._api_key = api_key
        self._model = model

        logger.info("CipherTax pipeline initialized")

    def _get_claude_client(self) -> ClaudeClient:
        """Lazy-initialize the Claude client."""
        if self._claude is None:
            self._claude = ClaudeClient(api_key=self._api_key, model=self._model)
        return self._claude

    def process(
        self,
        pdf_path: str | Path,
        task: TaskType = TaskType.EXTRACT,
        query: str | None = None,
        force_ocr: bool = False,
        skip_ai: bool = False,
    ) -> ProcessingResult:
        """Process a tax PDF through the full pipeline.

        Args:
            pdf_path: Path to the tax PDF file.
            task: AI task type (extract, advise, review, file).
            query: Optional specific question (for advise task).
            force_ocr: Force OCR for all pages.
            skip_ai: If True, only extract/detect/redact (don't send to AI).

        Returns:
            ProcessingResult with all pipeline outputs.
        """
        pdf_path = Path(pdf_path)
        errors: list[str] = []

        # Step 1: Extract text from PDF
        logger.info("Step 1/5: Extracting text from %s", pdf_path.name)
        pages = extract_text_from_file(pdf_path, force_ocr=force_ocr)
        full_text = "\n\n".join(f"--- Page {p['page']} ---\n{p['text']}" for p in pages)
        extraction_methods = list(set(p["method"] for p in pages))

        # Step 2: Detect PII
        logger.info("Step 2/5: Detecting PII entities")
        entities: list[PIIEntity] = self._detector.detect(full_text)
        entity_types = list(set(e.entity_type for e in entities))

        # Step 3: Tokenize (redact PII)
        logger.info("Step 3/5: Tokenizing PII (smart redaction)")
        redacted_text, token_mapping = self._tokenizer.redact(full_text, entities)

        # Step 4: Store mapping in encrypted vault
        logger.info("Step 4/5: Storing token mapping in encrypted vault")
        self._vault.update(token_mapping)

        # Step 5: Send to AI (optional)
        ai_response = None
        ai_response_rehydrated = None

        if not skip_ai:
            logger.info("Step 5/5: Sending redacted text to Claude (%s)", task.value)
            try:
                client = self._get_claude_client()
                ai_response = client.process(
                    redacted_text=redacted_text,
                    task=task,
                    query=query,
                )

                # Rehydrate the response
                full_mapping = self._vault.retrieve()
                rehydrator = Rehydrator(full_mapping)
                ai_response_rehydrated = rehydrator.rehydrate(ai_response)

            except Exception as e:
                error_msg = f"AI processing failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        else:
            logger.info("Step 5/5: Skipping AI (inspect-only mode)")

        redacted_count = sum(1 for e in entities if e.should_redact)

        result = ProcessingResult(
            source_file=str(pdf_path),
            pages_extracted=len(pages),
            extraction_methods=extraction_methods,
            pii_entities_found=len(entities),
            pii_entities_redacted=redacted_count,
            entity_types=entity_types,
            original_text=full_text,
            redacted_text=redacted_text,
            token_mapping=token_mapping,
            ai_response=ai_response,
            ai_response_rehydrated=ai_response_rehydrated,
            vault_path=str(self._vault.path),
            errors=errors,
        )

        logger.info(
            "Pipeline complete: %d pages, %d PII entities found, %d redacted, %d errors",
            result.pages_extracted,
            result.pii_entities_found,
            result.pii_entities_redacted,
            len(result.errors),
        )

        return result

    def process_multiple(
        self,
        pdf_paths: list[str | Path],
        task: TaskType = TaskType.EXTRACT,
        query: str | None = None,
        force_ocr: bool = False,
        skip_ai: bool = False,
    ) -> list[ProcessingResult]:
        """Process multiple tax PDFs through the pipeline.

        All documents share the same vault (consistent token mapping across docs).

        Args:
            pdf_paths: List of PDF file paths.
            task: AI task type.
            query: Optional question.
            force_ocr: Force OCR.
            skip_ai: Skip AI step.

        Returns:
            List of ProcessingResult objects.
        """
        results = []
        for pdf_path in pdf_paths:
            result = self.process(
                pdf_path=pdf_path,
                task=task,
                query=query,
                force_ocr=force_ocr,
                skip_ai=skip_ai,
            )
            results.append(result)
        return results

    @property
    def vault_password(self) -> str:
        """Return the vault password (needed to reload the vault later)."""
        return self._vault_password

    @property
    def vault_path(self) -> Path:
        """Return the vault file path."""
        return self._vault.path

    def cleanup(self) -> None:
        """Securely destroy the vault after processing is complete."""
        self._vault.destroy()
        logger.info("Vault securely destroyed")
