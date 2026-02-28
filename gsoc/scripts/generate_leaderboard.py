import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_START_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
DEFAULT_OUTPUT_PATH = "data/leaderboard.json"
# One-time 2025 generation command:
# python scripts/generate_leaderboard.py --start-date 2024-09-01 \
# --end-date 2025-06-01 --output data/leaderboard-2025.json
REPO_CANDIDATES = [
    ("alphaonelabs", "alphaonelabs-education-website"),
    ("AlphaOneLabs", "education-website"),
]
MAX_CLOSED_PAGES = 10
MAX_OPEN_PAGES = 5
PER_PAGE = 100
DELAY_SECONDS = 0.35


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


def fetch_pull_page(state: str, page: int):
    not_found_count = 0

    for owner, repo in REPO_CANDIDATES:
        query = urllib.parse.urlencode(
            {
                "state": state,
                "per_page": PER_PAGE,
                "page": page,
            }
        )
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "alphaonelabs-leaderboard-generator",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                not_found_count += 1
                continue

            if error.code == 403:
                remaining = (
                    error.headers.get("x-ratelimit-remaining")
                    if error.headers
                    else None
                )
                if remaining == "0":
                    raise RuntimeError(
                        "GitHub API rate limit reached. Please try later."
                    )
                raise RuntimeError(
                    "GitHub API access is temporarily restricted (403)."
                ) from error

            raise RuntimeError(f"GitHub API error: {error.code}") from error
        except urllib.error.URLError as error:
            raise RuntimeError("Unable to fetch contributor data.") from error

    if not_found_count == len(REPO_CANDIDATES):
        raise RuntimeError("Configured GitHub repository not found.")


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
    value: datetime, start_date: datetime, end_date: Optional[datetime]
):
    if not value or value < start_date:
        return False
    if end_date and value >= end_date:
        return False
    return True


def build_leaderboard(start_date: datetime, end_date: datetime):
    contributor_stats = {}

    closed_prs = []
    for page in range(1, MAX_CLOSED_PAGES + 1):
        rows = fetch_pull_page("closed", page)
        if not isinstance(rows, list) or len(rows) == 0:
            break
        closed_prs.extend(rows)
        time.sleep(DELAY_SECONDS)

    for pr in closed_prs:
        user = pr.get("user")
        if (
            not user
            or not user.get("login")
            or should_exclude(user.get("login"))
        ):
            continue

        merged_at = parse_github_date(pr.get("merged_at"))
        closed_at = parse_github_date(pr.get("closed_at"))
        relevant_date = merged_at or closed_at
        if not is_within_date_range(relevant_date, start_date, end_date):
            continue

        ensure_contributor(contributor_stats, user)
        if merged_at:
            contributor_stats[user["login"]]["merged_pr_count"] += 1
        else:
            contributor_stats[user["login"]]["closed_pr_count"] += 1

    open_prs = []
    for page in range(1, MAX_OPEN_PAGES + 1):
        rows = fetch_pull_page("open", page)
        if not isinstance(rows, list) or len(rows) == 0:
            break
        open_prs.extend(rows)
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


def main():
    args = parse_args()
    contributors = build_leaderboard(args.start_date, args.end_date)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "start_date": args.start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contributors": contributors,
    }

    if args.end_date:
        payload["end_date"] = args.end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    main()
