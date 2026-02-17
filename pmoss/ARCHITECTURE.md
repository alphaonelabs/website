# Architecture

Technical architecture of the OSS Project Management system.

## Overview

```
┌─────────────┐
│   Browser   │
│   (Client)  │
└──────┬──────┘
       │ HTTPS
       ↓
┌─────────────────────────────────────────┐
│   Cloudflare Workers (Edge Network)     │
│  ┌────────────────────────────────┐     │
│  │       src/index.js             │     │
│  │    (Request Router)            │     │
│  └────────────┬───────────────────┘     │
│               │                          │
│    ┌──────────┼──────────┐              │
│    ↓          ↓          ↓              │
│ ┌─────┐  ┌──────┐  ┌────────┐          │
│ │ UI  │  │ Auth │  │  API   │          │
│ └─────┘  └───┬──┘  └───┬────┘          │
│              │          │                │
│         ┌────┴──────────┴───┐           │
│         ↓                    ↓           │
│    ┌─────────┐        ┌──────────┐      │
│    │ GitHub  │        │    D1    │      │
│    │   API   │        │ Database │      │
│    └────┬────┘        └──────────┘      │
└─────────┼──────────────────────────────┘
          │
          ↓
   ┌─────────────┐
   │   GitHub    │
   │ (OAuth &    │
   │  Webhooks)  │
   └─────────────┘
```

## Components

### 1. Frontend (src/ui.js)

**Technology**: Vanilla JavaScript, HTML, CSS

**Responsibilities**:
- Render single-page application
- Handle user interactions
- Make API calls
- Display data in tables
- Manage UI state

**Key Features**:
- Server-side rendered HTML string
- Client-side JavaScript for interactivity
- Dark theme inspired by GitHub
- Responsive design

### 2. Request Router (src/index.js)

**Technology**: Cloudflare Workers (JavaScript)

**Responsibilities**:
- Route incoming HTTP requests
- Handle CORS
- Authenticate requests
- Delegate to appropriate handlers
- Error handling

**Routes**:
```javascript
GET  /                     → UI
GET  /auth                 → OAuth initiation
GET  /auth/callback        → OAuth callback
POST /webhook              → GitHub webhooks
GET  /api/issues           → List issues
GET  /api/issues/:number   → Get issue
PATCH /api/issues/:number  → Update issue
PATCH /api/issues/bulk     → Bulk update
POST /api/sync             → Sync repository
GET  /api/metrics          → Get metrics
```

### 3. Authentication (src/auth.js)

**Technology**: GitHub OAuth 2.0

**Flow**:
```
1. User clicks "Connect with GitHub"
2. Redirect to GitHub authorization page
3. User authorizes app
4. GitHub redirects back with code
5. Exchange code for access token
6. Fetch user info
7. Create session in D1
8. Set session cookie
9. Redirect to app
```

**Session Management**:
- Session ID stored in HttpOnly cookie
- Session data stored in D1 database
- 7-day expiration
- Verified on each API request

### 4. API Handlers (src/api.js)

**Technology**: REST API

**Capabilities**:
- CRUD operations on issues
- Advanced filtering and sorting
- Pagination
- Bulk operations
- GitHub synchronization

**Query Building**:
- Dynamic SQL generation
- Prepared statements for security
- Join operations for labels/assignees
- Indexed queries for performance

### 5. GitHub Integration (src/github.js)

**Technology**: GitHub REST API v3

**Functions**:
- Fetch repository issues
- Update issues
- Sync issue data
- Calculate metrics
- Handle rate limits

**API Calls**:
- GET /repos/:owner/:repo/issues
- PATCH /repos/:owner/:repo/issues/:number
- Paginated requests (100 per page)

### 6. Webhook Handler (src/webhook.js)

**Technology**: GitHub Webhooks

**Process**:
```
1. GitHub sends webhook to /webhook
2. Verify HMAC-SHA256 signature
3. Parse event type
4. Process issue changes
5. Update D1 database
6. Update metrics
7. Return success response
```

**Events Handled**:
- issues (opened, closed, edited, labeled, etc.)
- ping (verification)

### 7. Metrics Engine (src/metrics.js)

**Technology**: SQL aggregations

**Calculations**:
- Total/open/closed counts
- Average time-to-close
- Label distribution
- Assignee statistics
- Historical trends
- Velocity metrics

**Aggregations**:
- Real-time queries for current stats
- Daily rollups in metrics table
- 30-day historical data

### 8. Database (D1)

**Technology**: Cloudflare D1 (SQLite at edge)

**Schema**:

```sql
issues
├── id (PRIMARY KEY)
├── number
├── title
├── body
├── state
├── created_at
├── updated_at
├── closed_at
├── repository
├── assignee
└── time_to_close

labels
├── id (PRIMARY KEY)
├── issue_id (FOREIGN KEY)
├── name
└── color

assignees
├── id (PRIMARY KEY)
├── issue_id (FOREIGN KEY)
└── username

metrics
├── id (PRIMARY KEY)
├── repository
├── metric_date
├── total_issues
├── open_issues
├── closed_issues
└── avg_time_to_close

sessions
├── id (PRIMARY KEY)
├── username
├── access_token
├── created_at
└── expires_at

sync_status
├── id (PRIMARY KEY)
├── repository
├── last_sync
├── status
└── error_message
```

