# OSS Project Management System

A minimal, fast open-source project management system that integrates with GitHub Issues. Built as a **Python-based Cloudflare Worker** with D1 database for high-performance caching and synchronization.

The live application is available at [pmoss.alphaonelabs.com](https://pmoss.alphaonelabs.com/).

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
# Create the database named in wrangler.toml
wrangler d1 create pmoss

# Use the returned database_id in wrangler.toml
```

The D1 binding in `wrangler.toml` is named `pmoss`. Keep the database name
`pmoss` in Wrangler commands and configuration, and replace the configured
`database_id` with the ID for your own database:

```toml
[[d1_databases]]
binding = "DB"
database_name = "pmoss"
database_id = "your-database-id-here"
```

### 4. Initialize Database Schema

```bash
wrangler d1 execute pmoss --file=./schema.sql
```

### 5. Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: OSS Project Management
   - **Homepage URL**: `https://pmoss.alphaonelabs.com`
   - **Authorization callback URL**: `https://pmoss.alphaonelabs.com/auth/callback`
4. Note the Client ID and generate a Client Secret

These are the URLs for the live deployment. If deploying your own copy, use
your own domain in the OAuth app and set the matching callback URL in
`wrangler.toml`.

### 6. Configure Secrets

```bash
# Set GitHub OAuth credentials
wrangler secret put GITHUB_CLIENT_ID
wrangler secret put GITHUB_CLIENT_SECRET

# Set webhook secret (generate a random string)
wrangler secret put GITHUB_WEBHOOK_SECRET

# Optional: Session secret for additional security
wrangler secret put SESSION_SECRET
```

Update `wrangler.toml` with your worker URL:

```toml
[vars]
GITHUB_REDIRECT_URI = "https://pmoss.alphaonelabs.com/auth/callback"
```

### 7. Deploy

```bash
# Deploy to Cloudflare Workers
wrangler deploy
```

## Usage

### Initial Setup

1. Navigate to [pmoss.alphaonelabs.com](https://pmoss.alphaonelabs.com/)
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
   - **Payload URL**: `https://pmoss.alphaonelabs.com/webhook`
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

```bash
# Run local development server
wrangler dev

# Access at http://localhost:8787
```

**Note**: Python Workers are fully supported by Wrangler. No separate Python installation or pip packages are needed.

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

For issues and questions, use [open PMOSS issues](https://github.com/alphaonelabs/website/issues?q=is%3Aissue+is%3Aopen+label%3A%22project%3A+pmoss%22).
