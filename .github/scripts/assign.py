#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

import requests


def main():
    print("Initiating process...")

    # Get GitHub
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    print("GitHub token acquired.")

    # Set up GitHub API headers
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    print("GitHub API headers set up.")

    # Get GitHub context from environment variables or event file
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    print(f"Event name: {event_name}")

    # Default values for repository
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    owner, repo = repository.split("/") if "/" in repository else ("", "")
    print(f"Repository: {repository}, Owner: {owner}, Repo: {repo}")

    # Initialize issue and comment data
    issue = None
    comment = None

    # Load event data if available
    if event_path and os.path.exists(event_path):
        print(f"Loading event data from: {event_path}")
        with open(event_path, "r") as f:
            event_data = json.load(f)
            if "issue" in event_data:
                issue = event_data["issue"]
                print(f"Issue detected: #{issue.get('number')}")
            if "comment" in event_data:
                comment = event_data["comment"]
                print(f"Comment detected from user: {comment.get('user', {}).get('login', '')}")

    print(f"Handling event: {event_name} in repository {repository}")

    # Keywords for assignment and unassignment
    assign_keywords = [
        "i am interested in contributing",
        "i am interested in doing this",
        "i can try fixing this",
        "work on this",
        "be assigned this",
        "assign me this",
        "assign it to me",
        "assign this to me",
        "assign to me",
        "/assign",
    ]
    unassign_keywords = ["/unassign"]

    # Process issue comments
    if event_name == "issue_comment" and issue and comment:
        print("Processing comment...")
        comment_body = comment.get("body", "").lower()

        # Check for unassign request
        is_unassign = any(keyword in comment_body for keyword in unassign_keywords)
        if is_unassign:
            user_login = comment.get("user", {}).get("login", "")
            issue_number = issue.get("number")
            print(f"Unassign request detected. Removing assignment of issue #{issue_number} from {user_login}")

            try:
                # Get issue details
                issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
                print(f"Fetching issue details from {issue_url}")
                issue_response = requests.get(issue_url, headers=headers)
                print(f"Issue details response status: {issue_response.status_code}")
                issue_data = issue_response.json()
                print("Issue details fetched.")

                # Check if issue has "assigned" label
                has_assigned_label = any(label.get("name") == "assigned" for label in issue_data.get("labels", []))
                print(f"'assigned' label present: {has_assigned_label}")

                if has_assigned_label:
                    # Remove assignee
                    assignees_url = f"{issue_url}/assignees"
                    print(f"Removing assignee {user_login} via {assignees_url}")
                    requests.delete(assignees_url, headers=headers, json={"assignees": [user_login]})
                    print("Assignee removed.")

                    # Remove "assigned" label
                    try:
                        label_url = f"{issue_url}/labels/assigned"
                        print(f"Removing 'assigned' label via {label_url}")
                        requests.delete(label_url, headers=headers)
                        print("'assigned' label removed.")
                    except Exception:
                        print("Label missing or already deleted.")

                    # Check for existing unassign comments
                    comments_url = f"{issue_url}/comments"
                    print(f"Fetching comments from {comments_url}")
                    comments_response = requests.get(comments_url, headers=headers)
                    comments_data = comments_response.json()
                    print("Comments fetched.")

                    has_unassign_comment = any(
                        "You have been unassigned. This task is now available for others." in c.get("body", "")
                        for c in comments_data
                    )
                    print(f"Unassign comment already exists: {has_unassign_comment}")

                    if not has_unassign_comment:
                        # Add unassign comment
                        unassign_msg = (
                            "You have been unassigned. This task is now available for others. "
                            "Type /assign if you'd like to take it again."
                        )
                        print("Posting unassign comment.")
                        requests.post(comments_url, headers=headers, json={"body": unassign_msg})
                        print("Unassign comment posted.")
                else:
                    print(f"Issue #{issue_number} lacks 'assigned' label, skipping unassignment.")
            except Exception as e:
                print(f"Failed to unassign issue #{issue_number}: {str(e)}")

        # Check for assign request
        is_assign = any(keyword in comment_body for keyword in assign_keywords)
        if is_assign:
            user_login = comment.get("user", {}).get("login", "")
            issue_number = issue.get("number")
            print(f"Assign request detected. Assigning issue #{issue_number} to {user_login}")

            try:
                # Define issue_url at the beginning of this block
                issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"

                # Get issue details to check if already assigned
                print(f"Fetching issue details from {issue_url}")
                issue_response = requests.get(issue_url, headers=headers)
                print(f"Issue details response status: {issue_response.status_code}")
                issue_data = issue_response.json()

                # Check if issue already has an assignee (implementing single assignee rule)
                current_assignee = issue_data.get("assignee")
                if current_assignee:
                    current_assignee_login = current_assignee.get("login")
                    print(f"Issue #{issue_number} already assigned to {current_assignee_login}")

                    # Don't allow a second person to be assigned
                    if current_assignee_login != user_login:
                        comment_body = (
                            f"@{user_login} This issue is already assigned to @{current_assignee_login}. "
                            f"Please wait until it becomes available or choose a different issue."
                        )
                        print(f"Rejecting assignment request from {user_login}")
                        requests.post(f"{issue_url}/comments", headers=headers, json={"body": comment_body})
                        return
                    else:
                        print(f"User {user_login} is already assigned to this issue. No action needed.")
                        return

                # Check if this is a "good first issue" and the user has existing PRs
                issue_labels = issue_data.get("labels", [])
                is_good_first_issue = any(label.get("name") == "good first issue" for label in issue_labels)

                if is_good_first_issue:
                    print(f"Issue #{issue_number} is labeled as 'good first issue', checking if user has existing PRs")

                    # Check if user has any PRs in the repository
                    search_url = "https://api.github.com/search/issues"
                    search_query = f"type:pr repo:{owner}/{repo} author:{user_login}"
                    search_params = {"q": search_query}
                    print(f"Searching PRs created by user with query: {search_query}")
                    search_response = requests.get(search_url, headers=headers, params=search_params)
                    print(f"Search response status: {search_response.status_code}")
                    search_data = search_response.json()

                    pr_count = search_data.get("total_count", 0)
                    print(f"User {user_login} has {pr_count} PRs in the repository")

                    if pr_count > 0:
                        # User has existing PRs, don't allow them to take a good first issue
                        comment_body = (
                            f"@{user_login} 'Good first issue' tasks are reserved for newcomers who haven't "
                            f"submitted PRs yet. Since you already have PRs in this repository, "
                            f"please choose a different issue to work on."
                        )
                        print(f"Rejecting 'good first issue' assignment for user with existing PRs: {user_login}")
                        requests.post(f"{issue_url}/comments", headers=headers, json={"body": comment_body})
                        return

                # Get user's open issues
                issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                params = {"state": "open", "assignee": user_login}
                print(f"Fetching open issues for user {user_login} from {issues_url} with params {params}")
                issues_response = requests.get(issues_url, headers=headers, params=params)
                print(f"Response status for open issues: {issues_response.status_code}")
                assigned_issues = issues_response.json()
                print(f"User {user_login} has {len(assigned_issues)} open assigned issues.")

                # Filter issues without open PRs
                issues_without_prs = []
                for assigned_issue in assigned_issues:
                    if assigned_issue.get("number") == issue_number:
                        continue

                    print(f"Checking for open PRs referencing issue #{assigned_issue.get('number')}")
                    # Search for PRs referencing this issue
                    search_url = "https://api.github.com/search/issues"
                    search_query = f"type:pr state:open repo:{owner}/{repo} {assigned_issue.get('number')} in:body"
                    search_params = {"q": search_query}
                    print(f"Searching PRs with query: {search_query}")
                    search_response = requests.get(search_url, headers=headers, params=search_params)
                    print(f"Search response status: {search_response.status_code}")
                    search_data = search_response.json()

                    if search_data.get("total_count", 0) == 0:
                        print(f"Issue #{assigned_issue.get('number')} lacks an open PR")
                        issues_without_prs.append(assigned_issue.get("number"))

                if issues_without_prs:
                    # User has uncompleted issues
                    issues_list = ", #".join(str(num) for num in issues_without_prs)
                    comment_body = (
                        f"You can't take this task yet. You still have uncompleted issues: "
                        f"#{issues_list}. Please complete them before requesting another."
                    )
                    print(f"User {user_login} blocked due to uncompleted issues: {issues_list}")
                    requests.post(f"{issue_url}/comments", headers=headers, json={"body": comment_body})
                    return

                # Assign the issue
                assignees_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/assignees"
                print(f"Assigning issue via {assignees_url}")
                assign_response = requests.post(assignees_url, headers=headers, json={"assignees": [user_login]})
                if assign_response.status_code >= 400:
                    print(f"Error assigning issue: {assign_response.status_code} - {assign_response.text}")
                    return
                else:
                    print(f"Issue #{issue_number} assigned to {user_login}")

                # Add "assigned" label
                labels_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/labels"
                print(f"Adding 'assigned' label via {labels_url}")
                label_response = requests.post(labels_url, headers=headers, json={"labels": ["assigned"]})
                if label_response.status_code >= 400:
                    print(f"Error adding label: {label_response.status_code} - {label_response.text}")
                else:
                    print(f"'assigned' label added to issue #{issue_number}")

                # Add assignment comment
                assignment_msg = (
                    f"Hey @{user_login}! You're now assigned to this issue. " f"Please finish your PR within 1 day."
                )
                print("Posting assignment comment.")
                comment_response = requests.post(
                    f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=headers,
                    json={"body": assignment_msg},
                )
                if comment_response.status_code >= 400:
                    print(f"Error posting comment: {comment_response.status_code} - {comment_response.text}")
                else:
                    print("Assignment comment posted successfully.")
            except Exception as e:
                print(f"Failed to assign issue #{issue_number}: {str(e)}")

    # Review inactive assignments
    print("Reviewing inactive assignments...")
    current_time = datetime.now()

    try:
        # Get open issues with assignees
        issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        print(f"Fetching open issues with assignees from {issues_url}")
        params = {"state": "open", "assignee": "*"}  # * means any assignee
        issues_response = requests.get(issues_url, headers=headers, params=params)
        print(f"Issues response status: {issues_response.status_code}")
        assigned_issues = issues_response.json()
        print(f"Found {len(assigned_issues)} open issues with assignees.")

        for issue in assigned_issues:
            issue_number = issue.get("number")
            issue_url = issue.get("url")
            assignee = issue.get("assignee", {}).get("login")

            if not assignee:
                print(f"Issue #{issue_number} has no assignee. Skipping.")
                continue

            print(f"Checking assignment age for issue #{issue_number} assigned to {assignee}")

            # Get issue timeline to find the assignment event
            timeline_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/timeline"
            timeline_headers = headers.copy()
            timeline_headers["Accept"] = "application/vnd.github.mockingbird-preview+json"
            print(f"Fetching timeline from {timeline_url}")
            timeline_response = requests.get(timeline_url, headers=timeline_headers)
            print(f"Timeline response status: {timeline_response.status_code}")
            timeline_events = timeline_response.json()

            # Find the most recent assignment event
            assignment_events = [
                event
                for event in timeline_events
                if event.get("event") == "assigned" and event.get("assignee", {}).get("login") == assignee
            ]

            if not assignment_events:
                print(f"No assignment events found for issue #{issue_number}. Skipping.")
                continue

            # Sort by created_at in descending order to get the most recent assignment
            assignment_events.sort(key=lambda x: x.get("created_at"), reverse=True)
            latest_assignment = assignment_events[0]
            assigned_at = datetime.strptime(latest_assignment.get("created_at"), "%Y-%m-%dT%H:%M:%SZ")
            days_since_assignment = (current_time - assigned_at).total_seconds() / 86400  # seconds in a day

            print(f"Issue #{issue_number} was assigned {days_since_assignment:.2f} days ago.")

            if days_since_assignment > 1:
                print(f"Issue #{issue_number} has exceeded 1 day since assignment, checking for linked PRs")

                # Check if this issue has any linked PRs before unassigning
                has_linked_pr = False

                # First check via GraphQL API for linked issues in the "Development" section
                try:
                    query = """
                        query($owner:String!, $repo:String!, $issue_number:Int!) {
                          repository(owner:$owner, name:$repo) {
                            issue(number:$issue_number) {
                              timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 10) {
                                nodes {
                                  ... on CrossReferencedEvent {
                                    source {
                                      ... on PullRequest {
                                        number
                                        state
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }
                    """

                    graphql_headers = headers.copy()
                    graphql_headers["Accept"] = "application/vnd.github.v4+json"
                    graphql_url = "https://api.github.com/graphql"

                    variables = {"owner": owner, "repo": repo, "issue_number": issue_number}

                    print(f"Checking for linked PRs via GraphQL for issue #{issue_number}")
                    graphql_response = requests.post(
                        graphql_url, headers=graphql_headers, json={"query": query, "variables": variables}
                    )

                    if graphql_response.status_code == 200:
                        graphql_data = graphql_response.json()
                        timeline_items = (
                            graphql_data.get("data", {})
                            .get("repository", {})
                            .get("issue", {})
                            .get("timelineItems", {})
                            .get("nodes", [])
                        )

                        for item in timeline_items:
                            source = item.get("source", {})
                            if source and "state" in source and source["state"] == "OPEN":
                                pr_number = source.get("number")
                                print(f"Found open PR #{pr_number} linked to issue #{issue_number}")
                                has_linked_pr = True
                                break
                except Exception as e:
                    print(f"Error checking for linked PRs via GraphQL: {str(e)}")

                # If no PRs found via GraphQL, try REST API fallback
                if not has_linked_pr:
                    try:
                        # Search for PRs referencing this issue
                        search_url = "https://api.github.com/search/issues"
                        search_query = f"type:pr state:open repo:{owner}/{repo} {issue_number} in:body"
                        search_params = {"q": search_query}
                        print(f"Searching PRs with REST API query: {search_query}")
                        search_response = requests.get(search_url, headers=headers, params=search_params)
                        search_data = search_response.json()

                        if search_data.get("total_count", 0) > 0:
                            pr_number = search_data.get("items", [])[0].get("number")
                            print(f"Found open PR #{pr_number} linked to issue #{issue_number} via REST API search")
                            has_linked_pr = True
                    except Exception as e:
                        print(f"Error checking for linked PRs via REST API: {str(e)}")

                # Only unassign if no linked PRs found
                if has_linked_pr:
                    print(f"Keeping assignment for issue #{issue_number} because it has linked open PR(s)")
                    continue
                print(
                    f"No linked PRs found, revoking assignment of issue #{issue_number} "
                    "due to exceeding 1 day since assignment"
                )

                # Check if issue has "assigned" label
                has_assigned_label = any(label.get("name") == "assigned" for label in issue.get("labels", []))
                print(f"'assigned' label present: {has_assigned_label}")

                if has_assigned_label:
                    # Remove assignee
                    assignees_url = f"{issue_url}/assignees"
                    print(f"Removing assignee {assignee} via {assignees_url}")
                    requests.delete(assignees_url, headers=headers, json={"assignees": [assignee]})
                    print("Assignee removed.")

                    # Remove "assigned" label
                    label_url = f"{issue_url}/labels/assigned"
                    print(f"Removing 'assigned' label via {label_url}")
                    requests.delete(label_url, headers=headers)
                    print("'assigned' label removed.")

                    # Add unassign comment
                    comments_url = f"{issue_url}/comments"
                    print(f"Posting unassign comment to {comments_url}")

                    unassign_message = (
                        f"⏳ @{assignee}, you have been unassigned due to 24+ hours of inactivity. "
                        f"This task is now available for reassignment."
                    )

                    requests.post(
                        comments_url,
                        headers=headers,
                        json={"body": unassign_message},
                    )
                    print("Unassign comment posted.")
                else:
                    print(f"Issue #{issue_number} lacks 'assigned' label, skipping revocation.")
    except Exception as e:
        print(f"Failed to process inactive assignments: {str(e)}")


if __name__ == "__main__":
    main()
