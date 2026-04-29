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
@click.option("--password", "-p", type=str, default=None, help="Vault encryption password.")
@click.option("--ocr", is_flag=True, default=False, help="Force OCR for all pages.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save output to file.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
def process(pdf_files, task, query, password, ocr, output, verbose):
    """Process tax PDF(s) through the privacy-preserving pipeline.

    Extracts text, redacts PII, sends to Claude, and rehydrates the response.

    Examples:

        ciphertax process w2.pdf

        ciphertax process w2.pdf --task advise -q "Am I eligible for EITC?"

        ciphertax process w2.pdf 1099-int.pdf --task file
    """
    setup_logging(verbose)

    from ciphertax.pipeline import CipherTaxPipeline

    task_type = TaskType(task)

    click.echo("🔐 CipherTax — Privacy-Preserving Tax Assistant")
    click.echo("=" * 50)
    click.echo()

    # Initialize pipeline
    click.echo("⚙️  Initializing pipeline...")
    try:
        pipeline = CipherTaxPipeline(vault_password=password)
    except Exception as e:
        click.echo(f"❌ Failed to initialize pipeline: {e}", err=True)
        sys.exit(1)

    click.echo(f"🔑 Vault password: {pipeline.vault_password}")
    click.echo(f"📁 Vault location: {pipeline.vault_path}")
    click.echo()

    # Process each PDF
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

            # Display results
            click.echo(f"  📝 Pages extracted: {result.pages_extracted}")
            click.echo(f"  🔍 PII entities found: {result.pii_entities_found}")
            click.echo(f"  🛡️  PII entities redacted: {result.pii_entities_redacted}")
            click.echo(f"  📊 Entity types: {', '.join(result.entity_types)}")
            click.echo()

            if result.redacted_text:
                click.echo("📤 Redacted text (sent to AI):")
                click.echo("-" * 40)
                # Show first 500 chars of redacted text
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
            elif result.ai_response:
                click.echo("📥 AI Response (tokenized):")
                click.echo("-" * 40)
                click.echo(result.ai_response)
                click.echo()

            if result.errors:
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
    if output:
        output_data = {
            "vault_path": str(pipeline.vault_path),
            "results": [
                {
                    "source": r.source_file,
                    "redacted_text": r.redacted_text,
                    "ai_response": r.ai_response,
                    "ai_response_rehydrated": r.ai_response_rehydrated,
                    "token_mapping": r.token_mapping,
                }
                for r in [result]
            ],
        }
        Path(output).write_text(json.dumps(output_data, indent=2))
        click.echo(f"💾 Output saved to: {output}")

    click.echo()
    click.echo("✅ Processing complete!")
    click.echo(f"🔑 Remember your vault password to access PII mappings later.")


@main.command()
@click.argument("pdf_files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--ocr", is_flag=True, default=False, help="Force OCR for all pages.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose logging.")
def inspect(pdf_files, ocr, verbose):
    """Inspect a tax PDF — show extracted text and detected PII without sending to AI.

    This is a dry-run mode that shows what PII would be redacted.

    Examples:

        ciphertax inspect w2.pdf

        ciphertax inspect w2.pdf --ocr
    """
    setup_logging(verbose)

    from ciphertax.pipeline import CipherTaxPipeline

    click.echo("🔍 CipherTax — Document Inspector (Dry Run)")
    click.echo("=" * 50)
    click.echo("⚠️  No data will be sent to AI in this mode.")
    click.echo()

    pipeline = CipherTaxPipeline()

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
            click.echo("  Token Mapping (what would be redacted):")
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
        # Overwrite with random data before deletion
        size = f.stat().st_size
        f.write_bytes(os.urandom(size))
        f.unlink()
        click.echo(f"  🗑️  Destroyed: {f.name}")

    click.echo("✅ All vault files securely destroyed.")


if __name__ == "__main__":
    main()
