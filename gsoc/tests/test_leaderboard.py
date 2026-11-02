from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_leaderboard as leaderboard


@pytest.mark.parametrize(
    ("username", "excluded"),
    [
        ("regular-user", False),
        ("dependabot[bot]", True),
        ("github-actions[bot]", True),
        ("Copilot", True),
        ("A1L13N", True),
    ],
)
def test_should_exclude(username, excluded):
    assert leaderboard.should_exclude(username) is excluded


def test_parse_github_date_accepts_github_timestamp():
    assert leaderboard.parse_github_date("2026-10-31T12:30:45Z") == datetime(
        2026, 10, 31, 12, 30, 45, tzinfo=timezone.utc
    )


@pytest.mark.parametrize("value", [None, "", "not-a-date", "2026-10-31"])
def test_parse_github_date_rejects_invalid_values(value):
    assert leaderboard.parse_github_date(value) is None


def test_calculate_smart_score_with_zero_merged_prs():
    item = {"merged_pr_count": 0, "closed_pr_count": 0, "open_pr_count": 0}
    assert leaderboard.calculate_smart_score(item) == 0


def test_calculate_smart_score_penalizes_closed_prs_when_more_than_half_of_merged():
    item = {"merged_pr_count": 2, "closed_pr_count": 3, "open_pr_count": 0}
    assert leaderboard.calculate_smart_score(item) == 16


def test_calculate_smart_score_penalizes_open_prs_above_merged_count():
    item = {"merged_pr_count": 3, "closed_pr_count": 1, "open_pr_count": 5}
    assert leaderboard.calculate_smart_score(item) == 28


def test_calculate_smart_score_handles_more_closed_than_merged():
    item = {"merged_pr_count": 1, "closed_pr_count": 4, "open_pr_count": 0}
    assert leaderboard.calculate_smart_score(item) == 3


def test_is_within_date_range_includes_start():
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    value = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert leaderboard.is_within_date_range(value, start, None)


def test_is_within_date_range_excludes_end():
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    value = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert not leaderboard.is_within_date_range(value, start, end)


def test_is_within_date_range_rejects_dates_before_start_or_missing_value():
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert not leaderboard.is_within_date_range(
        datetime(2026, 8, 31, tzinfo=timezone.utc), start, None
    )
    assert not leaderboard.is_within_date_range(None, start, None)


def test_add_legacy_merges_matches_usernames_case_insensitively_and_recalculates_totals():
    contributors = [
        {
            "username": "KanishJebaMathewM",
            "merged_pr_count": 2,
            "closed_pr_count": 1,
            "open_pr_count": 1,
        }
    ]

    result = leaderboard.add_legacy_merges(
        contributors, {"kanishjebamathewm": 3}
    )

    assert len(result) == 1
    assert result[0]["username"] == "KanishJebaMathewM"
    assert result[0]["merged_pr_count"] == 5
    assert result[0]["total_pr_count"] == 7
    assert result[0]["smart_score"] == 50


def test_add_legacy_merges_skips_excluded_bot():
    result = leaderboard.add_legacy_merges([], {"LegacyBot[bot]": 99})
    assert result == []


def test_add_legacy_merges_adds_new_user_and_sorts_by_score():
    contributors = [
        {
            "username": "lower-score",
            "merged_pr_count": 1,
            "closed_pr_count": 0,
            "open_pr_count": 0,
        }
    ]

    result = leaderboard.add_legacy_merges(
        contributors, {"higher-score": 5, "lower-score": 2}
    )

    assert [item["username"] for item in result] == ["higher-score", "lower-score"]
