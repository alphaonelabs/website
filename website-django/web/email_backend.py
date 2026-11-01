import json
import logging
from typing import List, Optional, Tuple

import requests
from django.conf import settings
from django.core.mail.backends.console import EmailBackend as ConsoleBackend

logger = logging.getLogger(__name__)


class SlackNotificationEmailBackend:
    """
    Email backend that sends a notification to Slack whenever an email is sent.
    This is a wrapper around another email backend.
    """

    def __init__(self, **kwargs):
        """Initialise the wrapped backend with graceful degradation.

        Behaviour:
        - In DEBUG always use console backend.
        - In production attempt to send via Mailgun HTTP API using
          MAILGUN_SENDING_KEY. On any failure, fall back to console backend
          semantics (no network send, just log) for the remainder of the
          process lifetime to avoid repeated errors.
        """
        # Prefer the global SLACK_WEBHOOK_URL; fall back to legacy EMAIL_SLACK_WEBHOOK
        self.webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", None) or getattr(
            settings, "EMAIL_SLACK_WEBHOOK", None
        )
        self.mailgun_enabled = False
        self._fallback_reason: Optional[str] = None
        # Allow overriding the Mailgun API base for EU region accounts
        # Defaults to US region: https://api.mailgun.net
        self.mailgun_api_base: str = getattr(settings, "MAILGUN_API_BASE", "https://api.mailgun.net").rstrip("/")

        if settings.DEBUG:
            self.backend = ConsoleBackend(**kwargs)
            self._fallback_reason = "debug-mode"
        else:
            # Enable Mailgun if the key is present; we send via HTTP in send_messages
            api_key = getattr(settings, "MAILGUN_SENDING_KEY", None) or getattr(settings, "MAILGUN_API_KEY", None)
            if api_key:
                self.backend = None  # Mailgun HTTP path; no Django backend instance needed
                self.mailgun_enabled = True
            else:
                self.backend = ConsoleBackend(**kwargs)
                self._fallback_reason = "MAILGUN_SENDING_KEY missing"
                logger.warning("Mailgun disabled; using console backend instead (reason=%s)", self._fallback_reason)

    def open(self):
        if getattr(self, "backend", None):
            return self.backend.open()
        return True

    def close(self):
        if getattr(self, "backend", None):
            return self.backend.close()
        return True

    def send_messages(self, email_messages):  # type: ignore[override]
        """Send a batch of messages with graceful failure handling.

        If Mailgun returns an error or any exception occurs, we:
        - Log a warning (NOT exception to avoid Sentry noise unless configured)
        - Log each email basic metadata so it's not lost
        - Return 0 to the caller (Django's email API treats that as 'not sent')
        """
        # If previously disabled or in console fallback, don't attempt network sends repeatedly.
        if not self.mailgun_enabled:
            return self._log_fallback(email_messages)

        try:
            sent_count = 0
            for message in email_messages:
                ok = self._send_via_mailgun(message)
                if ok:
                    sent_count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("Email send failed via Mailgun (%s): %s", e.__class__.__name__, e)
            self.mailgun_enabled = False
            self._fallback_reason = str(e)
            return self._log_fallback(email_messages)

        # Slack notifications only if actual send happened
        if self.webhook_url and sent_count:
            for message in email_messages:
                self._notify_slack(message)
        return sent_count

    def _log_fallback(self, email_messages: List):
        """Log email metadata when we intentionally skip sending."""
        for m in email_messages:
            try:
                logger.info(
                    "EMAIL_FALLBACK to=%s subject=%s reason=%s",
                    m.to,
                    getattr(m, "subject", "(no-subject)"),
                    self._fallback_reason,
                )
            except Exception:  # pragma: no cover - defensive
                pass
        return 0

    def _notify_slack(self, email_message):
        """Send a notification to Slack about the email."""
        if not self.webhook_url:
            return

        try:
            # Create a message for Slack
            recipients = ", ".join(email_message.to)
            subject = email_message.subject

            slack_message = {
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": "📧 Email Sent", "emoji": True}},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*To:*\n{recipients}"},
                            {"type": "mrkdwn", "text": f"*From:*\n{email_message.from_email}"},
                        ],
                    },
                    {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*Subject:*\n{subject}"}]},
                ]
            }

            # Send the notification to Slack
            response = requests.post(
                self.webhook_url, data=json.dumps(slack_message), headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to send Slack notification: {response.status_code} {response.text}")

        except Exception as e:
            logger.exception(f"Error sending Slack notification: {str(e)}")

    # ---- Mailgun HTTP helpers ----
    def _mailgun_auth_and_domain(self) -> Tuple[str, str]:
        """Return (api_key, domain) for Mailgun.

        - api_key from settings.MAILGUN_SENDING_KEY (or MAILGUN_API_KEY fallback)
        - domain derived from DEFAULT_FROM_EMAIL/EMAIL_FROM if MAILGUN_DOMAIN is not set
        """
        api_key = getattr(settings, "MAILGUN_SENDING_KEY", None) or getattr(settings, "MAILGUN_API_KEY", None)
        if not api_key:
            raise RuntimeError("MAILGUN_SENDING_KEY not configured")

        domain = getattr(settings, "MAILGUN_DOMAIN", None)
        if not domain:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_FROM", None)
            if not from_email or "@" not in from_email:
                raise RuntimeError("Unable to infer Mailgun domain from DEFAULT_FROM_EMAIL/EMAIL_FROM")
            domain = from_email.split("@", 1)[1]
        return api_key, domain

    def _send_via_mailgun(self, email_message) -> bool:
        api_key, domain = self._mailgun_auth_and_domain()

        # Basic fields
        from_email = getattr(email_message, "from_email", None) or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        to_emails = email_message.to or []
        subject = getattr(email_message, "subject", "")

        # Determine text/html bodies
        text_body = getattr(email_message, "body", None)
        html_body = None
        # EmailMultiAlternatives provides .alternatives as [(content, mimetype), ...]
        for alt in getattr(email_message, "alternatives", []) or []:
            try:
                content, mimetype = alt
            except Exception:  # pragma: no cover
                continue
            if mimetype == "text/html":
                html_body = content
                break

        data = {
            "from": from_email,
            "to": to_emails,
            "subject": subject,
        }
        if text_body:
            data["text"] = text_body
        if html_body:
            data["html"] = html_body

        # Attachments (best-effort minimal support)
        files = []
        for attachment in getattr(email_message, "attachments", []) or []:
            try:
                if isinstance(attachment, tuple) and len(attachment) in (2, 3):
                    # (filename, content[, mimetype])
                    filename = attachment[0]
                    content = attachment[1]
                    files.append(("attachment", (filename, content)))
            except Exception:  # pragma: no cover
                continue

        url = f"{self.mailgun_api_base}/v3/{domain}/messages"
        resp = requests.post(url, auth=("api", api_key), data=data, files=files if files else None, timeout=15)
        if resp.status_code >= 200 and resp.status_code < 300:
            return True
        # Log and return False to trigger fallback logging for this message
        logger.warning("Mailgun send failed (%s): %s", resp.status_code, resp.text[:500])
        return False
