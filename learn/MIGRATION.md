# Migration handoff

Last updated: July 6, 2026

This document is the human-readable migration summary. `audit.md` remains the detailed file-by-file reference, but this file only keeps decisions and follow-up work that still matter.

## Current platform direction

- The Cloudflare Python Worker site is the current product.
- Django, Docker, Ansible, Railway, legacy migrations, and old server runtime files are no longer part of the current app.
- Courses are now first-class `Activity` records.
- Canonical public URLs are clean routes such as `/activity`, `/activity/<slug>`, `/terms`, `/login`, and `/virtual-classroom`.
- Static pages now use a lightweight Jinja-style Worker renderer with `base.html`, `{% block %}`, `{% include %}`, and server data tags.
- The old `/en/...` language-prefixed URLs redirect to current canonical routes where there is an obvious equivalent; otherwise they return a styled 404.

## Completed migration work

- Pulled the legacy site source into `legacy-site-source` for reference.
- Created `audit.md` with the full legacy file inventory, comparable current file, migration status, and owner notes.
- Consolidated older planning docs into the audit and removed the old scattered planning files.
- Imported or preserved core legacy data into the Worker/D1 model where appropriate:
  - Users and encrypted user identity fields.
  - Legacy Django password hash support.
  - Email verification state.
  - Profiles and referral fields.
  - Activities from courses.
  - Sessions, tags, enrollments, interest/waiting room state, carts, checkout sessions, and selected content records.
- Preserved referral program behavior and referral leaderboard surfaces.
- Added cart and checkout support for multiple activities, including guest cart behavior.
- Restored activity list/detail routes and switched detail pages to `/activity/<slug>`.
- Added homepage server-rendered featured activity cards so the top classes appear immediately.
- Added activity images and square image presentation around activity cards/detail surfaces.
- Uploaded generated activity images to the production R2 bucket, linked matching activity rows to `/media/activities/generated/...`, and removed the local generated image assets.
- Added admin routing through `ADMIN_URL` with basic auth handling.
- Restored current header/footer navigation and moved the dropdown-heavy nav inventory into an organized footer.
- Added `base.html` and converted public pages to extend it.
- Added server-rendered data tags for featured activities, activity listings, activity detail preload, waiting rooms, and restored record pages.
- Restored About and Terms content from the legacy templates.
- Added styled 404, 429, and 500 pages.
- Added HTML 500 handling for non-API Worker failures.
- Added account deletion from the profile page through `DELETE /api/profile`.
- Added global password visibility toggles.
- Added scheduled session-reminder cron plumbing in the Worker.
- Added virtual classroom and whiteboard current pages with public viewing and login-required interaction.
- Added a virtual-labs-moved link to Alpha One Labs GitHub.
- Added GSOC 2027 link on the homepage and copied the GSOC logo.
- Moved retained docs/config/assets into the current tree where still useful.
- Removed explicitly obsolete or omitted legacy artifacts from `legacy-site-source`.

## Purposefully omitted

- Merchandise, goods, storefront, and old product-image systems.
- Raw `WebRequest` import.
- Raw `SearchLog` import; only useful current analytics should remain.
- Docker and Ansible deployment systems.
- Django runtime, Django migrations, Django management commands, ASGI/WSGI, and Django templates that only supported removed systems.
- Old standalone video-request/upload pages; videos should be represented as activities.
- Old standalone virtual lab implementation; current page links to the moved/open-source location instead.
- Teams and old team goal pages unless the product decision is reopened.
- Old leaderboards other than the referral leaderboard.

## Needs more testing

These are implemented or partially implemented, but should be tested before the old server is destroyed or before calling the migration finished.

1. Account registration and verification
   - Register a new user.
   - Confirm verification email sends using production Mailgun/SendGrid settings.
   - Verify the email link marks the account verified.
   - Confirm login is blocked before verification and allowed after verification.

2. Forgot-password flow
   - Request reset email.
   - Confirm reset link uses the clean `/reset-password?token=...` page.
   - Set a new password.
   - Confirm old password no longer works and new password works.

3. Profile and account deletion
   - Load profile while logged in.
   - Update profile fields.
   - Toggle public profile and teacher flags.
   - Delete a test account and confirm local auth state clears.
   - Confirm account deletion does not break hosted activities or unrelated records.

4. Activity list and activity detail
   - `/activity` renders useful server-side content before JavaScript runs.
   - `/activity/<slug>` loads the correct activity.
   - Old `/activity.html?slug=...` and `/activity.html?id=...` compatibility still behaves acceptably.
   - Filters, tag cloud, pagination, and detail actions still work after server preloading.

