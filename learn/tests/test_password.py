"""
Tests for password hashing: hash_password(), verify_password().
"""

import base64
from tests.helpers import load_worker

worker = load_worker()


class TestHashPassword:
    def test_returns_string(self):
        assert isinstance(worker.hash_password("password", "alice"), str)

    def test_returns_non_empty(self):
        assert worker.hash_password("password", "alice") != ""

    def test_output_is_base64(self):
        h = worker.hash_password("password", "alice")
        # Should not raise
        base64.b64decode(h)

    def test_deterministic(self):
        h1 = worker.hash_password("password123", "alice")
        h2 = worker.hash_password("password123", "alice")
        assert h1 == h2

    def test_different_passwords_differ(self):
        h1 = worker.hash_password("password1", "alice")
        h2 = worker.hash_password("password2", "alice")
        assert h1 != h2

    def test_same_password_different_users_differ(self):
        h1 = worker.hash_password("samepassword", "alice")
        h2 = worker.hash_password("samepassword", "bob")
        assert h1 != h2

    def test_empty_password_allowed(self):
        h = worker.hash_password("", "alice")
        assert isinstance(h, str) and h != ""

    def test_unicode_password(self):
        h = worker.hash_password("pässwörd!", "alice")
        assert isinstance(h, str)


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        stored = worker.hash_password("mypassword", "alice")
        assert worker.verify_password("mypassword", stored, "alice") is True

    def test_wrong_password_returns_false(self):
        stored = worker.hash_password("mypassword", "alice")
        assert worker.verify_password("wrongpassword", stored, "alice") is False

    def test_wrong_username_returns_false(self):
        stored = worker.hash_password("mypassword", "alice")
        # Same password, different username → different salt → different hash
        assert worker.verify_password("mypassword", stored, "bob") is False

    def test_empty_password_correct(self):
        stored = worker.hash_password("", "alice")
        assert worker.verify_password("", stored, "alice") is True

    def test_empty_password_incorrect(self):
        stored = worker.hash_password("", "alice")
        assert worker.verify_password("notempty", stored, "alice") is False

    def test_case_sensitive(self):
        stored = worker.hash_password("Password", "alice")
        assert worker.verify_password("password", stored, "alice") is False
