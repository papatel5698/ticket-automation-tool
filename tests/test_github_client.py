import pytest
from unittest.mock import patch, MagicMock
from src.github_client import (
    get_open_issues, get_issue, add_label, post_comment,
    create_issue, find_summary_issue,
)


def _mock_response(status_code=200, json_data=None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.text = ""
    mock.headers = {}
    mock.raise_for_status.return_value = None
    return mock


class TestGetOpenIssues:
    @patch("src.github_client.requests.get")
    def test_returns_issues(self, mock_get):
        issues = [
            {"number": 1, "title": "Bug 1"},
            {"number": 2, "title": "Bug 2"},
        ]
        mock_get.side_effect = [
            _mock_response(json_data=issues),
            _mock_response(json_data=[]),
        ]
        result = get_open_issues("owner/repo", "token123")
        assert len(result) == 2
        assert result[0]["number"] == 1

    @patch("src.github_client.requests.get")
    def test_filters_pull_requests(self, mock_get):
        issues = [
            {"number": 1, "title": "Issue"},
            {"number": 2, "title": "PR", "pull_request": {"url": "..."}},
        ]
        mock_get.side_effect = [
            _mock_response(json_data=issues),
            _mock_response(json_data=[]),
        ]
        result = get_open_issues("owner/repo", "token123")
        assert len(result) == 1
        assert result[0]["number"] == 1

    @patch("src.github_client.requests.get")
    def test_paginates(self, mock_get):
        page1 = [{"number": i, "title": f"Issue {i}"} for i in range(1, 101)]
        page2 = [{"number": 101, "title": "Issue 101"}]
        mock_get.side_effect = [
            _mock_response(json_data=page1),
            _mock_response(json_data=page2),
            _mock_response(json_data=[]),
        ]
        result = get_open_issues("owner/repo", "token123")
        assert len(result) == 101


class TestGetIssue:
    @patch("src.github_client.requests.get")
    def test_returns_issue(self, mock_get):
        issue = {"number": 5, "title": "Test Issue", "body": "Description"}
        mock_get.return_value = _mock_response(json_data=issue)
        result = get_issue("owner/repo", 5, "token123")
        assert result["number"] == 5
        assert result["title"] == "Test Issue"


class TestAddLabel:
    @patch("src.github_client.requests.post")
    def test_adds_label(self, mock_post):
        mock_post.return_value = _mock_response(json_data=[{"name": "stale"}])
        result = add_label("owner/repo", 1, "stale", "token123")
        assert mock_post.call_count == 2  # create label + add to issue

    @patch("src.github_client.requests.post")
    def test_handles_existing_label(self, mock_post):
        # First call (create label) fails, second (add label) succeeds
        error_resp = MagicMock()
        error_resp.status_code = 422
        error_resp.text = "already exists"
        error_resp.headers = {}
        error_resp.raise_for_status.side_effect = Exception("422")

        success_resp = _mock_response(json_data=[{"name": "stale"}])
        mock_post.side_effect = [error_resp, success_resp]
        result = add_label("owner/repo", 1, "stale", "token123")
        assert result == [{"name": "stale"}]


class TestPostComment:
    @patch("src.github_client.requests.post")
    def test_posts_comment(self, mock_post):
        comment = {"id": 1, "body": "Test comment"}
        mock_post.return_value = _mock_response(json_data=comment)
        result = post_comment("owner/repo", 1, "Test comment", "token123")
        assert result["body"] == "Test comment"


class TestCreateIssue:
    @patch("src.github_client.requests.post")
    def test_creates_issue(self, mock_post):
        issue = {"number": 10, "title": "New Issue"}
        mock_post.return_value = _mock_response(json_data=issue)
        result = create_issue("owner/repo", "New Issue", "Body", "token123")
        assert result["number"] == 10


class TestFindSummaryIssue:
    @patch("src.github_client.requests.post")
    @patch("src.github_client.requests.get")
    def test_finds_existing_summary(self, mock_get, mock_post):
        issues = [
            {"number": 5, "title": "Weekly Stale Ticket Summary"},
        ]
        mock_get.side_effect = [
            _mock_response(json_data=issues),
            _mock_response(json_data=[]),
        ]
        result = find_summary_issue("owner/repo", "token123")
        assert result == 5

    @patch("src.github_client.requests.post")
    @patch("src.github_client.requests.get")
    def test_creates_summary_if_missing(self, mock_get, mock_post):
        mock_get.side_effect = [
            _mock_response(json_data=[]),
        ]
        mock_post.return_value = _mock_response(
            json_data={"number": 21, "title": "Weekly Stale Ticket Summary"}
        )
        result = find_summary_issue("owner/repo", "token123")
        assert result == 21
