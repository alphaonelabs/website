from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from web.encrypted_fields import EncryptedField, make_hash
from web.models import UserEncryptedData

User = get_user_model()

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EncryptedFieldTests(TestCase):
    """Unit tests for the EncryptedField custom model field."""

    def test_get_prep_value_encrypts(self):
        """get_prep_value should return ciphertext that differs from plaintext."""
        field = EncryptedField()
        plaintext = "test@example.com"
        ciphertext = field.get_prep_value(plaintext)
        self.assertNotEqual(plaintext, ciphertext)
        self.assertIsInstance(ciphertext, str)

    def test_from_db_value_decrypts(self):
        """from_db_value should recover the original plaintext."""
        field = EncryptedField()
        plaintext = "test@example.com"
        ciphertext = field.get_prep_value(plaintext)
        decrypted = field.from_db_value(ciphertext, None, None)
        self.assertEqual(decrypted, plaintext)

    def test_empty_string_passthrough(self):
        """Empty string should not be encrypted and should be returned as-is."""
        field = EncryptedField()
        self.assertEqual(field.get_prep_value(""), "")
        self.assertEqual(field.from_db_value("", None, None), "")

    def test_none_passthrough(self):
        """None should not be encrypted and should be returned as-is."""
        field = EncryptedField()
        self.assertIsNone(field.get_prep_value(None))
        self.assertIsNone(field.from_db_value(None, None, None))

    def test_different_ciphertexts_same_plaintext(self):
        """Fernet produces different ciphertexts for the same plaintext each time."""
        field = EncryptedField()
        plaintext = "hello"
        ct1 = field.get_prep_value(plaintext)
        ct2 = field.get_prep_value(plaintext)
        self.assertNotEqual(ct1, ct2)
        self.assertEqual(field.from_db_value(ct1, None, None), plaintext)
        self.assertEqual(field.from_db_value(ct2, None, None), plaintext)

    def test_invalid_token_returns_value_unchanged(self):
        """from_db_value should return the raw value when it cannot be decrypted."""
        field = EncryptedField()
        garbage = "not-a-valid-fernet-token"
        result = field.from_db_value(garbage, None, None)
        self.assertEqual(result, garbage)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MakeHashTests(TestCase):
    """Unit tests for the make_hash helper."""

    def test_deterministic(self):
        """The same input always produces the same hash."""
        self.assertEqual(make_hash("hello@example.com"), make_hash("hello@example.com"))

    def test_different_inputs_different_hashes(self):
        """Different inputs produce different hashes."""
        self.assertNotEqual(make_hash("a@example.com"), make_hash("b@example.com"))

    def test_returns_hex_string(self):
        """Hash is a 64-character hex string (SHA-256 output)."""
        result = make_hash("test")
        self.assertEqual(len(result), 64)
        int(result, 16)  # raises ValueError if not valid hex


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class UserEncryptedDataModelTests(TestCase):
    """Integration tests for UserEncryptedData model and its sync signal."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="enctest_user",
            email="enctest@example.com",
            password="secret123",
        )

    def tearDown(self):
        self.user.delete()

    def test_record_created_on_user_save(self):
        """A UserEncryptedData row should be created automatically for new users."""
        self.assertTrue(UserEncryptedData.objects.filter(user=self.user).exists())

    def test_encrypted_values_differ_from_plaintext(self):
        """Values stored in the DB should be ciphertext, not plaintext."""
        raw_email = (
            UserEncryptedData.objects.filter(user=self.user).values("encrypted_email").first()["encrypted_email"]
        )
        self.assertNotEqual(raw_email, "enctest@example.com")

    def test_decrypted_email_matches(self):
        """The decrypted email should match the user's actual email."""
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertEqual(enc.encrypted_email, "enctest@example.com")

    def test_decrypted_username_matches(self):
        """The decrypted username should match the user's actual username."""
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertEqual(enc.encrypted_username, "enctest_user")

    def test_email_hash_stored(self):
        """email_hash should be the HMAC-SHA256 of the user's email."""
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertEqual(enc.email_hash, make_hash("enctest@example.com"))

    def test_username_hash_stored(self):
        """username_hash should be the HMAC-SHA256 of the user's username."""
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertEqual(enc.username_hash, make_hash("enctest_user"))

    def test_record_updated_on_user_email_change(self):
        """Updating a user's email should update the encrypted copy and hash."""
        self.user.email = "new@example.com"
        self.user.save()
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertEqual(enc.encrypted_email, "new@example.com")
        self.assertEqual(enc.email_hash, make_hash("new@example.com"))

    def test_record_updated_on_username_change(self):
        """Updating a user's username should update the encrypted copy and hash."""
        self.user.username = "new_username"
        self.user.save()
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertEqual(enc.encrypted_username, "new_username")
        self.assertEqual(enc.username_hash, make_hash("new_username"))

    def test_str_representation(self):
        """__str__ should include the user id."""
        enc = UserEncryptedData.objects.get(user=self.user)
        self.assertIn(str(self.user.pk), str(enc))
