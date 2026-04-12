"""
Tests for utility functions: new_id(), _clean_path(), capture_exception().
"""

import re
from tests.helpers import load_worker

worker = load_worker()


# ---------------------------------------------------------------------------
# new_id()
# ---------------------------------------------------------------------------

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class TestNewId:
    def test_returns_string(self):
        assert isinstance(worker.new_id(), str)

    def test_uuid_v4_format(self):
        uid = worker.new_id()
        assert UUID_RE.match(uid), f"Not a valid UUID v4: {uid!r}"

    def test_version_nibble_is_4(self):
        uid = worker.new_id()
        # 13th character (0-indexed: 14) must be '4'
        assert uid[14] == "4"

    def test_variant_bits(self):
        uid = worker.new_id()
        # 17th character (index 19) must be 8, 9, a, or b
        assert uid[19] in "89ab"

    def test_uniqueness(self):
        ids = {worker.new_id() for _ in range(500)}
        assert len(ids) == 500, "new_id() produced duplicate IDs"

    def test_length(self):
        assert len(worker.new_id()) == 36


# ---------------------------------------------------------------------------
# _clean_path()
# ---------------------------------------------------------------------------

class TestCleanPath:
    def test_empty_string_returns_default(self):
        assert worker._clean_path("") == "/admin"

    def test_none_equivalent_returns_default(self):
        assert worker._clean_path("   ") == "/admin"

    def test_slash_passes_through(self):
        assert worker._clean_path("/") == "/"

    def test_simple_path(self):
        assert worker._clean_path("/admin") == "/admin"

    def test_trailing_slash_stripped(self):
        assert worker._clean_path("/admin/") == "/admin"

    def test_double_slashes_collapsed(self):
        # Note: urlparse("//x//y") treats "x" as netloc; this tests the
        # regex substitution on paths that don't have a netloc component.
        assert worker._clean_path("/admin//panel") == "/admin/panel"

    def test_no_leading_slash_is_added(self):
        assert worker._clean_path("admin").startswith("/")

    def test_custom_default(self):
        assert worker._clean_path("", default="/dashboard") == "/dashboard"

    def test_full_url_extracts_path(self):
        # urlparse extracts the path component
        result = worker._clean_path("http://example.com/my/path")
        assert result == "/my/path"

    def test_long_path_preserved(self):
        path = "/a/b/c/d/e/f"
        assert worker._clean_path(path) == path

    def test_whitespace_stripped(self):
        assert worker._clean_path("  /admin  ") == "/admin"


# ---------------------------------------------------------------------------
# capture_exception()
# ---------------------------------------------------------------------------

class TestCaptureException:
    def test_does_not_raise_without_request(self):
        # Should never propagate exceptions
        try:
            worker.capture_exception(ValueError("oops"), where="test")
        except Exception:
            pytest.fail("capture_exception raised unexpectedly")

    def test_does_not_raise_with_mock_request(self):
        from tests.helpers import MockRequest
        req = MockRequest(method="POST", url="http://localhost/api/register")
        try:
            worker.capture_exception(RuntimeError("bad"), req=req, where="test")
        except Exception:
            pytest.fail("capture_exception raised unexpectedly with request")

    def test_handles_exception_with_no_traceback(self):
        exc = ValueError("no traceback")
        try:
            worker.capture_exception(exc)
        except Exception:
            pytest.fail("capture_exception raised unexpectedly")
