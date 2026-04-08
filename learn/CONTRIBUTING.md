# Contributing to Alpha One Labs Learn

First off, thank you for considering contributing to Alpha One Labs Learn.

This document explains how to contribute effectively to this repository. Following these guidelines helps maintainers review changes faster and keeps contributions consistent across features, bug fixes, and documentation updates.

## Code of Conduct

This project and everyone participating in it is expected to act respectfully and constructively.

If you encounter unacceptable behavior, please open an issue with the maintainers.

## Getting Started

### Prerequisites

Before you begin:

1. Ensure you have a [GitHub account](https://github.com/signup)
2. Read [README.md](README.md) for setup instructions
3. Install required tooling:
   - Node.js (for Wrangler and local static hosting)
   - Wrangler CLI (`npm install -g wrangler`)
   - Cloudflare account access for Workers + D1
4. Familiarize yourself with this repo's stack:
   - Backend: Python on Cloudflare Workers
   - Frontend: Static HTML + Tailwind CSS + vanilla JavaScript
   - Database: Cloudflare D1 (SQLite)

### Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/your-username/learn.git
   cd learn
   ```

3. Create a branch for your change:

   ```bash
   git checkout -b feat/your-change-name
   ```

4. Authenticate Wrangler:

   ```bash
   wrangler login
   ```

5. Create and configure a D1 database if needed:

   ```bash
   wrangler d1 create education_db
   wrangler d1 execute education_db --file=schema.sql
   ```

6. Configure local secrets in `.dev.vars`:

   ```env
   ENCRYPTION_KEY=your-dev-encryption-key
   JWT_SECRET=your-dev-jwt-secret
   ```

## Making Changes

### Coding Standards

We follow these standards in this repository:

1. Python (Worker backend)
   - Follow PEP 8 style where practical
   - Keep handler logic readable and explicit
   - Add concise docstrings for non-trivial functions
   - Prefer clear error handling and consistent API responses

2. JavaScript (frontend behavior)
   - Use modern vanilla JavaScript
   - Keep DOM logic modular and avoid duplicated request logic
   - Guard async actions from duplicate submissions where applicable

3. HTML/Tailwind
   - Use semantic HTML5 structure
   - Keep class usage consistent with existing page patterns
   - Maintain responsive behavior for mobile and desktop

4. Security and privacy
   - Do not log secrets, tokens, or plaintext sensitive data
   - Preserve encryption and authentication behavior
   - Treat auth and enrollment flows as security-sensitive paths

### Documentation

- Update [README.md](README.md) if setup, behavior, or API usage changes
- Add/update inline comments only where logic is genuinely non-obvious
- Keep new docs concise and actionable

### Testing

There is no mandatory automated test suite in this repo yet, so contributors should perform manual validation before opening a PR.

Recommended checks:

1. Run backend locally:

   ```bash
   wrangler dev
   ```

2. Serve frontend locally:

   ```bash
   npx serve public
   ```

3. Verify core flows end-to-end:
   - Register and login
   - Browse activities with filters/search
   - Join an activity
   - Create activity/session from host flow
   - Dashboard loads without errors

4. If schema changes are introduced, verify D1 migration/schema application with `schema.sql`

## Commit Messages

We use Conventional Commits:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Common types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `refactor`: Internal code refactor
- `test`: Test-related changes
- `chore`: Maintenance work

Example:

```text
fix(auth): prevent duplicate submit in login flow

Add in-flight request lock to block repeated login submissions.
Handle button state restoration in finally blocks.

Closes #42
```

## Pull Request Process

1. Keep PR scope focused
   - One clear problem per PR whenever possible

2. Update docs where needed
   - README updates for setup/API behavior changes

3. Validate locally
   - Confirm backend and frontend run cleanly
   - Confirm changed flows work manually

4. Open the PR
   - Use a clear title
   - Explain what changed and why
   - Link related issues
   - Include screenshots or recordings for UI changes

5. Address review feedback
   - Respond to comments promptly
   - Keep discussions technical and constructive

## Merge Expectations

Before merge, PRs should have:

1. Passing local validation for changed flows
2. No unresolved review feedback
3. No merge conflicts
4. Updated documentation when required

## License

By contributing, you agree that your contributions are licensed under the GNU Affero General Public License v3.0 (AGPLv3), consistent with this repository.

## Questions or Need Help?

- Open an issue for bugs and feature requests
- Start a discussion in the PR if you need design direction

Thank you for contributing.
