import requests
import time
import json

API_BASE = "https://api.devin.ai/v1"
MAX_RETRIES = 5
RETRY_DELAY = 2
DEFAULT_TIMEOUT = 600  # 10 minutes


def _headers(devin_token):
    """Build request headers with authentication."""
    return {
        "Authorization": f"Bearer {devin_token}",
        "Content-Type": "application/json",
    }


def _request_with_retries(method, url, devin_token, **kwargs):
    """Make an HTTP request with retry logic and 429 backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = method(url, headers=_headers(devin_token), **kwargs)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", RETRY_DELAY * (2 ** attempt)))
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
                continue
            raise Exception(f"Devin API request failed after {MAX_RETRIES} attempts: {e}")


def create_analysis_session(devin_token, issue_data, repo):
    """Create a Devin session that analyzes a ticket."""
    prompt = (
        f"Analyze the following GitHub issue from the repository {repo}.\n\n"
        f"Issue #{issue_data['number']}: {issue_data['title']}\n"
        f"Body: {issue_data.get('body', 'No description provided.')}\n"
        f"Labels: {', '.join(l['name'] for l in issue_data.get('labels', []))}\n\n"
        "Investigate this issue and the codebase, then respond with a JSON object "
        "containing the following fields:\n"
        "- type: one of 'bug', 'feature', 'cleanup'\n"
        "- action: one of 'automate' (Devin can fix this), 'engineer_review' "
        "(needs human review), 'needs_more_info' (insufficient information)\n"
        "- action_reasoning: explanation for the recommended action\n"
        "- confidence: 0-100 confidence score\n"
        "- priority: one of 'high', 'medium', 'low'\n"
        "- complexity: one of 'high', 'medium', 'low'\n"
        "- complexity_reasoning: explanation for the complexity score\n"
        "- description: a generated summary of the issue and recommended approach\n\n"
        "Return ONLY the JSON object, no other text."
    )

    url = f"{API_BASE}/sessions"
    data = {"prompt": prompt}
    resp = _request_with_retries(requests.post, url, devin_token, json=data)
    return resp.json()


def create_automation_session(devin_token, issue_data, repo):
    """Create a Devin session that resolves a ticket and opens a PR."""
    prompt = (
        f"Fix the following GitHub issue in the repository {repo}.\n\n"
        f"Issue #{issue_data['number']}: {issue_data['title']}\n"
        f"Body: {issue_data.get('body', 'No description provided.')}\n\n"
        "Steps:\n"
        "1. Investigate the issue and understand the root cause\n"
        "2. Fix the code\n"
        "3. Write or update tests to cover the fix\n"
        "4. Open a PR with a description following this format:\n\n"
        "## What\n"
        "[Description of what the issue was]\n\n"
        "## Why\n"
        "[Explanation of why it needed to be fixed]\n\n"
        "## How\n"
        "[Description of how it was fixed]\n\n"
        f"Resolves #{issue_data['number']}"
    )

    url = f"{API_BASE}/sessions"
    data = {"prompt": prompt}
    resp = _request_with_retries(requests.post, url, devin_token, json=data)
    return resp.json()


def get_session_status(devin_token, session_id):
    """Get the current status of a Devin session."""
    url = f"{API_BASE}/sessions/{session_id}"
    resp = _request_with_retries(requests.get, url, devin_token)
    return resp.json()


def wait_for_session(devin_token, session_id, timeout=DEFAULT_TIMEOUT, poll_interval=10):
    """Poll until a Devin session completes or times out."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = get_session_status(devin_token, session_id)
        state = status.get("status_enum", "")
        if state in ("finished", "stopped", "failed"):
            return status
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Devin session {session_id} did not complete within {timeout} seconds."
    )


def parse_analysis_result(session_result):
    """Extract structured analysis from Devin's response."""
    structured_output = session_result.get("structured_output", {})

    # Try to parse from structured output first
    if structured_output:
        return structured_output

    # Fall back to parsing the last message from the conversation
    last_message = session_result.get("last_message", "")
    try:
        # Try to find JSON in the message
        start = last_message.find("{")
        end = last_message.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(last_message[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "type": "unknown",
        "action": "needs_more_info",
        "action_reasoning": "Could not parse Devin's analysis response.",
        "confidence": 0,
        "priority": "low",
        "complexity": "unknown",
        "complexity_reasoning": "Could not determine complexity.",
        "description": last_message or "No analysis available.",
    }
