# Mailgun Email Event Tracking

This implementation provides email event tracking for Mailgun webhooks, similar to the SendGrid implementation.

## Features

- Tracks email events (delivered, opened, clicked, failed, rejected, complained, etc.)
- Stores events in the EmailEvent model for historical tracking
- Updates user Profile with email metrics (counts for various event types)
- Sends Slack notifications for email events
- Admin interface integration to view email status

## Setup

### 1. Configure Mailgun Webhook Signing Key

Add the following to your `.env` file or Django settings:

```python
MAILGUN_WEBHOOK_SIGNING_KEY = "your-mailgun-webhook-signing-key"
```

You can find your webhook signing key in the Mailgun dashboard under **Sending > Webhooks**.

### 2. Configure Mailgun Webhook URL

In the Mailgun dashboard, configure the webhook URL to point to:

```
https://yourdomain.com/mailgun-webhook/
```

Subscribe to the following events:
- Delivered
- Opened
- Clicked
- Failed
- Rejected
- Complained/Spam
- Unsubscribed

### 3. Run Migrations

```bash
python manage.py migrate
```

## Models

### EmailEvent

Stores individual email events from Mailgun:

- `email`: Email address of the recipient
- `user`: Foreign key to User model (if email matches a user)
- `event_type`: Type of event (delivered, opened, clicked, etc.)
- `timestamp`: When the event occurred
- `mg_message_id`: Mailgun message ID
- `mg_event_id`: Mailgun event ID
- `event_data`: Full JSON data from the webhook
- `created_at`: When the event was recorded in our database

### Profile (Extended)

Added the following fields to track email statistics:

- `last_email_sent_at`: Timestamp of last email sent
- `last_email_event`: Most recent email event type
- `last_email_event_time`: Timestamp of most recent event
- `email_bounce_count`: Number of bounced emails
- `email_delivered_count`: Number of delivered emails
- `email_open_count`: Number of opened emails
- `email_click_count`: Number of clicked links
- `email_drop_count`: Number of dropped/rejected emails
- `email_spam_report_count`: Number of spam complaints
- `email_last_event_data`: Full JSON of last event

## Admin Interface

The admin interface has been updated to show:

1. **Profile Admin**:
   - Email status column showing the latest event with color coding
   - Email Status fieldset showing all email metrics

2. **User Admin**:
   - Email status column in the user list
   - Filter by last email event type

3. **EmailEvent Admin**:
   - Read-only view of all email events
   - Search by email, user, or message ID
   - Filter by event type and timestamp

## Event Types

Mailgun event types mapped to our system:

- `accepted`: Email accepted by Mailgun
- `rejected`: Email rejected by Mailgun
- `delivered`: Email successfully delivered
- `failed`: Permanent delivery failure (bounce)
- `opened`: Email opened by recipient
- `clicked`: Link clicked in email
- `unsubscribed`: Recipient unsubscribed
- `complained`: Recipient marked as spam
- `stored`: Email stored by Mailgun

## Color Coding

In the admin interface, events are color-coded:

- 🟢 Green (Success): delivered, opened, clicked, accepted
- 🔴 Red (Danger): failed, rejected, complained
- 🟠 Orange (Warning): unsubscribed
- 🔵 Blue (Info): stored, other events
- ⚫ Gray: No events

## Testing

Run the Mailgun webhook tests:

```bash
python manage.py test tests.test_mailgun_webhooks
```

## Webhook Security

The webhook endpoint verifies the signature sent by Mailgun using HMAC-SHA256:

1. Mailgun sends `timestamp`, `token`, and `signature` with each webhook
2. We compute the HMAC-SHA256 hash of `timestamp + token` using the signing key
3. We compare our computed signature with Mailgun's signature
4. If they don't match, the request is rejected with a 403 Forbidden response

This ensures that webhook requests are genuinely from Mailgun and haven't been tampered with.

## Troubleshooting

### Webhook signature verification fails

- Verify `MAILGUN_WEBHOOK_SIGNING_KEY` is correctly set
- Check Mailgun dashboard for the correct signing key
- Ensure the webhook URL is using HTTPS (required for production)

### Events not being recorded

- Check the Django logs for error messages
- Verify the webhook URL is correctly configured in Mailgun
- Test the webhook using Mailgun's webhook testing tool

### User profile not updating

- Ensure the email in the webhook matches the user's email exactly (case-insensitive)
- Check that the user has a Profile object created

## Differences from SendGrid Implementation

This Mailgun implementation mirrors the SendGrid implementation with the following differences:

1. **Signature Verification**: Uses HMAC-SHA256 instead of SendGrid's EventWebhook class
2. **Event Types**: Maps Mailgun event types to similar semantics
3. **Field Names**: Uses `mg_` prefix for Mailgun-specific fields instead of `sg_`
4. **Webhook Data Structure**: Handles Mailgun's webhook format which is different from SendGrid

## Integration with Email Backend

The email tracking works independently of the email sending backend. The existing `SlackNotificationEmailBackend` in `web/email_backend.py` handles sending emails via Mailgun's API, while this webhook handler tracks delivery events asynchronously.
