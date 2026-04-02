"""Module for handling Mailgun webhook events."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone as django_timezone
from django.views.decorators.csrf import csrf_exempt

from .models import EmailEvent
from .slack import send_slack_notification

logger = logging.getLogger(__name__)


@csrf_exempt
def mailgun_webhook(request):
    """Process Mailgun webhook events."""
    if request.method != "POST":
        return HttpResponse(status=405)  # Method not allowed

    # 1️⃣  Verify signature
    try:
        timestamp = request.POST.get("timestamp", "")
        token = request.POST.get("token", "")
        signature = request.POST.get("signature", "")
        signing_key = getattr(settings, "MAILGUN_WEBHOOK_SIGNING_KEY", None)

        if not (timestamp and token and signature and signing_key):
            logger.warning("Missing Mailgun webhook signature data")
            return HttpResponseForbidden()

        # Verify the signature
        hmac_digest = hmac.new(
            key=signing_key.encode("utf-8"),
            msg=f"{timestamp}{token}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, hmac_digest):
            logger.warning("Mailgun webhook signature verification failed")
            return HttpResponseForbidden()

    except Exception:
        logger.exception("Error verifying Mailgun webhook signature")
        return HttpResponseForbidden()

    try:
        # Process the event
        event_data = request.POST.get("event-data")
        if event_data:
            # Parse JSON if event-data is a string
            if isinstance(event_data, str):
                event_data = json.loads(event_data)
            process_mailgun_event(event_data)
        else:
            # For simple events, build from POST data
            event = {
                "event": request.POST.get("event", "other"),
                "recipient": request.POST.get("recipient", ""),
                "timestamp": request.POST.get("timestamp", ""),
                "message": {
                    "headers": {
                        "message-id": request.POST.get("Message-Id", ""),
                    }
                },
            }
            process_mailgun_event(event)

        return HttpResponse(status=200)

    except Exception as e:
        logger.exception(f"Error processing Mailgun webhook: {e}")
        return HttpResponse(status=500)  # Internal server error


def process_mailgun_event(event):
    """Process a single Mailgun event and update user records."""
    # Get event data - Mailgun webhook structure
    event_type = event.get("event", "other")
    recipient = event.get("recipient", "")
    timestamp = event.get("timestamp")

    # Message ID can be in different places
    message_headers = event.get("message", {}).get("headers", {})
    mg_message_id = message_headers.get("message-id", "") or event.get("id", "")

    # Event ID
    mg_event_id = event.get("id", "")

    # Skip if no recipient is provided
    if not recipient:
        logger.warning("Received Mailgun event with no recipient address")
        return

    email = recipient.lower()

    # Convert timestamp to datetime
    if timestamp:
        try:
            # Mailgun timestamp is Unix epoch seconds (can be float)
            dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
        except (ValueError, TypeError):
            dt = django_timezone.now()
    else:
        dt = django_timezone.now()

    # Find the associated user
    user = User.objects.filter(email__iexact=email).first()

    # Create an event record
    EmailEvent.objects.create(
        email=email,
        user=user,
        event_type=event_type,
        timestamp=dt,
        mg_message_id=mg_message_id,
        mg_event_id=mg_event_id,
        event_data=event,
    )

    # Update profile statistics if user exists
    if user and hasattr(user, "profile"):
        profile = user.profile

        # Update the event counters based on Mailgun event types
        if event_type == "delivered":
            profile.email_delivered_count += 1
        elif event_type == "opened":
            profile.email_open_count += 1
        elif event_type == "clicked":
            profile.email_click_count += 1
        elif event_type == "failed":
            profile.email_bounce_count += 1
        elif event_type == "rejected":
            profile.email_drop_count += 1
        elif event_type == "complained":
            profile.email_spam_report_count += 1

        # Update last event information
        profile.last_email_event = event_type
        profile.last_email_event_time = dt
        profile.email_last_event_data = event

        # Save the profile
        profile.save(
            update_fields=[
                "email_delivered_count",
                "email_open_count",
                "email_click_count",
                "email_bounce_count",
                "email_drop_count",
                "email_spam_report_count",
                "last_email_event",
                "last_email_event_time",
                "email_last_event_data",
            ]
        )

    # Send notification to Slack
    send_mailgun_event_to_slack(event, email, event_type, user)


def send_mailgun_event_to_slack(event, email, event_type, user=None):
    """Send Mailgun event notification to Slack."""
    # Map event types to emojis for better visibility in Slack
    event_emojis = {
        "accepted": "✅",
        "rejected": "❌",
        "delivered": "📬",
        "failed": "🔴",
        "opened": "👁️",
        "clicked": "🖱️",
        "unsubscribed": "👋",
        "complained": "🚫",
        "stored": "💾",
    }

    emoji = event_emojis.get(event_type, "📧")
    user_info = f" ({user.username})" if user else ""

    # Format the message based on event type
    header = f"{emoji} Mailgun *{event_type.upper()}* event for {email}{user_info}"

    # Add event details
    details = []
    for key in ["event", "recipient", "timestamp", "id"]:
        if key in event:
            details.append(f"*{key}:* {event[key]}")

    # The full message
    message = header + "\n" + "\n".join(details)

    # Reason for failed or rejected emails
    if event_type in ["failed", "rejected"]:
        reason = event.get("reason", event.get("reject", {}).get("reason", "Unknown reason"))
        message += f"\n*Reason:* {reason}"

    # Send to Slack
    send_slack_notification(message)
