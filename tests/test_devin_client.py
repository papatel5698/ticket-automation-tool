import pytest
from unittest.mock import patch, MagicMock
from src.devin_client import (
    create_analysis_session, create_automation_session,
    get_session_status, wait_for_session, parse_analysis_result,
    terminate_session,
)


def _mock_response(status_code=200, json_data=None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.raise_for_status.return_value = None
    return mock


class TestCreateAnalysisSession:
    @patch("src.devin_client.requests.post")
    def test_creates_session(self, mock_post):
        session = {"session_id": "abc123", "status_enum": "running"}
        mock_post.return_value = _mock_response(json_data=session)

        issue = {"number": 1, "title": "Test Bug", "body": "Description", "labels": []}
        result = create_analysis_session("token", issue, "owner/repo")

        assert result["session_id"] == "abc123"
        mock_post.assert_called_once()

    @patch("src.devin_client.requests.post")
    def test_includes_issue_info_in_prompt(self, mock_post):
        mock_post.return_value = _mock_response(
            json_data={"session_id": "abc123"}
        )
        issue = {
            "number": 5,
            "title": "Division bug",
            "body": "7/2 returns 3",
            "labels": [{"name": "bug"}],
        }
        create_analysis_session("token", issue, "owner/repo")
        call_args = mock_post.call_args
        json_body = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1]["json"]
        assert "Division bug" in json_body["prompt"]


class TestCreateAutomationSession:
    @patch("src.devin_client.requests.post")
    def test_creates_automation_session(self, mock_post):
        session = {"session_id": "def456"}
        mock_post.return_value = _mock_response(json_data=session)

        issue = {"number": 1, "title": "Fix bug", "body": "Crash on input"}
        result = create_automation_session("token", issue, "owner/repo")

        assert result["session_id"] == "def456"

    @patch("src.devin_client.requests.post")
    def test_includes_pr_format_in_prompt(self, mock_post):
        mock_post.return_value = _mock_response(
            json_data={"session_id": "def456"}
        )
        issue = {"number": 3, "title": "Fix", "body": "Bug"}
        create_automation_session("token", issue, "owner/repo")
        call_args = mock_post.call_args
        json_body = call_args[1].get("json") or call_args[1]["json"]
        assert "## What" in json_body["prompt"]
        assert "## Why" in json_body["prompt"]
        assert "## How" in json_body["prompt"]
        assert "Resolves #3" in json_body["prompt"]


class TestGetSessionStatus:
    @patch("src.devin_client.requests.get")
    def test_returns_status(self, mock_get):
        status = {"session_id": "abc123", "status_enum": "finished"}
        mock_get.return_value = _mock_response(json_data=status)
        result = get_session_status("token", "abc123")
        assert result["status_enum"] == "finished"


class TestWaitForSession:
    @patch("src.devin_client.time.sleep")
    @patch("src.devin_client.requests.get")
    def test_returns_on_finished(self, mock_get, mock_sleep):
        mock_get.return_value = _mock_response(
            json_data={"session_id": "abc", "status_enum": "finished"}
        )
        result = wait_for_session("token", "abc", timeout=30)
        assert result["status_enum"] == "finished"

    @patch("src.devin_client.time.sleep")
    @patch("src.devin_client.requests.get")
    def test_returns_on_blocked(self, mock_get, mock_sleep):
        mock_get.return_value = _mock_response(
            json_data={"session_id": "abc", "status_enum": "blocked"}
        )
        result = wait_for_session("token", "abc", timeout=30)
        assert result["status_enum"] == "blocked"

    @patch("src.devin_client.time.sleep")
    @patch("src.devin_client.requests.get")
    def test_returns_on_failed(self, mock_get, mock_sleep):
        mock_get.return_value = _mock_response(
            json_data={"session_id": "abc", "status_enum": "failed"}
        )
        result = wait_for_session("token", "abc", timeout=30)
        assert result["status_enum"] == "failed"

    @patch("src.devin_client.time.time")
    @patch("src.devin_client.time.sleep")
    @patch("src.devin_client.requests.get")
    def test_polls_until_complete(self, mock_get, mock_sleep, mock_time):
        mock_time.side_effect = [0, 5, 10, 15]
        mock_get.side_effect = [
            _mock_response(json_data={"status_enum": "running"}),
            _mock_response(json_data={"status_enum": "finished"}),
        ]
        result = wait_for_session("token", "abc", timeout=30, poll_interval=5)
        assert result["status_enum"] == "finished"

    @patch("src.devin_client.time.time")
    @patch("src.devin_client.time.sleep")
    @patch("src.devin_client.requests.get")
    def test_timeout_raises_error(self, mock_get, mock_sleep, mock_time):
        mock_time.side_effect = [0, 100, 200, 700]
        mock_get.return_value = _mock_response(
            json_data={"status_enum": "running"}
        )
        with pytest.raises(TimeoutError):
            wait_for_session("token", "abc", timeout=600, poll_interval=5)


class TestTerminateSession:
    @patch("src.devin_client.requests.delete")
    def test_terminates_session(self, mock_delete):
        mock_delete.return_value = _mock_response(
            json_data={"detail": "Session terminated successfully"}
        )
        result = terminate_session("token", "abc123")
        assert result["detail"] == "Session terminated successfully"
        mock_delete.assert_called_once()

    @patch("src.devin_client.requests.delete")
    def test_returns_none_on_failure(self, mock_delete):
        mock_delete.side_effect = Exception("API error")
        result = terminate_session("token", "abc123")
        assert result is None


class TestParseAnalysisResult:
    def test_parses_structured_output(self):
        result = {
            "structured_output": {
                "type": "bug",
                "action": "automate",
                "confidence": 95,
            }
        }
        parsed = parse_analysis_result(result)
        assert parsed["type"] == "bug"
        assert parsed["action"] == "automate"

    def test_parses_json_from_message(self):
        result = {
            "structured_output": {},
            "messages": [
                {"type": "user_message", "event_id": "1", "message": "Analyze this issue", "timestamp": "2024-01-01T00:00:00Z"},
                {"type": "agent_message", "event_id": "2", "message": 'Here is the analysis: {"type": "feature", "action": "engineer_review", "confidence": 80}', "timestamp": "2024-01-01T00:01:00Z"},
            ],
        }
        parsed = parse_analysis_result(result)
        assert parsed["type"] == "feature"
        assert parsed["action"] == "engineer_review"

    def test_returns_defaults_on_failure(self):
        result = {
            "structured_output": {},
            "messages": [
                {"type": "agent_message", "event_id": "1", "message": "no json here", "timestamp": "2024-01-01T00:00:00Z"},
            ],
        }
        parsed = parse_analysis_result(result)
        assert parsed["type"] == "unknown"
        assert parsed["action"] == "needs_more_info"
        assert parsed["confidence"] == 0

    def test_handles_empty_result(self):
        parsed = parse_analysis_result({})
        assert parsed["type"] == "unknown"

    def test_finds_json_in_earlier_message_when_last_has_none(self):
        result = {
            "messages": [
                {"type": "agent_message", "event_id": "1", "message": '{"type": "bug", "action": "automate", "confidence": 85}', "timestamp": "2024-01-01T00:00:00Z"},
                {"type": "agent_message", "event_id": "2", "message": "Done with analysis.", "timestamp": "2024-01-01T00:01:00Z"},
            ],
        }
        parsed = parse_analysis_result(result)
        assert parsed["type"] == "bug"
        assert parsed["action"] == "automate"
        assert parsed["confidence"] == 85
