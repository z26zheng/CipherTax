"""CipherTax CLI — command-line interface for privacy-preserving tax processing.

Usage:
    ciphertax process w2.pdf --task extract
    ciphertax process w2.pdf --task advise --query "What deductions can I take?"
    ciphertax inspect w2.pdf
    ciphertax vault list
    ciphertax vault clean
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from ciphertax.ai.claude_client import TaskType


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


@click.group()
@click.version_option(package_name="ciphertax")
def main():
    """🔐 CipherTax — Privacy-preserving tax assistant.

    Process tax documents with AI while keeping your PII secure.
    No personally identifiable information ever leaves your machine.
    """
    pass


@main.command()
@click.argument("pdf_files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--task",
    type=click.Choice(["extract", "advise", "review", "file"]),
    default="extract",
    help="AI task to perform on the document.",
)
@click.option("--query", "-q", type=str, default=None, help="Specific question to ask (for advise task).")
@click.option(
    "--persist-vault",
    is_flag=True,
    default=False,
    help="Encrypt PII mappings to disk for re-use across sessions. "
         "Requires entering a password interactively.",
)
@click.option("--ocr", is_flag=True, default=False, help="Force OCR for all pages.")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Save sanitized output to file (does NOT include PII mappings unless --include-secrets is set).",
)
@click.option(
    "--include-secrets",
    is_flag=True,
    default=False,
    help="DANGEROUS: include the PII↔token mapping in the output file. "
         "Only use if you understand the risk.",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
def process(pdf_files, task, query, persist_vault, ocr, output, include_secrets, verbose):
    """Process tax PDF(s) through the privacy-preserving pipeline.

    Extracts text, redacts PII, sends to Claude, and rehydrates the response.
    By default, PII mappings are kept in memory only (cleared after process exits).

    Examples:

        ciphertax process w2.pdf

        ciphertax process w2.pdf --task advise -q "Am I eligible for EITC?"

        ciphertax process w2.pdf 1099-int.pdf --task file --persist-vault
    """
    setup_logging(verbose)

    from ciphertax.pipeline import CipherTaxPipeline

    task_type = TaskType(task)

    click.echo("🔐 CipherTax — Privacy-Preserving Tax Assistant")
    click.echo("=" * 50)
    click.echo()

    # Get vault password securely (only if persisting)
    vault_password = None
    if persist_vault:
        vault_password = click.prompt(
            "🔑 Enter vault password (input hidden)",
            hide_input=True,
            confirmation_prompt=True,
        )

    # Initialize pipeline
    click.echo("⚙️  Initializing pipeline...")
    try:
        pipeline = CipherTaxPipeline(
            vault_password=vault_password,
            persist_vault=persist_vault,
        )
    except Exception as e:
        click.echo(f"❌ Failed to initialize pipeline: {e}", err=True)
        sys.exit(1)

    if persist_vault:
        click.echo(f"🔐 Vault will be persisted (password not displayed)")
    else:
        click.echo(f"🔓 Mappings kept in memory only (no disk vault)")
    click.echo()

    # Process each PDF
    results = []
    for pdf_file in pdf_files:
        click.echo(f"📄 Processing: {pdf_file}")
        click.echo("-" * 40)

        try:
            result = pipeline.process(
                pdf_path=pdf_file,
                task=task_type,
                query=query,
                force_ocr=ocr,
            )
            results.append(result)

            # Display results
            click.echo(f"  📝 Pages extracted: {result.pages_extracted}")
            click.echo(f"  🔍 PII entities found: {result.pii_entities_found}")
            click.echo(f"  🛡️  PII entities redacted: {result.pii_entities_redacted}")
            click.echo(f"  📊 Entity types: {', '.join(result.entity_types)}")
            click.echo()

            # Handle PII leak
            if result.pii_leak_blocked:
                click.echo(
                    "  ❌ PII LEAK BLOCKED — API call was prevented because un-redacted "
                    "PII was detected. Redacted text and mappings withheld for safety.",
                    err=True,
                )
                for error in result.errors:
                    click.echo(f"     {error}", err=True)
                click.echo()
                continue

            # Show redacted text only if no leak occurred
            if result.redacted_text and not result.pii_leak_blocked:
                click.echo("📤 Redacted text (sent to AI):")
                click.echo("-" * 40)
                preview = result.redacted_text[:500]
                if len(result.redacted_text) > 500:
                    preview += f"\n... ({len(result.redacted_text) - 500} more chars)"
                click.echo(preview)
                click.echo()

            if result.ai_response_rehydrated:
                click.echo("📥 AI Response (with PII restored):")
                click.echo("-" * 40)
                click.echo(result.ai_response_rehydrated)
                click.echo()

            if result.errors and not result.pii_leak_blocked:
                click.echo("⚠️  Errors:")
                for error in result.errors:
                    click.echo(f"  - {error}")
                click.echo()

        except Exception as e:
            click.echo(f"❌ Error processing {pdf_file}: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()

    # Save output if requested
    if output and results:
        output_data = {
            "results": [
                {
                    "source": r.source_file,
                    "pages_extracted": r.pages_extracted,
                    "pii_entities_found": r.pii_entities_found,
                    "pii_entities_redacted": r.pii_entities_redacted,
                    "entity_types": r.entity_types,
                    # Note: redacted_text contains tokens, not PII — safe to save
                    "redacted_text": r.redacted_text if not r.pii_leak_blocked else None,
                    "ai_response": r.ai_response,
                    "ai_response_rehydrated": (
                        r.ai_response_rehydrated if include_secrets else "[CONTAINS_PII — use --include-secrets to include]"
                    ),
                    "pii_leak_blocked": r.pii_leak_blocked,
                    "errors": r.errors,
                }
                for r in results
            ],
        }
        # Only include token_mapping if explicitly requested
        if include_secrets:
            click.echo(
                "⚠️  WARNING: --include-secrets is enabled. The output file will contain "
                "REAL PII (SSNs, names, etc.). Treat this file as sensitive!",
                err=True,
            )
            for i, r in enumerate(results):
                output_data["results"][i]["token_mapping"] = r.token_mapping
                output_data["results"][i]["original_text"] = r.original_text

        Path(output).write_text(json.dumps(output_data, indent=2))
        click.echo(f"💾 Output saved to: {output}")

    click.echo()
    click.echo("✅ Processing complete!")
    if not persist_vault:
        click.echo("🔓 In-memory mappings will be cleared on process exit.")


@main.command()
@click.argument("pdf_files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--ocr", is_flag=True, default=False, help="Force OCR for all pages.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
def inspect(pdf_files, ocr, verbose):
    """Inspect a tax PDF — show extracted text and detected PII without sending to AI.

    This is a dry-run mode that shows what PII would be redacted.
    No vault is created on disk.

    Examples:

        ciphertax inspect w2.pdf

        ciphertax inspect w2.pdf --ocr
    """
    setup_logging(verbose)

    from ciphertax.pipeline import CipherTaxPipeline

    click.echo("🔍 CipherTax — Document Inspector (Dry Run)")
    click.echo("=" * 50)
    click.echo("⚠️  No data will be sent to AI in this mode.")
    click.echo("🔓 No vault will be created — mappings are in-memory only.")
    click.echo()

    # Inspect mode — no vault, no AI
    pipeline = CipherTaxPipeline(persist_vault=False)

    for pdf_file in pdf_files:
        click.echo(f"📄 Inspecting: {pdf_file}")
        click.echo("-" * 40)

        result = pipeline.process(
            pdf_path=pdf_file,
            force_ocr=ocr,
            skip_ai=True,
        )

        click.echo(f"  📝 Pages: {result.pages_extracted}")
        click.echo(f"  📊 Methods: {', '.join(result.extraction_methods)}")
        click.echo(f"  🔍 PII entities: {result.pii_entities_found}")
        click.echo(f"  🛡️  Would redact: {result.pii_entities_redacted}")
        click.echo()

        if result.token_mapping:
            click.echo("  Token Mapping (what would be redacted — values masked):")
            for token, original in result.token_mapping.items():
                masked = original[:3] + "***" if len(original) > 3 else "***"
                click.echo(f"    {token} ← {masked}")
            click.echo()

        click.echo("  Redacted text preview:")
        preview = result.redacted_text[:800]
        if len(result.redacted_text) > 800:
            preview += f"\n  ... ({len(result.redacted_text) - 800} more chars)"
        click.echo(f"  {preview}")
        click.echo()


@main.group()
def vault():
    """Manage encrypted PII vaults."""
    pass


@vault.command("list")
@click.option("--vault-dir", type=click.Path(), default=None, help="Vault directory path.")
def vault_list(vault_dir):
    """List all vault files."""
    from ciphertax.vault.secure_vault import SecureVault

    vault_dir_path = Path(vault_dir) if vault_dir else None
    vaults = SecureVault.list_vaults(vault_dir_path)

    if not vaults:
        click.echo("No vault files found.")
        return

    click.echo(f"Found {len(vaults)} vault(s):")
    for v in vaults:
        size = v.stat().st_size
        click.echo(f"  📁 {v.name} ({size} bytes)")


@vault.command("clean")
@click.option("--vault-dir", type=click.Path(), default=None, help="Vault directory path.")
@click.option("--force", "-f", is_flag=True, default=False, help="Skip confirmation.")
def vault_clean(vault_dir, force):
    """Securely delete all vault files."""
    from ciphertax.vault.secure_vault import DEFAULT_VAULT_DIR

    vault_dir_path = Path(vault_dir) if vault_dir else DEFAULT_VAULT_DIR

    if not vault_dir_path.exists():
        click.echo("No vault directory found.")
        return

    vault_files = list(vault_dir_path.glob("vault_*"))
    if not vault_files:
        click.echo("No vault files to clean.")
        return

    click.echo(f"Found {len(vault_files)} vault file(s) to delete.")

    if not force:
        if not click.confirm("⚠️  This will permanently delete all vault files. Continue?"):
            click.echo("Cancelled.")
            return

    import os

    for f in vault_files:
        size = f.stat().st_size
        f.write_bytes(os.urandom(size))
        f.unlink()
        click.echo(f"  🗑️  Destroyed: {f.name}")

    click.echo("✅ All vault files securely destroyed.")


if __name__ == "__main__":
    main()
