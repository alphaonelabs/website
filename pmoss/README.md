# OSS Project Management System

A minimal, fast open-source project management system that integrates with GitHub Issues. Built as a **Python-based Cloudflare Worker** with D1 database for high-performance caching and synchronization.

## Quick Links

📚 **[Quick Start Guide](QUICKSTART.md)** - Get started in 10 minutes  
🚀 **[Deployment Guide](DEPLOYMENT.md)** - Detailed deployment instructions  
📖 **[API Documentation](API.md)** - Complete API reference  
⚙️ **[Features](FEATURES.md)** - Full feature list  
🏗️ **[Architecture](ARCHITECTURE.md)** - Technical architecture details  
🤝 **[Contributing](CONTRIBUTING.md)** - How to contribute

## Features

- 🚀 **Fast Table-Driven UI** - Responsive, GitHub-styled interface showing all issue data
- 🔍 **Advanced Filtering** - Filter by state, labels, assignees, and more
- 📊 **Real-time Metrics** - Track open/closed issues, time-to-close, and trends
- 🔄 **GitHub Sync** - Webhook-based real-time sync and on-demand repository sync
- ✏️ **Bulk Operations** - Update multiple issues at once (close, reopen, label)
- 🔐 **OAuth Authentication** - Secure GitHub OAuth integration
- 📈 **Analytics Dashboard** - Label distribution, assignee stats, velocity tracking
- ⚡ **Edge Performance** - Runs on Cloudflare's global network with D1 database
- 🐍 **Python-Powered** - Pure Python backend, no Node.js or npm required

## Architecture

- **Backend**: **Python** on Cloudflare Workers
- **Database**: Cloudflare D1 (SQLite at the edge)
- **Frontend**: Single-page application (vanilla JavaScript)
- **Integration**: GitHub API v3 + OAuth + Webhooks

## Project Structure

```
.
├── src/
│   ├── main.py       # Main worker entry point and request router
│   ├── auth.py       # GitHub OAuth authentication
│   ├── api.py        # API endpoints for issues CRUD
│   ├── github.py     # GitHub API client and sync logic
│   ├── webhook.py    # GitHub webhook handler
│   ├── metrics.py    # Analytics and metrics engine
│   └── ui.py         # Frontend single-page application
├── schema.sql        # D1 database schema
├── wrangler.toml     # Cloudflare Workers configuration
├── requirements.txt  # Python dependencies (reference)
├── README.md         # This file
├── QUICKSTART.md     # Quick start guide
├── DEPLOYMENT.md     # Detailed deployment guide
├── API.md            # API documentation
├── FEATURES.md       # Complete feature list
├── ARCHITECTURE.md   # Technical architecture details
└── CONTRIBUTING.md   # Contribution guidelines
```

## Prerequisites

