# Contributing to OSS Project Management

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Wrangler CLI
- Cloudflare account (for testing)
- GitHub account

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/your-username/alphaonelabs-oss-project-management.git
cd alphaonelabs-oss-project-management
```

2. **Install dependencies**

```bash
npm install
```

3. **Set up local D1 database**

```bash
# Create local database for testing
wrangler d1 create oss-pm-db-dev

# Initialize schema
wrangler d1 execute oss-pm-db-dev --local --file=./schema.sql
```

4. **Configure environment**

Copy `.env.example` to `.dev.vars` and fill in your development credentials:

```bash
cp .env.example .dev.vars
# Edit .dev.vars with your GitHub OAuth app credentials
```

5. **Run development server**

```bash
npm run dev
```

The local server will be available at `http://localhost:8787`

## Project Structure

```
├── src/
│   ├── index.js      # Main worker entry point
│   ├── auth.js       # OAuth authentication
│   ├── api.js        # API endpoint handlers
│   ├── github.js     # GitHub API client
│   ├── webhook.js    # Webhook handler
│   ├── metrics.js    # Analytics and metrics
│   └── ui.js         # Frontend UI
├── schema.sql        # D1 database schema
├── wrangler.toml     # Cloudflare Workers config
├── package.json      # Node dependencies
└── requirements.txt  # Python dependencies (reference)
```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/alphaonelabs/alphaonelabs-oss-project-management/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Environment details (browser, OS)

### Suggesting Features

1. Check [Issues](https://github.com/alphaonelabs/alphaonelabs-oss-project-management/issues) for similar suggestions
2. Create a new issue with:
   - Clear title and description
   - Use case and benefits
   - Proposed implementation (if applicable)
   - Mock-ups or examples (if applicable)

### Submitting Changes

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
   - Follow the coding style (see below)
   - Write clear, concise commit messages
   - Add comments for complex logic
   - Update documentation if needed

3. **Test your changes**

```bash
# Run local development server
npm run dev

# Test in browser
# Verify all features work as expected
```

4. **Commit your changes**

```bash
git add .
git commit -m "feat: Add your feature description"
```

Use conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

5. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

6. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template
   - Link related issues

## Coding Standards

### JavaScript Style

- Use ES6+ features (const, let, arrow functions, async/await)
- Use 2 spaces for indentation
- Use single quotes for strings
- Add semicolons
- Use descriptive variable and function names
- Add JSDoc comments for functions

Example:

```javascript
/**
 * Fetch issues from GitHub API
 * @param {string} owner - Repository owner
 * @param {string} repo - Repository name
 * @param {string} accessToken - GitHub access token
 * @returns {Promise<Array>} Array of issues
 */
async function fetchIssues(owner, repo, accessToken) {
  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': 'application/vnd.github.v3+json'
    }
  });
  return response.json();
}
```

### SQL Style

- Use uppercase for SQL keywords
- Use snake_case for table and column names
- Add appropriate indexes
- Use meaningful constraint names

Example:

```sql
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_issues_state ON issues(state);
```

### Frontend Style

- Keep UI code in ui.js
- Use semantic HTML
- Follow BEM naming for CSS classes (if adding)
- Make UI responsive
- Ensure accessibility (ARIA labels, keyboard navigation)

## Testing Checklist

Before submitting a PR, ensure:

- [ ] Code runs without errors
- [ ] OAuth flow works correctly
- [ ] Issue listing and filtering work
- [ ] Sorting works in both directions
- [ ] Bulk operations work correctly
- [ ] Metrics display correctly
- [ ] Webhook sync works (if modified)
- [ ] UI is responsive on mobile
- [ ] No console errors
- [ ] Documentation is updated

## Documentation

When adding new features:

1. Update README.md if it changes setup/usage
2. Update API.md if it changes API endpoints
3. Update DEPLOYMENT.md if it changes deployment process
4. Add inline code comments for complex logic
5. Update this CONTRIBUTING.md if it changes contribution process

## Areas for Contribution

Good areas to contribute:

### Features
- Additional bulk operations (add/remove labels, assign users)
- Custom filters and saved views
- Export functionality (CSV, JSON)
- Advanced analytics visualizations
- Issue templates
- Multi-repository dashboard
- Markdown rendering for issue bodies

### Improvements
- Performance optimizations
- Better error handling
- Enhanced UI/UX
- Mobile responsiveness
- Accessibility improvements
- Security enhancements

### Documentation
- Tutorial videos
- Example use cases
- Troubleshooting guides
- API usage examples
- Deployment automation scripts

### Infrastructure
- CI/CD pipeline
- Automated testing
- Code quality tools
- Monitoring and logging

## Questions?

If you have questions:

1. Check the [README](README.md) and [DEPLOYMENT](DEPLOYMENT.md) guides
2. Search existing [Issues](https://github.com/alphaonelabs/alphaonelabs-oss-project-management/issues)
3. Create a new issue with the "question" label
4. Join discussions in existing issues and PRs

## Recognition

Contributors will be:
- Listed in the project README
- Mentioned in release notes
- Appreciated in our community

Thank you for contributing to OSS Project Management! 🚀
