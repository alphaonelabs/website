import hashlib
import hmac
import json
import time

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from web.models import EmailEvent, Profile


class MailgunWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")
        # Ensure profile exists
        if not hasattr(self.user, "profile"):
            Profile.objects.create(user=self.user)

    def _create_mailgun_signature(self, timestamp, token, signing_key):
        """Helper to create a valid Mailgun signature."""
        hmac_digest = hmac.new(
            key=signing_key.encode("utf-8"),
            msg=f"{timestamp}{token}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac_digest

    @override_settings(MAILGUN_WEBHOOK_SIGNING_KEY="test-signing-key")
    def test_mailgun_webhook_delivered_event(self):
        """Test processing a delivered event from Mailgun."""
        timestamp = str(int(time.time()))
        token = "test-token-123"
        signing_key = "test-signing-key"
        signature = self._create_mailgun_signature(timestamp, token, signing_key)

        event_data = {
            "event": "delivered",
            "recipient": "test@example.com",
            "timestamp": timestamp,
            "id": "event-id-123",
            "message": {"headers": {"message-id": "msg-id-123"}},
        }

        response = self.client.post(
            reverse("mailgun_webhook"),
            {
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
                "event-data": json.dumps(event_data),
            },
        )

        self.assertEqual(response.status_code, 200)

        # Check that the event was created
        event = EmailEvent.objects.filter(email="test@example.com").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "delivered")
        self.assertEqual(event.user, self.user)

        # Check that profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.email_delivered_count, 1)
        self.assertEqual(self.user.profile.last_email_event, "delivered")

    @override_settings(MAILGUN_WEBHOOK_SIGNING_KEY="test-signing-key")
    def test_mailgun_webhook_opened_event(self):
        """Test processing an opened event from Mailgun."""
        timestamp = str(int(time.time()))
        token = "test-token-456"
        signing_key = "test-signing-key"
        signature = self._create_mailgun_signature(timestamp, token, signing_key)

        event_data = {
            "event": "opened",
            "recipient": "test@example.com",
            "timestamp": timestamp,
            "id": "event-id-456",
            "message": {"headers": {"message-id": "msg-id-456"}},
        }

        response = self.client.post(
            reverse("mailgun_webhook"),
            {
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
                "event-data": json.dumps(event_data),
            },
        )

        self.assertEqual(response.status_code, 200)

        # Check that the event was created
        event = EmailEvent.objects.filter(email="test@example.com", event_type="opened").first()
        self.assertIsNotNone(event)

        # Check that profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.email_open_count, 1)
        self.assertEqual(self.user.profile.last_email_event, "opened")

    @override_settings(MAILGUN_WEBHOOK_SIGNING_KEY="test-signing-key")
    def test_mailgun_webhook_clicked_event(self):
        """Test processing a clicked event from Mailgun."""
        timestamp = str(int(time.time()))
        token = "test-token-789"
        signing_key = "test-signing-key"
        signature = self._create_mailgun_signature(timestamp, token, signing_key)

        event_data = {
            "event": "clicked",
            "recipient": "test@example.com",
            "timestamp": timestamp,
            "id": "event-id-789",
            "message": {"headers": {"message-id": "msg-id-789"}},
        }

        response = self.client.post(
            reverse("mailgun_webhook"),
            {
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
                "event-data": json.dumps(event_data),
            },
        )

        self.assertEqual(response.status_code, 200)

        # Check that profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.email_click_count, 1)
        self.assertEqual(self.user.profile.last_email_event, "clicked")

    @override_settings(MAILGUN_WEBHOOK_SIGNING_KEY="test-signing-key")
    def test_mailgun_webhook_failed_event(self):
        """Test processing a failed event from Mailgun."""
        timestamp = str(int(time.time()))
        token = "test-token-bounce"
        signing_key = "test-signing-key"
        signature = self._create_mailgun_signature(timestamp, token, signing_key)

        event_data = {
            "event": "failed",
            "recipient": "test@example.com",
            "timestamp": timestamp,
            "id": "event-id-bounce",
            "reason": "Mailbox does not exist",
            "message": {"headers": {"message-id": "msg-id-bounce"}},
        }

        response = self.client.post(
            reverse("mailgun_webhook"),
            {
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
                "event-data": json.dumps(event_data),
            },
        )

        self.assertEqual(response.status_code, 200)

        # Check that profile was updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.email_bounce_count, 1)
        self.assertEqual(self.user.profile.last_email_event, "failed")

    @override_settings(MAILGUN_WEBHOOK_SIGNING_KEY="test-signing-key")
    def test_mailgun_webhook_invalid_signature(self):
        """Test that invalid signatures are rejected."""
        timestamp = str(int(time.time()))
        token = "test-token-invalid"
        signature = "invalid-signature"

        event_data = {
            "event": "delivered",
            "recipient": "test@example.com",
            "timestamp": timestamp,
        }

        response = self.client.post(
            reverse("mailgun_webhook"),
            {
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
                "event-data": json.dumps(event_data),
            },
        )

        self.assertEqual(response.status_code, 403)
        # Ensure no event was created
        self.assertEqual(EmailEvent.objects.count(), 0)

    def test_mailgun_webhook_get_request(self):
        """Test that GET requests are rejected."""
        response = self.client.get(reverse("mailgun_webhook"))
        self.assertEqual(response.status_code, 405)

    @override_settings(MAILGUN_WEBHOOK_SIGNING_KEY="test-signing-key")
    def test_mailgun_webhook_unknown_user(self):
        """Test processing an event for an unknown email address."""
        timestamp = str(int(time.time()))
        token = "test-token-unknown"
        signing_key = "test-signing-key"
        signature = self._create_mailgun_signature(timestamp, token, signing_key)

        event_data = {
            "event": "delivered",
            "recipient": "unknown@example.com",
            "timestamp": timestamp,
            "id": "event-id-unknown",
            "message": {"headers": {"message-id": "msg-id-unknown"}},
        }

        response = self.client.post(
            reverse("mailgun_webhook"),
            {
                "timestamp": timestamp,
                "token": token,
                "signature": signature,
                "event-data": json.dumps(event_data),
            },
        )

        self.assertEqual(response.status_code, 200)

        # Check that the event was created even without a user
        event = EmailEvent.objects.filter(email="unknown@example.com").first()
        self.assertIsNotNone(event)
        self.assertIsNone(event.user)
