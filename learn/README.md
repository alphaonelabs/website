# AlphaOneLabs Education Platform

## Project Overview

Alpha One Labs is an education platform designed to facilitate both learning and teaching. The platform provides a comprehensive environment where educators can create and manage courses, while students can learn, collaborate, and engage with peers. With features like study groups, peer connections, and discussion forums, we aim to create a collaborative learning environment that goes beyond traditional online education.

## Tech Stack

- Frontend: HTML,Tailwind CSS 
- Backend: Python (Cloudflare Worker)
- Database: Cloudflare D1 (SQLite)

## Set Up Instructions

### Prerequisites

Make sure you have installed:
 - Node.js
 - Wrangler CLI

Install Wrangler:

```bash
npm install -g wrangler
```

### Clone the Repository

```bash
git clone https://github.com/alphaonelabs/website.git
cd website/learn
```

### Login to Cloudflare (One time)

```bash
wrangler login
```

### Setup Database (D1)

- Create Database:

```bash
wrangler d1 create education_db
```

- Add the generated database_id to your wrangler.toml:

```toml
[[d1_databases]]
binding = "DB"
database_name = "education_db"
database_id = "YOUR_DATABASE_ID"
```

- Apply Schema:

```bash
wrangler d1 execute education_db --file=schema.sql
```

### Setup Environment Variables

This project requires environment variables for encryption and authentication.

- For Local Development

Create a `.dev.vars` file in the project root:

```
ENCRYPTION_KEY=your-dev-encryption-key
JWT_SECRET=your-dev-jwt-secret
SENTRY_DSN=your-sentry-dsn
```

- For Production
Use Wrangler secrets:

```bash
wrangler secret put ENCRYPTION_KEY
wrangler secret put JWT_SECRET
wrangler secret put SENTRY_DSN
```

Or upload all values from an env file after verifying the active Cloudflare account:

```bash
./scripts/upload-vars.sh .env.production --account-id YOUR_ACCOUNT_ID
```

To run with no arguments, add your account ID to `.env.production`:

```
CLOUDFLARE_ACCOUNT_ID=YOUR_ACCOUNT_ID
```

Then run:

```bash
./scripts/upload-vars.sh
```

You can also verify by account name:

```bash
./scripts/upload-vars.sh .env.production --account-name "Your Account Name"
```

Optional Sentry tuning secrets:

```bash
wrangler secret put SENTRY_TRACES_SAMPLE_RATE
wrangler secret put SENTRY_ENVIRONMENT
wrangler secret put SENTRY_RELEASE
```


### Run Backend

```bash
wrangler dev
```

Backend server starts at:

```bash
http://127.0.0.1:8787
```

### Run Frontend

- Open directly

```bash
public/index.html
```

- Use a local server

```bash
npx serve public
```

Frontend Server will start at:

```bash
http://localhost:3000
```

### Service worker and offline shell

Learn registers `public/service-worker.js` at the Learn origin with `/` scope.
The worker uses the versioned `learn-app-shell-v1` cache for a small, explicit
set of same-origin static assets and the offline fallback page. Static shell
assets use cache-first behavior. Allowlisted public navigations use
network-first behavior and are cached only after a successful same-origin
response; if the network and navigation cache both miss, `offline.html` is
returned. API, admin, media, referral, and authenticated requests are excluded
from the generic cache.

The worker removes older `learn-app-shell-*` caches during activation. Browser
update failures are logged and do not block normal online page loading. The
manifest and install icons are maintained separately by issue #1130 and PR
#1197.

For local manual validation, serve `public/` over a local HTTP server (service
workers do not run from `file://` URLs), open a public page in a browser, and
use DevTools Application > Service Workers and Network > Offline to verify
cached navigation and the fallback page. The repository currently has no
browser-test framework; the focused service-worker lifecycle test can be run
with:

```bash
node --test learn/tests/test_service_worker.mjs
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|----------|----------|-------------|
| POST | /api/register | Register a new user |
| POST | /api/login | Authenticate and return token |

### Activities

| Method | Endpoint | Description |
|----------|----------|-------------|
| GET | /api/activities | List activities |
| POST | /api/activities | Create activity |
| GET | /api/activities/:id | Get activity details |
| POST | /api/join | Join activity |

### Dashboard

| Method | Endpoint | Description |
|----------|----------|-------------|
| GET | /api/dashboard | User dashboard |