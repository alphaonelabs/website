import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


# Safety limits for GitHub Search pagination.
# GitHub Search API caps results at 1000 (10 pages at 100 per page).
MAX_CLOSED_PAGES = 10
MAX_OPEN_PAGES = 5


DEFAULT_START_DATE = datetime(2025, 9, 1, tzinfo=timezone.utc)
# Each GSoC year's contribution season runs from September 1 of the year before.
SEASONS = {
    "2027": (datetime(2026, 9, 1, tzinfo=timezone.utc), datetime(2027, 9, 1, tzinfo=timezone.utc)),
    "2026": (datetime(2025, 9, 1, tzinfo=timezone.utc), datetime(2026, 9, 1, tzinfo=timezone.utc)),
    "2025": (datetime(2024, 9, 1, tzinfo=timezone.utc), datetime(2025, 9, 1, tzinfo=timezone.utc)),
}
CURRENT_SEASON = "2027"
# On 2026-11-01 every open Django PR was closed when the site moved to the
# monorepo. Those closures say nothing about the contributor, so skip them.
MIGRATION_CLOSE_DAY = "2026-11-01"
LEGACY_PATH = Path(__file__).resolve().parent.parent / "data" / "legacy-merges.json"
DEFAULT_OUTPUT_PATH = "data/leaderboard.json"
GITHUB_ORG = "alphaonelabs"


def format_query_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def build_search_query(
    org: str,
    state: str,
    start_date: datetime,
    end_date: Optional[datetime],
    date_field: str,
) -> str:
    terms = [
        f"org:{org}",
        "is:pr",
        f"state:{state}",
        f"{date_field}:>={format_query_date(start_date)}",
    ]
    if end_date:
        terms.append(f"{date_field}:<{format_query_date(end_date)}")
    return " ".join(terms)


def fetch_search_pulls(query_text: str, page: int):
    time.sleep(DELAY_SECONDS)
    query = urllib.parse.urlencode(
        {
            "q": query_text,
            "sort": "updated",
            "order": "desc",
            "per_page": PER_PAGE,
            "page": page,
        }
    )
    url = f"https://api.github.com/search/issues?{query}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "alphaonelabs-leaderboard-generator",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("items", [])
    except urllib.error.HTTPError as error:
        if error.code == 403:
            remaining = (
                error.headers.get("x-ratelimit-remaining")
                if error.headers
                else None
            )
            if remaining == "0":
                raise RuntimeError("GitHub API rate limit reached. Please try later.")
            raise RuntimeError("GitHub API access is temporarily restricted (403).") from error
        if error.code == 422:
            raise RuntimeError(
                "GitHub search query exceeded API limits. Narrow the date range."
            ) from error
        raise RuntimeError(f"GitHub API error: {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError("Unable to fetch contributor data.") from error


PER_PAGE = 100
# The search API allows 30 requests a minute; three seasons need many pages.
DELAY_SECONDS = 2.2


def parse_cli_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD format."
        ) from error


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate contributor leaderboard data from GitHub PRs."
    )
    parser.add_argument(
        "--start-date",
        type=parse_cli_date,
        default=DEFAULT_START_DATE,
        help="Inclusive UTC date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        type=parse_cli_date,
        default=None,
        help="Exclusive UTC date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSON file path.",
    )

    args = parser.parse_args()
    if args.end_date and args.end_date <= args.start_date:
        parser.error("--end-date must be greater than --start-date")
    return args


def should_exclude(username: str) -> bool:
    normalized = str(username or "").lower()
    return (
        "[bot]" in normalized
        or "dependabot" in normalized
        or "copilot" in normalized
        or normalized == "a1l13n"
    )


def parse_github_date(value: str):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def calculate_smart_score(item: dict) -> float:
    smart_score = item["merged_pr_count"] * 10

    if item["closed_pr_count"] > (item["merged_pr_count"] / 2):
        smart_score -= (
            item["closed_pr_count"] - (item["merged_pr_count"] / 2)
        ) * 2

    if item["open_pr_count"] > item["merged_pr_count"]:
        smart_score -= item["open_pr_count"] - item["merged_pr_count"]

    return smart_score





def ensure_contributor(stats: dict, user: dict):
    username = user["login"]
    if username not in stats:
        stats[username] = {
            "username": username,
            "avatar_url": user.get("avatar_url"),
            "profile_url": user.get("html_url"),
            "merged_pr_count": 0,
            "closed_pr_count": 0,
            "open_pr_count": 0,
            "total_pr_count": 0,
            "smart_score": 0,
        }


def is_within_date_range(
    value: Optional[datetime], start_date: datetime, end_date: Optional[datetime]
):
    if value is None or value < start_date:
        return False
    if end_date and value >= end_date:
        return False
    return True


