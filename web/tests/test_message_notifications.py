from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from web.models import PeerMessage

User = get_user_model()


class NewMessageNotificationTest(TestCase):
    """Test new message email notifications."""

    def setUp(self):
        """Set up test users."""
        self.sender = User.objects.create_user(username="sender", email="sender@example.com", password="testpass123")
        self.receiver = User.objects.create_user(
            username="receiver", email="receiver@example.com", password="testpass123"
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_DOMAIN="testserver.com",
    )
    def test_new_message_sends_email_notification(self):
        """Test that creating a new message sends an email notification."""
        # Clear the test email outbox
        mail.outbox = []

        # Create a new message
        PeerMessage.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="encrypted_test_content",
            encrypted_key="encrypted_test_key",
        )

        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Check email details
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, "New Message Received")
        self.assertEqual(sent_email.to, [self.receiver.email])
        self.assertIn("noreply@example.com", sent_email.from_email)  # Check for default from email

        # Check that the email contains the message URL (in HTML version)
        html_content = sent_email.alternatives[0][0] if sent_email.alternatives else sent_email.body
        self.assertIn("https://testserver.com/messaging/dashboard/", html_content)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_URL="https://example.com",
    )
    def test_message_url_uses_site_url_setting(self):
        """Test that the message URL uses the SITE_URL setting."""
        # Clear the test email outbox
        mail.outbox = []

        # Create a new message
        PeerMessage.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="encrypted_test_content",
            encrypted_key="encrypted_test_key",
        )

        # Check that an email was sent with correct URL
        sent_email = mail.outbox[0]
        html_content = sent_email.alternatives[0][0] if sent_email.alternatives else sent_email.body
        self.assertIn("https://example.com/messaging/dashboard/", html_content)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_DOMAIN="testserver.com",
    )
    def test_email_contains_sender_information(self):
        """Test that the email contains sender information."""
        # Set up sender with full name
        self.sender.first_name = "John"
        self.sender.last_name = "Doe"
        self.sender.save()

        # Clear the test email outbox
        mail.outbox = []

        # Create a new message
        PeerMessage.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="encrypted_test_content",
            encrypted_key="encrypted_test_key",
        )

        # Check that the email contains sender information
        sent_email = mail.outbox[0]
        html_content = sent_email.alternatives[0][0] if sent_email.alternatives else sent_email.body
        self.assertIn("John Doe", html_content)
        self.assertIn("sender@example.com", html_content)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_DOMAIN="testserver.com",
    )
    def test_email_contains_receiver_information(self):
        """Test that the email contains receiver information."""
        # Set up receiver with full name
        self.receiver.first_name = "Jane"
        self.receiver.last_name = "Smith"
        self.receiver.save()

        # Clear the test email outbox
        mail.outbox = []

        # Create a new message
        PeerMessage.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="encrypted_test_content",
            encrypted_key="encrypted_test_key",
        )

        # Check that the email contains receiver information
        sent_email = mail.outbox[0]
        html_content = sent_email.alternatives[0][0] if sent_email.alternatives else sent_email.body
        self.assertIn("Hi Jane Smith", html_content)

    @patch("web.notifications.logger")
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend")
    def test_email_sending_error_logged(self, mock_logger):
        """Test that email sending errors are logged."""
        # Create a new message - this should trigger email sending
        with patch("web.notifications.send_mail", side_effect=Exception("Email error")):
            PeerMessage.objects.create(
                sender=self.sender,
                receiver=self.receiver,
                content="encrypted_test_content",
                encrypted_key="encrypted_test_key",
            )

        # Check that error was logged
        mock_logger.error.assert_called_once()
        self.assertIn("Failed to send new message notification", str(mock_logger.error.call_args))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_DOMAIN="testserver.com",
    )
    def test_no_email_on_message_update(self):
        """Test that updating a message doesn't send another email."""
        # Clear the test email outbox
        mail.outbox = []

        # Create a new message
        message = PeerMessage.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="encrypted_test_content",
            encrypted_key="encrypted_test_key",
        )

        # Clear outbox after creation
        mail.outbox = []

        # Update the message
        message.is_read = True
        message.save()

        # Check that no additional email was sent
        self.assertEqual(len(mail.outbox), 0)
