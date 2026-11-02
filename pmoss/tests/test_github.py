from unittest.mock import AsyncMock, patch

import pytest

from github import calculate_time_to_close, fetch_repository_issues


def test_calculate_time_to_close_with_z_timestamps():
    assert calculate_time_to_close(
        "2026-01-01T10:00:00Z",
        "2026-01-01T12:30:00Z",
    ) == 2


def test_calculate_time_to_close_accepts_exactly_two_hours():
    assert calculate_time_to_close(
        "2026-01-01T10:00:00Z",
        "2026-01-01T12:00:00Z",
    ) == 2


def test_calculate_time_to_close_accepts_fractional_hours():
    assert calculate_time_to_close(
        "2026-01-01T10:00:00+00:00",
        "2026-01-01T10:31:00+00:00",
    ) == 1


def test_calculate_time_to_close_preserves_negative_duration():
    assert calculate_time_to_close(
        "2026-01-02T12:00:00Z",
        "2026-01-02T10:00:00Z",
    ) == -2


def test_calculate_time_to_close_rejects_malformed_timestamp():
    with pytest.raises(ValueError):
        calculate_time_to_close("not-a-date", "2026-01-01T12:00:00Z")


@pytest.mark.asyncio
async def test_fetch_repository_issues_filters_pull_requests():
    pages = [
        [
            {"number": 1, "title": "Issue"},
            {"number": 2, "title": "PR", "pull_request": {"url": "https://api.github.com/pulls/2"}},
        ]
    ]

    with patch("github.github_request", new=AsyncMock(side_effect=pages)):
        issues = await fetch_repository_issues("owner", "repo", "token")

    assert issues == [{"number": 1, "title": "Issue"}]


@pytest.mark.asyncio
async def test_fetch_repository_issues_fetches_multiple_pages():
    first_page = [{"number": index, "title": f"Issue {index}"} for index in range(100)]
    second_page = [{"number": 101, "title": "Issue 101"}]

    mock_request = AsyncMock(side_effect=[first_page, second_page])
    with patch("github.github_request", new=mock_request):
        issues = await fetch_repository_issues("owner", "repo", "token", state="open")

    assert len(issues) == 101
    assert issues[-1]["number"] == 101
    assert mock_request.await_count == 2
    assert "page=1" in mock_request.await_args_list[0].args[0]
    assert "page=2" in mock_request.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_fetch_repository_issues_empty_first_page():
    with patch("github.github_request", new=AsyncMock(return_value=[])):
        issues = await fetch_repository_issues("owner", "repo", "token")

    assert issues == []
