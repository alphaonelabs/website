
"""Regression tests for language-prefixed URL redirects."""

import pytest

from tests.helpers import MockRequest, load_worker

worker = load_worker()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/es", "/"),
        ("/es/", "/"),
        ("/en", "/"),
        ("/fr/courses", "/activity"),
        ("/fr/courses/", "/activity"),
        ("/de/images/x.png", "/images/x.png"),
        ("/de/js/app.js", "/js/app.js"),
        ("/zh/partials/nav.html", "/partials/nav.html"),
        ("/en/media/image.png", "/media/image.png"),
        ("/xx/foo", None),
        ("/ES/about", "/about"),
        ("/about", None),
        ("/english/about", None),
        ("", None),
        ("/en/about.html", "/about"),
        ("/es/signup", "/login?tab=register"),
        ("/en/courses/python", "/activity/python"),
        ("/fr/course/python", "/activity/python"),
        ("/de/classes/python", "/activity/python"),
        ("/en/study-groups/python", "/activity/python"),
        ("/en/study-group/python", "/activity/python"),
        ("/es/features", "/feature-votes"),
        ("/es/legacy-features", "/feature-votes"),
        ("/fr/activity/example", "/activity/example"),
        ("/de/memes/example", "/memes/example"),
        ("/en/nonexistent-page", ""),
    ],
)
def test_language_prefixed_target(path, expected):
    """Language prefixes resolve to the existing canonical routes."""
    assert worker._language_prefixed_target(path) == expected


@pytest.mark.parametrize(
    ("request_url", "target", "expected"),
    [
        (
            "https://example.com/es/about",
            "/about",
            "https://example.com/about",
        ),
        (
            "https://example.com/es/signup?ref=home",
            "/login?tab=register",
            "https://example.com/login?tab=register&ref=home",
        ),
        (
            "https://example.com/fr/courses?sort=new",
            "/activity",
            "https://example.com/activity?sort=new",
        ),
        (
            "https://example.com/es/signup",
            "/login?tab=register",
            "https://example.com/login?tab=register",
        ),
        (
            "https://example.com/es",
            "",
            "https://example.com/",
        ),
        (
            "https://example.com/es/about?x=1",
            "/about",
            "https://example.com/about?x=1",
        ),
    ],
)
def test_redirect_to_current_route(request_url, target, expected):
    """Redirects preserve and merge URL query parameters."""
    request = MockRequest(url=request_url)

    response = worker._redirect_to_current_route(request, target)

    assert response.status == 302
    assert response.headers["Location"] == expected
