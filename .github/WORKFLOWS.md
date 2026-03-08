# GitHub Actions Workflows Documentation

This document describes the GitHub Actions workflows used in this project.

## Production Deployment Workflow

**File:** `.github/workflows/deploy-production.yml`

**Trigger:** Manual (workflow_dispatch)

### Purpose

This workflow automates the deployment of the application to the production server and creates a new GitHub release with version tracking.

### Features

1. **Automated Deployment**
   - Connects to production server via SSH
   - Pulls latest code from the main branch
   - Installs/updates dependencies using Poetry
   - Runs database migrations
   - Collects static files
   - Restarts application and nginx services

2. **Deployment Verification**
   - Checks if the application service is running
   - Verifies nginx is operational

3. **Automatic Release Creation**
   - Retrieves the latest release tag
   - Increments the version number automatically
   - Generates release notes from commits since the last release
   - Creates a new GitHub release with the version tag
   - Pushes the version tag to the repository

### Version Scheme

- Uses semantic versioning: `vMAJOR.MINOR` (e.g., v1.0, v1.1, v2.0)
- Automatically increments the **minor** version on each deployment
- Default starting version is `v0.0` if no previous releases exist
- Examples:
  - v1.0 → v1.1 → v1.2 → v1.3
  - v2.0 → v2.1 → v2.2

### Release Notes

Release notes are automatically generated and include:

- Production deployment title with version number
- Deployment date and time (UTC)
- List of commits since the last release
- Commit messages with short SHA hashes
- Footer indicating automated creation

Example release notes:

```markdown
## Production Deployment - v1.1

**Deployment Date:** 2025-10-05 12:00:00 UTC

### Changes in this release:

- Add user authentication feature (abc1234)
- Fix navigation bug (def5678)
- Update dependencies (ghi9012)

---

_This release was automatically created by the production deployment workflow._
```

### How to Deploy

1. Go to the [Actions](../../actions) tab in GitHub
2. Select "Deploy to Production" workflow
3. Click "Run workflow"
4. Select the branch (usually `main`)
5. Click "Run workflow" button

The workflow will:

1. Deploy the code to production
2. Verify the deployment
3. Create a new release (e.g., v1.0 → v1.1)
4. Tag the commit with the new version

### Requirements

The workflow requires the following GitHub secrets to be configured:

- `PRODUCTION_SERVER_IP`: IP address of the production server
- `PRODUCTION_SERVER_USER`: SSH username for the production server
- `PRODUCTION_SERVER_PASSWORD`: SSH password for the production server

### Permissions

The workflow has `contents: write` permission to:

- Create and push version tags
- Create GitHub releases

### Notes

- The workflow uses SSH password authentication via `sshpass`
- Host key checking is disabled for the production server
- The workflow tags the current HEAD of the branch being deployed
- All merge commits are excluded from the release notes
- If deployment fails, the release will not be created

### Troubleshooting

**Issue:** Deployment fails at SSH connection

- **Solution:** Verify server secrets are correctly configured

**Issue:** Version tag already exists

- **Solution:** Manually delete the tag or increment the version scheme

**Issue:** Permission denied when creating release

- **Solution:** Ensure the workflow has `contents: write` permission

## Close Issues from Non-Maintainers Workflow

**File:** `.github/workflows/close-non-maintainer-issues.yml`

**Trigger:** When a new issue is opened (`issues: opened`)

### Purpose

This project follows a **PR-first** contribution model. Maintainers manage the issue tracker internally; external contributors are encouraged to submit changes directly as Pull Requests. This workflow enforces that policy by automatically closing issues opened by users who are not repository maintainers (owners, org members, or collaborators) and leaving a comment directing them to open a Pull Request instead.

**What to contribute via PR:**

- Bug fixes
- New features or improvements
- Documentation updates
- Any other code or content changes

### How it works

1. Checks the `author_association` of the issue creator from the GitHub event payload (no extra API calls needed).
2. Allows issues from users with `OWNER`, `MEMBER`, or `COLLABORATOR` association.
3. For all other users, it:
   - Leaves a friendly comment explaining that issues are not accepted from external contributors and asking them to open a PR directly.
   - Closes the issue automatically.

### Allowed roles

| `author_association`                              | Description                            | Allowed to open issues              |
| ------------------------------------------------- | -------------------------------------- | ----------------------------------- |
| `OWNER`                                           | Repository owner                       | ✅ Yes                              |
| `MEMBER`                                          | Organization member                    | ✅ Yes                              |
| `COLLABORATOR`                                    | Outside collaborator with write access | ✅ Yes                              |
| `CONTRIBUTOR` / `FIRST_TIME_CONTRIBUTOR` / `NONE` | External user                          | ❌ No — asked to open a PR directly |

