# Quick Start Guide

Get your OSS Project Management system running in under 10 minutes!

## Prerequisites

✅ Cloudflare account ([Sign up free](https://dash.cloudflare.com/sign-up))  
✅ GitHub account  
✅ **Wrangler CLI** (for deployment only)  
❌ **No Node.js, npm, or Python installation required!**

## 1. Install Wrangler CLI

Choose one method:

```bash
# Option 1: Using npm (quickest)
npm install -g wrangler

# Option 2: Using Cargo (Rust)
cargo install wrangler

# Option 3: Using Homebrew (macOS)
brew install cloudflare-wrangler2
```

## 2. Login to Cloudflare

```bash
wrangler login
```

## 3. Clone and Setup

```bash
# Clone the monorepo (use your fork URL if you forked it)
git clone https://github.com/alphaonelabs/website.git
cd website/pmoss

# No npm install or pip install needed! Python Workers run directly
```

## 4. Create D1 Database

```bash
# Create database
wrangler d1 create pmoss
```

Copy the `database_id` from output and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "pmoss"
database_id = "paste-your-database-id-here"
```

Initialize schema:

```bash
wrangler d1 execute pmoss --file=./schema.sql
```

## 5. Create GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Use your deployment's URL. The live application uses:
   - Name: `OSS Project Management`
   - Homepage: `https://pmoss.alphaonelabs.com`
   - Callback: `https://pmoss.alphaonelabs.com/auth/callback`
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

The live application is at [https://pmoss.alphaonelabs.com](https://pmoss.alphaonelabs.com/). For your own deployment, use the URL configured for your Worker/custom domain.

## 8. Update GitHub OAuth App

1. Go back to https://github.com/settings/developers
2. Edit your OAuth app
3. Update **Homepage URL** and **Callback URL** with your actual worker URL
4. Save changes. For your own deployment, use the URL configured for your Worker/custom domain.

Update `wrangler.toml`:

```toml
[vars]
GITHUB_REDIRECT_URI = "https://pmoss.alphaonelabs.com/auth/callback"
```

Redeploy:

```bash
wrangler deploy
```

## 9. Start Using!

1. Open [pmoss.alphaonelabs.com](https://pmoss.alphaonelabs.com/) or your own deployment URL
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
   - **Payload URL**: `https://pmoss.alphaonelabs.com/webhook` (or your own deployment URL)
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
3. Open a [PMOSS issue](https://github.com/alphaonelabs/website/issues?q=is%3Aissue+is%3Aopen+label%3A%22project%3A+pmoss%22)

---

**That's it!** You now have a fully functional project management system! 🎉
