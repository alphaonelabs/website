import re
from pathlib import Path

from django.test import SimpleTestCase


class EnvSampleTests(SimpleTestCase):
    def test_env_sample_covers_runtime_environment_variables(self):
        repo_root = Path(__file__).resolve().parents[2]
        env_sample = (repo_root / ".env.sample").read_text(encoding="utf-8")
        settings_source = (repo_root / "web" / "settings.py").read_text(encoding="utf-8")

        sample_variables = {
            line.split("=", 1)[0].strip()
            for line in env_sample.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and "=" in line
        }

        referenced_variables = set(re.findall(r'env\.(?:str|bool|list)\("([A-Z0-9_]+)"', settings_source))
        referenced_variables.update(re.findall(r'os\.getenv\("([A-Z0-9_]+)"', settings_source))
        referenced_variables.update(re.findall(r'os\.environ\.get\("([A-Z0-9_]+)"', settings_source))
        referenced_variables.update({"DATABASE_URL", "SENDGRID_PASSWORD"})

        missing_variables = referenced_variables - sample_variables

        self.assertFalse(
            missing_variables,
            f".env.sample is missing runtime variables: {sorted(missing_variables)}",
        )

    def test_env_sample_does_not_list_unused_debug_flags(self):
        repo_root = Path(__file__).resolve().parents[2]
        env_sample = (repo_root / ".env.sample").read_text(encoding="utf-8")

        self.assertNotIn("DEBUG=", env_sample)
        self.assertNotIn("DJANGO_DEBUG=", env_sample)
