# Quick Start Guide

Get your OSS Project Management system running in under 10 minutes!

## Prerequisites

✅ Cloudflare account ([Sign up free](https://dash.cloudflare.com/sign-up))  
✅ GitHub account  
✅ Node.js 16+ installed

## 1. Install Wrangler CLI

```bash
npm install -g wrangler
```

## 2. Login to Cloudflare

```bash
wrangler login
```

## 3. Clone and Setup

```bash
# Clone repository
git clone https://github.com/alphaonelabs/alphaonelabs-oss-project-management.git
cd alphaonelabs-oss-project-management

# Install dependencies
npm install
```

## 4. Create D1 Database

```bash
# Create database
wrangler d1 create oss-pm-db
```

Copy the `database_id` from output and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "oss-pm-db"
database_id = "paste-your-database-id-here"
```

Initialize schema:

```bash
wrangler d1 execute oss-pm-db --file=./schema.sql
```

## 5. Create GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in (use temporary values, we'll update after deploy):
   - Name: `OSS Project Management`
   - Homepage: `https://oss-project-management.your-subdomain.workers.dev`
   - Callback: `https://oss-project-management.your-subdomain.workers.dev/auth/callback`
4. Save **Client ID** and **Client Secret**

## 6. Configure Secrets

```bash
# Set GitHub credentials
wrangler secret put GITHUB_CLIENT_ID
# Paste your Client ID when prompted

wrangler secret put GITHUB_CLIENT_SECRET
# Paste your Client Secret when prompted

# Generate and set webhook secret
wrangler secret put GITHUB_WEBHOOK_SECRET
# Generate with: openssl rand -hex 32
```

## 7. Deploy!

```bash
wrangler deploy
```

Copy your worker URL from the output (e.g., `https://oss-project-management.your-subdomain.workers.dev`)

## 8. Update GitHub OAuth App

1. Go back to https://github.com/settings/developers
2. Edit your OAuth app
3. Update **Homepage URL** and **Callback URL** with your actual worker URL
4. Save changes

Update `wrangler.toml`:

```toml
[vars]
GITHUB_REDIRECT_URI = "https://your-actual-worker-url.workers.dev/auth/callback"
```

Redeploy:

```bash
wrangler deploy
```

## 9. Start Using!

1. Open your worker URL in browser
2. Click **"Connect with GitHub"**
3. Authorize the app
4. Enter a repository: `owner/repo`
5. Click **"Sync"** to import issues
6. Click **"Load Issues"** to view!

## Features to Try

✨ **Filter** - Use state, label, and assignee filters  
✨ **Sort** - Click column headers to sort  
✨ **Bulk Actions** - Select multiple issues and close/reopen  
✨ **Metrics** - View analytics at the top of the page  
✨ **Real-time Sync** - Set up webhooks for automatic updates

## Optional: GitHub Webhooks

For automatic syncing when issues change:

1. Go to your repo → Settings → Webhooks
2. Click **"Add webhook"**
3. Enter:
   - **Payload URL**: `https://your-worker-url.workers.dev/webhook`
   - **Content type**: `application/json`
   - **Secret**: Same as your `GITHUB_WEBHOOK_SECRET`
   - **Events**: Select "Issues"
4. Save

## Troubleshooting

### "Unauthorized" after login
- Verify OAuth app callback URL matches `GITHUB_REDIRECT_URI` in wrangler.toml
- Check secrets are set correctly: `wrangler secret list`

### "Database not found"
- Verify `database_id` in wrangler.toml matches created database
- Check with: `wrangler d1 list`

### Issues not loading
- Make sure you clicked "Sync" first
- Check worker logs: `wrangler tail`

## Next Steps

📖 Read the full [README](README.md) for detailed features  
🚀 Check [DEPLOYMENT.md](DEPLOYMENT.md) for advanced setup  
📚 See [API.md](API.md) for API documentation  
🤝 Read [CONTRIBUTING.md](CONTRIBUTING.md) to contribute

## Support

Having issues? 

1. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
2. View logs with `wrangler tail`
3. Open an issue on GitHub

---

**That's it!** You now have a fully functional project management system! 🎉
