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
| GET | /api/activities/:id/offline-package | Get an authorized offline activity manifest |
| POST | /api/join | Join activity |

#### Offline activity package manifest

`GET /api/activities/:id/offline-package` requires a valid bearer token and an
active enrollment, host role, or administrator access. The activity identifier
may be its ID or slug. The response is a package manifest with stable
`package_id`, deterministic `package_version`, activity metadata, and ordered
resource entries:

```json
{
  "package": {
    "package_id": "activity:activity-id",
    "package_version": "sha256 hex digest",
    "activity_id": "activity-id",
    "title": "Python 101",
    "generated_at": "2026-11-07T00:00:00+00:00",
    "resources": [
      {
        "asset_id": "material:material-id",
        "material_id": "material-id",
        "title": "Lesson notes",
        "material_type": "pdf",
        "display_order": 1,
        "downloadable": true,
        "availability": "available",
        "url": "/media/materials/lesson.pdf",
        "content_type": "application/pdf",
        "size_bytes": 2048,
        "content_hash": "sha256:...",
        "revision": "r2-etag",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-02T00:00:00"
      }
    ]
  }
}
```

`package_version` hashes the canonical activity and resource metadata,
excluding the request timestamp, so identical manifests produce identical
versions. Material ordering is deterministic. A manifest revision changes
when relevant activity/material metadata, availability, or R2 revision
metadata changes. Resource availability is `available`, `online_only`, or
`unavailable`; online-only resources are never advertised as downloadable.
Missing R2 size, content type, checksum, or revision metadata is returned as
`null` rather than fabricated. The API does not expose a separate R2 bucket
key, credentials, authentication data, quiz answers, or unrelated learner
data. Removed materials are absent from the current manifest.

This endpoint defines metadata only. It does not download files, add IndexedDB
domain stores, modify the service worker, synchronize content, or manage
storage.

### Dashboard

| Method | Endpoint | Description |
|----------|----------|-------------|
| GET | /api/dashboard | User dashboard |