**Indexes**:
- issues: state, repository
- labels: issue_id
- assignees: issue_id
- metrics: repository
- sessions: username

## Data Flow

### Issue Listing Flow

```
1. User filters/sorts in UI
2. JavaScript makes GET /api/issues
3. Router authenticates request
4. API handler builds SQL query
5. D1 executes query with indexes
6. Results joined with labels/assignees
7. JSON response to client
8. UI renders table
```

### Issue Update Flow

```
1. User selects issues, clicks action
2. JavaScript makes PATCH /api/issues/bulk
3. Router authenticates request
4. API handler processes each issue:
   a. Call GitHub API to update
   b. Sync response to D1
   c. Update metrics
5. Return results to client
6. UI reloads data
```

### Webhook Sync Flow

```
1. GitHub sends issue event
2. Worker verifies signature
3. Parse issue data
4. Update issues table
5. Update labels table
6. Update assignees table
7. Recalculate metrics
8. Store in metrics table
```

## Performance Characteristics

### Response Times (Typical)

| Operation | Time | Notes |
|-----------|------|-------|
| Page load | 200-500ms | Including auth check |
| Issue list | 50-200ms | With 50 results |
| Single update | 500-1000ms | GitHub API + sync |
| Bulk update | 2-5s | 10 issues |
| Sync repo | 10-60s | Depends on issue count |
| Webhook | 50-100ms | Database update only |

### Scalability

**Cloudflare Workers**:
- Runs on 200+ data centers globally
- Automatic scaling
- Sub-50ms startup time
- 50ms CPU time limit per request

**D1 Database**:
- Automatic replication
- Read replicas at edge
- 100k reads/day (free tier)
- 100k writes/day (free tier)

**GitHub API**:
- 5,000 requests/hour per user
- Conditional requests for caching
- Pagination for large datasets

## Security Architecture

### Authentication Layer

```
User → Session Cookie → D1 Lookup → Access Token → GitHub API
        (HttpOnly)      (Encrypted)   (Validated)
```

### Webhook Security

```
GitHub → HMAC-SHA256 → Verify Signature → Process Event
         Signature      (Secret Key)
```

### Data Security

- Tokens encrypted at rest in D1
- HTTPS only (enforced by Cloudflare)
- Secure cookies with SameSite
- Prepared statements (SQL injection prevention)
- Input validation
- Rate limiting (via Cloudflare)

## Deployment Architecture

```
Development                Production
───────────                ──────────
Local Machine              Cloudflare Edge
  ↓                          ↓
wrangler dev              wrangler deploy
  ↓                          ↓
Local D1 (--local)        D1 (replicated)
  ↓                          ↓
GitHub OAuth Dev App      GitHub OAuth Prod App
```

### Environment Separation

| Environment | Database | OAuth App | Secrets |
|-------------|----------|-----------|---------|
| Development | Local D1 | Dev | .dev.vars |
| Production | Edge D1 | Prod | Wrangler secrets |

## Technology Stack

### Runtime
- **Platform**: Cloudflare Workers
- **Language**: JavaScript (ES2020+)
- **Runtime**: V8 JavaScript engine

### Storage
- **Database**: Cloudflare D1 (SQLite)
- **Session Store**: D1 database
- **Cache**: Cloudflare edge cache

### External Services
- **Auth**: GitHub OAuth 2.0
- **Data Source**: GitHub REST API v3
- **Real-time Sync**: GitHub Webhooks

### Frontend
- **Framework**: Vanilla JavaScript
- **Styling**: Inline CSS
- **Architecture**: Single-page application

## Monitoring & Observability

### Logging

```javascript
console.log()   → Cloudflare Logs
console.error() → Cloudflare Logs
wrangler tail   → Real-time logs
```

### Metrics

- Worker execution time
- Request count
- Error rate
- D1 query performance
- GitHub API rate limit usage

### Debugging

```bash
# Development
wrangler dev          # Local server
console.log()         # Browser console

# Production
wrangler tail         # Real-time logs
Cloudflare Dashboard  # Metrics & logs
```

## Design Decisions

### Why Cloudflare Workers?

✅ Global edge network (low latency)  
✅ Serverless (no infrastructure management)  
✅ Generous free tier  
✅ Integrated D1 database  
✅ Built-in security (DDoS protection)  

### Why D1 Database?

✅ SQLite (familiar, powerful)  
✅ Edge replication  
✅ ACID transactions  
✅ Low latency  
✅ Cost-effective  

### Why Vanilla JavaScript?

✅ No build step required  
✅ Fast initial load  
✅ Small bundle size  
✅ Direct deployment  
✅ Simple maintenance  

### Why Single Repository?

✅ Easy to deploy  
✅ Simple architecture  
✅ Fast development  
✅ Single source of truth  

## Extension Points

To extend the system:

1. **Add new API endpoints**: Edit src/api.js
2. **Add UI features**: Edit src/ui.js
3. **Add database tables**: Update schema.sql
4. **Add integrations**: Create new module in src/
5. **Add analytics**: Edit src/metrics.js

## Future Architecture Considerations

As the system scales:

- **Caching**: Add Redis/KV for hot data
- **Queue**: Add queue for async operations
- **Sharding**: Shard D1 by repository
- **CDN**: Add static asset caching
- **Microservices**: Split into specialized workers

---

For implementation details, see the source code in `src/` directory.
