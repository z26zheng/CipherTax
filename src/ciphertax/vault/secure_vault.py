"""Secure Vault — encrypted local storage for PII token mappings.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) to store
the token↔PII mapping on disk. The mapping never leaves the local machine.

The vault file is a single encrypted JSON file that can be decrypted
only with the correct password.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

DEFAULT_VAULT_DIR = Path.home() / ".ciphertax"


class SecureVault:
    """Encrypted local storage for PII token mappings.

    Stores the mapping between placeholder tokens (e.g., [SSN_1]) and
    original PII values (e.g., 123-45-6789) in an encrypted file.

    Usage:
        # Create a new vault
        vault = SecureVault.create(password="my-secure-password")
        vault.store({"[SSN_1]": "123-45-6789", "[PERSON_1]": "John Smith"})

        # Load an existing vault
        vault = SecureVault.load(vault_path, password="my-secure-password")
        mapping = vault.retrieve()
    """

    def __init__(self, vault_path: Path, fernet: Fernet):
        """Initialize the vault with a path and encryption key.

        Use SecureVault.create() or SecureVault.load() instead of
        calling this constructor directly.
        """
        self._vault_path = vault_path
        self._fernet = fernet

    @classmethod
    def create(
        cls,
        password: str | None = None,
        session_id: str | None = None,
        vault_dir: Path | None = None,
    ) -> tuple[SecureVault, str]:
        """Create a new vault with a fresh encryption key.

        Args:
            password: Password for key derivation. If None, auto-generates one.
            session_id: Unique session identifier. If None, auto-generates one.
            vault_dir: Directory to store vault files. Defaults to ~/.ciphertax/

        Returns:
            Tuple of (SecureVault instance, password used).
        """
        vault_dir = vault_dir or DEFAULT_VAULT_DIR
        vault_dir.mkdir(parents=True, exist_ok=True)

        if password is None:
            password = secrets.token_urlsafe(32)
            logger.info("Auto-generated vault password (save this!)")

        if session_id is None:
            session_id = secrets.token_hex(8)

        vault_path = vault_dir / f"vault_{session_id}.enc"

        # Generate salt and derive key
        salt = os.urandom(16)
        fernet = cls._derive_fernet(password, salt)

        # Store salt in a companion file
        salt_path = vault_path.with_suffix(".salt")
        salt_path.write_bytes(salt)

        vault = cls(vault_path, fernet)

        # Initialize with empty mapping
        vault.store({})

        logger.info("Created new vault: %s", vault_path)
        return vault, password

    @classmethod
    def load(cls, vault_path: str | Path, password: str) -> SecureVault:
        """Load an existing vault from disk.

        Args:
            vault_path: Path to the encrypted vault file.
            password: Password used to create the vault.

        Returns:
            SecureVault instance.

        Raises:
            FileNotFoundError: If vault file doesn't exist.
            ValueError: If password is incorrect.
        """
        vault_path = Path(vault_path)
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault not found: {vault_path}")

        # Load salt
        salt_path = vault_path.with_suffix(".salt")
        if not salt_path.exists():
            raise FileNotFoundError(f"Vault salt file not found: {salt_path}")

        salt = salt_path.read_bytes()
        fernet = cls._derive_fernet(password, salt)

        vault = cls(vault_path, fernet)

        # Verify password by attempting to decrypt
        try:
            vault.retrieve()
        except InvalidToken:
            raise ValueError("Incorrect vault password")

        logger.info("Loaded vault: %s", vault_path)
        return vault

    def store(self, mapping: dict[str, str]) -> None:
        """Encrypt and store the token mapping to disk.

        Args:
            mapping: Dictionary of token → original PII value.
        """
        plaintext = json.dumps(mapping, ensure_ascii=False).encode("utf-8")
        encrypted = self._fernet.encrypt(plaintext)
        self._vault_path.write_bytes(encrypted)

        logger.info("Stored %d mappings in vault (%d bytes encrypted)", len(mapping), len(encrypted))

    def retrieve(self) -> dict[str, str]:
        """Decrypt and retrieve the token mapping from disk.

        Returns:
            Dictionary of token → original PII value.

        Raises:
            cryptography.fernet.InvalidToken: If password is wrong or data corrupted.
        """
        encrypted = self._vault_path.read_bytes()
        plaintext = self._fernet.decrypt(encrypted)
        mapping = json.loads(plaintext.decode("utf-8"))

        logger.info("Retrieved %d mappings from vault", len(mapping))
        return mapping

    def update(self, additional_mapping: dict[str, str]) -> None:
        """Add new mappings to the vault (merge with existing).

        Args:
            additional_mapping: New token → PII mappings to add.
        """
        existing = self.retrieve()
        existing.update(additional_mapping)
        self.store(existing)

    def destroy(self) -> None:
        """Securely delete the vault and salt files.

        Overwrites files with random data before deletion.
        """
        for path in [self._vault_path, self._vault_path.with_suffix(".salt")]:
            if path.exists():
                # Overwrite with random data before deleting
                size = path.stat().st_size
                path.write_bytes(os.urandom(size))
                path.unlink()
                logger.info("Securely destroyed: %s", path)

    @property
    def path(self) -> Path:
        """Return the vault file path."""
        return self._vault_path

    @staticmethod
    def _derive_fernet(password: str, salt: bytes) -> Fernet:
        """Derive a Fernet key from a password using PBKDF2.

        Args:
            password: User password.
            salt: Random salt bytes.

        Returns:
            Fernet instance for encryption/decryption.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        return Fernet(key)

    @classmethod
    def list_vaults(cls, vault_dir: Path | None = None) -> list[Path]:
        """List all vault files in the vault directory.

        Args:
            vault_dir: Directory to search. Defaults to ~/.ciphertax/

        Returns:
            List of vault file paths.
        """
        vault_dir = vault_dir or DEFAULT_VAULT_DIR
        if not vault_dir.exists():
            return []
        return sorted(vault_dir.glob("vault_*.enc"))
