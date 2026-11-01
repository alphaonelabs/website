"""
Tests for encryption helpers:
  * _derive_key()
  * _derive_aes_key_bytes()
  * _encrypt_xor() / _decrypt_xor()
  * blind_index()
  * encrypt_aes() / decrypt_aes()
"""

import base64
import pytest
from tests.helpers import load_worker

worker = load_worker()


# ---------------------------------------------------------------------------
# _derive_key()
# ---------------------------------------------------------------------------

class TestDeriveKey:
    def test_returns_bytes(self):
        assert isinstance(worker._derive_key("secret"), bytes)

    def test_returns_32_bytes(self):
        assert len(worker._derive_key("secret")) == 32

    def test_deterministic(self):
        assert worker._derive_key("hello") == worker._derive_key("hello")

    def test_different_secrets_differ(self):
        assert worker._derive_key("secret1") != worker._derive_key("secret2")

    def test_empty_secret(self):
        key = worker._derive_key("")
        assert len(key) == 32


# ---------------------------------------------------------------------------
# _derive_aes_key_bytes()
# ---------------------------------------------------------------------------

class TestDeriveAesKeyBytes:
    def test_returns_32_bytes(self):
        assert len(worker._derive_aes_key_bytes("secret")) == 32

    def test_deterministic(self):
        assert worker._derive_aes_key_bytes("hello") == worker._derive_aes_key_bytes("hello")

    def test_different_from_derive_key(self):
        # Uses PBKDF2 not SHA-256 directly
        assert worker._derive_aes_key_bytes("same") != worker._derive_key("same")

    def test_different_secrets_differ(self):
        assert worker._derive_aes_key_bytes("a") != worker._derive_aes_key_bytes("b")


# ---------------------------------------------------------------------------
# XOR encrypt / decrypt
# ---------------------------------------------------------------------------

class TestXorEncryption:
    def test_empty_plaintext_returns_empty(self):
        assert worker._encrypt_xor("", "secret") == ""

    def test_empty_ciphertext_returns_empty(self):
        assert worker._decrypt_xor("", "secret") == ""

    def test_round_trip_ascii(self):
        ct = worker._encrypt_xor("hello world", "my-secret")
        assert worker._decrypt_xor(ct, "my-secret") == "hello world"

    def test_round_trip_unicode(self):
        pt = "café résumé 日本語"
        ct = worker._encrypt_xor(pt, "key")
        assert worker._decrypt_xor(ct, "key") == pt

    def test_ciphertext_is_base64(self):
        ct = worker._encrypt_xor("test", "key")
        # Should not raise
        base64.b64decode(ct)

    def test_different_key_fails_decrypt(self):
        ct = worker._encrypt_xor("secret data", "key1")
        result = worker._decrypt_xor(ct, "key2")
        assert result != "secret data"

    def test_ciphertext_differs_from_plaintext(self):
        pt = "plaintext"
        ct = worker._encrypt_xor(pt, "key")
        assert ct != pt

    def test_invalid_base64_returns_error_string(self):
        result = worker._decrypt_xor("not-valid-base64!!!", "key")
        assert result == "[decryption error]"


# ---------------------------------------------------------------------------
# blind_index()
# ---------------------------------------------------------------------------

class TestBlindIndex:
    def test_returns_hex_string(self):
        result = worker.blind_index("alice", "secret")
        assert all(c in "0123456789abcdef" for c in result)

    def test_returns_64_char_hex(self):
        assert len(worker.blind_index("alice", "secret")) == 64

    def test_deterministic(self):
        assert worker.blind_index("alice", "secret") == worker.blind_index("alice", "secret")

    def test_case_insensitive(self):
        assert worker.blind_index("Alice", "key") == worker.blind_index("alice", "key")
        assert worker.blind_index("ALICE", "key") == worker.blind_index("alice", "key")

    def test_different_values_differ(self):
        assert worker.blind_index("alice", "key") != worker.blind_index("bob", "key")

    def test_different_secrets_differ(self):
        assert worker.blind_index("alice", "key1") != worker.blind_index("alice", "key2")

    def test_empty_value(self):
        result = worker.blind_index("", "key")
        assert len(result) == 64


# ---------------------------------------------------------------------------
# encrypt_aes() / decrypt_aes()  (using the stub js module from conftest)
# ---------------------------------------------------------------------------

class TestAesEncryption:
    async def test_empty_plaintext_returns_empty(self):
        assert await worker.encrypt_aes("", "secret") == ""

    async def test_empty_ciphertext_returns_empty(self):
        assert await worker.decrypt_aes("", "secret") == ""

    async def test_round_trip_ascii(self):
        ct = await worker.encrypt_aes("hello world", "my-secret")
        assert await worker.decrypt_aes(ct, "my-secret") == "hello world"

    async def test_round_trip_unicode(self):
        pt = "café 日本語"
        ct = await worker.encrypt_aes(pt, "key")
        assert await worker.decrypt_aes(ct, "key") == pt

    async def test_ciphertext_starts_with_v1_prefix(self):
        ct = await worker.encrypt_aes("test", "key")
        assert ct.startswith("v1:")

    async def test_different_plaintexts_differ(self):
        ct1 = await worker.encrypt_aes("hello", "key")
        ct2 = await worker.encrypt_aes("world", "key")
        assert ct1 != ct2

    async def test_decrypt_legacy_xor_ciphertext(self):
        # Legacy ciphertext (no "v1:" prefix) should be decrypted via XOR fallback
        legacy_ct = worker._encrypt_xor("legacy value", "secret")
        result = await worker.decrypt_aes(legacy_ct, "secret")
        assert result == "legacy value"

    async def test_corrupt_ciphertext_returns_error_string(self):
        # Provide a v1:-prefixed but invalid base64 payload
        result = await worker.decrypt_aes("v1:!!!invalid!!!", "key")
        assert result == "[decryption error]"

    async def test_encrypt_returns_string(self):
        ct = await worker.encrypt_aes("data", "secret")
        assert isinstance(ct, str)

    async def test_sync_encrypt_raises(self):
        with pytest.raises(RuntimeError):
            worker.encrypt("test", "key")

    async def test_sync_decrypt_raises(self):
        with pytest.raises(RuntimeError):
            worker.decrypt("test", "key")
