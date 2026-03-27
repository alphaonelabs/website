#!/usr/bin/env python3
"""Label GitHub issues based on their creation date (YYYY-MM format)."""

import os
import re
import sys
from datetime import datetime

import requests


def create_label_if_not_exists(owner, repo, label_name, headers):
    """Create a label if it doesn't already exist."""
    # Check if label exists
    labels_url = f"https://api.github.com/repos/{owner}/{repo}/labels/{label_name}"
    response = requests.get(labels_url, headers=headers)

    if response.status_code == 404:
        # Label doesn't exist, create it
        create_url = f"https://api.github.com/repos/{owner}/{repo}/labels"
        # Use a color scheme based on the month
        colors = {
            "01": "0E8A16",
            "02": "1D76DB",
            "03": "5319E7",
            "04": "E99695",
            "05": "F9D0C4",
            "06": "FEF2C0",
            "07": "BFD4F2",
            "08": "D4C5F9",
            "09": "C2E0C6",
            "10": "FBCA04",
            "11": "D93F0B",
            "12": "0052CC",
        }
        # Extract month from label (format: YYYY-MM)
        month = label_name.split("-")[1] if "-" in label_name else "01"
        color = colors.get(month, "EDEDED")

        payload = {
            "name": label_name,
            "color": color,
            "description": f"Issues created in {label_name}",
        }
        response = requests.post(create_url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"Created label: {label_name}")
            return True
        else:
            print(f"Failed to create label {label_name}: {response.status_code} - {response.text}")
            return False
    elif response.status_code == 200:
        print(f"Label {label_name} already exists")
        return True
    else:
        print(f"Error checking label {label_name}: {response.status_code}")
        return False


def label_issue_by_date(owner, repo, issue_number, created_at, headers):
    """Add a date label to an issue based on its creation date."""
    # Parse the creation date using ISO 8601 format
    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

    # Format as YYYY-MM
    date_label = created_date.strftime("%Y-%m")

    # Get current labels for the issue
    issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    response = requests.get(issue_url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to get issue #{issue_number}: {response.status_code}")
        return False

    issue_data = response.json()
    current_labels = [label["name"] for label in issue_data.get("labels", [])]

    # Check if the date label is already present
    if date_label in current_labels:
        print(f"Issue #{issue_number} already has label {date_label}")
        return True

    # Check if any other date label exists (format: YYYY-MM using regex)
    existing_date_labels = [label for label in current_labels if re.match(r"^\d{4}-\d{2}$", label)]
    if existing_date_labels:
        print(f"Issue #{issue_number} already has date label(s): {existing_date_labels}")
        return True

    # Create the label if it doesn't exist
    create_label_if_not_exists(owner, repo, date_label, headers)

    # Add the label to the issue
    labels_url = f"{issue_url}/labels"
    payload = {"labels": [date_label]}
    response = requests.post(labels_url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        print(f"Added label {date_label} to issue #{issue_number}")
        return True
    else:
        print(f"Failed to add label to issue #{issue_number}: {response.status_code} - {response.text}")
        return False


def main():
    """Main function to process all issues and add date labels."""
    print("Starting date-based issue labeling process...")

    # Get GitHub token
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    # Set up GitHub API headers
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

    # Get repository information
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repository:
        print("Error: GITHUB_REPOSITORY environment variable must be in format 'owner/repo'")
        sys.exit(1)

    owner, repo = repository.split("/")
    print(f"Processing repository: {owner}/{repo}")

    # Fetch all issues (both open and closed)
    page = 1
    per_page = 100
    total_processed = 0
    total_labeled = 0

    while True:
        # Fetch issues from the API
        issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {"state": "all", "page": page, "per_page": per_page}

        print(f"Fetching page {page} of issues...")
        response = requests.get(issues_url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Failed to fetch issues: {response.status_code} - {response.text}")
            sys.exit(1)

        issues = response.json()

        if not issues:
            print(f"No more issues to process (page {page})")
            break

        # Process each issue
        for issue in issues:
            # Skip pull requests (they are returned as issues in the API)
            if "pull_request" in issue:
                print(f"Skipping PR #{issue['number']}")
                continue

            issue_number = issue["number"]
            created_at = issue["created_at"]

            print(f"Processing issue #{issue_number} (created: {created_at})...")
            total_processed += 1

            if label_issue_by_date(owner, repo, issue_number, created_at, headers):
                total_labeled += 1

        # Move to next page
        page += 1

        # Safety check to avoid infinite loops (configurable via env var)
        max_pages = int(os.environ.get("MAX_PAGES", "1000"))
        if page > max_pages:
            print(f"Reached page limit ({max_pages}), stopping")
            break

    print(f"\nCompleted! Processed {total_processed} issues, labeled {total_labeled} issues.")


if __name__ == "__main__":
    main()