- [Cloudflare Account](https://dash.cloudflare.com/sign-up)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- [GitHub OAuth App](https://github.com/settings/developers)
- **No Node.js or npm required!** (Python Workers only need Wrangler CLI)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/alphaonelabs/website.git
cd website/pmoss
```

### 2. Install Wrangler CLI

```bash
# Using npm (only for Wrangler CLI, not for the project)
npm install -g wrangler

# Or using Cargo (Rust)
cargo install wrangler

# Or using Homebrew (macOS)
brew install cloudflare-wrangler2
```

### 3. Create a D1 Database

```bash
# Create the database
wrangler d1 create oss-pm-db

# Note the database_id from the output and update wrangler.toml
```

Update `wrangler.toml` with your database ID:

```toml
[[d1_databases]]
binding = "DB"
database_name = "oss-pm-db"
database_id = "your-database-id-here"
```

### 4. Initialize Database Schema

```bash
wrangler d1 execute oss-pm-db --file=./schema.sql
```

### 5. Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers) and follow the [OAuth app setup guide](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: OSS Project Management
   - **Homepage URL**: `https://your-worker.workers.dev`
   - **Authorization callback URL**: `https://your-worker.workers.dev/auth/callback`
4. Note the Client ID and generate a Client Secret

### 6. Configure Secrets

```bash
# Set GitHub OAuth credentials
wrangler secret put GITHUB_CLIENT_ID
wrangler secret put GITHUB_CLIENT_SECRET

# Set this before registering a GitHub webhook
wrangler secret put GITHUB_WEBHOOK_SECRET
```

Update `wrangler.toml` with your worker URL:

```toml
[vars]
GITHUB_REDIRECT_URI = "https://your-worker.workers.dev/auth/callback"
```

### Environment Variables

PMOSS reads these five GitHub settings from the Worker environment. The D1
database is provided separately as the DB binding in wrangler.toml.

| Name | Needed when | Purpose |
| --- | --- | --- |
| GITHUB_CLIENT_ID | Signing in | Client ID for the GitHub OAuth app. |
| GITHUB_CLIENT_SECRET | Completing sign-in | Client secret used to exchange the OAuth code for an access token. |
| GITHUB_REDIRECT_URI | Signing in | OAuth callback URL. wrangler.toml sets the production URL; local development uses the localhost URL in .dev.vars. |
| GITHUB_REDIRECT_URI_DEFAULT | Only as a fallback | Used only when GITHUB_REDIRECT_URI is missing or empty. |
| GITHUB_WEBHOOK_SECRET | Using GitHub webhooks | Secret used to verify webhook signatures. Set it for any exposed webhook; if it is absent, the current handler logs a warning and accepts requests that include a signature header without checking its value. |

SESSION_SECRET is not read by the PMOSS source and is not required.

### 7. Deploy

```bash
# Deploy to Cloudflare Workers
wrangler deploy
```

## Usage

### Initial Setup

1. Navigate to your worker URL: `https://your-worker.workers.dev`
2. Click "Connect with GitHub" to authenticate
3. Enter a repository in the format `owner/repo`
4. Click "Sync" to initially sync issues from GitHub
5. Click "Load Issues" to view the synced data

### Filtering and Sorting

- **State Filter**: Show all, open, or closed issues
- **Label Filter**: Filter by specific label
- **Assignee Filter**: Filter by username or "none" for unassigned
- **Sorting**: Click column headers to sort (Number, Title, State, Created, Time to Close)

### Bulk Operations

1. Select issues using checkboxes
2. Choose action: Close Selected or Reopen Selected
3. Changes sync back to GitHub immediately

### GitHub Webhooks (Optional)

For real-time synchronization, set up a webhook:

1. Go to your repository settings → Webhooks
2. Add a new webhook:
   - **Payload URL**: `https://your-worker.workers.dev/webhook`
   - **Content type**: `application/json`
   - **Secret**: Use the same value as `GITHUB_WEBHOOK_SECRET`
   - **Events**: Select "Issues"
3. Save the webhook

Now issue changes in GitHub will automatically sync to your dashboard.

## API Endpoints

### Authentication
- `GET /auth` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler

### Issues
- `GET /api/issues` - List issues with filtering/sorting
  - Query params: `repository`, `state`, `label`, `assignee`, `sort`, `order`, `page`, `per_page`
- `GET /api/issues/:number` - Get single issue
- `PATCH /api/issues/:number` - Update issue
- `PATCH /api/issues/bulk` - Bulk update issues

### Sync
- `POST /api/sync` - Sync repository from GitHub
  - Body: `{ "repository": "owner/repo" }`

### Metrics
- `GET /api/metrics` - Get repository metrics and analytics
  - Query params: `repository`

### Webhooks
- `POST /webhook` - GitHub webhook handler

## Database Schema

The D1 database includes the following tables:

- **issues** - Core issue data (number, title, state, dates, time-to-close)
- **labels** - Issue labels with colors
- **assignees** - Issue assignees (supports multiple)
- **metrics** - Daily aggregated metrics per repository
- **sync_status** - Track sync operations and errors
- **sessions** - User authentication sessions

## Development

### Local Development

Wrangler loads local variables from .dev.vars beside wrangler.toml. From the
pmoss directory, copy .dev.vars.example to .dev.vars by running
cp .dev.vars.example .dev.vars (or Copy-Item .dev.vars.example .dev.vars in
PowerShell). Edit the copy with credentials from a separate GitHub OAuth app
for local development.
Repeat step 5 to create a separate OAuth app for local development. Set its
homepage URL to http://localhost:8787 and its authorization callback
URL to exactly http://localhost:8787/auth/callback. The local callback in
.dev.vars overrides the production callback configured in wrangler.toml. Keep
the client secret in .dev.vars; that file is ignored by Git. See Cloudflare's
[local environment variable guide](https://developers.cloudflare.com/workers/local-development/environment-variables/).

Initialize the local D1 database with wrangler d1 execute pmoss --local --file=schema.sql,
then start the Worker with the command below. Both commands should run from
the pmoss directory. Local D1 data is separate from production.

```bash
# Run local development server
wrangler dev

# Access at http://localhost:8787
```

**Note**: Python Workers are fully supported by Wrangler. No separate Python installation or pip packages are needed.

Open http://localhost:8787/ and choose Connect with GitHub. A successful
sign-in requires valid credentials from the local OAuth app.

### Testing GitHub Webhooks Locally

GitHub cannot deliver events directly to localhost. Keep wrangler dev running,
then expose it from a second terminal with cloudflared tunnel --url
http://localhost:8787. Use the generated HTTPS URL with /webhook as the payload
URL in the GitHub repository's webhook settings. Set the webhook secret to the
same value as GITHUB_WEBHOOK_SECRET in .dev.vars, select the Issues event, and
save. To replay an earlier delivery, open that webhook's Recent Deliveries in
GitHub and choose Redeliver. See Cloudflare's
[Quick Tunnels guide](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

### Testing Locally

Use a tool like [ngrok](https://ngrok.com/) to test webhooks locally:

```bash
ngrok http 8787
```

Then use the ngrok URL for your GitHub webhook.

## Security Considerations

- OAuth tokens are stored encrypted in D1
- Webhook signatures are verified using HMAC-SHA256
- Sessions expire after 7 days
- All API endpoints require authentication except webhooks
- CORS headers configured for cross-origin requests

## Performance

- **Edge Caching**: Cloudflare Workers run on 200+ data centers globally
- **D1 Database**: SQLite at the edge with automatic replication
- **Optimized Queries**: Indexed columns for fast filtering and sorting
- **Lazy Loading**: Pagination reduces initial load time
- **Minimal Payload**: Only necessary data transferred

## Limitations

- D1 database size limits apply (check Cloudflare documentation)
- GitHub API rate limits: 5,000 requests/hour per authenticated user
- Worker execution time: 50ms CPU time (should be sufficient for all operations)

## Roadmap

- [ ] Additional bulk operations (add/remove labels, assign users)
- [ ] Custom filters and saved views
- [ ] Issue templates and automation
- [ ] Multi-repository dashboard
- [ ] Export data (CSV, JSON)
- [ ] Advanced analytics (burndown charts, velocity graphs)
- [ ] Markdown rendering for issue bodies
- [ ] Dark/light theme toggle

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please use the [GitHub Issues](https://github.com/alphaonelabs/alphaonelabs-oss-project-management/issues) page.