def build_leaderboard(start_date: datetime, end_date: Optional[datetime]):
    contributor_stats = {}

    closed_query = build_search_query(
        GITHUB_ORG,
        "closed",
        start_date,
        end_date,
        "closed",
    )

    closed_prs = []
    page = 1
    while page <= MAX_CLOSED_PAGES:
        rows = fetch_search_pulls(closed_query, page)
        if not isinstance(rows, list) or len(rows) == 0:
            break
        closed_prs.extend(rows)
        if len(rows) < PER_PAGE:
            break
        page += 1
        time.sleep(DELAY_SECONDS)

    for pr in closed_prs:
        user = pr.get("user")
        if (
            not user
            or not user.get("login")
            or should_exclude(user.get("login"))
        ):
            continue

        merged_at = parse_github_date(pr.get("pull_request", {}).get("merged_at"))
        closed_at = parse_github_date(pr.get("closed_at"))
        relevant_date = merged_at or closed_at
        if not is_within_date_range(relevant_date, start_date, end_date):
            continue

        if not merged_at and closed_at and closed_at.strftime("%Y-%m-%d") == MIGRATION_CLOSE_DAY:
            continue

        ensure_contributor(contributor_stats, user)
        if merged_at:
            contributor_stats[user["login"]]["merged_pr_count"] += 1
        else:
            contributor_stats[user["login"]]["closed_pr_count"] += 1

    open_query = build_search_query(
        GITHUB_ORG,
        "open",
        start_date,
        end_date,
        "created",
    )

    open_prs = []
    page = 1
    while page <= MAX_OPEN_PAGES:
        rows = fetch_search_pulls(open_query, page)
        if not isinstance(rows, list) or len(rows) == 0:
            break
        open_prs.extend(rows)
        if len(rows) < PER_PAGE:
            break
        page += 1
        time.sleep(DELAY_SECONDS)

    for pr in open_prs:
        user = pr.get("user")
        if (
            not user
            or not user.get("login")
            or should_exclude(user.get("login"))
        ):
            continue

        created_at = parse_github_date(pr.get("created_at"))
        if not is_within_date_range(created_at, start_date, end_date):
            continue

        ensure_contributor(contributor_stats, user)
        contributor_stats[user["login"]]["open_pr_count"] += 1

    contributors = []
    for item in contributor_stats.values():
        total_pr_count = (
            item["merged_pr_count"]
            + item["closed_pr_count"]
            + item["open_pr_count"]
        )
        item["total_pr_count"] = total_pr_count
        item["smart_score"] = calculate_smart_score(item)
        contributors.append(item)

    contributors.sort(
        key=lambda item: (item["smart_score"], item["merged_pr_count"]),
        reverse=True,
    )
    return contributors


def add_legacy_merges(contributors: list, legacy: dict):
    """Fold in merged PRs from deleted repos that GitHub search can no longer see."""
    by_name = {item["username"].lower(): item for item in contributors}
    for username, merged in legacy.items():
        if should_exclude(username):
            continue
        item = by_name.get(username.lower())
        if item is None:
            item = {
                "username": username,
                "avatar_url": f"https://github.com/{username}.png?size=96",
                "profile_url": f"https://github.com/{username}",
                "merged_pr_count": 0,
                "closed_pr_count": 0,
                "open_pr_count": 0,
            }
            contributors.append(item)
            by_name[username.lower()] = item
        item["merged_pr_count"] += merged
    for item in contributors:
        item["total_pr_count"] = item["merged_pr_count"] + item["closed_pr_count"] + item["open_pr_count"]
        item["smart_score"] = calculate_smart_score(item)
    contributors.sort(key=lambda item: (item["smart_score"], item["merged_pr_count"]), reverse=True)
    return contributors


def main():
    args = parse_args()
    now = datetime.now(timezone.utc)
    stamp = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.start_date != DEFAULT_START_DATE or args.end_date:
        # Custom range: the original single-leaderboard output.
        payload = {"generated_at": stamp(now), "start_date": stamp(args.start_date),
                   "contributors": build_leaderboard(args.start_date, args.end_date)}
        if args.end_date:
            payload["end_date"] = stamp(args.end_date)
    else:
        legacy = json.loads(LEGACY_PATH.read_text()).get("seasons", {}) if LEGACY_PATH.exists() else {}
        seasons = {}
        for year, (start, end) in SEASONS.items():
            if start > now:
                continue
            contributors = build_leaderboard(start, end)
            seasons[year] = {
                "start_date": stamp(start),
                "end_date": stamp(end),
                "contributors": add_legacy_merges(contributors, legacy.get(year, {})),
            }
        payload = {"generated_at": stamp(now), "current": CURRENT_SEASON, "seasons": seasons}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    main()
