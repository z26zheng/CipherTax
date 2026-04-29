"""Tests for the secure vault (encrypted local storage)."""

import pytest
from pathlib import Path

from ciphertax.vault.secure_vault import SecureVault


class TestSecureVault:
    """Test encrypted vault operations."""

    @pytest.fixture
    def vault_dir(self, tmp_path):
        return tmp_path / "test_vaults"

    def test_create_vault(self, vault_dir):
        vault, password = SecureVault.create(
            password="test-password",
            session_id="test123",
            vault_dir=vault_dir,
        )
        assert vault.path.exists()
        assert vault.path.name == "vault_test123.enc"
        assert password == "test-password"

    def test_create_vault_auto_password(self, vault_dir):
        vault, password = SecureVault.create(vault_dir=vault_dir)
        assert len(password) > 20  # Auto-generated passwords are long
        assert vault.path.exists()

    def test_store_and_retrieve(self, vault_dir):
        vault, password = SecureVault.create(
            password="test-password",
            vault_dir=vault_dir,
        )
        mapping = {
            "[SSN_1]": "123-45-6789",
            "[PERSON_1]": "John Smith",
            "[EIN_1]": "98-7654321",
        }
        vault.store(mapping)

        retrieved = vault.retrieve()
        assert retrieved == mapping

    def test_load_existing_vault(self, vault_dir):
        vault, password = SecureVault.create(
            password="my-password",
            session_id="reload",
            vault_dir=vault_dir,
        )
        vault.store({"[SSN_1]": "123-45-6789"})
        vault_path = vault.path

        # Load it fresh
        loaded = SecureVault.load(vault_path, password="my-password")
        mapping = loaded.retrieve()
        assert mapping["[SSN_1]"] == "123-45-6789"

    def test_wrong_password_raises(self, vault_dir):
        vault, _ = SecureVault.create(
            password="correct-password",
            vault_dir=vault_dir,
        )
        vault.store({"[SSN_1]": "123-45-6789"})

        with pytest.raises(ValueError, match="Incorrect vault password"):
            SecureVault.load(vault.path, password="wrong-password")

    def test_update_mapping(self, vault_dir):
        vault, _ = SecureVault.create(password="test", vault_dir=vault_dir)
        vault.store({"[SSN_1]": "123-45-6789"})
        vault.update({"[PERSON_1]": "John Smith"})

        mapping = vault.retrieve()
        assert "[SSN_1]" in mapping
        assert "[PERSON_1]" in mapping

    def test_destroy_vault(self, vault_dir):
        vault, _ = SecureVault.create(password="test", vault_dir=vault_dir)
        vault.store({"[SSN_1]": "123-45-6789"})
        vault_path = vault.path
        salt_path = vault_path.with_suffix(".salt")

        vault.destroy()
        assert not vault_path.exists()
        assert not salt_path.exists()

    def test_list_vaults(self, vault_dir):
        SecureVault.create(password="test", session_id="a", vault_dir=vault_dir)
        SecureVault.create(password="test", session_id="b", vault_dir=vault_dir)
        SecureVault.create(password="test", session_id="c", vault_dir=vault_dir)

        vaults = SecureVault.list_vaults(vault_dir)
        assert len(vaults) == 3

    def test_list_vaults_empty_dir(self, tmp_path):
        vaults = SecureVault.list_vaults(tmp_path)
        assert vaults == []

    def test_list_vaults_nonexistent_dir(self, tmp_path):
        vaults = SecureVault.list_vaults(tmp_path / "nonexistent")
        assert vaults == []

    def test_unicode_pii(self, vault_dir):
        """Vault should handle Unicode PII values."""
        vault, _ = SecureVault.create(password="test", vault_dir=vault_dir)
        mapping = {"[PERSON_1]": "José García-López"}
        vault.store(mapping)
        retrieved = vault.retrieve()
        assert retrieved["[PERSON_1]"] == "José García-López"

    def test_large_mapping(self, vault_dir):
        """Vault should handle large mappings."""
        vault, _ = SecureVault.create(password="test", vault_dir=vault_dir)
        mapping = {f"[TOKEN_{i}]": f"value_{i}" for i in range(1000)}
        vault.store(mapping)
        retrieved = vault.retrieve()
        assert len(retrieved) == 1000
        assert retrieved["[TOKEN_500]"] == "value_500"
