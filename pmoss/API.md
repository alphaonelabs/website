# API Documentation

Complete API reference for the OSS Project Management system.

## Base URL

```
https://your-worker.workers.dev
```

## Authentication

All API endpoints (except `/auth`, `/auth/callback`, and `/webhook`) require authentication via session cookie.

### Session Cookie

After successful OAuth authentication, a session cookie is set:

```
Cookie: session=<session-id>
```

The session is valid for 7 days.

## Endpoints

### Authentication

#### `GET /auth`

Initiate GitHub OAuth flow.

**Response**: Redirects to GitHub authorization page

---

#### `GET /auth/callback`

OAuth callback handler. GitHub redirects here after user authorization.

**Query Parameters**:
- `code` (required): OAuth authorization code from GitHub

**Response**: Redirects to `/` with session cookie set

---

### Issues API

#### `GET /api/issues`

List issues with filtering and sorting.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repository` | string | - | Repository in format `owner/repo` |
| `state` | string | `all` | Filter by state: `all`, `open`, `closed` |
| `label` | string | - | Filter by label name |
| `assignee` | string | - | Filter by assignee username or `none` |
| `sort` | string | `updated_at` | Sort field: `number`, `title`, `state`, `created_at`, `updated_at`, `closed_at`, `time_to_close` |
| `order` | string | `desc` | Sort order: `asc`, `desc` |
| `page` | integer | `1` | Page number for pagination |
| `per_page` | integer | `50` | Results per page (max 100) |

**Example Request**:
```bash
curl -X GET 'https://your-worker.workers.dev/api/issues?repository=owner/repo&state=open&sort=created_at&order=desc' \
  -H 'Cookie: session=<session-id>'
