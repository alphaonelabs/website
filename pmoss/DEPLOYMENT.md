# Deployment Guide

This guide walks you through deploying the OSS Project Management system to Cloudflare Workers.

## Prerequisites Checklist

- [ ] Cloudflare account created
- [ ] Wrangler CLI installed (`npm install -g wrangler`)
- [ ] Authenticated with Wrangler (`wrangler login`)
- [ ] GitHub OAuth app created
- [ ] Node.js 16+ installed

## Step-by-Step Deployment

### 1. Prepare Your Cloudflare Account

```bash
# Login to Cloudflare
wrangler login

# Verify login
wrangler whoami
```

### 2. Create and Configure D1 Database

```bash
# Create the database
wrangler d1 create oss-pm-db
```

You'll receive output like:
```
✅ Successfully created DB 'oss-pm-db'

[[d1_databases]]
binding = "DB"
database_name = "oss-pm-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Copy the `database_id` and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "oss-pm-db"
database_id = "your-actual-database-id"  # Replace this
```

### 3. Initialize Database Schema

```bash
# Apply schema to D1 database
wrangler d1 execute oss-pm-db --file=./schema.sql

# Verify tables created
wrangler d1 execute oss-pm-db --command="SELECT name FROM sqlite_master WHERE type='table'"
```

### 4. Set Up GitHub OAuth App

1. Navigate to https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in:
   - **Application name**: `OSS Project Management`
   - **Homepage URL**: `https://oss-project-management.your-subdomain.workers.dev`
   - **Authorization callback URL**: `https://oss-project-management.your-subdomain.workers.dev/auth/callback`
4. Click **"Register application"**
5. Note your **Client ID**
6. Click **"Generate a new client secret"** and save it securely

### 5. Configure Worker Name and Redirect URI

Edit `wrangler.toml`:

```toml
name = "oss-project-management"  # Choose your worker name

[vars]
GITHUB_REDIRECT_URI = "https://oss-project-management.your-subdomain.workers.dev/auth/callback"
```

### 6. Set Secrets

```bash
# Set GitHub OAuth credentials
echo "Enter your GitHub Client ID:"
wrangler secret put GITHUB_CLIENT_ID

echo "Enter your GitHub Client Secret:"
wrangler secret put GITHUB_CLIENT_SECRET

# Generate and set webhook secret
echo "Enter a random webhook secret (or generate one):"
wrangler secret put GITHUB_WEBHOOK_SECRET

# Optional: Set session secret
echo "Enter a random session secret (or generate one):"
wrangler secret put SESSION_SECRET
```

To generate secure secrets:
```bash
# macOS/Linux
openssl rand -hex 32

# Or use this online generator:
# https://randomkeygen.com/
```

### 7. Deploy the Worker

```bash
# Install dependencies
npm install

# Deploy to Cloudflare
wrangler deploy

# You should see output like:
# ✨ Deployment complete!
# https://oss-project-management.your-subdomain.workers.dev
```

### 8. Verify Deployment

1. Open your worker URL in a browser
2. You should see the login page
3. Click "Connect with GitHub"
4. Authorize the OAuth app
5. You should be redirected back to the dashboard

### 9. Set Up GitHub Webhook (Optional)

For real-time synchronization:

1. Go to your repository: `https://github.com/owner/repo/settings/hooks`
2. Click **"Add webhook"**
3. Configure:
   - **Payload URL**: `https://your-worker.workers.dev/webhook`
   - **Content type**: `application/json`
   - **Secret**: Use the same value as `GITHUB_WEBHOOK_SECRET`
   - **Which events**: Select "Issues"
   - **Active**: Check this
4. Click **"Add webhook"**
5. GitHub will send a ping event - check for green checkmark

### 10. Test the System

1. Navigate to your worker URL
2. Authenticate with GitHub
3. Enter a repository: `owner/repo`
4. Click **"Sync"** to import issues
5. Click **"Load Issues"** to view
6. Test filtering, sorting, and bulk operations

## Updating the Worker

To deploy updates:

```bash
# Pull latest changes
git pull

# Deploy
wrangler deploy
```

## Monitoring and Logs

View real-time logs:

```bash
wrangler tail
```

View logs in Cloudflare dashboard:
1. Go to https://dash.cloudflare.com
2. Select your account
3. Go to Workers & Pages
4. Click on your worker
5. View logs and metrics

## Troubleshooting

### Error: "Database not found"

- Verify database_id in wrangler.toml matches created database
- Run `wrangler d1 list` to see all databases

### Error: "Unauthorized" after login

- Check GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are set correctly
- Verify GITHUB_REDIRECT_URI matches your OAuth app configuration
- Check OAuth app callback URL exactly matches

### Webhook not receiving events

- Verify webhook secret matches `GITHUB_WEBHOOK_SECRET`
- Check webhook delivery logs in GitHub repository settings
- Use `wrangler tail` to view incoming webhook requests

### Issues not syncing

- Verify OAuth token has correct scopes (`repo` and `read:user`)
- Check GitHub API rate limits
- View worker logs for error messages

## Custom Domain (Optional)

To use a custom domain:

1. Go to Cloudflare dashboard
2. Navigate to Workers & Pages → your worker
3. Click "Triggers" tab
4. Add custom domain
5. Update OAuth app callback URL to match new domain

## Performance Optimization

For better performance:

- Enable Cloudflare caching headers
- Use D1 prepared statements (already implemented)
- Implement pagination (already implemented)
- Consider using Durable Objects for real-time features (future enhancement)

## Security Best Practices

- ✅ Rotate secrets regularly
- ✅ Use strong random webhook secrets
- ✅ Enable 2FA on your Cloudflare account
- ✅ Limit OAuth app permissions to required scopes
- ✅ Monitor worker logs for suspicious activity
- ✅ Keep dependencies updated

## Support

If you encounter issues:

1. Check the logs: `wrangler tail`
2. Review the [Cloudflare Workers docs](https://developers.cloudflare.com/workers/)
3. Open an issue on GitHub
