import json
import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_slack_notification(message: str, channel: Optional[str] = None) -> bool:
    """
    Send a notification to Slack using the configured webhook URL.

    Args:
        message (str): The message to send to Slack
        channel (str, optional): The channel to send the message to. If not provided,
                               uses the default channel configured in the webhook.

    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", None)
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping Slack notification")
        return False

    try:
        payload = {"text": message}
        if channel:
            payload["channel"] = channel

        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")
        return False
