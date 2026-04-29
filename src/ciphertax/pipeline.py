"""Pipeline — orchestrates the full CipherTax workflow.

Ties together extraction, detection, tokenization, vault storage,
AI interaction, and rehydration into a single cohesive workflow.

Workflow:
    PDF → Extract Text → Detect PII → Tokenize → (Optional) Encrypted Vault
    → Send Redacted Text to Claude → Rehydrate Response → Output

The vault is created LAZILY — only if AI is actually called and the user
opts to persist mappings. Inspect mode and skip_ai mode never create vaults.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ciphertax.ai.claude_client import ClaudeClient, PIILeakError, TaskType
from ciphertax.detection.detector import PIIDetector, PIIEntity
from ciphertax.extraction import extract_text_from_file
from ciphertax.redaction.rehydrator import Rehydrator
from ciphertax.redaction.tokenizer import Tokenizer
from ciphertax.vault.secure_vault import SecureVault

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a tax document through the pipeline.

    SECURITY NOTE: `token_mapping` contains real PII. Never write this
    to disk unencrypted. The pipeline keeps it in memory only by default.
    """

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
    token_mapping: dict[str, str]  # Contains real PII — handle with care

    # AI response (if applicable)
    ai_response: str | None = None
    ai_response_rehydrated: str | None = None

    # Vault (only set if persist_vault=True)
    vault_path: str | None = None

    # Metadata
    errors: list[str] = field(default_factory=list)
    pii_leak_blocked: bool = False  # True if safety check fired


class CipherTaxPipeline:
    """Main pipeline for privacy-preserving tax document processing.

    Usage:
        # Inspect-only (no vault, no AI)
        pipeline = CipherTaxPipeline()
        result = pipeline.process("w2.pdf", skip_ai=True)

        # Full processing with persistent vault (requires user password)
        pipeline = CipherTaxPipeline(
            vault_password="my-password",
            persist_vault=True,
        )
        result = pipeline.process("w2.pdf", task=TaskType.EXTRACT)
    """

    def __init__(
        self,
        vault_password: str | None = None,
        vault_dir: Path | None = None,
        api_key: str | None = None,
        model: str | None = None,
        score_threshold: float = 0.25,
        persist_vault: bool = False,
    ):
        """Initialize the pipeline.

        Args:
            vault_password: Password for the encrypted vault. REQUIRED if
                persist_vault=True. Should come from interactive prompt
                or environment variable, NEVER from a CLI argument.
            vault_dir: Directory for vault files. Defaults to ~/.ciphertax/
            api_key: Anthropic API key. If None, reads from env.
            model: Claude model to use.
            score_threshold: Minimum PII detection confidence score.
            persist_vault: If True, create an encrypted vault on disk.
                If False (default), keep mappings in memory only.
                Use False for inspect-only or single-session workflows.
        """
        self._detector = PIIDetector(score_threshold=score_threshold)
        self._tokenizer = Tokenizer()

        # Vault is created LAZILY — only if persist_vault=True
        self._persist_vault = persist_vault
        self._vault: SecureVault | None = None
        self._vault_password: str | None = None
        self._vault_dir = vault_dir
        self._user_vault_password = vault_password

        # In-memory mapping (always used; vault is optional persistence)
        self._memory_mapping: dict[str, str] = {}

        # Initialize Claude client lazily
        self._claude: ClaudeClient | None = None
        self._api_key = api_key
        self._model = model

        logger.info("CipherTax pipeline initialized (persist_vault=%s)", persist_vault)

    def _get_or_create_vault(self) -> SecureVault:
        """Lazy vault creation — only if persist_vault=True and AI is called."""
        if self._vault is None:
            if not self._persist_vault:
                raise RuntimeError(
                    "Vault access requested but persist_vault=False. "
                    "Pass persist_vault=True to enable disk persistence."
                )
            if self._user_vault_password is None:
                raise ValueError(
                    "vault_password is required when persist_vault=True. "
                    "Use interactive prompt — do NOT pass via CLI argument."
                )
            self._vault, self._vault_password = SecureVault.create(
                password=self._user_vault_password,
                vault_dir=self._vault_dir,
            )
        return self._vault

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
            skip_ai: If True, only extract/detect/redact (don't send to AI,
                don't create a vault — inspect mode).

        Returns:
            ProcessingResult with all pipeline outputs.
        """
        pdf_path = Path(pdf_path)
        errors: list[str] = []
        pii_leak_blocked = False

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

        # Step 4: Store mapping (in-memory always; vault only if persisting and using AI)
        self._memory_mapping.update(token_mapping)
        vault_path = None

        if not skip_ai and self._persist_vault:
            logger.info("Step 4/5: Storing token mapping in encrypted vault")
            vault = self._get_or_create_vault()
            vault.update(token_mapping)
            vault_path = str(vault.path)
        else:
            logger.info("Step 4/5: Keeping mappings in memory only (no vault)")

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

                # Rehydrate the response from in-memory mapping
                rehydrator = Rehydrator(self._memory_mapping)
                ai_response_rehydrated = rehydrator.rehydrate(ai_response)

            except PIILeakError as e:
                # CRITICAL: PII leak detected. Do NOT include redacted_text in
                # the result — it contains the leaked PII.
                pii_leak_blocked = True
                errors.append(f"PII LEAK BLOCKED: {e}")
                logger.error("PII leak blocked — clearing redacted_text from result")
                redacted_text = "[REDACTED — PII leak detected, content withheld]"
                token_mapping = {}  # Don't expose mappings either

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
            original_text=full_text if not pii_leak_blocked else "[REDACTED]",
            redacted_text=redacted_text,
            token_mapping=token_mapping,
            ai_response=ai_response,
            ai_response_rehydrated=ai_response_rehydrated,
            vault_path=vault_path,
            errors=errors,
            pii_leak_blocked=pii_leak_blocked,
        )

        logger.info(
            "Pipeline complete: %d pages, %d PII entities found, %d redacted, %d errors%s",
            result.pages_extracted,
            result.pii_entities_found,
            result.pii_entities_redacted,
            len(result.errors),
            " (PII LEAK BLOCKED)" if pii_leak_blocked else "",
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

        All documents share the same vault and tokenizer (consistent
        token mapping across docs).
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
    def vault_password(self) -> str | None:
        """Return the vault password if a vault was created."""
        return self._vault_password

    @property
    def vault_path(self) -> Path | None:
        """Return the vault file path if a vault was created."""
        return self._vault.path if self._vault else None

    @property
    def memory_mapping(self) -> dict[str, str]:
        """Return the in-memory token → PII mapping.

        SECURITY: Contains real PII. Do not log or persist unencrypted.
        """
        return dict(self._memory_mapping)

    def cleanup(self) -> None:
        """Securely destroy any vault and clear in-memory mappings."""
        if self._vault:
            self._vault.destroy()
            self._vault = None
            logger.info("Vault securely destroyed")
        self._memory_mapping.clear()
        self._tokenizer.reset()
        logger.info("In-memory mappings cleared")
