# PR Review Reminder Workflow Setup

## Overview

This workflow automatically notifies maintainers when a PR has only been reviewed by CodeRabbit AI and no human review has occurred within 24 hours.

## Features

✅ Detects PRs with only CodeRabbit reviews
✅ Automatically requests maintainer reviews
✅ Posts notification comments tagging maintainers
✅ Runs every 6 hours + on PR review events
✅ **No labels required** - uses comment tracking instead
✅ **Zero setup required** - works out of the box

## Maintainer Action Required

🎉 **NONE!** This workflow is ready to use immediately. No label creation or setup needed

## Configuration

Current settings in the workflow:

- **Maintainers:** A1L13N
- **Time threshold:** 24 hours
- **Check frequency:** Every 6 hours
- **Tracking method:** Comment history (no labels needed)

### To Add More Maintainers

Edit `.github/workflows/pr-review-reminder.yml` line 26:

```yaml
MAINTAINERS: "A1L13N,maintainer2,maintainer3"
```

### To Change Time Threshold

Edit `.github/workflows/pr-review-reminder.yml` line 29:

```yaml
DEFAULT_HOURS_THRESHOLD: 48 # Change to 48 hours
```

## How It Works

1. **Triggers:**
   - When any PR review is submitted
   - Every 6 hours via cron schedule
   - Manual trigger from Actions tab

2. **For each open PR, checks:**
   - Is it older than 24 hours?
   - Has it only been reviewed by CodeRabbit?
   - Have we already posted a notification? (checks comment history)

3. **If yes to all above:**
   - Posts comment mentioning maintainers (with hidden tracking marker)
   - Requests reviews from maintainers

4. **Prevents spam:**
   - Won't notify same PR twice (detects previous notification comments)
   - Skips PRs with human comments/reviews

## Testing

### Manual Test

1. Go to: Actions → PR Review Reminder → Run workflow
2. Set "hours_threshold" to `0` (for immediate testing)
3. Click "Run workflow"
4. Check logs in Actions tab

### Live Test

1. Create a test PR
2. Wait for CodeRabbit to review
3. Wait for scheduled run (or trigger manually)
4. Verify notification comment appears

## Monitoring

Check workflow runs in the **Actions** tab:

- ✅ Green check = workflow ran successfully
- ❌ Red X = check logs for errors
- 🟡 Yellow dot = workflow is running

Common issues:

- **No PRs notified:** All PRs have human reviewers or are too recent
- **Permission denied:** Repository needs to grant Actions write permissions
- **Duplicate notifications:** Shouldn't happen (comment tracking prevents this)

## Permissions

The workflow requires:

- `pull-requests: write` - To request reviews
- `issues: write` - To post comments
- `contents: read` - To read repository data

These are configured in the workflow file and should work with default `GITHUB_TOKEN`.

## Support

If you encounter issues:

1. Check the workflow logs in Actions tab
2. Ensure maintainer usernames are correct
3. Check repository permissions for GitHub Actions
4. Verify CodeRabbit bot username is correct (`coderabbitai[bot]`)

---

**Ready to merge!** 🚀 The workflow requires zero setup and will work immediately upon merge.