```

**Response**:
```json
{
  "issues": [
    {
      "id": 123456,
      "number": 42,
      "title": "Bug in feature X",
      "body": "Description of the issue...",
      "state": "open",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-02T00:00:00Z",
      "closed_at": null,
      "html_url": "https://github.com/owner/repo/issues/42",
      "repository": "owner/repo",
      "assignee": "username",
      "milestone": "v1.0",
      "time_to_close": null,
      "labels": [
        { "name": "bug", "color": "d73a4a" }
      ],
      "assignees": ["username1", "username2"]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "total_pages": 3
  }
}
```

---

#### `GET /api/issues/:number`

Get a single issue by number.

**Path Parameters**:
- `number` (required): Issue number

**Query Parameters**:
- `repository` (required): Repository in format `owner/repo`

**Example Request**:
```bash
curl -X GET 'https://your-worker.workers.dev/api/issues/42?repository=owner/repo' \
  -H 'Cookie: session=<session-id>'
```

**Response**:
```json
{
  "id": 123456,
  "number": 42,
  "title": "Bug in feature X",
  "body": "Description...",
  "state": "open",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z",
  "closed_at": null,
  "html_url": "https://github.com/owner/repo/issues/42",
  "repository": "owner/repo",
  "assignee": "username",
  "milestone": "v1.0",
  "time_to_close": null,
  "labels": [
    { "name": "bug", "color": "d73a4a" }
  ],
  "assignees": ["username1"]
}
```

---

#### `PATCH /api/issues/:number`

Update an issue on GitHub and sync back to database.

**Path Parameters**:
- `number` (required): Issue number

**Query Parameters**:
- `repository` (required): Repository in format `owner/repo`

**Request Body**:
```json
{
  "state": "closed",
  "labels": ["bug", "fixed"],
  "assignees": ["username1"],
  "milestone": "v1.0",
  "title": "Updated title",
  "body": "Updated description"
}
```

**Example Request**:
```bash
curl -X PATCH 'https://your-worker.workers.dev/api/issues/42?repository=owner/repo' \
  -H 'Cookie: session=<session-id>' \
  -H 'Content-Type: application/json' \
  -d '{"state": "closed"}'
```

**Response**:
```json
{
  "success": true,
  "issue": {
    "id": 123456,
    "number": 42,
    "state": "closed",
    ...
  }
}
```

---

#### `PATCH /api/issues/bulk`

Update multiple issues at once.

**Request Body**:
```json
{
  "repository": "owner/repo",
  "issue_numbers": [42, 43, 44],
  "updates": {
    "state": "closed",
    "labels": ["resolved"]
  }
}
```

**Example Request**:
```bash
curl -X PATCH 'https://your-worker.workers.dev/api/issues/bulk' \
  -H 'Cookie: session=<session-id>' \
  -H 'Content-Type: application/json' \
  -d '{"repository":"owner/repo","issue_numbers":[42,43],"updates":{"state":"closed"}}'
```

**Response**:
```json
{
  "results": [
    { "issue_number": 42, "success": true },
    { "issue_number": 43, "success": true }
  ]
}
```

---

### Sync API

#### `POST /api/sync`

Sync all issues from a GitHub repository to the local database.

**Request Body**:
```json
{
  "repository": "owner/repo"
}
```

**Example Request**:
```bash
curl -X POST 'https://your-worker.workers.dev/api/sync' \
  -H 'Cookie: session=<session-id>' \
  -H 'Content-Type: application/json' \
  -d '{"repository":"owner/repo"}'
```

**Response**:
```json
{
  "success": true,
  "count": 150
}
```

---

### Metrics API

#### `GET /api/metrics`

Get analytics and metrics for a repository.

**Query Parameters**:
- `repository` (required): Repository in format `owner/repo`

**Example Request**:
```bash
curl -X GET 'https://your-worker.workers.dev/api/metrics?repository=owner/repo' \
  -H 'Cookie: session=<session-id>'
```

**Response**:
```json
{
  "current": {
    "total_issues": 150,
    "open_issues": 45,
    "closed_issues": 105,
    "avg_time_to_close_hours": 168,
    "avg_time_to_close_days": "7.0",
    "oldest_issue_date": "2023-01-01T00:00:00Z",
    "latest_update_date": "2024-01-15T12:00:00Z"
  },
  "labels": [
    { "name": "bug", "color": "d73a4a", "count": 32 },
    { "name": "feature", "color": "a2eeef", "count": 28 }
  ],
  "assignees": [
    {
      "username": "user1",
      "assigned_issues": 25,
      "open_assigned": 8,
      "closed_assigned": 17
    }
  ],
  "historical": [
    {
      "metric_date": "2024-01-01",
      "total_issues": 145,
      "open_issues": 50,
      "closed_issues": 95,
      "avg_time_to_close": 160
    }
  ],
  "time_to_close_distribution": [
    { "bucket": "< 1 day", "count": 15 },
    { "bucket": "1-7 days", "count": 45 },
    { "bucket": "1-4 weeks", "count": 30 },
    { "bucket": "> 4 weeks", "count": 15 }
  ],
  "velocity": {
    "opened": [
      { "date": "2024-01-15", "opened": 5 },
      { "date": "2024-01-14", "opened": 3 }
    ],
    "closed": [
      { "date": "2024-01-15", "closed": 7 },
      { "date": "2024-01-14", "closed": 4 }
    ]
  }
}
```

---

### Webhook API

#### `POST /webhook`

GitHub webhook handler for real-time issue synchronization.

**Headers**:
- `X-GitHub-Event`: Event type (e.g., `issues`, `ping`)
- `X-Hub-Signature-256`: HMAC SHA-256 signature for verification

**Request Body**: GitHub webhook payload (JSON)

**Example GitHub Webhook Configuration**:
- Payload URL: `https://your-worker.workers.dev/webhook`
- Content type: `application/json`
- Secret: Your `GITHUB_WEBHOOK_SECRET`
- Events: Issues

**Response**:
```json
{
  "status": "processed"
}
```

---

## Error Responses

All endpoints return JSON error responses with appropriate HTTP status codes:

### 400 Bad Request
```json
{
  "error": "repository parameter required"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized"
}
```

### 404 Not Found
```json
{
  "error": "Issue not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "Detailed error message"
}
```

---

## Rate Limits

- **GitHub API**: 5,000 requests per hour per authenticated user
- **Cloudflare Workers**: 100,000 requests per day (free plan)
- **D1 Database**: 100,000 read/write operations per day (free plan)

---

## CORS

All API endpoints support CORS with the following headers:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## Pagination

Paginated endpoints return pagination metadata:

```json
{
  "page": 1,
  "per_page": 50,
  "total": 150,
  "total_pages": 3
}
```

Use `page` and `per_page` query parameters to navigate results.

---

## Filtering Tips

### Multiple Filters

Combine filters for precise results:
```
/api/issues?repository=owner/repo&state=open&label=bug&assignee=username
```

### Unassigned Issues

Use `assignee=none` to find unassigned issues:
```
/api/issues?repository=owner/repo&assignee=none
```

### Sorting

Common sorting patterns:
- Newest first: `sort=created_at&order=desc`
- Oldest first: `sort=created_at&order=asc`
- Recently updated: `sort=updated_at&order=desc`
- Fastest closed: `sort=time_to_close&order=asc`

---

## Examples

### Get all open bugs assigned to user

```bash
curl 'https://your-worker.workers.dev/api/issues?repository=owner/repo&state=open&label=bug&assignee=username' \
  -H 'Cookie: session=<session-id>'
```

### Close all selected issues

```bash
curl -X PATCH 'https://your-worker.workers.dev/api/issues/bulk' \
  -H 'Cookie: session=<session-id>' \
  -H 'Content-Type: application/json' \
  -d '{
    "repository": "owner/repo",
    "issue_numbers": [42, 43, 44, 45],
    "updates": { "state": "closed" }
  }'
```

### Sync repository and get metrics

```bash
# Sync
curl -X POST 'https://your-worker.workers.dev/api/sync' \
  -H 'Cookie: session=<session-id>' \
  -H 'Content-Type: application/json' \
  -d '{"repository":"owner/repo"}'

# Get metrics
curl 'https://your-worker.workers.dev/api/metrics?repository=owner/repo' \
  -H 'Cookie: session=<session-id>'
```
