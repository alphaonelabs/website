# OSS Project Management System

A minimal, fast open-source project management system that integrates with GitHub Issues. Built as a Cloudflare Worker with D1 database for high-performance caching and synchronization.

## Features

- 🚀 **Fast Table-Driven UI** - Responsive, GitHub-styled interface showing all issue data
- 🔍 **Advanced Filtering** - Filter by state, labels, assignees, and more
- 📊 **Real-time Metrics** - Track open/closed issues, time-to-close, and trends
- 🔄 **GitHub Sync** - Webhook-based real-time sync and on-demand repository sync
- ✏️ **Bulk Operations** - Update multiple issues at once (close, reopen, label)
- 🔐 **OAuth Authentication** - Secure GitHub OAuth integration
- 📈 **Analytics Dashboard** - Label distribution, assignee stats, velocity tracking
- ⚡ **Edge Performance** - Runs on Cloudflare's global network with D1 database

## Architecture

- **Backend**: JavaScript on Cloudflare Workers
- **Database**: Cloudflare D1 (SQLite at the edge)
- **Frontend**: Single-page application (vanilla JavaScript)
- **Integration**: GitHub API v3 + OAuth + Webhooks

## Prerequisites

- [Cloudflare Account](https://dash.cloudflare.com/sign-up)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- [GitHub OAuth App](https://github.com/settings/developers)
- Node.js 16+ (for development)

## Setup

### 1. Clone the Repository

\`\`\`bash
git clone https://github.com/alphaonelabs/alphaonelabs-oss-project-management.git
cd alphaonelabs-oss-project-management
\`\`\`

### 2. Install Dependencies

\`\`\`bash
npm install
\`\`\`

### 3. Create a D1 Database

\`\`\`bash
# Create the database
wrangler d1 create oss-pm-db

# Note the database_id from the output and update wrangler.toml
\`\`\`

Update `wrangler.toml` with your database ID:

\`\`\`toml
[[d1_databases]]
binding = "DB"
database_name = "oss-pm-db"
database_id = "your-database-id-here"
\`\`\`

### 4. Initialize Database Schema

\`\`\`bash
wrangler d1 execute oss-pm-db --file=./schema.sql
\`\`\`

### 5. Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: OSS Project Management
   - **Homepage URL**: `https://your-worker.workers.dev`
   - **Authorization callback URL**: `https://your-worker.workers.dev/auth/callback`
4. Note the Client ID and generate a Client Secret

### 6. Configure Secrets

\`\`\`bash
# Set GitHub OAuth credentials
wrangler secret put GITHUB_CLIENT_ID
wrangler secret put GITHUB_CLIENT_SECRET

# Set webhook secret (generate a random string)
wrangler secret put GITHUB_WEBHOOK_SECRET

# Optional: Session secret for additional security
wrangler secret put SESSION_SECRET
\`\`\`

Update `wrangler.toml` with your worker URL:

\`\`\`toml
[vars]
GITHUB_REDIRECT_URI = "https://your-worker.workers.dev/auth/callback"
\`\`\`

### 7. Deploy

\`\`\`bash
# Deploy to Cloudflare Workers
wrangler deploy
\`\`\`

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

\`\`\`bash
# Run local development server
npm run dev

# Access at http://localhost:8787
\`\`\`

### Testing Locally

Use a tool like [ngrok](https://ngrok.com/) to test webhooks locally:

\`\`\`bash
ngrok http 8787
\`\`\`

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
