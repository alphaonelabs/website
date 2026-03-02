import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def get_fernet():
    """Return a Fernet instance using the FIELD_ENCRYPTION_KEY setting."""
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def make_hash(value: str) -> str:
    """Return a hex-encoded HMAC-SHA256 of *value* keyed with FIELD_ENCRYPTION_KEY.

    The hash is deterministic so the same plaintext always produces the same
    digest, allowing exact-match lookups in the database without revealing the
    plaintext.  The key acts as a pepper so the hashes are not brute-forceable
    without access to the application secret.
    """
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


class EncryptedField(models.TextField):
    """
    A Django model field that transparently encrypts values on write and decrypts on read
    using Fernet symmetric encryption (cryptography library).

    Values are stored as base64-encoded ciphertext in the database.
    """

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except (InvalidToken, UnicodeDecodeError, ValueError):
            return value

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if not value:
            return value
        return get_fernet().encrypt(value.encode()).decode()
