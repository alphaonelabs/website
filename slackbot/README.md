# Slack bot

A small Cloudflare Worker at `slackbot.alphaonelabs.com` for the Alpha One Labs Slack.

When someone posts a link to an open `alphaonelabs` pull request in a channel the bot is in:

- **No peer approval yet:** it replies in a thread, mentions the poster, and explains how to get a peer review.
- **Already peer reviewed:** it reacts with ✅.

Closed, merged and draft PRs are ignored, as are bot messages and edits. The bot reads only messages that contain a PR link and stores nothing.

The `peer reviewed` label itself is managed by `.github/workflows/peer-review-reminder.yml`. That workflow can also announce new PRs in Slack (see step 5 below).

## Setup (maintainers)

1. **Create the Slack app.** At <https://api.slack.com/apps>, choose *Create New App → From a manifest*, pick the alphaonelabs workspace, and paste [`slack-app-manifest.json`](slack-app-manifest.json). Install it to the workspace.
2. **Set the worker secrets** from this folder:
   ```bash
   npx wrangler secret put SLACK_SIGNING_SECRET   # Basic Information → Signing Secret
   npx wrangler secret put SLACK_BOT_TOKEN        # OAuth & Permissions → Bot User OAuth Token
   npx wrangler secret put GITHUB_TOKEN           # fine-grained, read-only "Pull requests"
   ```
3. **Verify the events URL.** In the app's *Event Subscriptions*, Slack checks `https://slackbot.alphaonelabs.com/slack/events`; it should show *Verified*.
4. **Invite the bot** to the channel(s) where PRs are shared: `/invite @alphaonelabs`. To limit it to specific channels, set `SLACK_CHANNEL_IDS` in `wrangler.toml`.
5. **Optional: announce new PRs.** Add an *Incoming Webhook* for the PR channel, save its URL as the repository secret `SLACK_PEER_REVIEW_WEBHOOK`, and set the repository variable `SLACK_PEER_REVIEW_CHANNEL` (e.g. `#pull-requests`) so GitHub reminders name the channel.

Until the secrets are set, the worker answers `503` and does nothing.

## Development

```bash
node --test tests/
npx wrangler dev
```
