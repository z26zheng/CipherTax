"""Claude AI Client — interacts with Anthropic's API using only redacted text.

Sends PII-free, tokenized tax document content to Claude and receives
responses that use the same placeholder tokens. The responses can then
be rehydrated locally with real PII values.
"""

from __future__ import annotations

import logging
import os
from enum import Enum

from anthropic import Anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class PIILeakError(Exception):
    """Raised when PII is detected in text that's about to be sent to AI.

    This is a fatal error — the API call must NOT proceed. Callers should
    NOT log or display the offending text, as it contains the leaked PII.
    """
    pass


class TaskType(str, Enum):
    """Types of tax-related tasks the AI can perform."""

    EXTRACT = "extract"  # Extract structured data from documents
    ADVISE = "advise"  # Answer tax questions
    REVIEW = "review"  # Review documents for completeness
    FILE = "file"  # Prepare data for filing


# System prompts for each task type
SYSTEM_PROMPTS = {
    TaskType.EXTRACT: """You are a tax document data extraction assistant. You receive tax document text 
where personally identifiable information has been replaced with placeholder tokens 
(e.g., [SSN_1], [PERSON_1], [ADDRESS_1], [EIN_1]).

Your job is to extract structured data from the document. Use the SAME placeholder tokens 
in your output — do NOT try to guess or generate real PII values.

Output the extracted data as structured JSON with clear field names.
Financial amounts (income, wages, tax withheld, etc.) are provided as real values — use them as-is.
State abbreviations are provided as real values — use them as-is.

Example output format for a W-2:
{
    "form_type": "W-2",
    "tax_year": "2024",
    "employee": {"name": "[PERSON_1]", "ssn": "[SSN_1]", "address": "[ADDRESS_1]"},
    "employer": {"name": "[PERSON_2]", "ein": "[EIN_1]", "address": "[ADDRESS_2]"},
    "wages": 75000.00,
    "federal_tax_withheld": 12500.00,
    "state": "CA",
    "state_wages": 75000.00,
    "state_tax_withheld": 4500.00
}""",
    TaskType.ADVISE: """You are a knowledgeable tax advisor assistant. You receive tax document information 
where personally identifiable information has been replaced with placeholder tokens 
(e.g., [SSN_1], [PERSON_1], [ADDRESS_1]).

When referring to the taxpayer or other individuals, use their placeholder tokens 
(e.g., "[PERSON_1]" instead of trying to guess their name).

Financial amounts and state information are real — you can use them for calculations.
Provide accurate, helpful tax advice based on the financial data provided.
Always note that you are providing general information, not personalized tax advice.""",
    TaskType.REVIEW: """You are a tax document review assistant. You receive tax document text where 
personally identifiable information has been replaced with placeholder tokens.

Review the document for:
1. Completeness — are all required fields present?
2. Consistency — do the numbers add up correctly?
3. Potential issues — unusual values, missing information, etc.

Use placeholder tokens when referring to people or sensitive data.
Financial amounts are real values — verify calculations with them.""",
    TaskType.FILE: """You are a tax filing preparation assistant. You receive tax document data where 
personally identifiable information has been replaced with placeholder tokens.

Help organize and prepare the data for tax filing. Identify:
1. Which tax forms need to be filed
2. Key financial figures (income, deductions, credits)
3. Filing status implications
4. Estimated tax liability or refund

Use placeholder tokens for all personal identifiers.
Financial amounts and state information are real — use them for all calculations.""",
}


class ClaudeClient:
    """Client for interacting with Claude AI using redacted tax data.

    Only sends PII-free, tokenized text to the API. Responses will contain
    the same placeholder tokens, which can be rehydrated locally.

    Usage:
        client = ClaudeClient()
        response = client.process(
            redacted_text="[PERSON_1] earned $75,000 at [PERSON_2]...",
            task=TaskType.EXTRACT,
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use. Defaults to CLAUDE_MODEL env var or claude-sonnet-4-20250514.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self._client = Anthropic(api_key=self.api_key)

        logger.info("Claude client initialized (model=%s)", self.model)

    def process(
        self,
        redacted_text: str,
        task: TaskType = TaskType.EXTRACT,
        query: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Send redacted tax document text to Claude for processing.

        Args:
            redacted_text: Tax document text with PII replaced by tokens.
            task: Type of task to perform.
            query: Optional specific question to ask (for ADVISE task).
            max_tokens: Maximum tokens in the response.

        Returns:
            Claude's response (containing placeholder tokens, no real PII).
        """
        system_prompt = SYSTEM_PROMPTS[task]

        # Build user message
        user_message = f"Here is the tax document content (PII has been redacted with tokens):\n\n{redacted_text}"

        if query:
            user_message += f"\n\nSpecific question: {query}"

        # Verify no PII leakage BEFORE the API call.
        # Raises PIILeakError if any redactable PII remains in the text.
        self._safety_check(redacted_text)

        logger.info(
            "Sending redacted text to Claude (%d chars, task=%s)",
            len(redacted_text),
            task.value,
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text

        logger.info(
            "Received response from Claude (%d chars, %d input tokens, %d output tokens)",
            len(response_text),
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        return response_text

    def chat(
        self,
        messages: list[dict[str, str]],
        task: TaskType = TaskType.ADVISE,
        max_tokens: int = 4096,
    ) -> str:
        """Multi-turn conversation with Claude about tax documents.

        Args:
            messages: List of message dicts with "role" and "content" keys.
            task: Type of task for system prompt.
            max_tokens: Maximum tokens in the response.

        Returns:
            Claude's response text.
        """
        system_prompt = SYSTEM_PROMPTS[task]

        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )

        return response.content[0].text

    @staticmethod
    def _safety_check(text: str) -> None:
        """Comprehensive safety check — re-runs full PII detection on
        text about to be sent to AI.

        This is a defense-in-depth check that catches any PII that escaped
        the primary tokenization layer. It runs the SAME detector used during
        initial redaction, so it covers SSN, EIN, ITIN, names, emails,
        phone numbers, addresses, bank accounts, routing numbers, etc.

        If ANY redactable PII is found, the API call is BLOCKED.

        Raises:
            PIILeakError: If any redactable PII entity is detected.
        """
        import re

        # Lazy import to avoid circular dependency
        from ciphertax.detection.detector import PIIDetector

        # Strip CipherTax tokens before re-detection — they contain words like
        # "PERSON" and "ORGANIZATION" that would trigger false-positive NER hits.
        # Replace tokens with neutral placeholders that don't trip detection.
        token_pattern = re.compile(r"\[(?:CT_[a-zA-Z0-9]+_)?[A-Z_]+_\d+\]")
        clean_text = token_pattern.sub("X", text)

        # Run full detection on the cleaned text
        detector = PIIDetector()
        entities = detector.detect(clean_text)
        leaked = [e for e in entities if e.should_redact]

        if leaked:
            # DO NOT log the leaked text itself — it contains the PII
            entity_summary = {}
            for entity in leaked:
                entity_summary[entity.entity_type] = entity_summary.get(entity.entity_type, 0) + 1

            error_msg = (
                f"SAFETY CHECK FAILED: Found {len(leaked)} un-redacted PII entities "
                f"in text about to be sent to AI. "
                f"Breakdown: {entity_summary}. "
                f"API call BLOCKED to prevent PII leakage. "
                f"This is a bug — please report to "
                f"https://github.com/z26zheng/CipherTax/issues"
            )
            logger.error(error_msg)
            raise PIILeakError(error_msg)

        logger.debug("Safety check passed — no PII detected in redacted text")
