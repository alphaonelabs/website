import sys

from django.apps import AppConfig
from django.conf import settings


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"

    def ready(self):
        """Import signals when the app is ready."""
        self._patch_django_context_copy_for_python_314_tests()

        import web.signals  # noqa

    @staticmethod
    def _patch_django_context_copy_for_python_314_tests():
        """Patch Django's template context copy logic for Python 3.14 during tests."""
        if not settings.TESTING or sys.version_info < (3, 14):
            return

        from django.template.context import BaseContext

        if getattr(BaseContext.__copy__, "__name__", "") == "_python314_safe_copy":
            return

        def _python314_safe_copy(self):
            duplicate = self.__class__.__new__(self.__class__)
            duplicate.__dict__ = self.__dict__.copy()
            duplicate.dicts = self.dicts[:]
            return duplicate

        BaseContext.__copy__ = _python314_safe_copy
