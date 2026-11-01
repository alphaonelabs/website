# web/tests/test_securemessaging.py

import datetime

from cryptography.fernet import InvalidToken
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import PeerMessage
from web.secure_messaging import (
    decrypt_message,
    decrypt_message_with_random_key,
    encrypt_message,
    encrypt_message_with_random_key,
)

User = get_user_model()


class CryptographySecurityTest(TestCase):
    def test_envelope_encryption_decryption(self):
        """
        Test that envelope encryption returns valid ciphertext and that
        decryption returns the original plaintext.
        """
        original_message = "This is a secret message!"
        encrypted_message, encrypted_random_key = encrypt_message_with_random_key(original_message)
        # Ensure the outputs are not the same as plaintext and not empty
        self.assertNotEqual(encrypted_message, original_message)
        self.assertNotEqual(encrypted_random_key, "")
        # Decrypt and verify
        decrypted = decrypt_message_with_random_key(encrypted_message, encrypted_random_key)
        self.assertEqual(decrypted, original_message)

    def test_envelope_encryption_is_random(self):
        """
        Verify that encrypting the same message multiple times produces different ciphertexts and keys.
        """
        original_message = "Test message for randomness."
        encrypted_messages = set()
        encrypted_keys = set()
        for _ in range(5):
            enc_msg, enc_key = encrypt_message_with_random_key(original_message)
            encrypted_messages.add(enc_msg)
            encrypted_keys.add(enc_key)
        self.assertGreater(len(encrypted_messages), 1)
        self.assertGreater(len(encrypted_keys), 1)

    def test_invalid_decryption(self):
        """
        Verify that modifying either the encrypted message or the encrypted random key causes decryption to fail.
        """
        original_message = "Test message"
        encrypted_message, encrypted_random_key = encrypt_message_with_random_key(original_message)
        # Tamper with the encrypted message (alter its last character)
        tampered_message = encrypted_message[:-1] + ("A" if encrypted_message[-1] != "A" else "B")
        with self.assertRaises(InvalidToken):
            _ = decrypt_message_with_random_key(tampered_message, encrypted_random_key)
        # Tamper with the encrypted key
        tampered_key = encrypted_random_key[:-1] + ("A" if encrypted_random_key[-1] != "A" else "B")
        with self.assertRaises(InvalidToken):
            _ = decrypt_message_with_random_key(encrypted_message, tampered_key)

    def test_simple_encryption_decryption(self):
        """
        Test that the simple encryption/decryption functions return the original message.
        """
        original_message = "Simple encryption test"
        encrypted = encrypt_message(original_message)
        decrypted = decrypt_message(encrypted)
        self.assertEqual(decrypted, original_message)


class SecureMessagingViewTestCase(TestCase):
    def setUp(self):
        # Create a test user and log in
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

    def test_send_encrypted_message_view(self):
        """
        Test that sending an encrypted message via the view works:
         - The message is stored with envelope encryption,
         - The encrypted_key field is populated,
         - Decryption returns the original message.
        """
        url = reverse("send_encrypted_message")
        original_message = "Hello envelope encryption!"
        response = self.client.post(url, {"message": original_message, "recipient": "testuser"})
        self.assertEqual(response.status_code, 200)

        msg = PeerMessage.objects.first()
        self.assertIsNotNone(msg)
        # Check that the stored content is not plaintext and the encrypted_key is populated
        self.assertNotEqual(msg.content, original_message)
        self.assertTrue(msg.encrypted_key)
        decrypted = decrypt_message_with_random_key(msg.content, msg.encrypted_key)
        self.assertEqual(decrypted, original_message)

    def test_dashboard_view_includes_messages(self):
        """
        Test that the messaging dashboard view renders correctly with messages.
        """
        # Create a message for the user
        original_message = "Dashboard test message"
        encrypted_message, encrypted_key = encrypt_message_with_random_key(original_message)
        PeerMessage.objects.create(
            sender=self.user,
            receiver=self.user,
            content=encrypted_message,
            encrypted_key=encrypted_key,
            is_read=False,
            created_at=timezone.now() - datetime.timedelta(hours=1),
        )
        url = reverse("messaging_dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that the original plaintext appears in the rendered HTML
        self.assertContains(response, original_message)
