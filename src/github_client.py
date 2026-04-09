import requests
import time

API_BASE = "https://api.github.com"
MAX_RETRIES = 3
RETRY_DELAY = 2


def _headers(github_token):
    """Build request headers with authentication."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    return headers


def _request_with_retries(method, url, github_token, **kwargs):
    """Make an HTTP request with retry logic and rate limit handling."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = method(url, headers=_headers(github_token), **kwargs)

            # Handle rate limiting
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait_time = max(reset_time - int(time.time()), 1)
                if wait_time <= 60:
                    time.sleep(wait_time)
                    continue
                raise Exception(f"GitHub API rate limit exceeded. Resets in {wait_time}s.")

            resp.raise_for_status()
            return resp

        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise Exception(f"GitHub API request failed after {MAX_RETRIES} attempts: {e}")


def get_open_issues(repo, github_token=None):
    """Fetch all open issues with their metadata."""
    issues = []
    page = 1
    while True:
        url = f"{API_BASE}/repos/{repo}/issues"
        params = {"state": "open", "per_page": 100, "page": page}
        resp = _request_with_retries(requests.get, url, github_token, params=params)
        page_issues = resp.json()
        if not page_issues:
            break
        # Filter out pull requests (GitHub API returns PRs as issues too)
        for issue in page_issues:
            if "pull_request" not in issue:
                issues.append(issue)
        page += 1
    return issues


def get_issue(repo, issue_number, github_token=None):
    """Get a single issue's full details."""
    url = f"{API_BASE}/repos/{repo}/issues/{issue_number}"
    resp = _request_with_retries(requests.get, url, github_token)
    return resp.json()


def add_label(repo, issue_number, label, github_token=None):
    """Add a label to an issue. Creates the label if it doesn't exist."""
    # Try to create the label first (ignore 422 if it already exists)
    create_url = f"{API_BASE}/repos/{repo}/labels"
    try:
        _request_with_retries(
            requests.post, create_url, github_token,
            json={"name": label, "color": "ededed"}
        )
    except Exception:
        pass  # Label likely already exists

    # Add the label to the issue
    url = f"{API_BASE}/repos/{repo}/issues/{issue_number}/labels"
    resp = _request_with_retries(
        requests.post, url, github_token,
        json={"labels": [label]}
    )
    return resp.json()


def post_comment(repo, issue_number, body, github_token=None):
    """Post a markdown comment on an issue."""
    url = f"{API_BASE}/repos/{repo}/issues/{issue_number}/comments"
    resp = _request_with_retries(
        requests.post, url, github_token,
        json={"body": body}
    )
    return resp.json()


def create_issue(repo, title, body, github_token=None):
    """Create a new issue on the repository."""
    url = f"{API_BASE}/repos/{repo}/issues"
    resp = _request_with_retries(
        requests.post, url, github_token,
        json={"title": title, "body": body}
    )
    return resp.json()


def find_summary_issue(repo, github_token=None):
    """Find the dedicated summary issue, or create it if it doesn't exist."""
    summary_title = "Weekly Stale Ticket Summary"

    # Search for existing summary issue
    issues = get_open_issues(repo, github_token)
    for issue in issues:
        if issue["title"] == summary_title:
            return issue["number"]

    # Create the summary issue if not found
    body = (
        "This issue is used by the ticket-automation-tool to post weekly "
        "analysis summaries of stale tickets.\n\n"
        "Subscribe to this issue to receive notifications when new analyses are posted."
    )
    new_issue = create_issue(repo, summary_title, body, github_token)
    return new_issue["number"]