5. Waiting-room and interest flows
   - Activities in waitlist/waiting-room state show interest CTAs.
   - Logged-in users can express interest.
   - Waiting rooms page renders server-side rows.
   - “I want to learn” and “I want to teach” request flows create the expected records.

6. Cart and checkout
   - Anonymous users can add paid activities to cart.
   - Bot-friction fields do not block normal users.
   - Logged-in users can add/remove items.
   - Guest checkout works through Stripe.
   - Logged-in checkout enrolls the user after payment confirmation.
   - Free activities still use the join flow, not checkout.

7. Referral program
   - `/api/referral` returns the correct link and stats.
   - Referral signup attribution works.
   - Referral leaderboard shows imported/current data.
   - `/ref/<code>` redirects to registration with the referral code.

8. Notifications and reminders
   - Notification preferences load and save.
   - Enrollment/session/system notifications are created at the right times.
   - Unread badge works without causing excessive API calls.
   - Scheduled session reminder cron creates in-app reminders.
   - Reminder emails send only when credentials and preferences allow it.

9. Email provider configuration
   - Confirm `.env.production` has all required Mailgun/SendGrid values.
   - Confirm Worker secrets are set in Cloudflare.
   - Confirm failures are logged without leaking secrets.

10. Admin surface
   - `ADMIN_URL` route works in production.
   - Basic auth succeeds.
   - Admin page loads after auth rather than returning 404.
   - Table-count and admin import endpoints remain protected.

11. Virtual classroom and whiteboard
   - Anonymous users can view classroom/presence.
   - Anonymous users cannot interact.
   - Logged-in users can move/interact/chat where supported.
   - Whiteboard connects to the classroom Durable Object.
   - Whiteboard drawing/clear is blocked for anonymous users and works for logged-in users.

12. Clean routes and old links
   - Clean slash routes work for all footer/header links.
   - `.html` compatibility does not create janky redirects.
   - `/en/...` routes redirect when mapped and show the styled 404 when unmapped.
   - Static assets still load through the new `base.html` layout.

13. Restored record pages
   - Forum, blog, study groups, quizzes, surveys, challenges, progress, grade links, calendar, memes, success stories, feature votes, and messages render server-side records.
   - Private pages still require login.
   - Pages do not rely on the old `/api/features` client fetch for first paint.

14. Deployment and CI
   - `run.sh` starts local Worker dev with `.env.production` loaded.
   - GitHub test workflow matches the current Cloudflare Worker project.
   - Pre-commit config is useful and not carrying Django-only checks.
   - Wrangler cron trigger is accepted in production.

## Needs deeper product rebuild

These are not just migration cleanup items. They need product-level implementation choices and should not be marked complete merely because old records are visible.

- Full quiz authoring, taking, grading, analytics, and attempts UI.
- Full survey authoring, response collection, and results UI.
- Forum authoring and thread/reply management.
- Blog authoring and comments.
- Study-group tools around activity-type study groups.
- Grade-link submission and grading workflow.
- Progress tracker/streak/certificate/badge experience.
- Admin analytics and system dashboard parity.
- Social media dashboard parity, if still wanted.
- Secure peer messaging beyond record display.
- Public profile detail pages, if still wanted.
- Membership checkout/settings/success pages, if still wanted.

## Data and environment preservation notes

- `.env.production` is intentionally local and should not be committed.
- `.secrets/` is intentionally local and should not be committed.
- The old server should not be destroyed until the production Worker has every needed secret, D1 data, R2 media, and payment/email configuration verified.
- Legacy media copied to R2 and current `public/images` assets should be checked visually on the live site.
- `legacy-site-source` is now a reference snapshot with removed/omitted junk stripped out; do not treat it as runtime code.

## Suggested final sign-off checklist

- Register, verify email, log in, reset password, and delete a disposable test account.
- Browse `/activity`, open `/activity/<slug>`, join a free activity, express interest in a waitlist activity, and add a paid activity to cart as a guest.
- Complete a Stripe test checkout for guest and logged-in carts.
- Confirm referral signup and leaderboard behavior.
- Open admin through `ADMIN_URL` in production.
- Open every footer link and confirm clean routes or intentional 404 behavior.
- Confirm classroom view/interact permissions with anonymous and logged-in users.
- Confirm scheduled reminders run in Cloudflare and do not duplicate notifications.