---

## PR Review Reminder Workflow

**File:** `.github/workflows/pr-review-reminder.yml`

**Triggers:**

- When a PR review is submitted (`pull_request_review: submitted`)
- Every 6 hours via cron schedule
- Manual trigger via workflow_dispatch

### Purpose

This workflow automatically notifies maintainers when a PR has only been reviewed by bots (like CodeRabbit AI) and no human review has occurred within a specified time threshold (default: 24 hours). It helps ensure that PRs don't get overlooked when they need human attention.

### Features

✅ Detects PRs with only bot reviews
✅ Automatically requests maintainer reviews
✅ Posts notification comments tagging maintainers
✅ Runs every 6 hours + on PR review events
✅ **No labels required** - uses comment tracking instead
✅ **Zero setup required** - works out of the box
✅ **Skips draft PRs** - only processes ready-for-review PRs

### Configuration

Current settings in the workflow:

- **Maintainers:** A1L13N
- **Time threshold:** 24 hours
- **Check frequency:** Every 6 hours
- **Tracking method:** Comment history (no labels needed)
- **Exempt bots:** coderabbitai[bot], github-actions[bot], dependabot[bot], copilot[bot], github-copilot[bot], copilot-swe-agent[bot]

### How It Works

1. **Triggers:**
   - When any PR review is submitted
   - Every 6 hours via cron schedule
   - Manual trigger from Actions tab

2. **For each open PR, checks:**
   - Is it older than the time threshold (default 24 hours)?
   - Is it not a draft PR?
   - Has it received no human reviews or comments?
   - Have we already posted a notification? (checks comment history)

3. **If yes to all above:**
   - Posts comment mentioning maintainers (with hidden tracking marker)
   - Requests reviews from maintainers

4. **Prevents spam:**
   - Won't notify same PR twice (detects previous notification comments)
   - Skips PRs with human comments/reviews
   - Skips draft PRs

### Manual Testing

1. Go to the [Actions](../../actions) tab in GitHub
2. Select "PR Review Reminder" workflow
3. Click "Run workflow"
4. Set "hours_threshold" to `0` (for immediate testing)
5. Click "Run workflow"
6. Check logs in Actions tab

### Customization

To add more maintainers, edit the `MAINTAINERS` environment variable:

```yaml
MAINTAINERS: "A1L13N,maintainer2,maintainer3"
```

To change the time threshold, edit the `DEFAULT_HOURS_THRESHOLD` environment variable:

```yaml
DEFAULT_HOURS_THRESHOLD: 48 # Change to 48 hours
```

### Permissions

The workflow requires:

- `pull-requests: write` - To request reviews
- `issues: write` - To post comments
- `contents: read` - To read repository data

---

## Other Workflows

### Label Issues by Creation Date Workflow

**File:** `.github/workflows/label-issues-by-date.yml`

**Triggers:**

- Daily at midnight UTC (scheduled)
- Manual trigger via workflow_dispatch

**Purpose:** Automatically labels issues with their creation date in YYYY-MM format (e.g., 2024-01, 2024-02).

**Features:**

- Processes all issues (both open and closed) in the repository
- Creates date labels automatically if they don't exist
- Uses color-coded labels based on the month
- Skips issues that already have a date label
- Skips pull requests (only processes issues)
- Runs daily to label new issues automatically

**How it works:**

1. Fetches all issues from the repository
2. Extracts the creation date of each issue
3. Formats the date as YYYY-MM (e.g., 2024-12)
4. Creates the label if it doesn't exist with a month-specific color
5. Adds the label to the issue

**Manual Trigger:**

1. Go to the [Actions](../../actions) tab in GitHub
2. Select "Label Issues by Creation Date" workflow
3. Click "Run workflow"
4. Click "Run workflow" button

**Use Cases:**

- Track when issues were created
- Filter and organize issues by time period
- Generate reports based on issue creation dates
- Monitor issue trends over time

### Test Workflow

**File:** `.github/workflows/test.yml`

- Runs linting checks
- Executes unit tests
- Performs security scans

### Pre-commit Workflow

**File:** `.github/workflows/pre-commit.yml`

- Validates code formatting
- Checks code quality

### CodeQL Workflow

**File:** `.github/workflows/codeql.yml`

- Performs security analysis
- Detects vulnerabilities

### Check Migrations Workflow

**File:** `.github/workflows/check-migrations.yml`

- Validates Django migrations
- Checks for migration conflicts

---

For more information about GitHub Actions, see the [GitHub Actions documentation](https://docs.github.com/en/actions).
