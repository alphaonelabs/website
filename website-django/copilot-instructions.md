# GitHub Copilot Instructions for Alpha One Labs Education Platform

## Pre-commit Hooks - Critical Requirements

**IMPORTANT**: All code changes MUST pass pre-commit hooks before being committed. Pre-commit hooks are automatically run before each commit to ensure code quality and consistency.

### Running Pre-commit Hooks

Before committing any changes, ALWAYS run:

```bash
poetry run pre-commit run --all-files
```

Or for specific files:

```bash
poetry run pre-commit run --files <file_path>
```

### Pre-commit Hook Configuration

Our project uses the following pre-commit hooks that MUST pass:

#### 1. Code Formatting (Auto-fixing)

- **black** (Python formatter): Formats Python code with 120 character line length
- **isort** (Python import sorter): Organizes Python imports alphabetically with black profile
- **djlint** (Django template formatter): Formats HTML/Django templates with 120 character line length
- **mixed-line-ending**: Ensures consistent LF line endings

#### 2. Code Quality Checks (Must Pass)

- **trailing-whitespace**: No trailing whitespace allowed
- **end-of-file-fixer**: Files must end with a newline
- **flake8** (Python linter): Python code must pass linting with max line length 120
- **check-yaml**: YAML files must be valid
- **check-json**: JSON files must be valid
- **check-toml**: TOML files must be valid
- **check-xml**: XML files must be valid
- **check-merge-conflict**: No merge conflict markers
- **detect-private-key**: No private keys or secrets in code
- **check-added-large-files**: No large files added to repository

#### 3. Django-Specific Checks

- **django-collectstatic**: Static files must be collected successfully
- **django-test**: All Django tests must pass before commit

### Code Style Guidelines

When generating or modifying code, ensure compliance with:

#### Python Code

- Follow PEP 8 guidelines
- Use Black formatting with 120 character line length
- Sort imports with isort using black profile
- Pass flake8 linting checks
- Maximum line length: 120 characters
- Use type hints where appropriate
- Add docstrings to functions, classes, and modules

Example:

```python
from typing import Optional

from django.db import models


class ExampleModel(models.Model):
    """Example model with proper formatting."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def get_display_name(self) -> str:
        """Return the display name for this model."""
        return self.name.strip().title()
```

#### HTML/Django Templates

- Use djlint formatting with 120 character line length
- Always use Tailwind CSS classes for styling (never custom CSS or inline styles)
- Include dark mode variants using `dark:` prefix
- Ensure proper HTML structure and accessibility
- Follow project color scheme:
  - Primary: `teal-300`
  - Secondary: `gray-600`
  - Success: `green-600`
  - Warning: `yellow-600`
  - Danger: `red-600`

Example:

```html
<div class="container mx-auto px-4">
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">{{ title }}</h2>
        <p class="text-gray-600 dark:text-gray-300">{{ description }}</p>
        <button class="bg-teal-300 hover:bg-teal-400 text-white px-6 py-2 rounded-lg transition duration-200">
            Click Me
        </button>
    </div>
</div>
```

#### JavaScript Code

- Follow project JavaScript style
- Use modern ES6+ syntax
- Ensure Alpine.js compatibility where used
- No trailing semicolons unless required

### Installation and Setup

Before starting development, ensure pre-commit is installed:

```bash
# Install Poetry dependencies (includes pre-commit)
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# (Optional) Update hooks to latest versions
poetry run pre-commit autoupdate
```

### Common Pre-commit Failures and Fixes

#### Black Formatting Issues

If black fails, it usually auto-fixes the code. Just stage the changes:

```bash
git add <file>
```

#### Isort Import Issues

isort will automatically sort imports. Stage the changes after it runs:

```bash
git add <file>
```

#### Flake8 Linting Errors

Common flake8 errors and fixes:

- `E501`: Line too long - Break line at 120 characters
- `F401`: Module imported but unused - Remove unused imports
- `E302`: Expected 2 blank lines - Add blank lines between top-level definitions
- `W503`: Line break before binary operator - Acceptable with Black

#### djlint Template Issues

djlint will auto-format templates. Common issues:

- Inconsistent indentation - Will be auto-fixed
- Long lines - Will be auto-fixed to wrap at 120 characters

#### Django Test Failures

If Django tests fail:

1. Run tests manually to see detailed output:
   ```bash
   poetry run python manage.py test --verbosity=2
   ```
2. Fix failing tests before committing
3. Ensure new code has appropriate test coverage

### Working with Pre-commit

#### Skip Pre-commit (Emergency Only)

Only in extreme circumstances, you can skip pre-commit:

```bash
git commit --no-verify -m "message"
```

**WARNING**: This should NEVER be used for normal development. PRs with failed pre-commit checks will be rejected.

#### Pre-commit in CI/CD

GitHub Actions automatically runs pre-commit checks on all PRs. Ensure local pre-commit passes before pushing to avoid CI failures.

### File Locations Reference

- Settings: `web/settings.py`
- URLs: `web/urls.py`
- Views: `web/views.py`
- Models: `web/models.py`
- Admin: `web/admin.py`
- Tests: `tests/` folder
- Templates: `web/templates/`
- Static files: `static/`

### Additional Resources

- [Pre-commit Configuration](.pre-commit-config.yaml)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [README](../README.md)
- [Django Documentation](https://docs.djangoproject.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

### Summary Checklist

Before suggesting or committing code changes:

- [ ] Code follows Black formatting (120 char line length)
- [ ] Imports are sorted with isort
- [ ] HTML templates use Tailwind CSS only (no custom CSS)
- [ ] HTML templates include dark mode variants
- [ ] Code passes flake8 linting
- [ ] No trailing whitespace
- [ ] Files end with newline
- [ ] No secrets or private keys in code
- [ ] YAML/JSON/TOML files are valid
- [ ] Django tests pass
- [ ] Static files collect successfully
- [ ] Line endings are LF (Unix style)

**Remember**: Running `poetry run pre-commit run --all-files` is the single command that validates all of the above!
