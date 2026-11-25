"""Error and edge paths in the cache, analyzer and GitHub client (#46)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src import analyzer, cache, github_client
from src.models import TicketAnalysis

ISSUE = {"number": 1, "title": "Bug", "body": "It broke", "labels": []}
RESULT = {
    "type": "bug", "action": "automate", "action_reasoning": "Simple fix",
    "confidence": 90, "priority": "high", "complexity": "low",
    "complexity_reasoning": "Easy", "description": "Fix the bug",
}


def analysis(number=1, title="Bug"):
    return TicketAnalysis(issue_number=number, title=title, **RESULT)


# --- cache -------------------------------------------------------------------


def test_load_cache_treats_a_corrupt_file_as_empty(isolated_cache):
    isolated_cache.mkdir()
    (isolated_cache / "analysis_cache.json").write_text("{not json")
    assert cache.load_cache() == {}


def test_cached_analysis_round_trips():
    cache.cache_analysis(ISSUE, analysis())
    assert cache.get_cached_analysis(ISSUE) == analysis()


def test_editing_an_issue_invalidates_its_cache_entry():
    cache.cache_analysis(ISSUE, analysis())
    assert cache.get_cached_analysis({**ISSUE, "body": "It broke differently"}) is None


# --- analyzer ----------------------------------------------------------------


@pytest.fixture
def clients():
    with patch.object(analyzer, "github_client") as gh, \
         patch.object(analyzer, "devin_client") as devin, \
         patch.object(analyzer.time, "sleep") as sleep:
        gh.get_open_issues.return_value = [ISSUE, {**ISSUE, "number": 2, "title": "Other"}]
        devin.create_analysis_session.return_value = {"session_id": "s"}
        devin.wait_for_session.return_value = {"status_enum": "finished"}
        devin.parse_analysis_result.return_value = RESULT
        yield gh, devin, sleep


def test_full_analysis_reports_progress_and_staggers_sessions(clients):
    _, _, sleep = clients
    events = []
    analyzer.run_full_analysis("gh", "dv", "o/r",
                               progress_callback=lambda *a, **k: events.append(a[0]))

    assert events[0] == "start"
    assert events.count("session_creating") == 2
    assert events.count("session_waiting") == 2
    assert events.count("done") == 2
    sleep.assert_called_with(2)  # the second session starts 2s after the first


def test_full_analysis_uses_cached_results(clients):
    _, devin, _ = clients
    cache.cache_analysis(ISSUE, analysis())
    starts = []

    _, analyses, _, _ = analyzer.run_full_analysis(
        "gh", "dv", "o/r",
        progress_callback=lambda event, total, *a, **k: starts.append(k) if event == "start" else None)

    assert len(analyses) == 2
    assert devin.create_analysis_session.call_count == 1  # only the uncached issue
    assert starts == [{"cached_count": 1}]


def test_full_analysis_without_cache_reanalyzes_and_stores_nothing(clients):
    _, devin, _ = clients
    analyzer.run_full_analysis("gh", "dv", "o/r", use_cache=False)

    assert devin.create_analysis_session.call_count == 2
    assert cache.load_cache() == {}


def test_full_analysis_reports_a_failed_issue_and_keeps_the_rest(clients):
    _, devin, _ = clients
    devin.create_analysis_session.side_effect = [RuntimeError("Devin down"), {"session_id": "s"}]
    events = []

    _, analyses, _, _ = analyzer.run_full_analysis(
        "gh", "dv", "o/r", progress_callback=lambda *a, **k: events.append(a))

    assert len(analyses) == 1
    errors = [e for e in events if e[0] == "error"]
    assert len(errors) == 1 and "Devin down" in errors[0][4]


def test_full_analysis_warns_on_failure_without_a_callback(clients, capsys):
    _, devin, _ = clients
    devin.create_analysis_session.side_effect = RuntimeError("Devin down")
    analyzer.run_full_analysis("gh", "dv", "o/r")
    assert "Failed to analyze issue" in capsys.readouterr().out


def test_full_analysis_survives_a_failed_discussion_post(clients, capsys):
    gh, _, _ = clients
    gh.create_summary_discussion.side_effect = RuntimeError("Discussions disabled")
    cli_output, *_ = analyzer.run_full_analysis("gh", "dv", "o/r")
    assert "Tickets Summary" in cli_output
    assert "Failed to post summary" in capsys.readouterr().out


# --- GitHub client -----------------------------------------------------------


def response(status=200, text="", headers=None, json_data=None):
    resp = MagicMock(status_code=status, text=text, headers=headers or {})
    resp.json.return_value = json_data if json_data is not None else []
    return resp


@patch.object(github_client.time, "sleep")
def test_rate_limit_waits_and_retries_when_the_reset_is_soon(sleep):
    with patch.object(github_client.time, "time", return_value=1000), \
         patch.object(github_client.requests, "get", side_effect=[
             response(403, "API rate limit exceeded", {"X-RateLimit-Reset": "1010"}),
             response(json_data=[]),
         ]) as get:
        assert github_client.get_open_issues("o/r", "tok") == []
    sleep.assert_called_once_with(10)
    assert get.call_count == 2


def test_rate_limit_fails_fast_when_the_reset_is_far_off():
    with patch.object(github_client.time, "time", return_value=1000), \
         patch.object(github_client.requests, "get", return_value=response(
             403, "API rate limit exceeded", {"X-RateLimit-Reset": "5000"})):
        with pytest.raises(Exception, match="rate limit exceeded. Resets in 4000s"):
            github_client.get_open_issues("o/r", "tok")


@patch.object(github_client.time, "sleep")
def test_network_errors_are_retried_then_reported(sleep):
    with patch.object(github_client.requests, "get",
                      side_effect=requests.exceptions.ConnectionError("no route")) as get:
        with pytest.raises(Exception, match="failed after 3 attempts: no route"):
            github_client.get_open_issues("o/r", "tok")
    assert get.call_count == github_client.MAX_RETRIES
    assert [c.args[0] for c in sleep.call_args_list] == [2, 4]


def test_graphql_errors_are_raised():
    with patch.object(github_client.requests, "post",
                      return_value=response(json_data={"errors": [{"message": "bad query"}]})):
        with pytest.raises(Exception, match="GraphQL error"):
            github_client._graphql_request("query {}", "tok")


def test_missing_discussion_category_is_reported():
    data = {"data": {"repository": {"id": "R1", "discussionCategories": {
        "nodes": [{"id": "C1", "name": "Ideas"}]}}}}
    with patch.object(github_client.requests, "post", return_value=response(json_data=data)):
        with pytest.raises(Exception, match="'General' not found in o/r"):
            github_client.get_repo_discussion_category("o/r", "General", "tok")
